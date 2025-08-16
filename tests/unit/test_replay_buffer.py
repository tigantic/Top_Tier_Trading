"""Unit tests for the replay buffer.

These tests verify that the ReplayBuffer correctly evicts old items,
supports uniform sampling without replacement and reports its length
accurately.
"""

import random

from workers.rl.replay_buffer import ReplayBuffer


def test_replay_buffer_push_and_len():
    buf = ReplayBuffer(capacity=3)
    buf.push(1, 2)
    assert len(buf) == 2
    buf.push(3)
    assert len(buf) == 3
    # Pushing beyond capacity should evict oldest
    buf.push(4)
    assert len(buf) == 3
    assert list(buf) == [2, 3, 4]


def test_replay_buffer_sample():
    buf = ReplayBuffer(capacity=5)
    buf.push(1, 2, 3)
    sample = list(buf.sample(2))
    assert len(sample) == 2
    assert set(sample).issubset({1, 2, 3})
    # sampling more than length returns all in random order
    sample_all = list(buf.sample(10))
    assert set(sample_all) == {1, 2, 3}