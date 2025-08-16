## Release Notes – 1.0.0

> **General Availability (GA)**
>
> This release marks the first general‑availability version of the crypto
> trading platform.  It solidifies the API and event schema defined
> during the 1.0.0‑rc1 cycle and freezes the documentation.  No
> breaking changes have been introduced since the release candidate.

### Major Features

The following capabilities are included in version 1.0.0.  See the
change log for a detailed chronological list of changes.

* **SDK Wiring & Schema Parity** – Workers can toggle between raw
  WebSockets and Coinbase SDK wrappers via the `USE_OFFICIAL_SDK`
  environment variable.  Canonical publisher helpers ensure that
  ticker and user update events emit identical schemas to the event
  bus in both modes.  Parity tests run in CI across both toggles.
* **Shared Event Contract** – A shared schema contract defines the
  required keys and types for ticker and user update events
  (`workers/src/workers/models/events.py`).  All publishers
  normalise numeric fields to floats and enforce required keys.
  Optional `meta` fields are passed through for traceability.
* **Volatility Models** – The risk engine supports standard deviation,
  exponentially weighted moving average (EWMA), Average True Range
  (ATR) and a GARCH(1,1) estimator with parameter clamps for
  stability.
* **Reinforcement Learning & Backtesting** – Included are a replay
  buffer and DQN training skeleton, linear Q‑learning, logistic
  regression and SMA strategies.  The RL guide describes state,
  action and reward definitions and the training loop.
* **Asynchronous Operations Bot & Metrics** – A Slack/Teams bot
  provides exposure and PnL queries, alerts with deduplication and
  retries, and a health endpoint.  A metrics service publishes
  exposures, open orders, kill switch status and PnL via
  Prometheus.  An SSE endpoint streams metrics to the dashboard.
* **Comprehensive Documentation & Governance** – Guides cover the
  architecture, SDK integration, risk modelling, RL concepts, ops
  runbooks, secrets management, governance and contribution
  workflows.  The documentation index offers a decision tree to
  navigate the material.

### Upgrade Notes

The schema contract and event bus normalisation functions live in
`workers/src/workers/models/events.py`.  When integrating this
platform into your environment:

1. **Event Bus Injection** – Ensure that any new clients or
   wrappers receive an event bus instance and publish normalised
   events via the helpers in `workers/src/workers/services/publishers.py`.
2. **Parities Guaranteed** – Use the parity tests and harness
   (`scripts/run_parity.py`) to verify that custom modifications
   maintain schema parity between raw and SDK paths.
3. **Configuration** – Set `USE_OFFICIAL_SDK` to `true` to enable
   SDK wrappers in production.  For offline or local development,
   leave it `false` to use raw WebSockets and stub SDK clients.
4. **Risk Calibration** – Select a volatility model (std, EWMA, ATR
   or GARCH) and calibrate parameters using `scripts/calibrate_vol.py`
   or manual analysis of event logs.

### Known Issues

The limitations identified during the release candidate remain in
place:

* **Real SDK Integration** – The Coinbase Advanced Trade SDK wrappers
  remain stubs offline; real streaming requires installing the SDK
  and network access.
* **Deep RL Training** – Deep learning requires installing PyTorch or
  TensorFlow and implementing a neural network; the provided DQN
  strategy uses a linear model for offline experimentation.
* **Ops UI Design System** – The dashboard uses a placeholder
  component; integrating a complete design system (e.g. shadcn/ui,
  Radix) will require online dependencies.
* **GARCH Calibration** – The simple GARCH estimator may not capture
  all market dynamics; calibrate and tune parameters offline.
