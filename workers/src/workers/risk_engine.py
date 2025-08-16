"""
Risk engine worker.

This module defines the `RiskEngine` class and a global instance used by
the execution service to perform pre‑trade and post‑trade risk checks.
The engine enforces a variety of configurable limits such as maximum
notional per order, maximum orders per minute, maximum concurrent open
orders, and price band thresholds.  It also tracks exposure and daily PnL
and triggers a kill switch when a daily loss limit is exceeded.
"""

from __future__ import annotations

import asyncio
import collections
import logging
import os
import time
from collections import deque, defaultdict
from dataclasses import dataclass
from typing import Dict

logger = logging.getLogger(__name__)


@dataclass
class OrderRequest:
    product_id: str
    side: str  # 'buy' or 'sell'
    size: float
    price: float


class RiskEngine:
    """Encapsulates risk management state and logic."""

    def __init__(self) -> None:
        # Configuration from environment variables
        self.max_order_notional: float = float(os.environ.get("MAX_ORDER_NOTIONAL", "1000"))
        self.max_orders_per_minute: int = int(os.environ.get("MAX_ORDERS_PER_MINUTE", "30"))
        self.max_open_orders: int = int(os.environ.get("MAX_OPEN_ORDERS", "50"))
        self.price_band_pct: float = float(os.environ.get("PRICE_BAND_PCT", "2.5"))
        self.daily_max_loss: float = float(os.environ.get("DAILY_MAX_LOSS", "10000"))
        allowed = os.environ.get("ALLOWED_MARKETS", "BTC-USD,ETH-USD,SOL-USD")
        self.allowed_markets = [p.strip() for p in allowed.split(",") if p.strip()]

        # State
        self.open_orders: int = 0
        # timestamps (seconds) of recent order submissions for rate limiting
        self.order_times: deque[float] = deque()
        # Exposure per product (notional): positive means long, negative short
        self.exposure: Dict[str, float] = defaultdict(float)
        # Daily PnL
        self.pnl: float = 0.0
        # Kill switch flag
        self.kill_switch: bool = False
        # Last reset timestamp (midnight boundaries) for daily metrics
        self._last_reset_day = time.gmtime().tm_yday

    def _reset_daily_metrics_if_needed(self) -> None:
        today = time.gmtime().tm_yday
        if today != self._last_reset_day:
            logger.info("Resetting daily metrics (PnL, order counts)")
            self.pnl = 0.0
            self.order_times.clear()
            self.open_orders = 0
            self.kill_switch = False
            self._last_reset_day = today

    def pre_trade_check(self, order: OrderRequest, reference_price: float | None = None) -> bool:
        """Return True if the order passes all pre‑trade checks.

        :param order: OrderRequest containing product_id, side, size, price.
        :param reference_price: Last observed market price to check price band; if None, band check is skipped.
        """
        self._reset_daily_metrics_if_needed()
        if self.kill_switch:
            logger.warning("Kill switch active: rejecting order")
            return False
        # Allowed market
        if order.product_id not in self.allowed_markets:
            logger.warning("Market %s not in allowed list %s", order.product_id, self.allowed_markets)
            return False
        # Notional check
        notional = order.size * order.price
        if notional > self.max_order_notional:
            logger.warning("Order notional %.2f exceeds limit %.2f", notional, self.max_order_notional)
            return False
        # Orders per minute check
        now = time.time()
        while self.order_times and now - self.order_times[0] > 60:
            self.order_times.popleft()
        if len(self.order_times) >= self.max_orders_per_minute:
            logger.warning("Rate limit: %d orders in the last minute (max %d)", len(self.order_times), self.max_orders_per_minute)
            return False
        # Open orders count
        if self.open_orders >= self.max_open_orders:
            logger.warning("Max open orders reached (%d >= %d)", self.open_orders, self.max_open_orders)
            return False
        # Price band check
        if reference_price:
            band = self.price_band_pct / 100.0
            lower = reference_price * (1 - band)
            upper = reference_price * (1 + band)
            if not (lower <= order.price <= upper):
                logger.warning(
                    "Price %.2f outside allowed band %.2f%% of reference %.2f (range %.2f..%.2f)",
                    order.price,
                    self.price_band_pct,
                    reference_price,
                    lower,
                    upper,
                )
                return False
        return True

    def register_order(self, order: OrderRequest) -> None:
        """Record a new order to update state for rate limiting and exposure."""
        now = time.time()
        self.order_times.append(now)
        self.open_orders += 1
        notional = order.size * order.price
        sign = 1.0 if order.side.lower() == 'buy' else -1.0
        self.exposure[order.product_id] += sign * notional

    def settle_order(self) -> None:
        """Indicate that an open order has been filled or cancelled."""
        if self.open_orders > 0:
            self.open_orders -= 1

    def post_trade(self, realized_pnl: float) -> None:
        """Update PnL after a trade and check daily loss limit."""
        self.pnl += realized_pnl
        if self.pnl < -self.daily_max_loss:
            logger.error(
                "Daily loss %.2f exceeds limit %.2f — activating kill switch", -self.pnl, self.daily_max_loss
            )
            self.kill_switch = True


# Global instance used by execution and other modules
risk_engine = RiskEngine()


async def start() -> None:
    """Background task to reset daily metrics at midnight and log risk state."""
    logger.info("Risk engine started")
    while True:
        # Reset daily metrics if the day has changed
        risk_engine._reset_daily_metrics_if_needed()
        # Sleep for a minute
        await asyncio.sleep(60)
