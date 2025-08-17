"""Tests for the RiskService."""

import os
import sys

import pytest

# Adjust sys.path so that tests can import the workers modules without installing the package.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workers", "src")))

from workers.services.risk_service import RiskService


@pytest.mark.asyncio
async def test_pre_trade_check_allows_small_order(monkeypatch) -> None:
    # Set environment variables for a permissive configuration
    monkeypatch.setenv("MAX_ORDER_NOTIONAL", "10000")
    monkeypatch.setenv("MAX_ORDERS_PER_MINUTE", "10")
    monkeypatch.setenv("MAX_OPEN_ORDERS", "10")
    monkeypatch.setenv("PRICE_BAND_PCT", "5")
    monkeypatch.setenv("SLIPPAGE_PCT", "1")
    monkeypatch.setenv("DAILY_MAX_LOSS", "100000")
    rs = RiskService()
    ok = await rs.pre_trade_check(
        product_id="BTC-USD",
        side="buy",
        size=0.1,
        price=10000.0,
        reference_price=10000.0,
    )
    assert ok is True
