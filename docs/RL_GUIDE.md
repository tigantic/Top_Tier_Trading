## Reinforcement Learning Guide

[← Back to docs index](./_index.md)

This guide outlines how reinforcement learning (RL) strategies are implemented in the trading platform and how you can extend or train them in a production environment.  The repository contains both tabular Q‑learning and linear Deep Q‑Network (DQN) examples that can serve as templates for more complex agents.

### State, Action and Reward

All RL strategies model the problem as a Markov Decision Process (MDP) with a discrete action space:

* **State (`s_t`)** – Encapsulates recent market information and the agent’s current position.  For the linear DQN strategy, the state is a vector of three features: 1) normalised price change (ΔP/P), 2) position (−1 for short, 0 for flat, +1 for long), and 3) a bias term (constant 1.0).  Other strategies may include additional context such as volatility or order book depth.
* **Action (`a_t`)** – One of three discrete actions: −1 (sell/short), 0 (hold), or +1 (buy/long).  Actions are executed via the `ExecutionService` and adjust the agent’s position accordingly.
* **Reward (`r_{t+1}`)** – The change in unrealised PnL resulting from the previous action, computed as `(P_{t+1} − P_t) × position_t`.  Positive rewards encourage profitable positions; negative rewards penalise losses.  You can customise the reward to include transaction costs or risk penalties.

### Replay Buffer

Deep RL algorithms typically rely on a replay buffer to store past experiences `(s_t, a_t, r_{t+1}, s_{t+1})`.  Sampling mini‑batches from this buffer helps decorrelate updates and stabilise training.  The repository includes a simple ring buffer implementation in `workers/src/workers/rl/replay_buffer.py`:

* `push(state, action, reward, next_state)` – Adds a new experience to the buffer, evicting the oldest when full.
* `sample(batch_size)` – Uniformly samples a batch of experiences for training.
* `__len__` – Returns the number of stored experiences.

This buffer is designed to work without external dependencies.  In production you may wish to implement prioritised experience replay or more advanced sampling strategies.

### Training Loop

The skeleton training script in `scripts/train_deep_rl.py` demonstrates how to set up a DQN training loop with optional PyTorch or TensorFlow support.  The general procedure is:

1. **Collect data** – Generate experiences using historical market data or a simulation environment.  You can convert the event log into a dataset using `scripts/event_log_to_csv.py`.
2. **Initialise network** – Create a neural network to approximate Q values.  The skeleton uses a simple two‑layer feed‑forward network when PyTorch or TensorFlow is available and falls back to a placeholder when not.
3. **Set up target network** – For stability, maintain a separate target network whose weights are periodically updated to match the main network.  The placeholder in the skeleton outlines where to copy weights every `N` steps.
4. **Sample mini‑batches** – Randomly sample batches from the replay buffer.  Compute predicted Q values, target Q values (`r + γ max_a′ Q_{target}(s′, a′)`), and minimise the loss (e.g. mean squared error).
5. **Backpropagate and update** – Perform a gradient descent step to update the main network.  Optionally update the target network at a fixed cadence.
6. **Monitor & save** – Log training metrics (loss, epsilon, reward) to your preferred system (e.g. TensorBoard) and periodically save model checkpoints for rollback or offline evaluation.

The script is instrumented to detect when ML libraries are unavailable and will print a message instead of failing.  To enable real training, install PyTorch or TensorFlow in your environment and uncomment the relevant sections.

### Safety Switch and Fallback Policy

RL strategies inherently involve exploration.  To protect against uncontrolled behaviour, always implement a **safety switch**:

* **Epsilon Greedy Decay** – Gradually reduce the exploration rate (`epsilon`) over time to converge to a deterministic policy.  Environment variables (`DQN_EPSILON_START`, `DQN_EPSILON_MIN`, `DQN_EPSILON_DECAY`) control this decay for the linear DQN strategy.
* **Fallback Policy** – Define a conservative fallback, such as holding a flat position, when the agent encounters unexpected states or model errors.  In our implementation, if any exception occurs during action selection, the strategy defaults to holding (`action = 0`).
* **PnL & Risk Limits** – Combine RL strategies with the risk engine’s pre‑trade checks (notional caps, volatility bands, kill switch) to prevent catastrophic trades.

### Checkpoints and Persistence

The training script includes placeholders for saving and loading model weights.  Implement these functions using your ML library’s save/load facilities.  When running in production, store checkpoints in a persistent volume or object storage and implement a management process to load the latest good model at startup.

### Next Steps

This skeleton is a starting point.  To move toward production:

* Integrate with a realistic simulation environment that feeds market data and executes trades.
* Add support for continuous action spaces and other RL algorithms (e.g. policy gradients, actor–critic).
* Implement hyperparameter tuning and offline evaluation using historical data.
* Monitor strategy performance post‑deployment and trigger alerts when performance deviates from expectations.