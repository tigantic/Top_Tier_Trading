# Runbook – Top_Tier_Trading Production Operations

This runbook provides step‑by‑step guidance for operating the Top_Tier_Trading platform in production.  It covers service startup, monitoring, scaling, troubleshooting and incident response.  Keep this document up to date as the system evolves.

## 1. Service Overview

| Service | Description | Startup Command | Health Check |
|---|---|---|---|
| **API (Node/Express)** | Exposes REST/GraphQL endpoints and SSE streams. | `docker compose up api` or `node dist/index.js` in `api/`. | `GET /healthz` should return HTTP 200. |
| **Ops UI (Next.js)** | Operations dashboard with authentication and backtesting. | `docker compose up ops-ui` or `next start` in `ops-ui/`. | `GET /` should return HTTP 200 and render the login page/dashboard. |
| **Workers (Python)** | Ingests market data, manages risk, executes orders, publishes metrics. | `docker compose up workers` or `python -m workers.worker_main_refactored`. | `python -m workers.healthcheck` returns exit code 0. |
| **Backtester (Python)** | Runs historical backtests on demand. | `docker compose up backtester` or `python -m backtester.backtester_main`. | `python -m backtester.healthcheck` returns exit code 0. |
| **Infrastructure services** | PostgreSQL, Redis, RabbitMQ, Prometheus, Grafana. | Managed via Docker Compose or Kubernetes manifests. | Check container health statuses via `docker compose ps` or Kubernetes probes. |

## 2. Startup Procedure

1. Ensure that `conf/secrets.env` is populated with all required environment variables (database credentials, API keys, OAuth secrets).  In Kubernetes, create Secrets and ConfigMaps accordingly.
2. Build the containers (if not already built) with:
   ```bash
   docker compose -f docker/docker-compose.yml build
   ```
3. Start the entire stack in detached mode:
   ```bash
   docker compose -f docker/docker-compose.yml up -d
   ```
4. Verify that all containers are healthy:
   ```bash
   docker compose ps
   ```
   Health status should show `healthy` for API, workers, backtester and ops-ui.  If a service fails its health check, inspect its logs (`docker compose logs <service>`).

## 3. Monitoring and Observability

* **Logs** – Logs are emitted in JSON format.  Use `docker compose logs -f <service>` to tail logs.  In Kubernetes, use `kubectl logs`.  All logs include timestamp, level and context fields (e.g. request ID, user ID).
* **Metrics** – Prometheus scrapes each service on its `/metrics` endpoint.  Grafana dashboards are provisioned in `grafana/dashboards/`.  Key panels include request rates, latency (p50/p95), error rates, worker throughput, exposure levels, backtest job counts and infrastructure metrics.
* **Alerts** – Prometheus alert rules are defined in `prometheus.yml` (see `OBSERVABILITY.md`).  Alerts are sent to the configured Alertmanager.  The most critical alerts are high error rate (>5%), high p95 latency (>200 ms) and Redis memory usage (>80%).
* **Tracing** – All services emit traces via OpenTelemetry.  Use the Jaeger/Tempo UI to view trace graphs.  This helps diagnose high latency and cross‑service calls.

## 4. Scaling & Maintenance

* **Horizontal scaling** – Workers are stateless and can be scaled up or down by adjusting the `replicas` field in the Kubernetes deployment or the `deploy.replicas` setting in Docker Compose.  Ensure that Redis has sufficient memory for the increased workload.
* **Database migrations** – Currently there are no schema migrations.  If future releases introduce migrations, run them before deploying the new version.  Use Alembic (for SQL) or Prisma (for Node) accordingly.
* **Upgrades** – Follow `UPGRADE_AND_ROLLBACK.md` for rolling upgrades.  Always deploy to staging and run tests before production rollout.
* **Secrets rotation** – Rotate API keys and database passwords regularly.  Update `conf/secrets.env` or the Kubernetes Secret and restart the affected services.  Do not store secrets in source control.

## 5. Troubleshooting

| Symptom | Possible Causes | Resolution |
|---|---|---|
| API returns 500 errors | Unhandled exceptions, database unreachable, Redis down | Check API logs for stack traces; verify database and Redis connectivity; restart API container. |
| Dashboard shows no metrics | Workers not publishing metrics, Prometheus misconfigured | Check worker logs; ensure `/metrics` endpoints are reachable; verify Prometheus scrape configs. |
| Workers crash on startup | Missing dependencies, invalid environment variables | Check `conf/secrets.env`; run `poetry install`; verify that required packages are installed. |
| High latency | Upstream API issues, database contention, overloaded workers | Check traces to locate slow spans; scale workers; inspect database locks; review third‑party API status. |
| Redis memory usage >80% | Too many open orders or exposures | Clean up old keys; increase Redis memory limit; investigate for runaway exposure updates. |

## 6. Incident Response

1. **Triage** – When an alert fires, quickly assess the impact (customer‑facing vs internal).  Consult dashboards and traces to identify the root cause.
2. **Mitigation** – Scale services, roll back the release or enable the kill switch via Redis if necessary.  Use feature flags to disable risky functionality.
3. **Communication** – Notify stakeholders via the incident channel.  Document all actions and timelines.
4. **Post‑mortem** – After resolving the issue, create a post‑mortem report outlining the root cause, mitigation steps, and improvements to prevent recurrence.

## 7. Backlog & Retro Notes

While the v1.1.0 release is feature complete, the following items are deferred to subsequent sprints:

1. **Backtester integration endpoint** – Implement the `/api/backtest` endpoint in the API and connect it to the backtester service.  Add E2E tests for full backtest execution.
2. **Expanded UI test coverage** – Introduce Playwright or Cypress tests for the Ops UI, focusing on chart rendering and error states.
3. **Automated secrets rotation** – Integrate with a secrets manager (e.g. AWS Secrets Manager or Vault) and automate rotation via CI/CD.
4. **Chaos testing** – Add fault injection tests (e.g. kill Redis, slow down the database) to validate resilience under adverse conditions.
5. **Performance benchmarking** – Conduct systematic load tests with varying concurrency levels and dataset sizes to set SLOs.
6. **Documentation enhancements** – Add architecture diagrams and API reference docs to `docs/`.  Create onboarding guides for new contributors.

## 8. Contacts

* **Primary on‑call** – `ops@top-tier.example.com`
* **DevOps** – `devops@top-tier.example.com`
* **Engineering Manager** – `em@top-tier.example.com`
* **Incident channel** – `#trading-platform-incident` on Slack/Teams

Ensure this runbook is stored in the repository and referenced in the `README.md`.  Update it whenever processes or architecture change.