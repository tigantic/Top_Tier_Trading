"""SMA Crossover Strategy
=======================

This strategy implements a simple moving‑average (SMA) crossover system.
It maintains a rolling window of the most recent prices for each
product and computes the mean.  When the current price crosses above
the moving average and the strategy is not already long, it buys.  When
the price crosses below the moving average and the strategy is not
already short, it sells.  Otherwise it holds.

Configuration
-------------

* ``SMA_WINDOW`` – the number of historical prices to include in the
  moving average (default ``20``).
* ``STRATEGY_SIZE`` – the order size used for trades (shared with
  other strategies; default ``0.001``).

To enable this strategy, include
``workers.src.workers.strategies.sma_strategy.SmaStrategy`` in the
``STRATEGIES`` environment variable.  For example::

    STRATEGIES=workers.src.workers.strategies.sma_strategy.SmaStrategy

Limitations
-----------

* This strategy operates on a per‑product basis but shares the same
  window length across all products.
* It ignores transaction costs, slippage and fees.
* The moving average resets if the process restarts; there is no
  persistence of historical prices.
"""

from __future__ import annotations

import os
from collections import defaultdict, deque
from typing import Dict, Tuple

from .base import BaseStrategy


class SmaStrategy(BaseStrategy):
    """A simple moving‑average crossover strategy."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Window length for the moving average
        self.window = int(os.getenv("SMA_WINDOW", "20"))
        if self.window <= 0:
            self.window = 1
        # Per‑product price history
        self.prices: Dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=self.window))
        # Per‑product previous price and MA to detect crossings
        self.prev_state: Dict[str, Tuple[float | None, float | None]] = defaultdict(
            lambda: (None, None)
        )
        # Trade size
        self.size = float(os.getenv("STRATEGY_SIZE", "0.001"))

    async def run(self) -> None:
        """Subscribe to ticker events and trade on SMA crossovers."""
        if self.event_bus is None:
            raise RuntimeError("SmaStrategy requires an event bus")
        # Track position per product: -1 short, 0 flat, 1 long
        positions: Dict[str, int] = defaultdict(int)
        async for event in self.event_bus.subscribe("ticker"):
            # Extract price and product id
            try:
                price = float(event.get("price"))
                product_id = str(event.get("product_id"))
            except Exception:
                continue
            # Update price history
            history = self.prices[product_id]
            history.append(price)
            if len(history) < self.window:
                # Not enough data to compute moving average yet
                self.prev_state[product_id] = (price, price)
                continue
            # Compute current SMA
            sma = sum(history) / float(len(history))
            prev_price, prev_sma = self.prev_state[product_id]
            # Determine crossover: price crossing above or below SMA
            cross_up = False
            cross_down = False
            if prev_price is not None and prev_sma is not None:
                # Cross above: previously below or equal and now above
                if prev_price <= prev_sma and price > sma:
                    cross_up = True
                # Cross below: previously above or equal and now below
                if prev_price >= prev_sma and price < sma:
                    cross_down = True
            # Record current state for next iteration
            self.prev_state[product_id] = (price, sma)
            # Execute trades based on crossover and current position
            position = positions[product_id]
            # Go long on cross up
            if cross_up and position <= 0:
                await self.execution_service.submit_order(
                    product_id=product_id,
                    side="buy",
                    size=self.size,
                    price=price,
                )
                positions[product_id] = 1
            # Go short on cross down
            elif cross_down and position >= 0:
                await self.execution_service.submit_order(
                    product_id=product_id,
                    side="sell",
                    size=self.size,
                    price=price,
                )
                positions[product_id] = -1
            # Otherwise hold; no position change
