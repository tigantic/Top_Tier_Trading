"""
Integration tests for event schema parity between raw and SDK paths.

These tests run fully offline and validate that when ``USE_OFFICIAL_SDK``
is toggled, both the market data and user channel workers emit events
with identical schemas via the injected event bus.  A fake WebSocket
and SDK clients produce deterministic events without network access.  The
test asserts that the number of events, event types, keys and value
types match between the two code paths.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Tuple

import pytest  # type: ignore

from workers.src.workers import market_data, user_channel

from tests.helpers.fake_bus import FakeBus
from tests.helpers.fake_streams import (
    DummyWebSocket,
    raw_ws_messages,
    raw_user_messages,
    ticker_stream,
    user_update_stream,
)


@pytest.mark.asyncio  # type: ignore
async def test_event_schema_parity(monkeypatch) -> None:
    """Events emitted from raw and SDK paths should have identical schemas and types."""
    # ---- RAW PATH ----
    bus_raw = FakeBus()
    # Patch websockets.connect for market data to return a dummy that yields raw ticker messages
    async def fake_md_connect(uri: str):
        return DummyWebSocket(raw_ws_messages())
    monkeypatch.setattr(market_data.websockets, "connect", fake_md_connect)
    # Patch the subscribe function to no‑op
    monkeypatch.setattr(market_data, "_subscribe", lambda ws, products: None)
    # Patch websockets.connect for user channel to return raw user messages
    async def fake_uc_connect(uri: str):
        return DummyWebSocket(raw_user_messages())
    monkeypatch.setattr(user_channel.websockets, "connect", fake_uc_connect)
    # Prevent JWT refresh from running timers
    monkeypatch.setattr(user_channel.JwtManager, "refresh_token", lambda self: asyncio.sleep(0))
    # Inject fake event bus
    market_data.event_bus = bus_raw
    user_channel.event_bus = bus_raw
    # Ensure SDK is disabled
    monkeypatch.setenv("USE_OFFICIAL_SDK", "false")
    # Run both workers concurrently for a brief time
    task_md = asyncio.create_task(market_data.start())
    task_uc = asyncio.create_task(user_channel.start())
    await asyncio.sleep(0.1)
    for task in [task_md, task_uc]:
        task.cancel()
    try:
        await asyncio.gather(task_md, task_uc)
    except Exception:
        pass
    events_raw: List[Tuple[str, Dict[str, Any]]] = bus_raw.events.copy()

    # ---- SDK PATH ----
    bus_sdk = FakeBus()
    # Define dummy SDK clients that mirror the offline streams
    class DummyMarketClient:
        def __init__(self, *args, **kwargs) -> None:
            self.event_bus = kwargs.get("event_bus")
        async def stream(self):
            async for msg in ticker_stream():
                # Optionally publish via event bus
                if self.event_bus is not None:
                    await self.event_bus.publish("ticker", msg)
                yield msg
    class DummyUserClient:
        def __init__(self, *args, **kwargs) -> None:
            self.event_bus = kwargs.get("event_bus")
        async def stream(self):
            async for msg in user_update_stream():
                if self.event_bus is not None:
                    await self.event_bus.publish("user_update", msg)
                yield msg
    # Patch SDK classes on the modules
    monkeypatch.setattr(market_data, "MarketDataClient", DummyMarketClient)
    monkeypatch.setattr(user_channel, "UserChannelClient", DummyUserClient)
    # Inject fake buses
    market_data.event_bus = bus_sdk
    user_channel.event_bus = bus_sdk
    # Enable SDK
    monkeypatch.setenv("USE_OFFICIAL_SDK", "true")
    task_md2 = asyncio.create_task(market_data.start())
    task_uc2 = asyncio.create_task(user_channel.start())
    await asyncio.sleep(0.1)
    for task in [task_md2, task_uc2]:
        task.cancel()
    try:
        await asyncio.gather(task_md2, task_uc2)
    except Exception:
        pass
    events_sdk: List[Tuple[str, Dict[str, Any]]] = bus_sdk.events.copy()

    # Split into categories for ticker and user_update
    def split_events(evts: List[Tuple[str, Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        buckets: Dict[str, List[Dict[str, Any]]] = {"ticker": [], "user_update": []}
        for etype, data in evts:
            buckets.setdefault(etype, []).append(data)
        return buckets

    raw_buckets = split_events(events_raw)
    sdk_buckets = split_events(events_sdk)
    # Ensure equal number of events per category
    assert len(raw_buckets["ticker"]) == len(sdk_buckets["ticker"])
    assert len(raw_buckets["user_update"]) == len(sdk_buckets["user_update"])
    # Define expected numeric fields per event type
    numeric_keys = {
        "ticker": ["price"],
        "user_update": ["price", "size", "balance"],
    }
    # Compare schemas and value types for each corresponding event
    for etype in ["ticker", "user_update"]:
        for raw_event, sdk_event in zip(raw_buckets[etype], sdk_buckets[etype]):
            # Same keys set
            assert set(raw_event.keys()) == set(sdk_event.keys())
            # Same key types
            for key in raw_event.keys():
                assert isinstance(raw_event[key], type(sdk_event[key]))
            # Numeric fields are floats after normalisation
            for nk in numeric_keys[etype]:
                if nk in raw_event:
                    assert isinstance(raw_event[nk], float)
                    assert isinstance(sdk_event[nk], float)
            # Snapshot of sorted key lists matches
            assert sorted(raw_event.keys()) == sorted(sdk_event.keys())