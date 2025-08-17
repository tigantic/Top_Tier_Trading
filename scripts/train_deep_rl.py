from __future__ import annotations

import random
from collections import deque
from typing import Any, Deque, List, Tuple

# Mocked or optional imports; keep lightweight for dev machines
try:
    import numpy as np  # noqa: F401
except Exception:
    np = None  # type: ignore

ReplayBuffer = None  # replace with your real buffer if present


def main() -> None:
    epochs = 1
    batch_size = 32
    env_data: List[Tuple[Any, Any, Any, Any]] = []

    # Example: collect some mock data (non-crypto-secure randomness is fine for RL simulation)
    mock_data: List[Tuple[list[float], int, float, list[float]]] = []
    for _ in range(100):
        state = [random.random() for _ in range(3)]
        action = random.choice([-1, 0, 1])
        reward = random.uniform(-1, 1)
        next_state = [random.random() for _ in range(3)]
        mock_data.append((state, action, reward, next_state))

    # Hyperparameters
    _gamma = 0.9  # was: gamma (unused) -> _gamma
    copy_target_steps = 10
    step_count = 0

    buffer: Deque[Any] | None = (
        deque(maxlen=max(len(env_data), 1))
        if ReplayBuffer is None
        else ReplayBuffer(max(len(env_data), 1))
    )  # type: ignore[call-arg]

    for epoch in range(epochs):
        # ... training stub ...
        try:
            # imitate a target copy
            _ = copy_target_steps
        except Exception:
            pass

        # Sample mini-batch
        _experiences = (
            list(buffer)[:batch_size] if buffer else mock_data[:batch_size]
        )  # was: experiences (unused)

        step_count += 1
        print(f"Completed epoch {epoch + 1}/{epochs}, steps={step_count}")


if __name__ == "__main__":
    main()
