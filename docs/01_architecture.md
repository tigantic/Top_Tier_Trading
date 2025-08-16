# Architecture Overview

[← Back to docs index](./_index.md)

The crypto trading platform is organized as a collection of services that communicate over an internal event bus and persist state in Postgres and Redis.  The design follows a multi‑agent model, where each agent (service) is responsible for a specific domain concern.  This modular approach improves testability, resilience, and scalability.

## Services

| Service        | Responsibility                                                                                 |
|---------------|-------------------------------------------------------------------------------------------------|
| **API**        | Exposes REST/GraphQL endpoints for client applications and wraps the Coinbase Advanced Trade REST API.  Handles authentication (API keys and OAuth) and performs lightweight request validation. |
| **Workers**    | A collection of asynchronous Python processes that handle market data ingestion (WebSocket), risk checks, order execution, portfolio management, and telemetry.  Each sub‑module runs concurrently under a single process supervisor. |
| **Backtester** | Runs historical simulations using recorded market data and strategies.  Produces PnL and risk metrics. |
| **Database (Postgres)** | Stores persistent state including account balances, orders, trades, strategy configurations, and backtest results. |
| **Cache (Redis)** | Provides low‑latency access to frequently accessed data such as order books and intermediate strategy state. |
| **Ops UI**     | A lightweight Next.js dashboard (to be implemented) for monitoring system health and viewing metrics. |

### Risk Engine

The risk engine provides real‑time risk checks before and after each order.
It enforces notional caps, slippage tolerance, price and volatility bands,
kill switches, and daily PnL limits.  Volatility bands can be based on
multiple models:

* **Standard deviation (STD)** – Computes the sample standard deviation of
  recent returns over a configurable window.
* **Exponentially weighted moving average (EWMA)** – Uses an exponential
  decay factor (alpha) to smooth historical volatility.
* **Average True Range (ATR)** – Calculates the average absolute return
  over a rolling window, providing a measure of market range.
* **GARCH(1,1) estimator** – A simple estimator defined in
  `workers/src/workers/risk/garch.py`.  It uses method‑of‑moments
  heuristics to fit the omega, alpha and beta parameters of a GARCH
  model without external libraries and provides a function to forecast
  volatility.  For more accurate estimation, replace this implementation
  with a full maximum likelihood estimator when network and package
  installation are available.

Users can calibrate volatility parameters offline using the
`scripts/calibrate_vol.py` utility, which reads event logs and produces
recommended window sizes and multipliers.

## Internal Event Bus

The workers share data via an in‑memory event bus (e.g., `asyncio.Queue` or a message broker).  Market data ingested from the WebSocket feed is published onto the bus; strategy modules consume this data and produce order intents; the risk engine evaluates these intents; the execution module submits approved orders; and the portfolio manager updates account state.  Telemetry is collected throughout and forwarded to monitoring systems.

## Sequence Diagrams

Detailed UML sequence diagrams will be added in later phases to illustrate interactions between modules during normal operation, reconnection, and failure scenarios.
