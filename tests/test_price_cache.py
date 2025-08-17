"""Tests for the PriceCache service."""

import os
import sys

import pytest

# Adjust sys.path so that tests can import the workers modules without installing the package.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workers", "src")))

from workers.services.price_cache import PriceCache


@pytest.mark.asyncio
async def test_price_cache_roundtrip() -> None:
    cache = PriceCache()
    await cache.update_price("BTC-USD", 42.0)
    price = await cache.get_price("BTC-USD")
    assert price == 42.0
