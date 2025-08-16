"""Replay buffer for reinforcement learning.

This module defines a simple ring buffer for storing experience tuples
used in off‑policy reinforcement learning algorithms such as Deep
Q‑Networks (DQN).  The buffer supports constant‑time insertion and
uniform random sampling without replacement.  It is implemented
without external dependencies and is safe for use in an offline
environment.
"""

from __future__ import annotations

import random
from collections import deque
from typing import Deque, Generic, Iterable, Iterator, List, Optional, Tuple, TypeVar

T = TypeVar("T")


class ReplayBuffer(Generic[T]):
    """Fixed‑size ring buffer for experience replay.

    Parameters
    ----------
    capacity : int
        Maximum number of experiences to store.  When the buffer is
        full, pushing a new item will evict the oldest one.

    Examples
    --------

    >>> buf = ReplayBuffer[int](capacity=3)
    >>> buf.push(1)
    >>> buf.push(2)
    >>> buf.push(3)
    >>> len(buf)
    3
    >>> buf.push(4)
    >>> list(buf.sample(2))  # sample without replacement
    [..., ...]
    """

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self.buffer: Deque[T] = deque(maxlen=capacity)

    def push(self, *items: T) -> None:
        """Add one or more items to the buffer.

        Items are appended in order.  If the buffer exceeds its
        capacity, the oldest items are discarded.
        """
        for item in items:
            self.buffer.append(item)

    def sample(self, batch_size: int) -> Iterable[T]:
        """Return a list of randomly sampled items.

        Sampling is without replacement.  If ``batch_size`` is larger
        than the number of stored items, all items are returned in
        random order.
        """
        if batch_size <= 0:
            return []
        return random.sample(list(self.buffer), min(batch_size, len(self.buffer)))

    def __len__(self) -> int:
        return len(self.buffer)

    def __iter__(self) -> Iterator[T]:
        return iter(self.buffer)