"""Tests for the publisher helper functions.

These unit tests verify that the ``publish_ticker`` and
``publish_user_update`` helpers defined in
``workers/src/workers/services/publishers.py`` correctly normalise
inputs, publish to the provided event bus and raise appropriate
errors when required keys are missing.  The tests run offline and
do not require network access or the Coinbase SDK.
"""

from __future__ import annotations

import pytest  # type: ignore

from tests.helpers.fake_bus import FakeBus
from workers.src.workers.services.publishers import (
    publish_ticker,
    publish_user_update,
)


@pytest.mark.asyncio  # type: ignore
async def test_publish_ticker_normalises_and_publishes() -> None:
    bus = FakeBus()
    msg = {"product_id": "BTC-USD", "price": "100.5"}
    norm = await publish_ticker(bus, msg)
    # Ensure the event was recorded
    assert len(bus.events) == 1
    event_type, payload = bus.events[0]
    assert event_type == "ticker"
    # Keys and types normalised
    assert payload["product_id"] == "BTC-USD"
    assert isinstance(payload["price"], float)
    assert payload["price"] == pytest.approx(100.5)
    # The helper returns the normalised payload
    assert norm == payload


@pytest.mark.asyncio  # type: ignore
async def test_publish_ticker_missing_key_raises() -> None:
    bus = FakeBus()
    # Missing product_id should raise from normalisation
    with pytest.raises(Exception):
        await publish_ticker(bus, {"price": 1.0})


@pytest.mark.asyncio  # type: ignore
async def test_publish_user_update_normalises_and_publishes() -> None:
    bus = FakeBus()
    msg = {
        "product_id": "ETH-USD",
        "price": "2000.0",
        "size": "0.05",
        "side": "sell",
        "balance": "0.95",
    }
    norm = await publish_user_update(bus, msg)
    assert len(bus.events) == 1
    event_type, payload = bus.events[0]
    assert event_type == "user_update"
    assert payload["product_id"] == "ETH-USD"
    assert isinstance(payload["price"], float)
    assert isinstance(payload["size"], float)
    assert isinstance(payload["balance"], float)
    assert payload["side"] == "sell"
    assert norm == payload


@pytest.mark.asyncio  # type: ignore
async def test_publish_user_update_missing_product_raises() -> None:
    bus = FakeBus()
    with pytest.raises(Exception):
        await publish_user_update(bus, {"price": 10.0})


@pytest.mark.asyncio  # type: ignore
async def test_publish_ticker_preserves_meta() -> None:
    """publish_ticker should include an optional meta field if present."""
    bus = FakeBus()
    msg = {
        "product_id": "BTC-USD",
        "price": "100.5",
        "meta": {"source": "sdk", "ts": "2025-01-01T00:00:00Z"},
    }
    norm = await publish_ticker(bus, msg)
    assert len(bus.events) == 1
    event_type, payload = bus.events[0]
    assert event_type == "ticker"
    # Meta field should be preserved verbatim
    assert payload["meta"] == msg["meta"]
    # Normalised fields still coerced to correct types
    assert isinstance(payload["price"], float)
    assert payload["price"] == pytest.approx(100.5)
    assert norm == payload


@pytest.mark.asyncio  # type: ignore
async def test_publish_user_update_preserves_meta() -> None:
    """publish_user_update should include an optional meta field if present."""
    bus = FakeBus()
    msg = {
        "product_id": "ETH-USD",
        "price": "2000.0",
        "size": "0.05",
        "side": "sell",
        "balance": "0.95",
        "meta": {"source": "raw", "ts": "2025-02-01T12:00:00Z"},
    }
    norm = await publish_user_update(bus, msg)
    assert len(bus.events) == 1
    event_type, payload = bus.events[0]
    assert event_type == "user_update"
    assert payload["meta"] == msg["meta"]
    # Numeric fields normalised
    assert isinstance(payload["price"], float)
    assert isinstance(payload["size"], float)
    assert isinstance(payload.get("balance"), float)
    assert norm == payload
