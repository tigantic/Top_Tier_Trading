"""Async Slack Ops Bot
======================

This script provides an asynchronous implementation of the Ops bot
using the Slack Bolt ``AsyncApp``.  It interacts with the platform
via Prometheus metrics and the Redis event bus to deliver real‑time
insights and alerts.  Secrets (Slack tokens and signing secret) are
loaded via the default secrets manager, allowing seamless integration
with environment variables, files or external secret stores.

Commands
--------

* ``/exposure`` – Fetch current exposures per product by querying the
  Prometheus metrics endpoint.  Requires ``METRICS_URL``.
* ``/pnl`` – Report daily PnL and kill switch status.
* ``/status`` – Summarise exposures, PnL, open orders and kill switch.

Alerts
------

If Redis is configured (``REDIS_HOST``/``REDIS_PORT``) and
``ALERT_ENABLE=true``, the bot subscribes to the ``pnl_update`` channel
and posts alerts when the kill switch engages or when daily PnL
falls below ``ALERT_PNL_THRESHOLD``.  Alerts are sent to
``SLACK_ALERT_CHANNEL`` (or ``SLACK_CHANNEL_ID`` as a fallback).

Dependencies
------------

* ``slack_bolt`` – Slack Bolt SDK for the asynchronous app.
* ``aiohttp`` – for non‑blocking HTTP requests to Prometheus.
* ``redis.asyncio`` – for subscribing to Redis channels asynchronously.

Install missing dependencies with::

    pip install slack_bolt aiohttp redis

Run the bot with::

    python ops_bot_async.py

"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from typing import Dict, Any, Optional, Set

try:
    from slack_bolt.async_app import AsyncApp  # type: ignore
    from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler  # type: ignore
except ImportError:
    raise SystemExit(
        "slack_bolt library is required for ops_bot_async. Please install with `pip install slack_bolt`"
    )

try:
    import aiohttp  # type: ignore
except ImportError:
    raise SystemExit("aiohttp is required for ops_bot_async. Please install with `pip install aiohttp`")

try:
    import redis.asyncio as aioredis  # type: ignore
except ImportError:
    aioredis = None  # type: ignore

from workers.src.workers.secrets_manager import get_default_secrets_manager  # type: ignore

try:
    from aiohttp import web  # type: ignore
except Exception:
    web = None  # type: ignore


async def fetch_metrics() -> Dict[str, Any]:
    """Fetch Prometheus metrics and return exposures, open orders, kill switch and PnL."""
    metrics_url = os.getenv("METRICS_URL", "http://localhost:9108/metrics")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(metrics_url, timeout=5) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    return parse_metrics(text)
    except Exception:
        pass
    return {}


def parse_metrics(metrics_text: str) -> Dict[str, Any]:
    """Parse Prometheus metrics into a structured dict."""
    exposures: Dict[str, float] = {}
    open_orders = 0
    kill_switch = False
    daily_pnl: Optional[float] = None
    for line in metrics_text.split("\n"):
        if line.startswith("atlas_open_orders"):
            parts = line.split(" ")
            if len(parts) >= 2:
                try:
                    open_orders = int(float(parts[1]))
                except Exception:
                    pass
        elif line.startswith("atlas_kill_switch"):
            parts = line.split(" ")
            if len(parts) >= 2:
                try:
                    kill_switch = float(parts[1]) == 1.0
                except Exception:
                    pass
        elif line.startswith("atlas_daily_pnl"):
            parts = line.split(" ")
            if len(parts) >= 2:
                try:
                    daily_pnl = float(parts[1])
                except Exception:
                    pass
        elif line.startswith("atlas_exposure"):
            # Format: atlas_exposure{product="BTC-USD"} value
            try:
                prefix, val = line.split("}")
                label_part = prefix.split("{")[1]
                # product="BTC-USD"
                product_label = label_part.split("=")[1]
                product = product_label.strip('"')
                exposures[product] = float(val.strip())
            except Exception:
                continue
    return {
        "exposures": exposures,
        "open_orders": open_orders,
        "kill_switch": kill_switch,
        "daily_pnl": daily_pnl,
    }


async def redis_listener(app: AsyncApp) -> None:
    """Listen for PnL updates on Redis and post alerts to Slack."""
    if aioredis is None:
        return
    if os.getenv("ALERT_ENABLE", "false").lower() not in {"true", "1", "yes"}:
        return
    host = os.getenv("REDIS_HOST") or "localhost"
    port = int(os.getenv("REDIS_PORT", "6379"))
    alert_threshold = float(os.getenv("ALERT_PNL_THRESHOLD", "0"))
    channel_name = "pnl_update"
    try:
        redis = aioredis.Redis(host=host, port=port, decode_responses=True)
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel_name)
    except Exception:
        return
    alert_channel = os.getenv("SLACK_ALERT_CHANNEL") or os.getenv("SLACK_CHANNEL_ID") or ""
    # Deduplication TTL cache: maps message text to expiry timestamp.  Messages
    # remain in the cache for ``ALERT_DEDUP_TTL`` seconds to prevent duplicates.
    dedup_cache: Dict[str, float] = {}
    expiry_seconds: float = float(os.getenv("ALERT_DEDUP_TTL", "60"))
    async for message in pubsub.listen():
        if message is None or message.get("type") != "message":
            continue
        try:
            data = json.loads(message.get("data"))
        except Exception:
            continue
        kill_switch = data.get("kill_switch")
        daily_pnl = data.get("daily_pnl")
        text: Optional[str] = None
        if kill_switch:
            text = (
                f"⚠️ Kill switch engaged! Daily PnL: {daily_pnl:.2f}" if daily_pnl is not None else "⚠️ Kill switch engaged!"
            )
        elif daily_pnl is not None and alert_threshold and (-daily_pnl) >= alert_threshold:
            text = f"🔻 PnL alert: Daily PnL = {daily_pnl:.2f} (threshold {alert_threshold})"
        if text and alert_channel:
            now_ts = time.time()
            # Evict expired entries from dedup cache
            expired = [msg for msg, ts in dedup_cache.items() if now_ts > ts]
            for msg in expired:
                dedup_cache.pop(msg, None)
            if text in dedup_cache:
                continue
            # Generate a correlation ID for logging and traceability
            correlation_id = uuid.uuid4().hex
            max_attempts = 3
            delay = 1.0
            for attempt in range(max_attempts):
                try:
                    await app.client.chat_postMessage(
                        channel=alert_channel,
                        text=f"{text} (corr_id={correlation_id})",
                    )
                    dedup_cache[text] = now_ts + expiry_seconds
                    break
                except Exception:
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay)
                        delay *= 2
                    else:
                        # Log failure after retries
                        print(
                            f"Failed to send alert after {max_attempts} attempts (corr_id={correlation_id})"
                        )
                        break


async def create_async_app() -> AsyncApp:
    """Instantiate an AsyncApp with secrets loaded from the secrets manager."""
    secrets = get_default_secrets_manager()
    bot_token = secrets.get_secret("SLACK_BOT_TOKEN") or os.getenv("SLACK_BOT_TOKEN")
    signing_secret = secrets.get_secret("SLACK_SIGNING_SECRET") or os.getenv("SLACK_SIGNING_SECRET")
    app_token = secrets.get_secret("SLACK_APP_TOKEN") or os.getenv("SLACK_APP_TOKEN")
    if not (bot_token and signing_secret and app_token):
        raise RuntimeError("Slack credentials must be provided via secrets manager or environment")
    app = AsyncApp(token=bot_token, signing_secret=signing_secret)

    @app.command("/exposure")
    async def handle_exposure(ack, body, respond):  # type: ignore[no-untyped-def]
        await ack()
        data = await fetch_metrics()
        exposures = data.get("exposures", {})
        if not exposures:
            await respond("No exposure data available.")
            return
        lines = [f"{symbol}: {notional:.2f}" for symbol, notional in exposures.items()]
        await respond("Current exposures:\n" + "\n".join(lines))

    @app.command("/pnl")
    async def handle_pnl(ack, body, respond):  # type: ignore[no-untyped-def]
        await ack()
        data = await fetch_metrics()
        daily_pnl = data.get("daily_pnl")
        kill_switch = data.get("kill_switch")
        if daily_pnl is None:
            await respond("No PnL data available.")
            return
        status = "🚫 Kill switch engaged" if kill_switch else "✅ Trading enabled"
        await respond(f"Daily PnL: {daily_pnl:.2f}\nStatus: {status}")

    @app.command("/status")
    async def handle_status(ack, body, respond):  # type: ignore[no-untyped-def]
        await ack()
        data = await fetch_metrics()
        exposures = data.get("exposures", {})
        daily_pnl = data.get("daily_pnl")
        open_orders = data.get("open_orders")
        kill_switch = data.get("kill_switch")
        lines = []
        if exposures:
            lines.append("*Exposures*:")
            for symbol, notional in exposures.items():
                lines.append(f"• {symbol}: {notional:.2f}")
        if daily_pnl is not None:
            lines.append(f"*Daily PnL*: {daily_pnl:.2f}")
        if open_orders is not None:
            lines.append(f"*Open Orders*: {open_orders}")
        lines.append(f"*Kill Switch*: {'ON' if kill_switch else 'OFF'}")
        await respond("\n".join(lines))
    return app, app_token


async def main() -> None:
    app, app_token = await create_async_app()
    # Launch Redis listener concurrently if enabled
    redis_task = asyncio.create_task(redis_listener(app))
    # Launch health endpoint if aiohttp.web is available
    health_task: Optional[asyncio.Task] = None
    if web is not None:
        async def start_health_server() -> None:
            async def health(request: web.Request) -> web.Response:  # type: ignore
                # Readiness: attempt to parse metrics (may return empty dict) and return OK
                try:
                    data = await fetch_metrics()
                    status = "ok" if data else "no-data"
                except Exception:
                    status = "error"
                return web.json_response({"status": status})
            health_app = web.Application()
            health_app.router.add_get("/healthz", health)
            runner = web.AppRunner(health_app)
            await runner.setup()
            site = web.TCPSite(runner, host="0.0.0.0", port=int(os.getenv("HEALTH_PORT", "8080")))
            await site.start()
            # Keep running until cancelled
            try:
                while True:
                    await asyncio.sleep(3600)
            except asyncio.CancelledError:
                await runner.cleanup()
        health_task = asyncio.create_task(start_health_server())
    handler = AsyncSocketModeHandler(app, app_token)
    try:
        await handler.start_async()
    finally:
        redis_task.cancel()
        if health_task:
            health_task.cancel()
        try:
            await redis_task
        except Exception:
            pass
        if health_task:
            try:
                await health_task
            except Exception:
                pass


if __name__ == "__main__":
    asyncio.run(main())