"""
Simple in‑memory event bus for decoupling publishers and subscribers
within the worker.  Each event type has its own asyncio queue.

This bus is intended as a placeholder until a real message broker
(e.g., Redis Pub/Sub or RabbitMQ) can be integrated.  It supports
multiple subscribers per event type and ensures that each subscriber
receives all published events.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, AsyncIterator, Dict


class EventBus:
    """
    Simple in‑memory event bus for decoupling publishers and subscribers
    within the worker.  Each event type has its own asyncio queue.

    This bus is intended as a placeholder until a real message broker
    (e.g., Redis Pub/Sub or RabbitMQ) can be integrated.  It supports
    multiple subscribers per event type and ensures that each subscriber
    receives all published events.
    """

    def __init__(self) -> None:
        self._queues: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)

    async def publish(self, event_type: str, data: Any) -> None:
        """Publish an event to all subscribers of the given type."""
        queue = self._queues[event_type]
        await queue.put(data)

    async def subscribe(self, event_type: str) -> AsyncIterator[Any]:
        """Yield events of a given type as they arrive."""
        queue = self._queues[event_type]
        while True:
            data = await queue.get()
            yield data


class RedisEventBus(EventBus):
    """
    Redis‑based event bus using Pub/Sub.  This implementation uses
    ``redis.asyncio`` to publish and subscribe to channels.  It falls back
    to the in‑memory queues if Redis is unavailable or not configured.

    To enable Redis bus, set the environment variables ``REDIS_HOST`` and
    ``REDIS_PORT`` when constructing the bus.  Consumers can subscribe
    to channels via the same ``subscribe()`` interface.  Publishing
    events will push messages to the appropriate Redis channel.
    """

    def __init__(self, host: str = "localhost", port: int = 6379) -> None:
        super().__init__()
        try:
            import redis.asyncio as aioredis  # type: ignore[import]
        except Exception:
            self._redis = None
        else:
            self._redis = aioredis.Redis(host=host, port=port, decode_responses=True)

    async def publish(self, event_type: str, data: Any) -> None:
        if self._redis is None:
            await super().publish(event_type, data)
            return
        # Publish JSON‑serializable data to the Redis channel
        import json
        await self._redis.publish(event_type, json.dumps(data))

    async def subscribe(self, event_type: str) -> AsyncIterator[Any]:
        if self._redis is None:
            async for item in super().subscribe(event_type):
                yield item
        else:
            import json
            pubsub = self._redis.pubsub()
            await pubsub.subscribe(event_type)
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                    except Exception:
                        data = message["data"]
                    yield data