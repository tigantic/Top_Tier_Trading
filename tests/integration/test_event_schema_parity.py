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
from typing import Any, Dict, List, Tuple

import pytest  # type: ignore

from workers.src.workers import market_data, user_channel

from tests.helpers.fake_bus import FakeBus
from tests.helpers.fake_streams import (
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
    for msg in raw_ws_messages():
        await market_data.publish_ticker(bus_raw, msg)
    for msg in raw_user_messages():
        await user_channel.publish_user_update(bus_raw, msg)
    events_raw: List[Tuple[str, Dict[str, Any]]] = bus_raw.events.copy()

    # ---- SDK PATH ----
    bus_sdk = FakeBus()

    class DummyMarketClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def stream(self):
            async for msg in ticker_stream():
                yield msg

    class DummyUserClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def stream(self):
            async for msg in user_update_stream():
                yield msg

    monkeypatch.setattr(market_data, "MarketDataClient", DummyMarketClient)
    monkeypatch.setattr(user_channel, "UserChannelClient", DummyUserClient)
    market_data.event_bus = bus_sdk
    user_channel.event_bus = bus_sdk
    monkeypatch.setenv("USE_OFFICIAL_SDK", "true")
    task_md2 = asyncio.create_task(market_data.start())
    task_uc2 = asyncio.create_task(user_channel.start())
    await asyncio.sleep(0.1)
    for task in (task_md2, task_uc2):
        task.cancel()
    try:
        await asyncio.gather(task_md2, task_uc2)
    except BaseException:
        pass
    events_sdk: List[Tuple[str, Dict[str, Any]]] = bus_sdk.events.copy()

    def split_events(
        evts: List[Tuple[str, Dict[str, Any]]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        buckets: Dict[str, List[Dict[str, Any]]] = {"ticker": [], "user_update": []}
        for etype, data in evts:
            buckets.setdefault(etype, []).append(data)
        return buckets

    raw_buckets = split_events(events_raw)
    sdk_buckets = split_events(events_sdk)
    assert len(raw_buckets["ticker"]) == len(sdk_buckets["ticker"])
    assert len(raw_buckets["user_update"]) == len(sdk_buckets["user_update"])
    numeric_keys = {"ticker": ["price"], "user_update": ["price", "size", "balance"]}
    for etype in ["ticker", "user_update"]:
        for raw_event, sdk_event in zip(raw_buckets[etype], sdk_buckets[etype]):
            assert set(raw_event.keys()) == set(sdk_event.keys())
            for key in raw_event.keys():
                assert isinstance(raw_event[key], type(sdk_event[key]))
            for nk in numeric_keys[etype]:
                if nk in raw_event:
                    assert isinstance(raw_event[nk], float)
                    assert isinstance(sdk_event[nk], float)
            assert sorted(raw_event.keys()) == sorted(sdk_event.keys())
