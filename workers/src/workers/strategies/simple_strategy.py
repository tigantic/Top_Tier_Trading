"""
A simple momentum strategy.

This strategy monitors the last price of each allowed product and
computes the percentage change relative to the previous observed price.
If the price rises above a configurable positive threshold, it triggers a
BUY; if it falls below a negative threshold, it triggers a SELL.  The
order size and thresholds are set via environment variables.

All orders are routed through the execution engine's `submit_order()`
function and are therefore subject to the risk engine's pre‑trade checks
and DRY_RUN settings.  This makes it safe to run in paper mode.

Environment variables:

* ALLOWED_MARKETS: comma‑separated list of products (default: "BTC-USD")
* STRATEGY_POLL_INTERVAL: seconds between price checks (default: 10)
* STRATEGY_PRICE_DELTA_PCT: percentage change threshold to trigger trades
  (default: 0.2 means 0.2% change)
* STRATEGY_SIZE: order size in base currency (default: 0.001)

This strategy is intentionally naive and serves as a starting point for
more sophisticated alpha modules.  In production you would implement
signal generation based on technical indicators, machine learning, or
other market analyses.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Dict, Optional

from ..execution import submit_order
from ..market_data import get_last_price
from ..risk_engine import OrderRequest

logger = logging.getLogger(__name__)


async def start() -> None:
    """Run the simple momentum strategy loop."""
    products = [
        p.strip() for p in os.environ.get("ALLOWED_MARKETS", "BTC-USD").split(",") if p.strip()
    ]
    poll_interval = int(os.environ.get("STRATEGY_POLL_INTERVAL", "10"))
    threshold_pct = float(os.environ.get("STRATEGY_PRICE_DELTA_PCT", "0.2")) / 100.0
    size = float(os.environ.get("STRATEGY_SIZE", "0.001"))
    # Track last observed prices per product
    last_seen: Dict[str, float] = {}
    logger.info(
        "Simple strategy started for products %s with interval %ds and threshold %.3f%%",
        products,
        poll_interval,
        threshold_pct * 100,
    )
    while True:
        for product in products:
            price: Optional[float] = get_last_price(product)
            if price is None:
                # skip if no market data yet
                continue
            prev = last_seen.get(product)
            if prev is not None and prev > 0:
                change = (price - prev) / prev
                if change > threshold_pct:
                    # momentum up: buy
                    order = OrderRequest(product_id=product, side="buy", size=size, price=price)
                    try:
                        await submit_order(order)
                        logger.info(
                            "Generated BUY order for %s: size=%.6f price=%.2f change=%.3f%%",
                            product,
                            size,
                            price,
                            change * 100,
                        )
                    except Exception as exc:
                        logger.error("Error submitting BUY order: %s", exc)
                elif change < -threshold_pct:
                    # momentum down: sell
                    order = OrderRequest(product_id=product, side="sell", size=size, price=price)
                    try:
                        await submit_order(order)
                        logger.info(
                            "Generated SELL order for %s: size=%.6f price=%.2f change=%.3f%%",
                            product,
                            size,
                            price,
                            change * 100,
                        )
                    except Exception as exc:
                        logger.error("Error submitting SELL order: %s", exc)
            # Update last seen price
            last_seen[product] = price
        await asyncio.sleep(poll_interval)
