# Secrets Audit – Top_Tier_Trading

This document catalogues the secrets and configuration parameters required to deploy and operate the `Top_Tier_Trading` platform.  It indicates which secrets are **mandatory**, which are **optional**, how they are used, where they should be injected (environment file, Kubernetes Secret, GitHub Actions Secret) and whether they are already accounted for in existing code or configuration.  Missing secrets are flagged for addition.

## 1. Mandatory Secrets and Config Variables

| Secret / Variable | Purpose / Usage | Injection Point | Covered? | Notes |
|---|---|---|---|---|
| **GH_TOKEN** | Personal access token used by GitHub Actions to create releases, upload artefacts and fetch PR metadata. | GitHub Actions Secret (`secrets.GH_TOKEN`) | ✅ | Must be created in repository settings.  Not needed in `.env`. |
| **NEXTAUTH_URL** | Public URL for Ops UI OAuth callbacks (e.g. `https://ops.example.com`).  Used by NextAuth to construct redirect URIs. | `.env` (ops-ui), Kubernetes ConfigMap | ➖ | Added to `.env.example` as a placeholder. |
| **NEXTAUTH_SECRET** | Secret string used by NextAuth for signing and encrypting sessions.  At least 32 random bytes. | `.env`, Kubernetes Secret | ➖ | Added to `.env.example`.  Should be unique per environment. |
| **GITHUB_ID** | OAuth client ID for GitHub login via NextAuth. | `.env`, GitHub Actions Secret (if building at runtime) | ➖ | Added to `.env.example`. |
| **GITHUB_SECRET** | OAuth client secret for GitHub login. | `.env`, Kubernetes Secret | ➖ | Added to `.env.example`. |
| **POSTGRES_USER** | Database username for PostgreSQL. | `.env`, Kubernetes Secret | ✅ | Present in `.env.example`. |
| **POSTGRES_PASSWORD** | Database password. | `.env`, Kubernetes Secret | ✅ | Present in `.env.example`. |
| **POSTGRES_DB** | Database name. | `.env`, Kubernetes ConfigMap | ✅ | Present in `.env.example`. |
| **POSTGRES_PORT** | Database port. | `.env`, ConfigMap | ✅ | Defaulted to `5432` in `.env.example`. |
| **REDIS_HOST** | Redis host name. | `.env`, ConfigMap | ✅ | Present in `.env.example`. |
| **REDIS_PORT** | Redis port. | `.env`, ConfigMap | ✅ | Present in `.env.example`. |
| **REDIS_PASSWORD** | Redis password if authentication is enabled. | `.env`, Kubernetes Secret | ❌ | Not in original matrix; add if Redis ACLs are used. |
| **RABBITMQ_URL** | Connection string for RabbitMQ event bus (`amqp://user:pass@host:port/`). | `.env`, Kubernetes Secret | ➖ | Added to `.env.example`; optional if using Redis event bus. |
| **RABBITMQ_HOST** | RabbitMQ hostname (alternative to URL). | `.env`, ConfigMap | ➖ | Added to `.env.example`. |
| **RABBITMQ_PORT** | RabbitMQ port. | `.env`, ConfigMap | ➖ | Added to `.env.example`. |
| **RABBITMQ_USERNAME** | RabbitMQ username. | `.env`, Kubernetes Secret | ➖ | Added to `.env.example`. |
| **RABBITMQ_PASSWORD** | RabbitMQ password. | `.env`, Kubernetes Secret | ➖ | Added to `.env.example`. |
| **COINBASE_API_KEY** | Coinbase exchange API key ID. | `.env`, Kubernetes Secret | ✅ | Present in `.env.example`. |
| **COINBASE_API_SECRET** | Coinbase API secret.  Stored separately, referenced via `COINBASE_API_SECRET_FILE` or injected directly. | `.env`, Kubernetes Secret | ❌ | Only `COINBASE_API_SECRET_FILE` was defined; include `COINBASE_API_SECRET` if direct injection is preferred. |
| **COINBASE_API_SECRET_FILE** | Path to PEM file containing the API secret. | `.env`, Kubernetes Secret (volume mount) | ✅ | Present in `.env.example`. |
| **COINBASE_PASSPHRASE** | Coinbase API passphrase. | `.env`, Kubernetes Secret | ✅ | Present in `.env.example`. |
| **COINBASE_CLIENT_ID / CLIENT_SECRET** | Optional OAuth credentials for Coinbase retail portfolio. | `.env`, Kubernetes Secret | ✅ | Present in `.env.example`. |
| **COINBASE_RETAIL_PORTFOLIO_ID** | Optional portfolio ID for Coinbase API. | `.env`, ConfigMap | ✅ | Present in `.env.example`. |
| **COINBASE_JWT** | Optional JWT for Coinbase Advanced Trade user channel. | `.env`, Kubernetes Secret | ✅ | Present in `.env.example`. |
| **ALLOWED_MARKETS** | Comma‑separated list of trading pairs. | `.env`, ConfigMap | ✅ | Present in `.env.example`. |
| **LIVE_TRADING_DEFAULT** | Enables live trading by default. | `.env`, ConfigMap | ✅ | Present in `.env.example`. |
| **DRY_RUN** | Forces no‑side‑effects mode. | `.env`, ConfigMap | ✅ | Present in `.env.example`. |
| **SAFE_MODE** | Enables conservative risk checks. | `.env`, ConfigMap | ✅ | Present in `.env.example`. |
| **MAX_ORDER_NOTIONAL** | Maximum notional value per order. | `.env`, ConfigMap | ✅ | Present in `.env.example`. |
| **MAX_ORDERS_PER_MINUTE** | Throttles order submission rate. | `.env`, ConfigMap | ✅ | Present in `.env.example`. |
| **MAX_OPEN_ORDERS** | Maximum simultaneous open orders. | `.env`, ConfigMap | ✅ | Present in `.env.example`. |
| **OTEL_EXPORTER_OTLP_ENDPOINT** | Endpoint for exporting OpenTelemetry traces (e.g. `http://otel-collector:4317`). | `.env`, ConfigMap/Secret | ➖ | Added to `.env.example`.  Required for tracing. |
| **OTEL_RESOURCE_ATTRIBUTES** | Additional trace attributes (e.g. `service.name=api`). | `.env`, ConfigMap | ➖ | Added to `.env.example`. |
| **PROM_AUTH_USER / PROM_AUTH_PASS** | Optional credentials for protecting Prometheus `/metrics` endpoints. | `.env`, Kubernetes Secret | ➖ | Added to `.env.example`.  Needed if basic auth is enabled on metrics. |
| **GH_TOKEN** (again) | Required for the release workflow to authenticate with the GitHub API. | GitHub Actions Secret | ✅ | Must be defined in repository secrets. |

### Missing Secrets

The following secrets were not included in the original credentials matrix but are required or recommended:

* **REDIS_PASSWORD** – Use if Redis is configured with authentication.
* **RABBITMQ_USERNAME / RABBITMQ_PASSWORD** – Required when RabbitMQ is enabled for the event bus.
* **COINBASE_API_SECRET** – Some deployments may prefer to inject the secret directly rather than mounting a PEM file.  Include one or the other.

## 2. Optional / Environment Configuration

Some variables are configuration rather than secrets, but are listed here for completeness:

* `LOG_LEVEL` – Controls logging verbosity (`info`, `debug`, etc.).
* `PAPER_TRADING`, `STRATEGY_POLL_INTERVAL`, `STRATEGY_PRICE_DELTA_PCT`, `STRATEGY_SIZE` – Tune strategy behaviour for the backtester/workers.
* `PROMETHEUS_PORT` – Port on which Prometheus exporter runs (already in `.env.example`).

These values can be injected via `.env` or ConfigMaps and adjusted per environment.

## 3. Injection Guidelines

* **Local development** – Copy `config/.env.example` to `.env` and fill in all placeholders.  Do not commit `.env` to version control.
* **Docker Compose** – Define a `conf/secrets.env` file containing secrets.  Reference it via `env_file:` in `docker-compose.yml`.  Keep it out of version control.
* **Kubernetes** – Store secrets in `Secret` objects and config values in `ConfigMap`.  Mount them as environment variables or files.  See the provided `k8s/secrets-example.yaml` template.
* **GitHub Actions** – Define `GH_TOKEN`, `NEXTAUTH_URL`, `NEXTAUTH_SECRET`, `GITHUB_ID`, `GITHUB_SECRET`, and any other required secrets in repository secrets.  Reference them in workflows using `${{ secrets.<NAME> }}`.

## 4. K8s Secret Manifest Template (example)

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: trading-platform-secrets
  namespace: trading-platform
type: Opaque
stringData:
  POSTGRES_USER: "postgres"
  POSTGRES_PASSWORD: "<your-db-password>"
  REDIS_PASSWORD: "<your-redis-password>"
  NEXTAUTH_SECRET: "<32-byte-random-string>"
  GITHUB_ID: "<github-oauth-client-id>"
  GITHUB_SECRET: "<github-oauth-client-secret>"
  COINBASE_API_KEY: "<coinbase-key>"
  COINBASE_API_SECRET: "<coinbase-secret>"
  COINBASE_PASSPHRASE: "<coinbase-passphrase>"
  RABBITMQ_USERNAME: "<rabbitmq-username>"
  RABBITMQ_PASSWORD: "<rabbitmq-password>"
  PROM_AUTH_USER: "<prom-user>"
  PROM_AUTH_PASS: "<prom-pass>"
```

Adjust the namespace and keys as appropriate.  Do **not** include secrets in plaintext in version control.

## 5. Conclusion

All secrets and configuration values required for deployment have been identified and documented.  Placeholders have been added to `config/.env.example` for every mandatory secret.  Optional variables and defaults are documented.  Ensure that `GH_TOKEN` and OAuth credentials are stored in GitHub repository secrets, while database, cache and API credentials are stored in environment files or Kubernetes Secrets.  This audit aligns the deployment credentials with the codebase and CI/CD workflows.