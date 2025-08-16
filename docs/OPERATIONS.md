## Operations & Runbooks

> 🚦 **Documentation Freeze**
>
> This operations guide is frozen for the 1.0.0 release.  Any
> updates to deployment, risk modelling or operational procedures will
> be tracked in `CHANGELOG.md` and `RELEASE_NOTES.md`.  Please refer to
> those documents before making changes.

[← Back to docs index](./_index.md)

This document provides operational guidance for the asynchronous Slack/Teams ops bot and general trading platform runtime.  Operators should familiarise themselves with the health endpoints, Helm deployment options, and runbooks for common failure scenarios.

### Ops Bot Deployment

The ops bot runs as a separate Python process that connects to Slack via the Slack Bolt SDK and optionally to Redis for real‑time alert streaming.  The bot loads its secrets via the configured secrets manager and can send alerts to both Slack and Microsoft Teams.  A container image and Helm chart are provided for deployment.

**Helm Installation**

```bash
helm repo add myrepo https://example.com/charts
helm install ops-bot myrepo/ops-bot \
  --set image.repository=myregistry/ops-bot \
  --set image.tag=latest \
  --set env.SLACK_BOT_TOKEN=... \
  --set env.SLACK_APP_TOKEN=... \
  --set env.SLACK_SIGNING_SECRET=... \
  --set env.SLACK_ALERT_CHANNEL=C12345 \
  --set env.TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/... \
  --set env.ALERT_ENABLE=true \
  --set env.ALERT_PNL_THRESHOLD=1000
```

See `charts/ops-bot/values.yaml` for all available overrides.  Secrets should be injected via Kubernetes secrets rather than set directly in values.  The chart includes `secret.yaml` and `configmap.yaml` templates to facilitate this.

### Health & Readiness

The asynchronous ops bot exposes a simple HTTP health check on `/healthz` (port `HEALTH_PORT`, default 8080).  The endpoint returns JSON of the form `{ "status": "ok" }` when it can successfully parse metrics or `{ "status": "no-data" }` when metrics are unavailable.  A readiness probe should consider both the health endpoint and whether Redis is reachable (if `ALERT_ENABLE=true`).

```
$ curl -s http://ops-bot-svc:8080/healthz
{"status": "ok"}
```

### Runbooks

| Scenario                    | Action                                                                                  |
|----------------------------|-----------------------------------------------------------------------------------------|
| **Redis unavailable**      | The bot will skip subscribing to the PnL channel and alerts will not be streamed.  Check the Redis deployment and restart the bot after Redis is back.  Alerts triggered by the kill switch will still be processed via polling. |
| **Slack rate limits**      | Slack APIs may return HTTP 429.  The bot implements exponential backoff retries; however repeated failures may require manually disabling alerts (`ALERT_ENABLE=false`) and investigating your Slack app’s rate limits. |
| **Teams webhook failure**  | Teams notifications use a simple HTTP POST.  Failures are logged.  Verify that `TEAMS_WEBHOOK_URL` is correct and that your Teams channel allows incoming webhooks.  Consider configuring both Slack and Teams for redundancy. |
| **Health check fails**     | Inspect the container logs.  If the status is `no-data`, ensure that the Prometheus metrics endpoint (`METRICS_URL`) is reachable and returning valid metrics. |
| **Secrets missing**        | Ensure your secrets manager is configured (see `docs/SECURITY.md` for backends).  The bot will exit at startup if Slack tokens are not provided. |

### Risk Modelling Notes

The risk engine supports several volatility models for price bands and PnL forecasting:

* **Standard deviation & EWMA** – Use sample standard deviation or exponentially weighted moving average of returns.  Configure via `VOLATILITY_METHOD=std` or `ewma`.
* **Average True Range (ATR)** – Computes average absolute percentage change over a window.  Set `VOLATILITY_METHOD=atr` and `ATR_WINDOW` accordingly.
* **GARCH(1,1) estimator** – A simple GARCH model in
  `workers/src/workers/risk/garch.py` estimates parameters (`omega`, `alpha`,
  `beta`) from return series using method‑of‑moments heuristics and
  forecasts future volatility.  To use GARCH, call the estimator from
  your strategy or risk checks.  See `tests/unit/test_garch.py` for
  example usage.

Operators should calibrate volatility parameters offline using
`scripts/calibrate_vol.py`, which reads event logs and produces suggested
window sizes and multipliers for EWMA and ATR.  For GARCH, manual
inspection of forecasted volatilities may be necessary until automated
calibration is available.

### Parity Checks in CI

As part of the release candidate, a CI matrix job runs the full test
suite twice: once with ``USE_OFFICIAL_SDK=false`` (raw WebSockets) and
once with ``USE_OFFICIAL_SDK=true`` (SDK wrappers).  A helper script
``scripts/run_parity.py`` invokes the workers with fake streams and
produces an ``artifacts/parity_summary.txt`` file summarising the
number of ``ticker`` and ``user_update`` events emitted by each
implementation.  Operators can inspect these summaries in the build
artifacts to confirm that the event schemas and counts are identical
across both code paths.  If parity fails, the status in the summary
file will be ``FAIL``.

In production, parity tests should always pass.  If you modify the
event schema or add new fields, update the contract in
``workers/src/workers/models/events.py`` and regenerate the parity tests.

### Idempotency & Deduplication

To prevent duplicate alerts, the bot uses a TTL cache keyed on the alert text.  Messages remain in the cache for `ALERT_DEDUP_TTL` seconds (default 60) and will not be resent during that period.  Correlation IDs are appended to alert messages to aid in tracing retries and failures.

### Concurrency & Backoff

The bot processes Slack commands concurrently and uses an exponential backoff strategy when sending alerts.  Failed message deliveries are retried up to three times with an increasing delay.  If delivery ultimately fails, the bot logs the correlation ID for investigation.