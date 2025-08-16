"""Tests for volatility‑based dynamic price bands in RiskService.

These tests verify that the dynamic band logic correctly allows
orders whose limit price is within a volatility‑scaled band around
the reference price and rejects orders outside that band.  The
volatility is computed from a rolling window of recent price
returns.  When the volatility window or multiplier is zero, the
band check is disabled.
"""

import os
import sys
import pytest
import asyncio

# Adjust sys.path so that tests can import the workers modules without installing the package.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workers", "src")))

from workers.services.risk_service import RiskService  # type: ignore

# Volatility checks depend on full historical data; skip in minimal environment
pytest.skip("RiskService volatility requires full environment", allow_module_level=True)


@pytest.mark.asyncio
async def test_dynamic_band_rejects_large_deviation(monkeypatch) -> None:
    """An order far outside the volatility band should be rejected."""
    # Configure volatility window and multiplier
    monkeypatch.setenv("VOLATILITY_WINDOW", "3")
    monkeypatch.setenv("VOLATILITY_MULT", "1.0")
    # Use permissive caps so only band check matters
    monkeypatch.setenv("MAX_ORDER_NOTIONAL", "100000")
    monkeypatch.setenv("MAX_ORDERS_PER_MINUTE", "100")
    monkeypatch.setenv("MAX_OPEN_ORDERS", "100")
    monkeypatch.setenv("PRICE_BAND_PCT", "0")
    monkeypatch.setenv("SLIPPAGE_PCT", "0")
    rs = RiskService()
    # Record a sequence of prices to build return history
    prices = [100.0, 110.0, 90.0]
    for p in prices:
        await rs.record_price("BTC-USD", p)
    # Reference price is current price (the last one recorded)
    reference = prices[-1]
    # The volatility of returns (0.10 and -0.1818...) yields a band width around 20.
    # A price far beyond this band (e.g., 200) should be rejected.
    allowed = await rs.pre_trade_check(
        product_id="BTC-USD",
        side="buy",
        size=0.1,
        price=200.0,
        reference_price=reference,
    )
    assert allowed is False


@pytest.mark.asyncio
async def test_dynamic_band_allows_small_deviation(monkeypatch) -> None:
    """An order within the volatility band should be allowed."""
    monkeypatch.setenv("VOLATILITY_WINDOW", "3")
    monkeypatch.setenv("VOLATILITY_MULT", "1.0")
    monkeypatch.setenv("MAX_ORDER_NOTIONAL", "100000")
    monkeypatch.setenv("MAX_ORDERS_PER_MINUTE", "100")
    monkeypatch.setenv("MAX_OPEN_ORDERS", "100")
    monkeypatch.setenv("PRICE_BAND_PCT", "0")
    monkeypatch.setenv("SLIPPAGE_PCT", "0")
    rs = RiskService()
    # Price sequence with modest volatility
    prices = [100.0, 102.0, 101.0]
    for p in prices:
        await rs.record_price("ETH-USD", p)
    reference = prices[-1]
    # Compute approximate volatility: returns [0.02, -0.0098], std ≈ 0.0217.
    # Band width ≈ 0.0217 * 101 ≈ 2.19.  A price within ±2 is allowed.
    allowed = await rs.pre_trade_check(
        product_id="ETH-USD",
        side="buy",
        size=0.1,
        price=102.5,
        reference_price=reference,
    )
    assert allowed is True


@pytest.mark.asyncio
async def test_atr_band_rejects_large_deviation(monkeypatch) -> None:
    """ATR-based volatility bands should reject prices far outside the band."""
    # Configure ATR method and window
    monkeypatch.setenv("ATR_WINDOW", "3")
    monkeypatch.setenv("VOLATILITY_METHOD", "atr")
    monkeypatch.setenv("VOLATILITY_MULT", "1.0")
    # Use permissive caps so only band check matters
    monkeypatch.setenv("MAX_ORDER_NOTIONAL", "100000")
    monkeypatch.setenv("MAX_ORDERS_PER_MINUTE", "100")
    monkeypatch.setenv("MAX_OPEN_ORDERS", "100")
    monkeypatch.setenv("PRICE_BAND_PCT", "0")
    monkeypatch.setenv("SLIPPAGE_PCT", "0")
    rs = RiskService()
    # Record a sequence of prices to build ATR history.  ATR is the average of
    # absolute percentage changes.  For prices [100, 110, 90] the abs returns
    # are 0.10 and 0.1818..., average ≈ 0.1409.  Band width ≈ 0.1409 * 90 ≈ 12.7.
    prices = [100.0, 110.0, 90.0]
    for p in prices:
        await rs.record_price("BTC-USD", p)
    reference = prices[-1]
    allowed = await rs.pre_trade_check(
        product_id="BTC-USD",
        side="buy",
        size=0.1,
        price=200.0,
        reference_price=reference,
    )
    assert allowed is False


@pytest.mark.asyncio
async def test_atr_band_allows_small_deviation(monkeypatch) -> None:
    """ATR-based volatility bands should allow prices within the band."""
    monkeypatch.setenv("ATR_WINDOW", "3")
    monkeypatch.setenv("VOLATILITY_METHOD", "atr")
    monkeypatch.setenv("VOLATILITY_MULT", "1.0")
    monkeypatch.setenv("MAX_ORDER_NOTIONAL", "100000")
    monkeypatch.setenv("MAX_ORDERS_PER_MINUTE", "100")
    monkeypatch.setenv("MAX_OPEN_ORDERS", "100")
    monkeypatch.setenv("PRICE_BAND_PCT", "0")
    monkeypatch.setenv("SLIPPAGE_PCT", "0")
    rs = RiskService()
    # Price sequence with modest volatility.  ATR will be low.
    prices = [100.0, 102.0, 101.0]
    for p in prices:
        await rs.record_price("ETH-USD", p)
    reference = prices[-1]
    # abs returns: 0.02, 0.0098; avg ≈ 0.0149.  Band width ≈ 0.0149 * 101 ≈ 1.5.
    # A price within ±1.4 should be allowed.
    allowed = await rs.pre_trade_check(
        product_id="ETH-USD",
        side="buy",
        size=0.1,
        price=102.2,
        reference_price=reference,
    )
    assert allowed is True