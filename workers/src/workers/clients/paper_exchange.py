"""
Paper exchange client for simulation.

This client is used in paper trading mode to simulate order creation
without interacting with the Coinbase Advanced Trade REST API.  It
immediately returns a synthetic response indicating that the order has
been filled.  No matching engine logic is implemented; orders are
assumed to execute at the submitted limit price.  If you wish to
simulate slippage, latency, or partial fills, extend this class
accordingly.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Dict, Any


class PaperExchangeClient:
    """Simulate order submission and return a fake fill response."""

    def __init__(self) -> None:
        # Track a simple ledger of submitted orders (id -> payload)
        self.orders: Dict[str, Dict[str, Any]] = {}

    async def create_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Pretend to create an order and return a fake success response.

        :param payload: The order payload that would be sent to the REST API.
        :return: A dictionary mimicking a minimal REST response.
        """
        # Simulate network latency
        await asyncio.sleep(0.1)
        order_id = str(uuid.uuid4())
        self.orders[order_id] = payload
        # Extract some fields for the response
        product_id = payload.get("product_id")
        side = payload.get("side")
        cfg = payload.get("order_configuration", {})
        limit_cfg = cfg.get("limit_limit_gtc", {})
        size = limit_cfg.get("base_size")
        price = limit_cfg.get("limit_price")
        return {
            "id": order_id,
            "product_id": product_id,
            "side": side,
            "price": price,
            "size": size,
            "status": "filled",
            "paper": True,
        }