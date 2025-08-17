"""Tests for the simple moving‑average crossover strategy.

This module exercises the ``SmaStrategy`` by simulating a sequence of
ticker events that produce moving‑average crossovers.  It verifies
that buy orders are submitted when the price crosses above the
moving average and sell orders are submitted when the price crosses
below.
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any, List

import pytest

# Adjust sys.path so that tests can import the workers modules without installing the package.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workers", "src")))

from workers.services.event_bus import EventBus  # type: ignore
from workers.strategies.sma_strategy import SmaStrategy  # type: ignore


class DummyExecutionService:
    """Simple stub for capturing submitted orders."""

    def __init__(self) -> None:
        self.orders: List[dict] = []

    async def submit_order(self, **kwargs: Any) -> None:
        self.orders.append(kwargs)


@pytest.mark.asyncio
async def test_sma_strategy_crossovers(monkeypatch) -> None:
    """SmaStrategy should trigger buy then sell on crossover events."""
    # Configure a small SMA window and trade size for testing
    monkeypatch.setenv("SMA_WINDOW", "3")
    monkeypatch.setenv("STRATEGY_SIZE", "0.001")
    bus = EventBus()
    exec_service = DummyExecutionService()
    # Instantiate strategy; price_cache is unused by this strategy
    sma = SmaStrategy(event_bus=bus, price_cache=None, execution_service=exec_service)
    # Run strategy loop in background
    task = asyncio.create_task(sma.run())
    # Price sequence: 10, 9, 8 build the moving average; 12 crosses above MA (buy); 5 crosses below (sell)
    prices = [10.0, 9.0, 8.0, 12.0, 5.0]
    for price in prices:
        await bus.publish("ticker", {"price": price, "product_id": "BTC-USD"})
    # Allow some time for strategy to process
    await asyncio.sleep(0.2)
    task.cancel()
    # We expect two orders: buy then sell
    orders = exec_service.orders
    assert len(orders) == 2
    assert orders[0]["side"] == "buy"
    assert orders[1]["side"] == "sell"
