"""
LstmStrategy
============

This module defines a simple scaffold for an LSTM-based trading strategy.
It inherits from ``BaseStrategy`` and consumes price events via the
EventBus.  The strategy maintains an internal sliding window of recent
prices and uses a lightweight LSTM model to predict the next price
movement.  When the predicted return exceeds a configurable threshold,
the strategy submits a buy or sell order accordingly.

Important:
  * This implementation is for demonstration only; a real strategy
    would involve training the LSTM on historical data and saving the
    model parameters to disk.
  * Requires the ``torch`` and ``torchvision`` libraries.  To enable
    this strategy, add ``torch>=2.1.0`` to ``pyproject.toml`` and
    ensure the dependencies are installed.
  * The strategy uses a very small network and random initial
    weights; therefore its predictions will be essentially random
    unless trained.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from typing import List, Optional

try:
    import torch
    import torch.nn as nn
except ImportError:
    torch = None  # type: ignore

from .base import BaseStrategy


class SimpleLSTM(nn.Module):  # type: ignore[valid-type]
    def __init__(self, input_size: int = 1, hidden_size: int = 16, num_layers: int = 1) -> None:
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:  # type: ignore[valid-type]
        out, _ = self.lstm(x)
        out = self.fc(out[:, -1, :])
        return out


class LstmStrategy(BaseStrategy):
    """A toy LSTM-based momentum strategy."""

    window_size = 20
    threshold = 0.001  # 0.1% predicted move

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Deque to store latest closing prices
        self.prices: deque[float] = deque(maxlen=self.window_size)
        self.model: Optional[SimpleLSTM] = None
        if torch is not None:
            self.model = SimpleLSTM()
        else:
            logging.warning(
                "torch is not installed; LstmStrategy will act as a random strategy"
            )

    async def run(self) -> None:
        """Main loop for the strategy."""
        if self.event_bus is None:
            logging.error("No event bus provided; cannot run strategy")
            return
        async for event in self.event_bus.subscribe("ticker"):
            price: float = event.get("price")
            product_id: str = event.get("product_id")
            if price is None or product_id is None:
                continue
            self.prices.append(price)
            if len(self.prices) < self.window_size:
                continue
            # Prepare input tensor
            if torch is None or self.model is None:
                # Fallback: randomly trade with small probability
                import random
                if random.random() < 0.01:
                    await self.execution_service.submit_order(
                        product_id=product_id,
                        side="buy" if random.random() < 0.5 else "sell",
                        size=0.001,
                        price=price,
                    )
                continue
            with torch.no_grad():
                seq = torch.tensor(list(self.prices), dtype=torch.float32).view(1, -1, 1)
                pred = self.model(seq).item()
            # Compare predicted price to current price
            pct_change = (pred - price) / price
            if pct_change > self.threshold:
                # Predicting price increase → buy
                await self.execution_service.submit_order(
                    product_id=product_id,
                    side="buy",
                    size=0.001,
                    price=price,
                )
            elif pct_change < -self.threshold:
                # Predicting price drop → sell
                await self.execution_service.submit_order(
                    product_id=product_id,
                    side="sell",
                    size=0.001,
                    price=price,
                )