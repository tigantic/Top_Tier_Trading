## Crypto Trading Platform

![CI Status](https://img.shields.io/badge/ci-passing-brightgreen.svg)
![Python Versions](https://img.shields.io/badge/python-3.10%20%7C%203.11-blue.svg)
![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)
![Coverage](https://img.shields.io/badge/coverage-N/A-lightgrey.svg)

> **General Availability:** Version 1.0.0 – The API and event schema are now
> stable.  Consult [`docs/RELEASE_NOTES.md`](docs/RELEASE_NOTES.md) and
> [`CHANGELOG.md`](CHANGELOG.md) for the final list of features,
> upgrade notes, and known issues.

For details on the badges displayed above and how to regenerate the
coverage badge, see [`BADGES.md`](BADGES.md).

This repository contains the scaffolding for a multi‑agent, event‑driven crypto trading platform targeting the Coinbase Advanced Trade API.  It is designed to run fully within Docker using a combination of Python and TypeScript services.  The platform is split into several independent services (API, workers, backtester, database, cache) that communicate over an internal event bus and share a common `.env` file for configuration.

### High Level Overview

1. **API Service (TypeScript)** – Exposes a REST/GraphQL interface for external clients (such as the web UI) and provides a thin wrapper around the Coinbase Advanced Trade REST API.  This service also handles OAuth flows and JWT refreshing.
2. **Worker Services (Python)** – A collection of long‑running processes responsible for market data ingestion (via WebSocket), risk management, order execution, portfolio management, and telemetry collection.  Each worker subscribes to an internal event bus and performs its domain‑specific logic.
3. **Backtester (Python)** – Replays historical market data, executes strategies in simulation, and produces performance metrics such as PnL, Sharpe ratio, and maximum drawdown.
4. **Database (Postgres)** – Stores account balances, trade history, configurations, and backtest results.  Migrations are managed via scripts in `scripts/migrate.*`.
5. **Cache (Redis)** – Provides fast access to recent market data, order books, and intermediate state for strategies and risk checks.
6. **Ops UI (Next.js)** – A minimal web dashboard (placeholder) for monitoring system health, viewing metrics, and triggering administrative tasks.

### At a glance

If you're looking for guidance on specific topics, use these shortcuts:

* **Documentation index:** See [`docs/_index.md`](docs/_index.md) for an overview of all available guides.
* **Coinbase SDK & stubs:** [`docs/COINBASE_INTEGRATION.md`](docs/COINBASE_INTEGRATION.md) details how to toggle between raw WebSockets and the official SDK wrappers.
* **Reinforcement learning:** [`docs/RL_GUIDE.md`](docs/RL_GUIDE.md) explains state/action definitions, replay buffers and training loops.
* **Operations & bots:** [`docs/OPERATIONS.md`](docs/OPERATIONS.md) provides runbooks and deployment instructions for the async Slack/Teams ops bot.
* **Security & secrets:** [`docs/SECURITY.md`](docs/SECURITY.md) describes secrets backends, Vault paths and rotation procedures.
* **Architecture overview:** [`docs/01_architecture.md`](docs/01_architecture.md) gives a conceptual description of the system.
* **Governance & contribution:** [`docs/GOVERNANCE.md`](docs/GOVERNANCE.md) outlines branch protection, code review and PR guidelines.  See [`CONTRIBUTING.md`](CONTRIBUTING.md) for contributor workflows.

### Getting Started

The project includes a Docker Compose definition under `docker/docker-compose.yml`.  The instructions below outline how to build and run the platform on both macOS/Linux and Windows.  First copy the example environment files, then build and start the services.

#### macOS / Linux (bash)

```bash
# Copy the example environment and secrets into place
cp .env.example .env
cp conf/secrets.env.example conf/secrets.env || true

# Build all Docker images using the compose file under docker/
docker compose -f docker/docker-compose.yml build --no-cache

# Start the services in detached mode
docker compose -f docker/docker-compose.yml up -d

# Tail logs from all containers
docker compose -f docker/docker-compose.yml logs --follow

# Tear down the stack when finished
docker compose -f docker/docker-compose.yml down

# Run a health check to verify environment variables
python scripts/health_check.py
```

#### Windows (PowerShell 7)

```powershell
# Copy the example environment and secrets
Copy-Item .env.example .env -ErrorAction SilentlyContinue
Copy-Item conf\secrets.env.example conf\secrets.env -ErrorAction SilentlyContinue

# Build images and start the stack
docker compose -f docker/docker-compose.yml build --no-cache
docker compose -f docker/docker-compose.yml up -d

# View consolidated logs
docker compose -f docker/docker-compose.yml logs --follow

# Shut down containers
docker compose -f docker/docker-compose.yml down

# Run a health check
python scripts\health_check.py
```

#### Smoke testing

To verify the application end‑to‑end, run the provided stub smoke tests from within the Docker container:

```bash
docker compose -f docker/docker-compose.yml run --rm workers python scripts/backtest.py --config conf/config.yaml --out ./artifacts/backtests
docker compose -f docker/docker-compose.yml run --rm workers python scripts/paper_trade.py --config conf/config.yaml --log ./artifacts/paper
docker compose -f docker/docker-compose.yml run --rm workers python scripts/live.py --config conf/config.live-btc.yaml --log ./artifacts/live
```

Each command will create a JSON file in the specified directory and print a success message to stdout.  These scripts are stubs intended solely for smoke testing; they do not execute real trading logic.

> **Note:** Live trading is disabled by default (`DRY_RUN=true`). To enable live trading you must flip the `LIVE_TRADING_DEFAULT` flag in your configuration and run the `enable-live` script.  The script will prompt for human confirmation before proceeding, ensuring that no real orders are placed accidentally.

### Database Initialization

The platform persists exposures, positions and daily PnL via the ``DatabaseStateStore`` when a `STATE_STORE_URI` is provided in your environment.  Before running the workers with a Postgres backend you must create the database schema.  A simple helper script is provided under ``scripts/init_db.py`` which will create the necessary tables if they do not exist.  For example:

```bash
python scripts/init_db.py --uri postgresql+asyncpg://user:pass@localhost:5432/trading
```

This command connects to your Postgres instance and executes ``CREATE TABLE`` statements for the ``exposures``, ``positions`` and ``daily_pnl`` tables.  You only need to run it once.  In production environments, we recommend using Alembic or another migration tool to manage schema changes over time.

### Advanced Features

The repository has evolved to include several powerful features beyond the initial scaffold:

* **Dynamic Volatility Bands** – The risk engine supports volatility‑based price bands.  Set ``VOLATILITY_WINDOW`` and ``VOLATILITY_MULT`` in your environment to enable a rolling standard‑deviation band for pre‑trade checks.  You can also choose an exponentially weighted method by setting ``VOLATILITY_METHOD=ewma`` and tuning the smoothing factor via ``VOLATILITY_ALPHA`` (e.g. 0.94).  The engine tracks recent returns per product, computes volatility and rejects orders whose limit price lies outside a configurable band.

* **Average True Range (ATR) Volatility** – In addition to standard deviation and EWMA methods, the risk engine now supports ATR‑based bands.  When ``VOLATILITY_METHOD=atr`` and ``ATR_WINDOW`` is set to a positive integer (e.g., 14), the engine computes the average of absolute percentage price changes over the specified window and scales it by ``VOLATILITY_MULT`` to determine the band width.  Orders whose limit price deviates beyond this ATR‑scaled band are rejected.
* **Persistence via PostgreSQL** – By specifying ``STATE_STORE_URI`` (e.g., `postgresql+asyncpg://...`) the risk engine will persist exposures, positions and daily PnL using SQLAlchemy.  A JSON file store is used when no URI is provided.  Database migrations are managed via Alembic and can be executed with ``python scripts/migrate_db.py``.

* **Automated Database Migrations** – When ``STATE_STORE_URI`` is defined, the refactored worker now runs Alembic migrations automatically at startup by invoking ``scripts.migrate_db``.  If migrations fail, the worker aborts to prevent running against an outdated schema.
* **Event Bus (Redis or RabbitMQ)** – A pluggable event bus decouples the data feed, strategies and execution.  When ``RABBITMQ_HOST`` is set, a RabbitMQ‑backed bus is used; when ``REDIS_HOST`` is set, a Redis bus is used; otherwise an in‑memory bus is used.  See ``worker_main_refactored.py`` for selection logic.
* **Strategy Plugin Framework** – Strategies are loaded dynamically via the ``STRATEGIES`` environment variable.  The repository includes several built‑in examples: a simple momentum strategy, a logistic regression strategy, a tabular Q‑learning strategy, a linear **DQN strategy** for reinforcement learning, a more sophisticated **Deep Q‑Network (DQN) strategy** that approximates the Q function with a small neural network, an LSTM‑based toy strategy, and a simple **SMA crossover strategy**.  The SMA strategy buys when the price crosses above its moving average and sells when it crosses below, with the window length controlled by ``SMA_WINDOW``.  For example, to enable the Q‑learning and logistic regression strategies, set:

```bash
export STRATEGIES="workers.src.workers.strategies.rl_strategy.RLStrategy,workers.src.workers.strategies.lr_strategy.LRStrategy"
```

Ensure any required ML libraries (e.g. PyTorch for RL or scikit‑learn for logistic regression) are installed in your environment.
* **Grafana Dashboards** – ``docker/docker-compose.yml`` provisions Prometheus and Grafana.  The default dashboard plots exposures, kill‑switch state, open orders and last prices.  Customize the dashboard JSON in ``docker/grafana/dashboards`` as needed.

* **PnL, Balance & Latency Panels** – The included Grafana dashboard has been extended with panels for daily PnL, account balance and order execution latency.  These metrics are exposed by the worker via Prometheus and updated automatically.
* **Real‑Time Event‑Driven Metrics** – A ``MetricsService`` subscribes to risk events on the internal event bus and exposes exposures, open orders, kill switch status and daily PnL via Prometheus gauges.  This ensures metrics reflect the latest state without polling internal objects.
* **Event Sourcing** – When ``EVENT_STORE_PATH`` is set, the data feed and execution service write raw market data and order events to a JSON Lines file.  This archive can be used to build training datasets or audit logs for further analysis.  A helper script at ``scripts/event_log_to_csv.py`` can convert the JSON Lines log into a CSV file for easy consumption.  For example:

  ```bash
  python scripts/event_log_to_csv.py \
    --input artifacts/events/events.jsonl \
    --output artifacts/events/events.csv \
    --fields event_type,timestamp,product_id,side,size,price
  ```

  The script reads each event in the log, flattens the event data and writes the selected fields to a CSV.  Missing values are left blank.
* **Slack/Teams Ops Bot (stub)** – A skeleton Slack bot script in ``scripts/ops_bot.py`` responds to ``/exposure`` and ``/position`` commands.  To enable it, install ``slack_bolt`` and set ``SLACK_BOT_TOKEN``, ``SLACK_APP_TOKEN`` and ``SLACK_SIGNING_SECRET`` environment variables.  The bot uses the refactored risk engine to report exposures and positions.
* **Alert Service** – When ``ALERT_ENABLE=true`` the worker spawns an ``AlertService`` that subscribes to PnL updates.  Alerts are triggered when the kill switch engages or when daily PnL crosses a configurable negative threshold.  Notifications can be sent to **Slack** (via ``SLACK_BOT_TOKEN`` and ``SLACK_CHANNEL_ID`` or ``SLACK_ALERT_CHANNEL``) and/or **Microsoft Teams** (via ``TEAMS_WEBHOOK_URL``).  The alert service loads credentials via the secrets manager and falls back to console logging if no notification channels are configured.  Set ``ALERT_PNL_THRESHOLD`` to a positive value (e.g., 1000) to enable PnL threshold alerts; a zero threshold disables PnL alerts.
* **Secrets Management** – The codebase provides a ``secrets_manager.py`` module that reads secrets from files, environment variables or external managers.  Supported backends include:
  * **env** (default) – Reads from environment variables or ``*_FILE`` paths (e.g. Kubernetes/Docker secrets).
  * **aws** – Fetches secrets from AWS Secrets Manager when ``SECRETS_BACKEND=aws`` is set.  Configure ``AWS_SECRETS_PREFIX`` and ``AWS_REGION`` for your environment.  JSON secrets are flattened so that nested keys can be accessed via dot notation (e.g. ``COINBASE_API_KEY.secret``).
  * **vault** – Retrieves secrets from HashiCorp Vault using ``VAULT_ADDR`` and ``VAULT_TOKEN``.  Secrets are expected under ``secret/data/{prefix}/{name}`` and a fallback to environment variables is provided if Vault is unavailable.

  These backends can be selected via the ``SECRETS_BACKEND`` environment variable.
* **CI/CD Pipeline** – The GitHub Actions workflow runs unit tests, linting, formatting, type checking, dependency vulnerability scanning via ``safety`` and ``bandit``, builds Docker images, and performs container scanning with Trivy.  Migrations are applied automatically in CI.

* **Server‑Sent Events (SSE) for Real‑Time UI** – The API service exposes a streaming endpoint at ``/api/streams/sse`` which uses Server‑Sent Events to push live risk metrics to the Ops dashboard.  By default it polls the Prometheus ``/metrics`` endpoint every few seconds and forwards exposures, PnL, kill switch state and open orders.  When ``USE_EVENT_BUS_SSE=true`` and Redis is configured (see ``REDIS_HOST``/``REDIS_PORT``), the SSE endpoint subscribes directly to the event bus channels ``exposure_update`` and ``pnl_update`` and streams state changes as they happen.  The Next.js dashboard subscribes to this endpoint and falls back to polling if SSE or Redis is unavailable.  Toggle SSE support via ``USE_SSE=true`` and choose the event bus mode via ``USE_EVENT_BUS_SSE=true`` in ``secrets.env``.

* **Official SDK Toggle** – The worker can optionally use the official Coinbase Advanced Trade SDK.  Set ``USE_OFFICIAL_SDK=true`` to construct an ``OfficialRestClient`` at runtime; otherwise it falls back to the built‑in HTTP client.  API credentials are read from environment variables or from a PEM file.

* **Coinbase SDK Integration Stubs & Harness** – The repository includes lightweight wrappers around the official Coinbase SDK for **market data** and **user channel** access (see ``workers/src/workers/clients/sdk_market_data.py`` and ``sdk_user_channel.py``).  When the SDK is not installed or network access is disabled, these wrappers yield no events but expose the expected interfaces.  A harness at ``scripts/sdk_integration_test.py`` demonstrates how to initialise these clients and stream events concurrently.  In a production deployment, replace the stub code with real SDK calls and install ``coinbase-advanced-py`` to stream live market and account data.

* **Ops Bot Enhancements** – A fully asynchronous Slack/Teams bot is provided in ``scripts/ops_bot_async.py``.  It uses Slack Bolt’s ``AsyncApp`` with **concurrency** and **retry** support, performs non‑blocking HTTP requests via ``aiohttp``, and subscribes to the internal event bus via ``redis.asyncio`` for real‑time alerts.  Deduplication and exponential backoff logic prevent duplicate notifications and handle transient failures.  A Dockerfile (``docker/ops_bot.Dockerfile``) and Helm chart (``charts/ops-bot``) are included for containerised deployment.  The bot loads its secrets via the configured secrets manager and can be deployed separately from the main workers.  Use the provided chart as a starting point and customise replica counts, resource limits and environment variables as needed.

* **Deep Reinforcement Learning Pipeline** – For more advanced strategy development, a **Deep Q‑Network** training skeleton is included in ``scripts/train_deep_rl.py``.  It defines a generic DQN architecture using either PyTorch or TensorFlow if available and falls back to placeholders when ML libraries are absent.  The script illustrates how to set up a replay buffer, approximate a Q function and perform training epochs, and serves as a template for future development.  In conjunction with the included ``DeepQNetworkStrategy`` (``workers/src/workers/strategies/deep_q_network_strategy.py``), it demonstrates how to integrate neural reinforcement learning into the trading loop.  Developers should install the appropriate ML library and implement a replay buffer, target network and optimiser for production usage.

* **CI / Test Harness Expansion** – The continuous integration pipeline has been expanded with additional test cases covering SDK stubs, the ops bot’s deduplication logic, Vault and AWS secrets backends, alert service behaviour and the DQN training skeleton.  A GitHub Actions workflow (``.github/workflows/ci.yml``) sets up Python, installs all necessary dependencies (including optional packages like ``slack_bolt``, ``aiohttp`` and ``redis``) and runs the test suite.  Integration tests exercise the wiring between services and stubs to ensure that code is ready for live deployment.  Use this CI configuration as a starting point for your own pipelines and extend it with real SDK tests when network access is available.

For more details on individual components, refer to the README files under ``workers``, ``api`` and ``ops-ui`` directories, as well as the project documentation in ``docs/``.
### Further Documentation

For detailed guidance on specific topics, see the following documents in the `docs/` directory:

* **Coinbase SDK Integration** – `docs/COINBASE_INTEGRATION.md` explains how to toggle between the raw WebSocket clients and the official Coinbase SDK wrappers, including a diagram and parity requirements.
* **Reinforcement Learning Guide** – `docs/RL_GUIDE.md` describes the state, action and reward definitions, the replay buffer implementation, and a suggested training loop for developing deep RL strategies.
* **Operations & Runbooks** – `docs/OPERATIONS.md` covers deployment of the asynchronous Slack/Teams ops bot, health and readiness endpoints, and runbooks for handling Redis downtime, Slack rate limits, Teams webhook issues, and other operational scenarios.
* **Security Guidelines** – `docs/SECURITY.md` summarises secrets management best practices, lists environment variables and their Vault paths, and provides rotation procedures and RBAC recommendations.
* **Project Governance** – `docs/GOVERNANCE.md` outlines branch protection rules, pull request workflows and roles within the project.
* **Release Notes** – `docs/RELEASE_NOTES.md` summarises the scope of the current release candidate, highlights major features and lists known limitations.

### Production checklist

Before running the trading platform in a live environment, verify each of the following:

1. **Configure secrets and environment** – Copy `.env.example` to `.env` and customise values.  Provide API credentials via your chosen secrets backend (env, AWS, Vault) and set `SECRETS_BACKEND` accordingly.
2. **Initialise the database** – If using PostgreSQL, run `python scripts/init_db.py --uri postgresql+asyncpg://user:pass@host:port/db` and ensure migrations succeed.  Set `STATE_STORE_URI` to your database URI.
3. **Select strategies** – Specify strategy classes via the `STRATEGIES` environment variable (e.g. SMA crossover, logistic regression, Q‑learning, DQN) and set any hyperparameters (`SMA_WINDOW`, `DQN_*`).
4. **Toggle SDK and event bus** – Set `USE_OFFICIAL_SDK=true` when ready to use the Coinbase SDK and `USE_EVENT_BUS_SSE=true` to stream metrics directly from the event bus.  Leave these flags false in offline mode.
5. **Enable alerts and bots** – Set `ALERT_ENABLE=true` and provide Slack/Teams credentials (`SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `SLACK_SIGNING_SECRET`, `TEAMS_WEBHOOK_URL`).  Deploy the async ops bot via the provided Helm chart or run it manually.
6. **Build and deploy services** – Use `docker compose -f docker/docker-compose.yml build` and `docker compose -f docker/docker-compose.yml up -d` to start all services.  Verify `/healthz` endpoints return `ok` and check Grafana dashboards for metrics.
