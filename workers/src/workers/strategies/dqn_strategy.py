"""
DqnStrategy
==========

This module implements a simple tabular Q‑learning strategy for trading
cryptocurrencies.  Although named "DqnStrategy", it uses a discrete
state/action space and updates a Q‑table rather than a deep neural
network.  The goal is to illustrate how reinforcement learning can be
applied to decision‑making in an online setting without external
dependencies.

State Representation
--------------------

The state is a tuple containing two elements:

* ``direction`` – whether the last price change was up (`1`), down
  (`-1`) or unchanged (`0`).
* ``position`` – the current inventory position (`-1` for short,
  `0` for flat, `1` for long).

Actions are integers: ``0`` = hold, ``1`` = buy, ``2`` = sell.

Rewards are computed on each tick as the change in unrealised PnL
resulting from the previous action.  The algorithm uses a standard
epsilon‑greedy policy with decay to balance exploration and
exploitation.

Configuration
-------------

The following environment variables influence the strategy:

* ``DQN_ALPHA`` – learning rate (default 0.1)
* ``DQN_GAMMA`` – discount factor (default 0.95)
* ``DQN_EPSILON_START`` – initial exploration rate (default 0.2)
* ``DQN_EPSILON_MIN`` – minimum exploration rate (default 0.01)
* ``DQN_EPSILON_DECAY`` – multiplicative decay factor per step (default 0.999)
* ``STRATEGY_SIZE`` – trade size (shared with other strategies; default 0.001)

To enable this strategy, include `workers.src.workers.strategies.dqn_strategy.DqnStrategy`
in the ``STRATEGIES`` environment variable.  For example:

```
STRATEGIES=workers.src.workers.strategies.dqn_strategy.DqnStrategy
```

Limitations
-----------

* This implementation is highly simplified and does not include
  experience replay or neural function approximation.
* The state space is tiny; in a real system you would discretise
  additional features (e.g. volatility, volume, order book depth).
* Rewards are based only on unrealised PnL; slippage and fees are ignored.
* Exploration parameters may need tuning for meaningful performance.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections import defaultdict
from typing import Dict, Tuple

import numpy as np

from .base import BaseStrategy


class DqnStrategy(BaseStrategy):
    """A simple tabular Q‑learning strategy."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Q‑table mapping state tuples to arrays of action values (size 3)
        self.q_table: Dict[Tuple[int, int], np.ndarray] = defaultdict(lambda: np.zeros(3))
        # Previous state and action
        self.prev_state: Tuple[int, int] | None = None
        self.prev_action: int | None = None
        # Last observed price
        self.last_price: float | None = None
        # Learning parameters
        self.alpha = float(os.getenv("DQN_ALPHA", "0.1"))
        self.gamma = float(os.getenv("DQN_GAMMA", "0.95"))
        self.epsilon = float(os.getenv("DQN_EPSILON_START", "0.2"))
        self.epsilon_min = float(os.getenv("DQN_EPSILON_MIN", "0.01"))
        self.epsilon_decay = float(os.getenv("DQN_EPSILON_DECAY", "0.999"))
        # Trade size
        self.size = float(os.getenv("STRATEGY_SIZE", "0.001"))

    def _get_state(self, price: float, position: int) -> Tuple[int, int]:
        """Construct the discrete state based on price direction and position."""
        if self.last_price is None or self.last_price == 0:
            direction = 0
        else:
            diff = price - self.last_price
            direction = 1 if diff > 0 else (-1 if diff < 0 else 0)
        return direction, position

    def _choose_action(self, state: Tuple[int, int]) -> int:
        """Choose an action using epsilon‑greedy policy."""
        if np.random.rand() < self.epsilon:
            return np.random.randint(0, 3)  # explore
        # exploit
        return int(np.argmax(self.q_table[state]))

    def _update_q(self, reward: float, next_state: Tuple[int, int]) -> None:
        """Update Q‑table based on the observed reward and transition."""
        if self.prev_state is None or self.prev_action is None:
            return
        # Current Q estimate
        q_sa = self.q_table[self.prev_state][self.prev_action]
        # Maximum Q for next state
        max_q_next = float(np.max(self.q_table[next_state]))
        # TD target
        target = reward + self.gamma * max_q_next
        # TD update
        self.q_table[self.prev_state][self.prev_action] = q_sa + self.alpha * (target - q_sa)

    async def run(self) -> None:
        """Main loop: subscribe to ticker events, update Q‑table and trade."""
        if self.event_bus is None:
            logging.error("DqnStrategy requires an event bus")
            return
        # Position: -1 short, 0 flat, 1 long
        position = 0
        async for event in self.event_bus.subscribe("ticker"):
            try:
                price = float(event.get("price"))
                product_id = str(event.get("product_id"))
            except Exception:
                continue
            # Build current state
            state = self._get_state(price, position)
            # Compute reward based on unrealised PnL since last step
            reward = 0.0
            if self.last_price is not None and position != 0:
                # Unrealised PnL change
                pnl_change = (price - self.last_price) * position * self.size
                reward = pnl_change
            # Q update based on previous transition
            next_state = state
            self._update_q(reward, next_state)
            # Choose next action
            action = self._choose_action(state)
            # Execute action
            if action == 1 and position <= 0:
                # Buy to go long or cover short
                await self.execution_service.submit_order(
                    product_id=product_id,
                    side="buy",
                    size=self.size,
                    price=price,
                )
                position = 1
            elif action == 2 and position >= 0:
                # Sell to go short or exit long
                await self.execution_service.submit_order(
                    product_id=product_id,
                    side="sell",
                    size=self.size,
                    price=price,
                )
                position = -1
            else:
                # Hold: no change to position
                pass
            # Update exploration rate
            if self.epsilon > self.epsilon_min:
                self.epsilon *= self.epsilon_decay
            # Update last state/action for next iteration
            self.prev_state = state
            self.prev_action = action
            self.last_price = price