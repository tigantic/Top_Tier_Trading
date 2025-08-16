"""
RabbitMQ event bus implementation for atlas-trader.

This module provides an event bus backed by RabbitMQ using the
``aio_pika`` library.  It implements the same interface as the
in-memory ``EventBus`` and ``RedisEventBus`` to support seamless
substitution.  Topics are mapped to RabbitMQ routing keys on a
topic exchange.  Each subscriber receives messages for the specific
topic via a unique exclusive queue.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator, Dict

import aio_pika


class RabbitMQEventBus:
    """Publish/subscribe event bus implemented on RabbitMQ."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5672,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username or "guest"
        self.password = password or "guest"
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None

    async def _connect(self) -> None:
        if self._connection is None:
            # Construct AMQP URL
            url = f"amqp://{self.username}:{self.password}@{self.host}:{self.port}/"
            self._connection = await aio_pika.connect_robust(url)
            self._channel = await self._connection.channel()
            # Declare a topic exchange for publishing events
            self._exchange = await self._channel.declare_exchange(
                "atlas_bus", aio_pika.ExchangeType.TOPIC, durable=True
            )

    async def publish(self, topic: str, message: Dict[str, Any]) -> None:
        """Publish a JSON-serialisable message on the given topic."""
        await self._connect()
        body = json.dumps(message).encode("utf-8")
        assert self._exchange is not None
        await self._exchange.publish(
            aio_pika.Message(body), routing_key=topic
        )

    async def subscribe(self, topic: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Subscribe to a topic and yield messages as they arrive."""
        await self._connect()
        assert self._channel is not None
        # Create an exclusive queue for this subscriber
        queue = await self._channel.declare_queue("", exclusive=True)
        assert self._exchange is not None
        # Bind the queue to the topic key
        await queue.bind(self._exchange, routing_key=topic)
        async with queue.iterator() as qit:
            async for message in qit:
                async with message.process():
                    try:
                        payload = json.loads(message.body.decode("utf-8"))
                        yield payload  # type: ignore[generator-yield-type]
                    except Exception:
                        # Ignore malformed messages
                        continue