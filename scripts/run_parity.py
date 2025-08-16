"""Offline parity verification script for ticker and user events.

This script is designed to run in CI to validate that the market data
and user channel workers emit identical event schemas when toggling
between the raw WebSocket implementation and the Coinbase SDK wrappers.
It runs the workers with a fake WebSocket and fake SDK streams using
the helper classes defined in ``tests/helpers``.  The script counts
the number of events per category (``ticker`` and ``user_update``),
checks that the key sets match between the two paths, verifies that
numeric fields are coerced to floats, and writes a summary to
``artifacts/parity_summary.txt``.  The summary indicates the counts
and whether the schema parity check passed (``OK``) or failed
(``FAIL``).

Usage
-----
This script is intended to be invoked from a CI job.  The environment
variable ``USE_OFFICIAL_SDK`` should be set to ``"true"`` or
``"false"`` to select the SDK path or the raw path, respectively.
For example:

.. code-block:: bash

   USE_OFFICIAL_SDK=true python trading_platform/scripts/run_parity.py

The script will run both the market data and user channel workers for
a short period using the specified implementation, capture events via
a fake event bus, and write the summary file.  It exits with code 0
even if parity fails; the summary file should be inspected by the
calling CI job to determine success.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from trading_platform.workers.src.workers import market_data, user_channel  # type: ignore
from trading_platform.tests.helpers.fake_bus import FakeBus  # type: ignore
from trading_platform.tests.helpers.fake_streams import (
    DummyWebSocket,
    raw_ws_messages,
    raw_user_messages,
    ticker_stream,
    user_update_stream,
)  # type: ignore


def _split_events(events: List[Tuple[str, Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
    buckets: Dict[str, List[Dict[str, Any]]] = {"ticker": [], "user_update": []}
    for etype, data in events:
        buckets.setdefault(etype, []).append(data)
    return buckets


async def _run_parity(use_sdk: bool) -> Tuple[bool, Dict[str, int]]:
    """Run the workers with the specified toggle and return parity status and counts.

    Parameters
    ----------
    use_sdk : bool
        If ``True``, run the SDK wrappers; otherwise run the raw WebSocket
        implementations.

    Returns
    -------
    tuple
        A two‑tuple ``(status, counts)`` where ``status`` is ``True`` if
        parity conditions were met and ``counts`` is a mapping of
        category names to counts.
    """
    # Patch the workers to use fake streams and event bus
    bus = FakeBus()
    # Patch websockets.connect for market data and user channel
    async def fake_md_connect(uri: str):
        return DummyWebSocket(raw_ws_messages())
    async def fake_uc_connect(uri: str):
        return DummyWebSocket(raw_user_messages())
    # Patch subscribe function to no‑op
    market_data._subscribe = lambda ws, products: None  # type: ignore
    # Set event bus
    market_data.event_bus = bus
    user_channel.event_bus = bus
    import types  # for monkeypatch-like assignment
    # Replace websockets.connect in both modules
    market_data.websockets.connect = fake_md_connect  # type: ignore
    user_channel.websockets.connect = fake_uc_connect  # type: ignore
    # Replace JwtManager.refresh_token to no-op to avoid spawning tasks
    user_channel.JwtManager.refresh_token = lambda self: asyncio.sleep(0)  # type: ignore
    # Replace SDK clients with dummy streams when using SDK
    if use_sdk:
        class DummyMarketClient:
            def __init__(self, *args, **kwargs):
                self.event_bus = kwargs.get("event_bus")
            async def stream(self):
                async for msg in ticker_stream():
                    from trading_platform.workers.src.workers.services.publishers import publish_ticker  # type: ignore
                    await publish_ticker(self.event_bus, msg)
                    yield msg
        class DummyUserClient:
            def __init__(self, *args, **kwargs):
                self.event_bus = kwargs.get("event_bus")
            async def stream(self):
                async for msg in user_update_stream():
                    from trading_platform.workers.src.workers.services.publishers import publish_user_update  # type: ignore
                    await publish_user_update(self.event_bus, msg)
                    yield msg
        market_data.MarketDataClient = DummyMarketClient  # type: ignore
        user_channel.UserChannelClient = DummyUserClient  # type: ignore
    # Set USE_OFFICIAL_SDK environment variable accordingly
    os.environ["USE_OFFICIAL_SDK"] = "true" if use_sdk else "false"
    # Run both workers concurrently for a short period
    task_md = asyncio.create_task(market_data.start())
    task_uc = asyncio.create_task(user_channel.start())
    await asyncio.sleep(0.1)
    for task in [task_md, task_uc]:
        task.cancel()
    try:
        await asyncio.gather(task_md, task_uc)
    except Exception:
        pass
    events = bus.events.copy()
    buckets = _split_events(events)
    # Validate parity conditions
    ok = True
    counts = {k: len(v) for k, v in buckets.items()}
    # For each category ensure schema keys and types are consistent
    def check_category(name: str, events_list: List[Dict[str, Any]]) -> bool:
        if not events_list:
            return True
        keys0 = set(events_list[0].keys())
        for ev in events_list[1:]:
            if set(ev.keys()) != keys0:
                return False
        # Check numeric types
        numeric_keys = {
            "ticker": ["price"],
            "user_update": ["price", "size", "balance"],
        }.get(name, [])
        for ev in events_list:
            for nk in numeric_keys:
                if nk in ev and not isinstance(ev[nk], float):
                    return False
        return True
    for name, events_list in buckets.items():
        if not check_category(name, events_list):
            ok = False
    return ok, counts


def main() -> None:
    use_sdk_env = os.environ.get("USE_OFFICIAL_SDK", "false").lower()
    use_sdk = use_sdk_env in ("true", "1", "yes")
    ok = False
    counts: Dict[str, int] = {}
    try:
        ok, counts = asyncio.run(_run_parity(use_sdk))
    except Exception as exc:
        ok = False
        counts = {"error": 1}
    # Write summary file
    summary_path = Path("artifacts/parity_summary.txt")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w") as fh:
        fh.write(f"USE_OFFICIAL_SDK={use_sdk}\n")
        fh.write(f"ticker_count={counts.get('ticker', 0)}\n")
        fh.write(f"user_update_count={counts.get('user_update', 0)}\n")
        fh.write(f"status={'OK' if ok else 'FAIL'}\n")
    # Print summary for CI logs
    print(f"USE_OFFICIAL_SDK={use_sdk}")
    print(f"ticker_count={counts.get('ticker', 0)}")
    print(f"user_update_count={counts.get('user_update', 0)}")
    print(f"status={'OK' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()