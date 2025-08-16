"""Tests for the PriceCache service."""

import pytest

from workers.src.workers.services.price_cache import PriceCache


@pytest.mark.asyncio
async def test_price_cache_roundtrip() -> None:
    cache = PriceCache()
    await cache.update_price("BTC-USD", 42.0)
    price = await cache.get_price("BTC-USD")
    assert price == 42.0
