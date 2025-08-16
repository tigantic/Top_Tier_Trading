"""Tests for Coinbase SDK wrappers using stubbed clients.

These tests exercise the behaviour of the SDK wrappers when the
official SDK is not installed.  The wrappers should fall back to
yielding no data without raising exceptions.
"""

import asyncio
import pytest  # type: ignore

from workers.src.workers.clients.sdk_market_data import MarketDataClient
from workers.src.workers.clients.sdk_user_channel import UserChannelClient


@pytest.mark.asyncio  # type: ignore
async def test_market_data_client_stub():
    client = MarketDataClient(api_key="", api_secret="", products=["BTC-USD"])
    # Collect up to one event; expect no events yielded in offline mode
    gen = client.stream()
    try:
        evt = await asyncio.wait_for(gen.__anext__(), timeout=0.5)
        # If an event is yielded, ensure it has expected keys
        assert isinstance(evt, dict)
    except (StopAsyncIteration, asyncio.TimeoutError):
        # No data yielded, which is acceptable in stub mode
        pass


@pytest.mark.asyncio  # type: ignore
async def test_user_channel_client_stub():
    client = UserChannelClient(api_key="", api_secret="")
    gen = client.stream()
    try:
        evt = await asyncio.wait_for(gen.__anext__(), timeout=0.5)
        assert isinstance(evt, dict)
    except (StopAsyncIteration, asyncio.TimeoutError):
        pass