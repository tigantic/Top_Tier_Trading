"""Fake in‑memory event bus for testing.

This helper provides a simple event bus implementation that records
published events.  Each call to ``publish(event_type, data)``
appends a tuple ``(event_type, data)`` to the ``events`` list.
Consumers can inspect the events after the test run to assert
properties about message ordering and schema.
"""

from __future__ import annotations

from typing import Any, List, Tuple


class FakeBus:
    """A minimal event bus used for capturing events in tests."""

    def __init__(self) -> None:
        self.events: List[Tuple[str, Any]] = []

    async def publish(self, event_type: str, data: Any) -> None:
        """Record an event.

        Parameters
        ----------
        event_type : str
            The type of event being published (e.g. ``"ticker"`` or
            ``"user_update"``).
        data : Any
            The event payload.  Tests should treat this as an opaque
            dictionary and only assert on keys and value types.
        """
        self.events.append((event_type, data))
