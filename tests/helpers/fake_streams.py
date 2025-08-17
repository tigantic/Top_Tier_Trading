"""Fake data streams for market and user events.

These helpers generate deterministic sequences of ticker and user update
events for use in integration tests.  They simulate the outputs of
both the raw WebSocket clients and the SDK wrappers, ensuring parity
between the two paths without requiring network access.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator, Dict, Iterable, List


class DummyWebSocket:
    """A dummy WebSocket context manager that yields messages from a list."""

    def __init__(self, messages: Iterable[Dict[str, Any]]):
        self._messages = list(messages)
        self.sent_subscribe = False

    async def __aenter__(self) -> "DummyWebSocket":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def send(self, msg: str) -> None:
        # ignore subscription messages for the purposes of testing
        self.sent_subscribe = True

    def __aiter__(self) -> "DummyWebSocket":  # pragma: no cover
        return self

    async def __anext__(self) -> str:  # pragma: no cover
        if not self._messages:
            raise StopAsyncIteration
        msg = self._messages.pop(0)
        # encode as JSON string to match websockets protocol
        import json

        return json.dumps(msg)


async def ticker_stream() -> AsyncGenerator[Dict[str, Any], None]:
    """Asynchronous generator yielding deterministic ticker events."""
    yield {"product_id": "BTC-USD", "price": 100.0}
    await asyncio.sleep(0)  # yield control
    yield {"product_id": "ETH-USD", "price": 2000.0}


async def user_update_stream() -> AsyncGenerator[Dict[str, Any], None]:
    """Asynchronous generator yielding deterministic user updates."""
    yield {
        "product_id": "BTC-USD",
        "price": 100.0,
        "size": 0.01,
        "side": "buy",
        "balance": 1.0,
    }
    await asyncio.sleep(0)
    yield {
        "product_id": "ETH-USD",
        "price": 2000.0,
        "size": 0.05,
        "side": "sell",
        "balance": 0.95,
    }


def raw_ws_messages() -> List[Dict[str, Any]]:
    """Return a list of raw WebSocket messages for market data and user channel.

    Raw messages include a ``type`` field to mimic the real WebSocket
    protocol.  These messages are consumed by ``DummyWebSocket`` to
    simulate a WebSocket connection.
    """
    return [
        {"type": "ticker", "product_id": "BTC-USD", "price": "100.0"},
        {"type": "ticker", "product_id": "ETH-USD", "price": "2000.0"},
    ]


def raw_user_messages() -> List[Dict[str, Any]]:
    """Return a list of raw WebSocket messages for the user channel.

    These messages include user account updates encoded as JSON strings.
    They are consumed by ``DummyWebSocket`` to simulate the user channel
    connection in offline tests.
    """
    return [
        json.loads(
            json.dumps(
                {
                    "product_id": "BTC-USD",
                    "price": 100.0,
                    "size": 0.01,
                    "side": "buy",
                    "balance": 1.0,
                }
            )
        ),
        json.loads(
            json.dumps(
                {
                    "product_id": "ETH-USD",
                    "price": 2000.0,
                    "size": 0.05,
                    "side": "sell",
                    "balance": 0.95,
                }
            )
        ),
    ]
