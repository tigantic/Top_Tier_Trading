"""
Base classes and interfaces for trading strategies.  Strategies
subscribe to market data events via the event bus and submit orders
through the execution service.  This module defines the common
contract that all strategies must implement.
"""

from __future__ import annotations

import abc

from ..services.event_bus import EventBus
from ..services.execution_service import ExecutionService
from ..services.price_cache import PriceCache


class BaseStrategy(abc.ABC):
    """Abstract base class for trading strategies."""

    def __init__(
        self,
        name: str,
        event_bus: EventBus,
        price_cache: PriceCache,
        execution_service: ExecutionService,
    ) -> None:
        self.name = name
        self.event_bus = event_bus
        self.price_cache = price_cache
        self.execution_service = execution_service

    @abc.abstractmethod
    async def run(self) -> None:
        """Run the strategy loop.  Implementations should subscribe to the
        necessary event types and submit orders via the execution service."""
        raise NotImplementedError
