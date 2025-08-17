"""
Deep Q‑Network (DQN) Strategy
=============================

This module provides a lightweight reinforcement‑learning strategy based on
a simple feed‑forward neural network trained with the Q‑learning update
rule.  Unlike the tabular Q‑learning strategy defined in
``rl_strategy.py``, this strategy approximates the Q function using a
linear model over a small set of features.  It is intended as a
demonstration of how a more advanced RL agent might integrate into
the trading platform without relying on heavyweight deep learning
libraries.  If ``numpy`` is available it will be used for vector
operations; otherwise Python lists are used.

Features and Actions
--------------------

The feature vector for each observation consists of three values:

1. Price change (delta) relative to the previous tick, normalised by the
   previous price.  This captures short‑term momentum.
2. The current position state (−1, 0, 1) encoded as a continuous
   feature.  This allows the agent to differentiate between being
   long, flat or short.
3. A constant bias term of 1.0.

The action space is identical to other strategies: ``-1`` (sell/short),
``0`` (hold) and ``1`` (buy/long).  The network outputs a Q‑value for
each action given the current feature vector.  Action selection is
epsilon‑greedy: with probability epsilon a random action is chosen;
otherwise the action with the highest Q‑value is selected.

Hyperparameters
---------------

The following environment variables configure the learning process:

``DQN_LR``
    Learning rate α (default ``0.01``).  Controls the step size for
    weight updates.

``DQN_GAMMA``
    Discount factor γ (default ``0.9``).  Determines how far into the
    future the agent looks when evaluating rewards.

``DQN_EPSILON_START``
    Initial exploration probability ε (default ``0.2``).

``DQN_EPSILON_MIN``
    Minimum ε value (default ``0.01``).  Exploration decays toward
    this value.

``DQN_EPSILON_DECAY``
    Multiplicative decay factor for ε applied after each step (default
    ``0.995``).

``DQN_SIZE``
    Order size per trade (default ``0.001``).

This strategy illustrates how to integrate a parametrised RL agent
without external dependencies; however, it is not suitable for
production trading and should be replaced or extended with a real
deep learning model if used beyond demonstration purposes.
"""

from __future__ import annotations

import os
import random
from typing import Any, Dict, List, Optional

try:
    import numpy as np  # type: ignore
except Exception:
    np = None  # type: ignore

from .base import BaseStrategy


class DeepQNetworkStrategy(BaseStrategy):
    """Approximate Q‑learning strategy using a simple linear network."""

    ACTIONS = [-1, 0, 1]

    def __init__(self, name: str, event_bus: Any, price_cache: Any, execution_service: Any) -> None:
        super().__init__(name, event_bus, price_cache, execution_service)
        # Hyperparameters
        self.lr: float = float(os.getenv("DQN_LR", "0.01"))
        self.gamma: float = float(os.getenv("DQN_GAMMA", "0.9"))
        self.epsilon: float = float(os.getenv("DQN_EPSILON_START", "0.2"))
        self.epsilon_min: float = float(os.getenv("DQN_EPSILON_MIN", "0.01"))
        self.epsilon_decay: float = float(os.getenv("DQN_EPSILON_DECAY", "0.995"))
        self.size: float = float(os.getenv("DQN_SIZE", os.getenv("RL_SIZE", "0.001")))
        # Model parameters: for three features and three actions
        self.n_features = 3
        self.n_actions = len(self.ACTIONS)
        # Weight matrix shape (actions x features).  Use numpy if available.
        if np is not None:
            self.W = np.zeros((self.n_actions, self.n_features), dtype=float)
        else:
            self.W = [[0.0 for _ in range(self.n_features)] for _ in range(self.n_actions)]  # type: ignore[list]
        # Track last price per product to compute deltas
        self.last_price: Dict[str, float] = {}
        # Current position per product (-1, 0, 1)
        self.position: Dict[str, int] = {}
        # Last feature and action for each product (for update step)
        self.last_features: Dict[str, List[float]] = {}
        self.last_action: Dict[str, int] = {}

    def _compute_features(self, product: str, price: float) -> List[float]:
        """Compute feature vector for the current observation."""
        prev = self.last_price.get(product)
        # Price delta normalised by previous price
        if prev is not None and prev != 0:
            delta = (price - prev) / prev
        else:
            delta = 0.0
        pos = self.position.get(product, 0)
        # Features: [delta, position, bias]
        return [delta, float(pos), 1.0]

    def _q_values(self, features: List[float]) -> List[float]:
        """Compute Q‑values for each action given features."""
        if np is not None:
            f_vec = np.array(features)
            return list(self.W.dot(f_vec))  # type: ignore[operator]
        # Manual dot product
        q_vals: List[float] = []
        for weights in self.W:  # type: ignore[assignment]
            s = 0.0
            for w, f in zip(weights, features):
                s += w * f
            q_vals.append(s)
        return q_vals

    def _update_weights(
        self,
        features: List[float],
        action_idx: int,
        reward: float,
        next_features: List[float],
    ) -> None:
        """Perform gradient update on the weights for the taken action."""
        # Compute target: reward + gamma * max_a' Q(next_state, a')
        q_current = self._q_values(features)[action_idx]
        q_next_vals = self._q_values(next_features)
        target = reward + self.gamma * max(q_next_vals)
        td_error = target - q_current
        # Update weight for the action
        if np is not None:
            update_vec = self.lr * td_error * np.array(features)
            self.W[action_idx] += update_vec  # type: ignore[index]
        else:
            for i in range(self.n_features):
                self.W[action_idx][i] += self.lr * td_error * features[i]  # type: ignore[index]

    async def run(self) -> None:
        """Subscribe to ticker events and trade using DQN."""
        async for event in self.event_bus.subscribe("ticker"):
            try:
                product = event.get("product_id")
                price = float(event.get("price"))
            except Exception:
                continue
            # Initialise position map
            if product not in self.position:
                self.position[product] = 0
            # Compute features
            features = self._compute_features(product, price)
            # Update Q network based on last action
            if product in self.last_features and product in self.last_action:
                prev_features = self.last_features[product]
                action_idx_prev = self.ACTIONS.index(self.last_action[product])
                # Reward is change in price times current position
                prev_price = self.last_price.get(product)
                reward = 0.0
                if prev_price is not None:
                    # Reward is position * price change (PnL)
                    reward = (price - prev_price) * self.position[product]
                self._update_weights(prev_features, action_idx_prev, reward, features)
            # Exploration vs exploitation
            if random.random() < self.epsilon:
                action = random.choice(self.ACTIONS)
            else:
                # Choose action with highest Q value
                q_vals = self._q_values(features)
                max_idx = 0
                max_val = q_vals[0]
                for i, val in enumerate(q_vals):
                    if val > max_val:
                        max_val = val
                        max_idx = i
                action = self.ACTIONS[max_idx]
            # Decay epsilon
            if self.epsilon > self.epsilon_min:
                self.epsilon *= self.epsilon_decay
                if self.epsilon < self.epsilon_min:
                    self.epsilon = self.epsilon_min
            # Determine side and place order if position changes
            side: Optional[str] = None
            # Transition logic: open position
            current_pos = self.position[product]
            if current_pos == 0:
                if action == 1:
                    side = "buy"
                    self.position[product] = 1
                elif action == -1:
                    side = "sell"
                    self.position[product] = -1
            elif current_pos == 1 and action == -1:
                # Close long
                side = "sell"
                self.position[product] = 0
            elif current_pos == -1 and action == 1:
                # Close short
                side = "buy"
                self.position[product] = 0
            # Submit order if side determined
            if side:
                try:
                    await self.execution_service.submit(product, side, self.size, price)
                except Exception:
                    # Ignore submission errors
                    pass
            # Store last state/action
            self.last_features[product] = features
            self.last_action[product] = action
            self.last_price[product] = price
