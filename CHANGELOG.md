## 1.0.0-rc1 – Release Candidate

### Highlights

- **SDK wiring & schema parity** – The market data and user channel workers can now toggle between raw WebSocket clients and Coinbase SDK wrappers via the `USE_OFFICIAL_SDK` flag.  Event bus publishing is unified through canonical publisher helpers, ensuring identical schemas and routing regardless of the source.  Comprehensive parity tests run in CI across both toggles.
- **Schema contract & normalisation** – A shared contract in `workers/src/workers/models/events.py` defines ticker and user update event structures.  All publishers normalise numeric fields to floats and enforce required keys.  Optional `meta` fields are passed through for traceability.
- **Volatility models** – Added ATR and a simple GARCH(1,1) estimator to complement standard deviation and EWMA.  The GARCH implementation clamps parameters for stability and forecasts volatilities offline.  A calibration script reads event logs to suggest parameter values.
- **Deep reinforcement learning** – Provided a skeleton DQN strategy with a replay buffer and training loop, plus linear Q‑learning and SMA crossover strategies.  A RL guide explains state/action/reward definitions and the training pipeline.
- **Asynchronous ops bot** – Fully asynchronous Slack/Teams bot with health checks, deduplication, exponential backoff retries, and Helm deployment.  Health and readiness endpoints support Kubernetes probes.
- **Docs & Governance** – Extensive documentation including an index, architecture overview, SDK integration guide, RL guide, operations manual, security guidelines, governance rules, contributing guide, release notes and change log.

### Breaking Changes

- Event schemas have been frozen for the 1.0.0‑rc1 release.  Any future changes will require a minor version bump and updates to the schema contract and parity tests.
- The repository now includes a `VERSION` file.  Tools and CI pipelines should read this file to determine the current release version.

### Migration Notes

To migrate an existing deployment to 1.0.0‑rc1:

1. Ensure you have copied `.env.example` to `.env` and `conf/secrets.env.example` to `conf/secrets.env`.  Set `USE_OFFICIAL_SDK` according to your environment (offline or SDK).
2. Run the Alembic migrations via `scripts/migrate_db.py` if you are using the database state store.
3. Deploy the updated ops bot and configure Slack/Teams credentials via your secrets backend.
4. Review the new GARCH estimator in `workers/src/workers/risk/garch.py` and adjust volatility configuration accordingly.  Calibrate parameters using `scripts/calibrate_vol.py`.
5. Read through the release notes (`docs/RELEASE_NOTES.md`) for a high‑level overview of the new features and known limitations.

## 1.0.0 – General Availability

This GA release finalises the features introduced in **1.0.0‑rc1** and marks
the API and event schema as stable.  There are no breaking changes
compared to the release candidate.  Key points for **1.0.0**:

* **Stable API & Schema** – The canonical event contract defined in
  `workers/src/workers/models/events.py` remains unchanged.  All
  publishers normalise numeric values and propagate optional `meta`
  fields.  Parity tests in CI continue to verify that the raw
  WebSocket path and the SDK wrappers emit identical schemas.
* **Volatility & Risk Models** – The standard deviation, EWMA, ATR and
  GARCH(1,1) models are supported.  The GARCH estimator clamps
  parameters for stability.  Risk modelling notes are included in
  `docs/OPERATIONS.md`.
* **Ops Bot & Metrics** – The asynchronous Slack/Teams bot with
  deduplication, exponential backoff and health checks is ready for
  production.  Metrics and SSE endpoints expose exposures, PnL,
  balances and kill switch status.
* **Docs & Governance** – The documentation index, RL guide, SDK
  integration guide, operations manual, governance and security
  guides remain frozen for this version.  See `docs/RELEASE_NOTES.md`
  for the consolidated release notes and `docs/GOVERNANCE.md` for
  branch protection and contribution policies.

No additional migration steps are required when upgrading from
**1.0.0‑rc1** to **1.0.0**.  Simply bump the version in your
environment (use `VERSION` file) and redeploy.