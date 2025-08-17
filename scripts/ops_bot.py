"""
Slack Ops Bot
=============

This script implements a Slack bot that operators can use to query
important metrics from the trading platform and receive real‑time
alerts.  It uses the ``slack_bolt`` library for handling events and
commands.  To enable the bot, provide the necessary Slack credentials
(bot token, signing secret, and optionally socket mode token) via
environment variables or a secrets manager.  The bot implements the
following commands:

* ``/exposure`` – Fetches current exposures per product by scraping the
  Prometheus metrics endpoint (``atlas_exposure``) and replies with
  a formatted list.  Requires ``METRICS_URL`` (default
  ``http://localhost:9108/metrics``) to be reachable.
* ``/pnl`` – Fetches the current daily PnL and kill switch status
  (``atlas_daily_pnl`` and ``atlas_kill_switch``) and replies with a
  summary.
* ``/status`` – Combines exposures, daily PnL, open orders and kill
  switch into a single report.

In addition to slash commands, if Redis is configured (``REDIS_HOST``/
``REDIS_PORT``) the bot subscribes to the ``pnl_update`` channel via
Redis and automatically posts alerts to Slack when the kill switch
engages or when daily PnL crosses a negative threshold (configured via
``ALERT_PNL_THRESHOLD``).

Before running this script, ensure ``slack_bolt``, ``requests``, and
``redis`` are installed.  The script assumes it is run in an
environment alongside the worker services (so that the metrics endpoint
and Redis bus are reachable).

Note: This script is intentionally simplified and should be extended
to handle authentication, error handling, and concurrency as needed.
"""

from __future__ import annotations

import os
import re
import threading
from typing import Any, Dict, Optional

try:
    import requests  # type: ignore[import]
except ImportError:
    raise SystemExit(
        "The requests library is required for ops_bot. Please install with `pip install requests`"
    )

try:
    import redis  # type: ignore[import]
except ImportError:
    redis = None  # type: ignore

try:
    from slack_bolt import App
    from slack_bolt.adapter.socket_mode import SocketModeHandler
except ImportError:
    raise SystemExit(
        "slack_bolt library not installed. Please install with `pip install slack_bolt`"
    )


def parse_metrics(metrics_text: str) -> Dict[str, Any]:
    """Parse a Prometheus metrics text into a dictionary of values."""
    exposures: Dict[str, float] = {}
    open_orders = 0
    kill_switch = False
    daily_pnl: Optional[float] = None
    lines = metrics_text.split("\n")
    exp_re = re.compile(r"atlas_exposure\{product=\"([^\"]+)\"\} ([0-9eE+\-.]+)")
    for line in lines:
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
        else:
            m = exp_re.match(line)
            if m:
                exposures[m.group(1)] = float(m.group(2))
    return {
        "exposures": exposures,
        "open_orders": open_orders,
        "kill_switch": kill_switch,
        "daily_pnl": daily_pnl,
    }


def fetch_metrics() -> Dict[str, Any]:
    metrics_url = os.getenv("METRICS_URL", "http://localhost:9108/metrics")
    try:
        resp = requests.get(metrics_url, timeout=5)
        if resp.status_code == 200:
            return parse_metrics(resp.text)
    except Exception:
        pass
    return {}


def create_app() -> App:
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    signing_secret = os.getenv("SLACK_SIGNING_SECRET")
    app_token = os.getenv("SLACK_APP_TOKEN")
    if not bot_token or not signing_secret or not app_token:
        raise RuntimeError("Slack bot token, app token and signing secret must be set")
    app = App(token=bot_token, signing_secret=signing_secret)

    @app.command("/exposure")
    def handle_exposure(ack, respond):
        ack()
        data = fetch_metrics()
        exposures = data.get("exposures", {})
        if not exposures:
            respond("No exposure data available.")
            return
        lines = [f"{symbol}: {notional:.2f}" for symbol, notional in exposures.items()]
        respond("Current exposures:\n" + "\n".join(lines))

    @app.command("/pnl")
    def handle_pnl(ack, respond):
        ack()
        data = fetch_metrics()
        daily_pnl = data.get("daily_pnl")
        kill_switch = data.get("kill_switch")
        if daily_pnl is None:
            respond("No PnL data available.")
            return
        status = "🚫 Kill switch engaged" if kill_switch else "✅ Trading enabled"
        respond(f"Daily PnL: {daily_pnl:.2f}\nStatus: {status}")

    @app.command("/status")
    def handle_status(ack, respond):
        ack()
        data = fetch_metrics()
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
        respond("\n".join(lines))

    return app


def start_redis_listener(app: App) -> None:
    """Start a background thread to listen for Redis PnL updates and post alerts."""
    if redis is None:
        return
    redis_host = os.getenv("REDIS_HOST")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    channel = "pnl_update"
    alert_threshold = float(os.getenv("ALERT_PNL_THRESHOLD", "0"))
    try:
        r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        pubsub = r.pubsub()
        pubsub.subscribe(channel)
    except Exception:
        return

    def listen():
        for message in pubsub.listen():
            if message and message.get("type") == "message":
                try:
                    import json

                    data = json.loads(message.get("data"))
                except Exception:
                    continue
                kill_switch = data.get("kill_switch")
                daily_pnl = data.get("daily_pnl")
                if kill_switch:
                    text = (
                        f"⚠️ Kill switch engaged! Daily PnL: {daily_pnl:.2f}"
                        if daily_pnl is not None
                        else "⚠️ Kill switch engaged!"
                    )
                    app.client.chat_postMessage(
                        channel=os.getenv("SLACK_ALERT_CHANNEL", os.getenv("SLACK_CHANNEL_ID", "")),
                        text=text,
                    )
                elif alert_threshold and daily_pnl is not None and (-daily_pnl) >= alert_threshold:
                    text = (
                        f"🔻 PnL alert: Daily PnL = {daily_pnl:.2f} (threshold {alert_threshold})"
                    )
                    app.client.chat_postMessage(
                        channel=os.getenv("SLACK_ALERT_CHANNEL", os.getenv("SLACK_CHANNEL_ID", "")),
                        text=text,
                    )

    thread = threading.Thread(target=listen, daemon=True)
    thread.start()


def main() -> None:
    app = create_app()
    # Start Redis listener for alerts
    start_redis_listener(app)
    handler = SocketModeHandler(app, app_token=os.getenv("SLACK_APP_TOKEN"))
    handler.start()


if __name__ == "__main__":
    main()
