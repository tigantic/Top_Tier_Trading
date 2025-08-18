# Upgrade and Rollback Plan for Package 1 (Version 1.1.0)

This document describes the planned upgrade of the `Top_Tier_Trading` platform from version 1.0.0 to **1.1.0** (hereafter referred to as *Package 1*).  The goal of the upgrade is to introduce multi‑user authentication, a backtesting dashboard, horizontal scaling of worker services, Redis‑backed risk state, and optional serverless deployment, while ensuring zero surprises and a safe rollback path.

## 1 Overview of Changes

| Area | Description |
|---|---|
| **Scaling and statelessness** | Scale the Python worker service to **3 replicas** (`replicas: 3`) and migrate all mutable state from in‑process variables to Redis.  Exposures, PnL and kill‑switch flags will be stored atomically using Redis commands (`hincrbyfloat`, `hget`, `get`). |
| **Authentication** | Introduce NextAuth to the Ops UI for GitHub‑based login.  Create `/pages/api/auth/[...nextauth].ts` with a GitHub provider, wrap `_app.tsx` in a `SessionProvider`, and update `index.tsx` to display session information with a sign‑out button when logged in. |
| **Backtesting dashboard** | Add a new `backtest.tsx` page featuring a simple form to trigger a backtest job and display results.  This prepares the UI for integration with the backtester service. |
| **Infrastructure** | Update `docker-compose.yml` to scale the `workers` service and to use `env_file` for secrets.  Provide an example `k8s/deployment.yaml` with Linkerd annotations and replicas set to 3.  Add a Terraform module for AWS infrastructure if deploying to the cloud. |
| **Serverless support** | Add `serverless/handler.ts` and `serverless/serverless.yml` to enable deployment of the API endpoint as an AWS Lambda function. |
| **Miscellaneous** | Refine `risk_service.py` to read and write state using a Redis client.  Add environment variables and secrets to `conf/secrets.env`.  Remove unused stateful class variables.  Ensure idempotent event handling. |

## 2 Pre‑Upgrade Checklist

1. **Create a release branch** – Branch from `main` into `release/v1.1.0` and protect it from direct pushes.
2. **Audit dependencies** – Review `package.json`, `poetry.lock` and Dockerfiles for outdated packages.  Upgrade Node to the latest LTS if necessary (18 → 20) and update dependencies only if required by the upgrade.  Regenerate the lockfiles.
3. **Populate secrets** – Copy `.env.example` to `conf/secrets.env` and fill in all required variables.  For production, create Kubernetes Secrets/ConfigMaps or AWS Secrets Manager entries.  Avoid committing secrets to version control.
4. **Update infrastructure manifests** – Apply the changes to `docker-compose.yml` (replicas, env_file) and `k8s/deployment.yaml` (replicas, Linkerd annotations).  Update Terraform scripts if deploying to AWS.
5. **Implement code changes** –
   - Refactor `workers/src/workers/services/risk_service.py` to use the passed `redis.Redis` client for all state reads/writes.  Remove in‑memory state.
   - Add `ops-ui/pages/api/auth/[...nextauth].ts`, wrap `_app.tsx` in `SessionProvider` and adjust `index.tsx` to display the authenticated user and provide a sign‑in/out flow.
   - Create `ops-ui/pages/backtest.tsx` with a form and placeholder results.  Hook it up to a `/api/backtest` endpoint (to be implemented in the API or backtester service).
   - Add `serverless/handler.ts` and `serverless/serverless.yml` to support serverless deployment.
6. **Run linters and type checkers** – Execute ESLint (`npm run lint`) for the API and UI, Ruff (`poetry run ruff`) and Mypy (`poetry run mypy`) for Python services.  Fix any reported issues.
7. **Execute tests** – Add or update unit tests for the new functionality.  Run Jest for the API, react‑testing‑library for the UI, and Pytest for the workers/backtester.  Ensure coverage meets the agreed threshold.
8. **Build containers** – Run `docker compose build` locally with the updated manifests.  Confirm that images build without errors and environment variables are correctly consumed.
9. **Generate artefacts** – Build a release candidate by compiling TypeScript (`npm run build`), building the Next.js app (`next build`), creating Python wheels (`poetry build`) and packaging the `dist/` directory along with run scripts and configuration files.  Generate an SBOM and record checksums.

## 3 Deployment Plan

1. **Staging rollout** – Deploy the new release to a staging environment using the updated Docker Compose or Kubernetes manifests.  Use canary or blue/green deployment strategies to minimise risk.  Monitor Prometheus/Grafana dashboards for anomalies in latency, error rates and order throughput.
2. **Smoke and integration tests** – Execute end‑to‑end tests against the staging environment, including login via GitHub, running backtests, placing simulated trades and verifying that metrics update correctly.  Validate that Redis state persists across worker replicas.
3. **Sign and tag release** – Once staging tests pass, tag the commit as `v1.1.0` and sign the container images using `cosign` or similar tools.  Publish the artefacts to the container registry and attach the signed zip, SBOM and checksums to the GitHub release.
4. **Production rollout** – Merge the release branch into `main` and deploy to production.  Use feature flags and progressive rollouts (e.g. 10 % of workers at a time) to manage risk.  Continue monitoring dashboards and error tracking for at least 24 hours.
5. **Post‑launch** – Prepare a runbook for on‑call engineers, update documentation and create backlog tasks for any remaining issues.

## 4 Rollback Strategy

If issues arise during or after deployment, execute the following steps to safely revert:

1. **Stop new services** – Scale down or remove the v1.1.0 deployment (e.g. set replicas back to 0 in Kubernetes or stop containers in Docker Compose).
2. **Deploy last known good version** – Redeploy the v1.0.0 containers or restore the previous tag from the container registry.  Ensure that environment variables are restored to their prior values.
3. **Revert database/state migrations** – Because state is now kept in Redis, rolling back simply requires flushing any new keys created by 1.1.0 if they are incompatible with 1.0.0.  No schema migrations are present; the database remains unchanged.
4. **Restore UI** – Remove the authentication pages and backtest dashboard from production.  Note that stale cookies may remain in users’ browsers; invalid sessions will be ignored by the v1.0.0 UI.
5. **Communicate** – Notify stakeholders that the rollback is in progress and track incident timelines.  Conduct a post‑mortem once stability is restored.

Following this plan ensures a controlled upgrade with clear checkpoints and a well‑defined rollback path.