"""
Execution service responsible for validating and submitting orders.

Orders are enqueued by strategies or external modules via the
``submit`` method.  The service processes queued orders sequentially,
performing a risk check using ``RiskService`` and retrieving the
reference price from ``PriceCache``.  If an order passes risk checks,
it generates a unique client order ID, registers the order with the
risk engine and submits it to Coinbase via an HTTP client.  The HTTP
client must implement an asynchronous ``create_order`` method that
accepts the required fields and returns a response.

Orders are currently submitted as limit orders with GTC time in force.
Additional parameters (e.g., post‑only, TIF) may be added later.

Note: this is a skeleton service; integration with order settlement
events from the user channel is pending.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any, Dict, Optional

from .price_cache import PriceCache
from .risk_service import RiskService


class ExecutionService:
    """Service managing the order submission pipeline."""

    def __init__(
        self,
        *,
        price_cache: PriceCache,
        risk_service: RiskService,
        http_client: Any,
        event_bus: Optional[Any] = None,
        event_store: Optional[Any] = None,
        paper_trading: bool = False,
    ) -> None:
        self.price_cache = price_cache
        self.risk_service = risk_service
        self.http_client = http_client
        self.event_bus = event_bus
        self.event_store = event_store
        self.paper_trading = paper_trading
        self.order_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self._running = False

    async def submit(self, product_id: str, side: str, size: float, price: float) -> None:
        """Queue a new order for processing."""
        await self.order_queue.put({
            "product_id": product_id,
            "side": side,
            "size": size,
            "price": price,
        })

    async def _process_order(self, order: Dict[str, Any]) -> None:
        product_id = order["product_id"]
        side = order["side"]
        size = order["size"]
        price = order["price"]
        # Reference price from cache
        reference_price = await self.price_cache.get_price(product_id)
        ok = await self.risk_service.pre_trade_check(
            product_id, side, size, price, reference_price
        )
        if not ok:
            # Drop the order silently; could log or notify
            return
        # Generate idempotent client order ID
        client_order_id = uuid.uuid4().hex
        await self.risk_service.register_order(
            client_order_id, product_id, side, size, price
        )
        # Publish order submission event
        submission_event = {
            "client_order_id": client_order_id,
            "product_id": product_id,
            "side": side,
            "size": size,
            "price": price,
        }
        if self.event_bus:
            await self.event_bus.publish("order_submitted", submission_event)
        if self.event_store:
            try:
                await self.event_store.log("order_submitted", submission_event)
            except Exception:
                pass
        # Build payload
        payload: Dict[str, Any] = {
            "product_id": product_id,
            "side": side.lower(),
            "order_type": "limit",
            "time_in_force": "gtc",
            "size": size,
            "price": price,
            "client_order_id": client_order_id,
        }
        # Include retail_portfolio_id if needed
        auth_mode = os.getenv("ACCOUNT_AUTH_MODE", "api_keys").lower()
        if auth_mode == "oauth":
            portfolio_id = os.getenv("COINBASE_RETAIL_PORTFOLIO_ID")
            if portfolio_id:
                payload["retail_portfolio_id"] = portfolio_id
        # Submit via HTTP client unless paper trading
        if self.paper_trading or os.getenv("DRY_RUN", "true").lower() == "true":
            # Simulate immediate fill; update risk engine
            await self.risk_service.settle_order(client_order_id, price, size)
            fill_event = {
                "client_order_id": client_order_id,
                "product_id": product_id,
                "side": side,
                "size": size,
                "price": price,
            }
            if self.event_bus:
                await self.event_bus.publish("order_filled", fill_event)
            if self.event_store:
                try:
                    await self.event_store.log("order_filled", fill_event)
                except Exception:
                    pass
            return
        try:
            response = await self.http_client.create_order(payload)
            # Response handling could be added here (e.g. log order ID)
        except Exception:
            # On failure we could requeue or cancel; for now we drop
            pass

    async def run(self) -> None:
        """Continuously process orders from the queue."""
        self._running = True
        while self._running:
            order = await self.order_queue.get()
            try:
                await self._process_order(order)
            except Exception:
                # Ensure we do not crash on unexpected errors
                pass
            finally:
                self.order_queue.task_done()
