"""Simple event store for logging events to a JSON lines file.

The event store accepts arbitrary event dictionaries and writes them
to a file in JSON Lines format.  Each call to ``log`` appends a new
line containing the event type and payload.  File writes are
performed via ``asyncio.to_thread`` to avoid blocking the event loop.

To enable event logging, set the environment variable
``EVENT_STORE_PATH`` to a writable file path and pass the resulting
``EventStore`` instance into services that produce events.  Events
can later be parsed to generate training datasets or audit logs.

This implementation does not enforce any schema on the logged events
and is intentionally minimal.  In a production system, consider
rotating the log file, compressing old logs and persisting to
durable storage or a database.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict


class EventStore:
    """Append‑only JSON Lines event logger."""

    def __init__(self, path: str) -> None:
        self.path = os.path.abspath(path)
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._lock = asyncio.Lock()

    async def log(self, event_type: str, data: Dict[str, Any]) -> None:
        """Append an event to the log file.

        Args:
            event_type: A string identifying the type of event.
            data: A dictionary of event data.  Must be JSON serializable.
        """
        line = json.dumps({"type": event_type, "data": data}, ensure_ascii=False) + "\n"
        async with self._lock:
            await asyncio.to_thread(self._append_to_file, line)

    def _append_to_file(self, line: str) -> None:
        """Write a single line to the event log file."""
        # Use 'a' mode to append.  Encoding is UTF‑8.
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line)
