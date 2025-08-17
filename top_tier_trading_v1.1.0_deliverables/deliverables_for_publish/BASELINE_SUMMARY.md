# Baseline Summary for Top_Tier_Trading (Phases 0–2)

This summary establishes a verified baseline for the `Top_Tier_Trading` crypto‑trading platform before attempting any package upgrades or hardening.  It is based on the provided code export, deployment log and upgrade plan.  Secrets have been scrubbed and replaced with placeholders.

## High‑Level Architecture

The platform is organised as a small micro‑service system.  Key services include:

| Service | Implementation | Description | Entrypoint |
|---|---|---|---|
| **API service** | TypeScript/Node.js (Express 4).  Built against **Node 18**.  Uses `express` for routing, `ws` for websockets and `redis` for a simple event bus. | Exposes REST/GraphQL endpoints and a Server‑Sent Events (SSE) stream.  Compiled with `tsc` into `dist/index.js`.  Dockerfile uses a multi‑stage build to run a production container (`node:18‑slim`). | `src/index.ts` → `dist/index.js` run via `node dist/index.js` |
| **Ops UI** | **Next.js 14** with React 18.  Front‑end uses `axios` for API calls and `chart.js`/`react‑chartjs‑2` for visualisations. | Provides an operations dashboard with risk metrics and exposures.  New authentication pages use NextAuth. | `next dev` for development or `next start` after `next build`; entrypoints live under `ops‑ui/pages`. |
| **Workers** | Python 3.11, managed via **Poetry**.  Asynchronous services use `asyncio`, `redis.asyncio`, optional `aio_pika` for RabbitMQ. | Implements market‑data ingestion, risk management, execution, metrics and alerting.  Uses an internal event bus (in‑memory, Redis or RabbitMQ). | `python -m workers.worker_main_refactored` |
| **Backtester** | Python 3.11 with Poetry. | Simulates trading strategies against historical data and provides results for a forthcoming backtesting dashboard. | `python -m backtester.backtester_main` |
| **Infrastructure services** | Postgres, Redis, Prometheus, Grafana and RabbitMQ are provided via Docker Compose.  Optional Kubernetes manifests and Terraform scripts support production deployments. | Provide persistence, caching, metrics, dashboards and messaging. | N/A |

The platform can be run locally via **Docker Compose** (`docker-compose.yml`) or orchestrated on Kubernetes using the manifests under `k8s/`.  Infrastructure can be provisioned on AWS via the Terraform module (`terraform/main.tf`).

## Technology Stack and Versions

* **Node/TS API** – Node 18; TypeScript 5.2; Express 4.18; uses Jest for tests and ESLint/Prettier for linting.  Build script compiles TS sources to JavaScript and runs in a slim runtime image.
* **Next.js UI** – Next.js 14; React 18.2; Chart.js 4.4; React Chart.js 5.2; uses Node 18 alpine base for production image.  `ops‑ui/package.json` declares it as a private package.
* **Python Workers and Backtester** – Python 3.11; Poetry for dependency management.  The shared `pyproject.toml` defines linting groups (ruff, mypy, bandit, safety) and ensures consistent tool versions.  Lint/typing are configured but not yet enforced in CI.
* **Infrastructure** – Docker Compose defines services for `db` (Postgres), `cache` (Redis), `api`, `workers`, `backtester`, `ops-ui`, `prometheus`, `grafana` and `rabbitmq`.  The `workers` service is configured to look up environment variables for RabbitMQ to determine whether to use the RabbitMQ event bus.  Kubernetes manifests under `k8s/` mirror the Compose configuration for production and include Linkerd annotations and horizontal scaling (replicas set to 3 in the upgrade plan).  Terraform scripts set up AWS VPC, EKS clusters and managed services for Postgres and Redis.

### Environment and Configuration

* Environment variables are defined in `.env.example` and loaded via `conf/secrets.env`.  Critical variables include `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT`, `REDIS_HOST`, `REDIS_PORT`, `COINBASE_API_KEY`, `ALLOWED_MARKETS`, `LIVE_TRADING_DEFAULT`, `DRY_RUN`, `SAFE_MODE`, `MAX_ORDER_NOTIONAL` and `MAX_OPEN_ORDERS`.  Many warnings in the deployment log indicate these were unset during the last build; `.env` should be populated to avoid defaults being blank.
* The Compose file forwards ports `8000` (API), `3000` (UI), `9108` (Prometheus exporter), `9090` (Prometheus), `3001` (Grafana) and `5672/15672` (RabbitMQ).  Health checks are defined for most services.
* The shared `pyproject.toml` configures ruff (line length 100), mypy (Python 3.12 target, excludes tests/docs/scripts, disables some noisy error categories) and pre‑commit hooks.  The top‑level `README.md` shows CI badges and notes that version 1.0.0 of the API/event schema is GA.

## CI/CD Overview

* **GitHub Actions** – `.github/workflows/ci.yml` triggers on pushes and pull requests to `main`.  Jobs include linting, type checking, testing and building.  Python is set up with `actions/setup-python@v5` (version 3.12) and Poetry via `abatilo/actions-poetry@v3`.  Cached dependencies are restored based on the `poetry.lock` hash.  Node jobs are not yet defined in the provided snippet; the CI pipeline may not test the Next.js and API services.
* **Reusable action** – `.github/actions/setup-python/action.yml` provides a composite action to set up Python/Poetry and install dependencies with caching.
* **Branch protection** – `PULL_REQUEST_TEMPLATE.md` requires contributors to fill in description, type of change, tests run, and to follow contribution guidelines.  There is no sign of a release workflow or SBOM generation yet.

## Current Deployment Status

The supplied **PowerShell transcript** shows the last attempted deployment on **2025‑08‑16**.  Key observations:

* `git push origin main` succeeded, indicating repository changes were pushed.
* `docker compose build` emitted numerous warnings that environment variables were unset (e.g. `POSTGRES_USER`, `POSTGRES_PASSWORD`, `ALLOWED_MARKETS`).  These defaulted to blank strings, which would lead to runtime failures.  The Compose output also notes that the `version` field in `docker-compose.yml` is obsolete.
* The build failed for the **backtester** and **workers** services because directories like `/backtester/src` and `/workers/src` were not found.  This suggests either incorrect context paths in the Dockerfiles or a missing `backtester/src` directory in the repository snapshot.
* Despite the build failures, `docker compose up -d` attempted to start containers and again warned about missing environment variables.  Without a successful build, the services would not run correctly.

## Identified Risks and Gaps

* **Missing env vars** – Many required environment variables are unset.  Sensitive credentials (e.g. Coinbase API key and secret) must be provided securely via secrets managers or Kubernetes secrets.  At minimum, `.env.example` should be copied to `.env` and filled out.
* **Build failures** – The backtester and worker Dockerfiles assume the presence of `backtester/src` and `workers/src` directories.  The export may have omitted these directories.  The build context in Compose may need to be adjusted (e.g. `context: ..` expects the root to contain these paths).
* **Incomplete CI** – Node.js services (API and Next.js) are not tested in CI; there are no lint/type checks for the front‑end or API.  Python type checking is configured but not enforced.  SBOM generation, SAST scanning and container image signing are absent.
* **Observability** – There is basic Prometheus and Grafana integration for metrics.  Logging configuration, distributed tracing and alerting integration are not fully detailed.
* **Security** – There is no mention of vulnerability scanning, secrets detection, or supply‑chain attestation.  The addition of authentication using NextAuth introduces new attack surfaces (OAuth configuration, callback URLs) that need to be secured.

This baseline will inform the subsequent upgrade and hardening phases.