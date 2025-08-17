"""
Reinforcement‑learning strategy stub.

This strategy demonstrates how a reinforcement‑learning agent could be
implemented on top of the event bus and execution service.  It is a
simple tabular Q‑learning agent that observes price changes and takes
actions (buy, sell, hold) based on a discretised state.  The agent
maintains an internal position (flat, long, or short) and places
orders when transitioning between these states.  Rewards are based on
unrealised PnL between ticks.  This implementation is intentionally
lightweight and not suitable for production use; it is intended as a
template for more sophisticated agents.

The state space is defined as the sign of the latest price change
(-1 for down, 0 for unchanged, 1 for up) combined with the current
position (-1, 0, 1).  Actions are also in { -1: sell, 0: hold, 1: buy }.

Hyperparameters (epsilon, alpha, gamma, trade size) can be configured
via environment variables:
  RL_EPSILON: exploration probability (default 0.1)
  RL_ALPHA: learning rate (default 0.01)
  RL_GAMMA: discount factor (default 0.9)
  RL_SIZE: order size per trade (default 0.001)
"""

from __future__ import annotations

import os
import random
from typing import Any, Dict, Tuple

from .base import BaseStrategy


class RLStrategy(BaseStrategy):
    """Tabular Q‑learning strategy for demonstration purposes."""

    def __init__(self, name: str, event_bus: Any, price_cache: Any, execution_service: Any) -> None:
        super().__init__(name, event_bus, price_cache, execution_service)
        # Q‑table mapping (state, action) -> value
        self.q: Dict[Tuple[int, int], float] = {}
        # Exploration probability
        self.epsilon: float = float(os.getenv("RL_EPSILON", "0.1"))
        # Learning rate
        self.alpha: float = float(os.getenv("RL_ALPHA", "0.01"))
        # Discount factor
        self.gamma: float = float(os.getenv("RL_GAMMA", "0.9"))
        # Size per trade
        self.size: float = float(os.getenv("RL_SIZE", "0.001"))
        # Current position: -1 = short, 0 = flat, 1 = long
        self.position: int = 0
        # Last price observed per product
        self.last_price: Dict[str, float] = {}
        # Last state and action for Q update
        self.last_state: Dict[str, Tuple[int, int]] = {}
        self.last_action: Dict[str, int] = {}

    def _state(self, product: str, price: float) -> int:
        """Compute discretised state based on price change and current position."""
        prev = self.last_price.get(product)
        delta = 0
        if prev is not None:
            if price > prev:
                delta = 1
            elif price < prev:
                delta = -1
        # Combine delta and position into a small integer state
        # e.g., -1 position and delta -1 -> state = -2; position 0 -> state = delta; position 1 -> state = 2+delta
        return self.position * 2 + delta

    def _choose_action(self, state: int) -> int:
        """Epsilon‑greedy action selection."""
        # Actions: -1=sell/short, 0=hold, 1=buy
        if random.random() < self.epsilon:
            return random.choice([-1, 0, 1])
        # Pick action with highest Q value
        best_value = float("-inf")
        best_action = 0
        for action in (-1, 0, 1):
            value = self.q.get((state, action), 0.0)
            if value > best_value:
                best_value = value
                best_action = action
        return best_action

    def _update_q(self, state: int, action: int, reward: float, next_state: int) -> None:
        """Update Q‑table via standard Q‑learning."""
        prev_q = self.q.get((state, action), 0.0)
        max_next = max(self.q.get((next_state, a), 0.0) for a in (-1, 0, 1))
        new_q = prev_q + self.alpha * (reward + self.gamma * max_next - prev_q)
        self.q[(state, action)] = new_q

    async def run(self) -> None:
        """Main loop: subscribe to tickers, update Q‑values, and place orders."""
        # Subscribe to ticker events on the event bus
        async for event in self.event_bus.subscribe("ticker"):
            try:
                product = event.get("product_id")
                price = float(event.get("price"))
            except Exception:
                continue
            # Compute current state
            state = self._state(product, price)
            # Reward for previous action (if any)
            last_state = self.last_state.get(product)
            last_action = self.last_action.get(product)
            reward = 0.0
            if last_state is not None and last_action is not None:
                prev_price = self.last_price.get(product)
                if prev_price is not None:
                    # Reward is change in price times position after last action
                    reward = (price - prev_price) * self.position
                # Update Q table
                self._update_q(last_state[0], last_action, reward, state)
            # Choose new action based on current state
            action = self._choose_action(state)
            # Determine side and submit order if action changes position
            side: str | None = None
            # Transition logic: if position is 0 and action is buy/sell, open position
            if self.position == 0:
                if action == 1:
                    side = "buy"
                    self.position = 1
                elif action == -1:
                    side = "sell"
                    self.position = -1
            # If already long and action == -1, close long (sell)
            elif self.position == 1 and action == -1:
                side = "sell"
                self.position = 0
            # If already short and action == 1, close short (buy)
            elif self.position == -1 and action == 1:
                side = "buy"
                self.position = 0
            # Hold action or no change results in no order
            if side:
                try:
                    await self.execution_service.submit(product, side, self.size, price)
                except Exception:
                    # Ignore submission errors
                    pass
            # Store last state and action for next iteration
            self.last_state[product] = (state, action)
            self.last_action[product] = action
            self.last_price[product] = price
