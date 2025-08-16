"""
LR Strategy
===========

This strategy implements a simple machine‑learning driven trading rule
using logistic regression.  It observes a rolling window of recent
prices and attempts to predict whether the next price will increase
or decrease.  When the predicted probability of an up move exceeds
``buy_threshold``, the strategy submits a buy order; when the
predicted probability of a down move exceeds ``sell_threshold``, it
submits a sell order.  The model is retrained on each new data
point to adapt to changing market conditions.

Requirements
------------

This strategy depends on scikit‑learn (`sklearn`).  Ensure that
``scikit-learn`` is installed in your Python environment and
added to ``pyproject.toml``.  If the import fails, the strategy
will be skipped.

Usage
-----

Add the fully qualified class name to the ``STRATEGIES``
environment variable:

.. code-block:: bash

    export STRATEGIES="workers.src.workers.strategies.lr_strategy.LRStrategy"

You can tune the rolling window size and probability thresholds via
environment variables:

* ``LR_WINDOW`` – Number of recent prices to use for training (default: 50)
* ``LR_BUY_THRESHOLD`` – Probability threshold for buys (default: 0.55)
* ``LR_SELL_THRESHOLD`` – Probability threshold for sells (default: 0.55)
"""

from __future__ import annotations

import os
import asyncio
from collections import deque
from typing import Any, Deque, Optional

try:
    import numpy as np  # type: ignore
    from sklearn.linear_model import LogisticRegression  # type: ignore
except ImportError:
    # Skip strategy if sklearn or numpy is not installed
    np = None  # type: ignore
    LogisticRegression = None  # type: ignore

from ..services.price_cache import PriceCache
from ..services.event_bus import EventBus
from ..services.execution_service import ExecutionService
from ..services.risk_service import RiskService
from .base import BaseStrategy


class LRStrategy(BaseStrategy):
    """Logistic regression strategy for directional trading."""

    def __init__(
        self,
        price_cache: PriceCache,
        execution_service: ExecutionService,
        event_bus: EventBus,
        risk_service: Optional[RiskService] = None,
        *,
        window: Optional[int] = None,
        buy_threshold: Optional[float] = None,
        sell_threshold: Optional[float] = None,
    ) -> None:
        super().__init__(price_cache, execution_service, event_bus, risk_service)
        # Configuration from environment with sensible defaults
        self.window = window or int(os.getenv("LR_WINDOW", 50))
        self.buy_threshold = buy_threshold or float(os.getenv("LR_BUY_THRESHOLD", 0.55))
        self.sell_threshold = sell_threshold or float(os.getenv("LR_SELL_THRESHOLD", 0.55))
        self._prices: Deque[float] = deque(maxlen=self.window + 1)
        self._model: Optional[LogisticRegression] = None
        self._product: str = os.getenv("STRATEGY_PRODUCT", "BTC-USD")

        if np is None or LogisticRegression is None:
            raise RuntimeError(
                "scikit-learn and numpy are required for LRStrategy. Install them to enable this strategy."
            )

    async def run(self) -> None:
        # Subscribe to ticker events for the configured product
        ticker_channel = "ticker"
        async for event in self.event_bus.subscribe(ticker_channel):
            product = event.get("product_id")
            price = event.get("price")
            if product != self._product or price is None:
                continue
            # Append price to history
            self._prices.append(float(price))
            if len(self._prices) <= self.window:
                continue  # need enough data to form features
            # Prepare training data: features are returns over the window; label is whether price increased
            prices = list(self._prices)
            returns = np.diff(prices) / prices[:-1]
            # Features: returns except last; label: last return > 0
            X_train = returns[:-1].reshape(-1, 1)
            y_train = (returns[1:] > 0).astype(int)
            # Train logistic regression model
            self._model = LogisticRegression()
            try:
                self._model.fit(X_train, y_train)
            except Exception:
                continue
            # Use the last window to predict next movement
            last_return = returns[-1].reshape(1, -1)
            try:
                prob_up = float(self._model.predict_proba(last_return)[0][1])
            except Exception:
                continue
            # Determine trade signal
            # Check risk service to get current exposure and avoid stacking positions
            if prob_up >= self.buy_threshold:
                # Submit a buy order of fixed size
                size = float(os.getenv("LR_TRADE_SIZE", 0.001))
                await self.execution_service.submit_order(
                    product_id=self._product,
                    side="buy",
                    size=size,
                    limit_price=float(price),
                )
            elif 1 - prob_up >= self.sell_threshold:
                size = float(os.getenv("LR_TRADE_SIZE", 0.001))
                await self.execution_service.submit_order(
                    product_id=self._product,
                    side="sell",
                    size=size,
                    limit_price=float(price),
                )