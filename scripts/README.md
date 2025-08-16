# Scripts

This directory contains utility scripts for development, testing and operations.  All scripts are designed to run in an offline environment by default.  Below is a summary of key scripts and how to run them.

## Database & Migrations

* **init_db.py** – Initialise the Postgres schema when using the database state store.  Run:

  ```bash
  python scripts/init_db.py --uri postgresql+asyncpg://user:pass@localhost:5432/trading
  ```

* **migrate_db.py** – Execute Alembic migrations programmatically.  This is invoked automatically by the worker when `STATE_STORE_URI` is set.  You can also run it manually:

  ```bash
  python scripts/migrate_db.py --uri postgresql+asyncpg://user:pass@localhost:5432/trading
  ```

## Event Logs

* **event_log_to_csv.py** – Convert a JSON Lines event log into a CSV for analysis or training.  Example:

  ```bash
  python scripts/event_log_to_csv.py \
    --input artifacts/events/events.jsonl \
    --output artifacts/events/events.csv \
    --fields event_type,timestamp,product_id,side,size,price
  ```

* **sdk_integration_test.py** – Harness that initialises the SDK market data and user channel clients concurrently.  This script exercises the stubs when offline and can be used to verify that event bus publishing works correctly.  Run with:

  ```bash
  export USE_OFFICIAL_SDK=true
  python scripts/sdk_integration_test.py
  ```

## Reinforcement Learning

* **train_deep_rl.py** – Skeleton training loop for a Deep Q‑Network (DQN).  It falls back to placeholders when ML libraries are unavailable.  To train with a mock dataset:

  ```bash
  python scripts/train_deep_rl.py
  ```

  See [RL_GUIDE.md](../docs/RL_GUIDE.md) for details on state/action definitions, replay buffers and the training loop.

## Operations & Bots

* **ops_bot_async.py** – Fully asynchronous Slack/Teams bot with health endpoint, deduplication and retry logic.  To run the bot offline:

  ```bash
  export SLACK_BOT_TOKEN=dummy
  export SLACK_APP_TOKEN=dummy
  export SLACK_SIGNING_SECRET=dummy
  export ALERT_ENABLE=true
  python scripts/ops_bot_async.py
  ```

  The bot will start a health endpoint on `/healthz` (default port 8080) and listen for commands `/exposure`, `/pnl` and `/status`.

For additional operational guidance and deployment instructions, refer to [OPERATIONS.md](../docs/OPERATIONS.md).