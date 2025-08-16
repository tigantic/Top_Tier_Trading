# Project Header

**Project Name:** Crypto Trading Platform (working title)

**Languages:** Python and TypeScript

**Containers:** `api`, `workers`, `backtester`, `db` (PostgreSQL), `cache` (Redis)

**Target Exchanges:** Coinbase Advanced Trade (REST and WebSocket)

**Live Trading Default:** `false` (must remain false until a human explicitly enables it)

**Account Authentication Modes:** API keys and OAuth

**Allowed Markets:** `BTC-USD`, `ETH-USD`, `SOL-USD` (modifiable via `.env`)

**Risk Limits:** Daily maximum loss, per‑order notional cap, maximum open orders, kill switch thresholds.  Actual values are configurable through environment variables or configuration files.

**Control Flags:** `DRY_RUN=true`, `SAFE_MODE=true`, `MAX_ORDER_NOTIONAL`, `MAX_ORDERS_PER_MINUTE`

**Secrets Management:** Store all sensitive values (API keys, client secrets, database passwords) in the `.env` file and a cloud key management service (KMS) in production.  Never log secrets or commit them to version control.

This document summarizes the key configuration parameters and defaults for the trading platform.  Adjust these values carefully and respect all risk management policies before engaging in live trading.
