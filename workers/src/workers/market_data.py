"""
Market data ingestion worker.

This module connects to the Coinbase Advanced Trade WebSocket API, subscribes
to ticker, candle, and level2 data for the configured trading pairs, and
publishes those events onto an internal event bus.  It also manages JWT
refreshing, heartbeat pings, and reconnection with exponential backoff.
"""

import asyncio
import json
import logging
import os
from typing import Any, List

import websockets
from tenacity import retry, stop_after_attempt, wait_exponential

try:
    # Import the Coinbase SDK wrapper for market data; may be unavailable offline
    from .clients.sdk_market_data import MarketDataClient  # type: ignore
except Exception:
    MarketDataClient = None  # type: ignore

# Import normalisation helper for ticker events
from .models_events import TickerEvent  # type: ignore
from .services.publishers import publish_ticker  # type: ignore

logger = logging.getLogger(__name__)

# Maintain a simple in‑memory cache of the most recent ticker price per product.
# This dictionary is updated whenever a ticker message is received from the
# WebSocket and can be queried by other modules (e.g., execution) for
# reference prices.  Keys are product IDs (e.g., "BTC-USD"), values are floats.
last_prices: dict[str, float] = {}

# Optional event bus used for publishing ticker events.  Tests or the
# worker orchestrator may assign an object with an asynchronous
# ``publish(event_type, data)`` coroutine to this variable.  When set,
# the market data worker will publish normalised ticker events via
# ``event_type='ticker'``.  A normalised event is a dictionary
# containing at least ``product_id`` (str) and ``price`` (float).
event_bus: Any | None = None


def get_last_price(product_id: str) -> float | None:
    """Return the last observed price for a product, or None if unknown."""
    return last_prices.get(product_id)


async def _subscribe(ws: websockets.WebSocketClientProtocol, products: List[str]) -> None:
    """Send a subscription message to the WebSocket with the desired channels."""
    sub_msg = {
        "type": "subscribe",
        "product_ids": products,
        "channels": ["ticker", "level2", "heartbeat", "candles"],
    }
    await ws.send(json.dumps(sub_msg))


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=30))
async def start() -> None:
    """Entry point for the market data worker.

    When ``USE_OFFICIAL_SDK=true`` and the Coinbase SDK is installed, the
    worker will initialise a ``MarketDataClient`` and await ticker events
    via the SDK.  Otherwise it falls back to connecting directly to the
    Coinbase WebSocket endpoint.  The worker updates the global
    ``last_prices`` dict for reference by other services.
    """
    products = os.environ.get("ALLOWED_MARKETS", "BTC-USD").split(",")
    use_sdk = os.getenv("USE_OFFICIAL_SDK", "false").lower() in {"true", "1", "yes"}
    if use_sdk and MarketDataClient is not None:
        # Attempt to load API credentials via secrets manager or environment
        api_key = os.getenv("COINBASE_API_KEY", "")
        api_secret = os.getenv("COINBASE_API_SECRET", "")
        passphrase = os.getenv("COINBASE_PASSPHRASE", "")
        sandbox = os.getenv("USE_STATIC_SANDBOX", "true").lower() in {
            "true",
            "1",
            "yes",
        }
        # Pass the event_bus into the SDK client so that it can publish
        client = MarketDataClient(
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase or None,
            sandbox=sandbox,
            products=products,
            event_bus=event_bus,
        )
        logger.info("Market data worker using Coinbase SDK wrapper (sandbox=%s)", sandbox)
        async for msg in client.stream():
            # Normalise and publish via helper; skip invalid messages
            try:
                norm: TickerEvent = await publish_ticker(event_bus, msg)
            except Exception:
                continue
            # Update the last price cache
            product_id = norm["product_id"]
            price_f = norm["price"]
            last_prices[product_id] = price_f
        return
    # Fallback: connect directly to websocket
    uri = "wss://advanced-trade-ws.coinbase.com"
    logger.info("Connecting to Coinbase WebSocket at %s", uri)
    async for ws in websockets.connect(uri):
        try:
            await _subscribe(ws, products)

            # Send periodic pings to keep the connection alive
            async def heartbeat() -> None:
                while True:
                    try:
                        await ws.send(json.dumps({"type": "ping"}))
                    except Exception as e:
                        logger.debug("Heartbeat error: %s", e)
                        break
                    await asyncio.sleep(30)

            hb_task = asyncio.create_task(heartbeat())
            async for message in ws:
                # Parse message JSON and update last_prices for ticker events
                try:
                    data = json.loads(message)
                except Exception as e:
                    logger.debug("Failed to parse WS message: %s", e)
                    continue
                msg_type = data.get("type")
                if msg_type == "ticker":
                    # Normalise and publish via helper; update price cache
                    try:
                        norm2: TickerEvent = await publish_ticker(event_bus, data)
                    except Exception:
                        continue
                    product_id = norm2["product_id"]
                    last_prices[product_id] = norm2["price"]
                logger.debug("Received message from WS: %s", data)
        except Exception as exc:
            logger.warning("WebSocket connection error: %s", exc)
            await asyncio.sleep(5)
            continue
        finally:
            await ws.close()
            if "hb_task" in locals():
                hb_task.cancel()
