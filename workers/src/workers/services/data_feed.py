"""
Data feed service for subscribing to Coinbase Advanced Trade WebSocket
market data and updating the price cache accordingly.  This service
handles automatic reconnection, heartbeat pings and jittered backoff
to comply with the exchange requirements (subscribe within 5 seconds
and send heartbeats to keep the connection alive).  Only ticker
messages are processed; other message types are ignored.

Usage:

    price_cache = PriceCache()
    feed = DataFeedService(price_cache)
    asyncio.create_task(feed.run())
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import time
from typing import Any, List, Optional

import websockets

from .price_cache import PriceCache


class DataFeedService:
    """Subscribe to tickers for allowed markets, update prices and publish events.

    Optionally records prices in a risk service for volatility tracking.  The
    risk service must implement a ``record_price(product_id, price)`` coroutine.
    """

    def __init__(
        self,
        price_cache: PriceCache,
        event_bus: Optional[Any] = None,
        risk_service: Optional[Any] = None,
        event_store: Optional[Any] = None,
    ) -> None:
        """Initialize the data feed.

        Args:
            price_cache: Shared cache for latest prices.
            event_bus: Optional event bus to publish ticker events.
            risk_service: Optional risk service used to record prices for volatility calculations.
            event_store: Optional event store used to persist raw market data events.
        """
        self.price_cache = price_cache
        self.event_bus = event_bus
        self.risk_service = risk_service
        self.event_store = event_store
        self.ws_url = os.getenv("COINBASE_WS_URL", "wss://advanced-trade-ws.coinbase.com")
        markets_env = os.getenv("ALLOWED_MARKETS", "BTC-USD,ETH-USD")
        self.products: List[str] = [p.strip() for p in markets_env.split(",") if p.strip()]
        self._reconnect_delay = 1.0
        self._running = False

    async def _subscribe_message(self) -> dict:
        """Construct the subscribe message for tickers."""
        return {
            "type": "subscribe",
            "product_ids": self.products,
            "channels": ["ticker"],
        }

    async def _heartbeat(self, ws: websockets.WebSocketClientProtocol) -> None:
        """Send periodic heartbeats to keep the connection alive."""
        try:
            while self._running:
                await ws.ping()
                await asyncio.sleep(30)
        except Exception:
            # Let outer loop handle reconnection
            pass

    async def run(self) -> None:
        """Run the WebSocket feed; reconnect on failures."""
        self._running = True
        while self._running:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    # Send subscribe within 5 seconds per exchange rules
                    sub_msg = await self._subscribe_message()
                    await ws.send(json.dumps(sub_msg))
                    # Start heartbeat task
                    hb_task = asyncio.create_task(self._heartbeat(ws))
                    async for message in ws:
                        try:
                            data = json.loads(message)
                        except Exception:
                            continue
                        if data.get("type") == "ticker":
                            product = data.get("product_id") or data.get("productId")
                            price_str = data.get("price") or data.get("last_trade_price")
                            try:
                                price = float(price_str)
                            except (TypeError, ValueError):
                                continue
                            if product:
                                # Update price cache
                                await self.price_cache.update_price(product, price)
                                # Record price for volatility tracking
                                if self.risk_service:
                                    try:
                                        await self.risk_service.record_price(product, price)
                                    except Exception:
                                        pass
                                # Persist event to event store
                                if self.event_store:
                                    try:
                                        await self.event_store.log(
                                            "market_data",
                                            {
                                                "product_id": product,
                                                "price": price,
                                                "timestamp": data.get("time")
                                                or data.get("ts")
                                                or time.time(),
                                            },
                                        )
                                    except Exception:
                                        pass
                                # Publish ticker event to event bus
                                if self.event_bus:
                                    await self.event_bus.publish(
                                        "ticker",
                                        {
                                            "product_id": product,
                                            "price": price,
                                            "timestamp": data.get("time")
                                            or data.get("ts")
                                            or time.time(),
                                        },
                                    )
            except Exception:
                # Exponential backoff with jitter
                await asyncio.sleep(self._reconnect_delay + random.random())
                self._reconnect_delay = min(self._reconnect_delay * 2, 60)
            finally:
                # Cancel heartbeat
                # Avoid leaving orphaned tasks
                if "hb_task" in locals():
                    hb_task.cancel()
                    try:
                        await hb_task
                    except Exception:
                        pass
