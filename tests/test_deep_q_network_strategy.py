"""Unit tests for the DeepQNetworkStrategy.

These tests cover feature computation, Q‑value evaluation and the
weight update logic.  They avoid exercising the asynchronous event
loop and order submission, focusing instead on the core learning
behaviour of the strategy.
"""

import math

from workers.src.workers.strategies.deep_q_network_strategy import DeepQNetworkStrategy


class DummyBus:
    async def subscribe(self, channel):  # type: ignore[override]
        yield {}


class DummyCache:
    async def get_price(self, product):  # type: ignore[override]
        return None


class DummyExec:
    async def submit(self, *args, **kwargs):  # type: ignore[override]
        return None


def test_compute_features():
    strat = DeepQNetworkStrategy("test", DummyBus(), DummyCache(), DummyExec())
    # No previous price, delta should be 0
    feats = strat._compute_features("BTC-USD", 100.0)
    assert feats == [0.0, 0.0, 1.0]
    # Set last price and position
    strat.last_price["BTC-USD"] = 100.0
    strat.position["BTC-USD"] = 1
    feats2 = strat._compute_features("BTC-USD", 110.0)
    # delta = (110-100)/100 = 0.1, position = 1
    assert math.isclose(feats2[0], 0.1, rel_tol=1e-6)
    assert feats2[1] == 1.0
    assert feats2[2] == 1.0


def test_update_weights():
    strat = DeepQNetworkStrategy("test", DummyBus(), DummyCache(), DummyExec())
    # Use simple features and simulate update
    features = [0.5, 0.0, 1.0]
    next_features = [0.0, 0.0, 1.0]
    action_idx = 2  # corresponds to ACTIONS[2] == 1 (buy)
    # Initially weights are zero
    q_vals = strat._q_values(features)
    assert all(abs(q) < 1e-9 for q in q_vals)
    # Apply update with positive reward
    strat._update_weights(features, action_idx, reward=1.0, next_features=next_features)
    # Weights for the action should have moved in direction of features
    updated_q = strat._q_values(features)[action_idx]
    assert updated_q > 0
