# Worker Services

This directory contains the Python services responsible for ingesting market data, managing risk, executing trades, persisting state and publishing metrics.  Each worker is a long‑running process that subscribes to an internal **event bus** and cooperates with other services via published events.

## Overview

The refactored worker architecture is modular.  Important components include:

* **Market Data** – Connects to Coinbase via WebSocket or the [official SDK](../docs/COINBASE_INTEGRATION.md) to receive ticker updates.  Events are normalised and published to the event bus.
* **Risk Service** – Tracks exposures, volatility bands (standard deviation, EWMA or ATR), price bands, slippage and kill‑switch rules.  It emits state changes via the bus and exposes Prometheus metrics.
* **Execution Service** – Validates orders against risk rules, registers them with Coinbase (or a paper trade simulator), and updates positions and exposures accordingly.
* **Event Store** – Optionally writes raw market data and orders to a JSON Lines file for later analysis or replay.
* **Metrics Service** – Subscribes to risk events and publishes gauges for exposures, open orders, kill switch state and PnL.
* **Alert Service** – Sends notifications via Slack and/or Teams when PnL thresholds are crossed or the kill switch engages.

## Running Offline

To run the refactored worker locally without network access, first copy the environment examples and then start the worker using the provided helper script:

```bash
# Copy environment and secrets templates
cp .env.example .env
cp conf/secrets.env.example conf/secrets.env

# Set USE_OFFICIAL_SDK=false to use raw WebSockets (offline safe)
export USE_OFFICIAL_SDK=false

# Start the worker (refactored version)
python workers/src/workers/worker_main_refactored.py

# The worker will connect to the in‑memory event bus, log that no data is being produced and sleep.
```

For detailed information on toggling the SDK clients and expected event schema, see [COINBASE_INTEGRATION.md](../docs/COINBASE_INTEGRATION.md).  To understand how RL strategies work, refer to [RL_GUIDE.md](../docs/RL_GUIDE.md).