# Deployment Guide

This guide walks you through deploying the AtlasTrade platform either on
macOS/Linux using bash or on Windows using PowerShell.  All commands are
provided as a single block that you can copy and paste into your terminal.

## Prerequisites

* **Docker** and **Docker Compose** installed.  On Windows, install Docker
  Desktop and ensure WSL 2 integration is enabled.  
* **Python 3.11** if you intend to run the management scripts outside of
  containers.
* A valid set of Coinbase Advanced Trade API credentials.  The API secret
  must be stored in `conf/coinbase_private_key.pem` and referenced via
  `COINBASE_API_SECRET_FILE` in `conf/secrets.env`.

## Directory layout

```
trading_platform/
├── api/                    # TypeScript API service
├── backtester/             # Historical backtester service
├── workers/                # Python agents (market data, risk, execution, etc.)
├── ops-ui/                 # Next.js dashboard
├── conf/                   # Configuration and secrets
│   ├── config.yaml         # Backtest/paper configuration
│   ├── config.live-btc.yaml# Live trading configuration
│   ├── secrets.env         # Environment variables (example)
│   ├── coinbase_private_key.pem # API secret (example placeholder)
├── scripts/                # Helper scripts (bash & PowerShell)
├── docker/                 # Container definitions
│   └── docker-compose.yml  # Compose definition used in deployment
└── README.md               # Project overview
```

## Deployment on macOS / Linux (bash)

```bash
# Navigate into the repository
cd trading_platform

# Copy example environment files
cp .env.example .env
cp conf/secrets.env.example conf/secrets.env

# Build Docker images and start the stack
docker compose -f docker/docker-compose.yml build --no-cache
docker compose -f docker/docker-compose.yml up -d

# Run smoke tests
docker compose -f docker/docker-compose.yml run --rm workers python scripts/backtest.py --config conf/config.yaml --out ./artifacts/backtests
docker compose -f docker/docker-compose.yml run --rm workers python scripts/paper_trade.py --config conf/config.yaml --log ./artifacts/paper
docker compose -f docker/docker-compose.yml run --rm workers python scripts/live.py --config conf/config.live-btc.yaml --log ./artifacts/live

# View the generated logs
ls -R artifacts

# Stop services when finished
docker compose -f docker/docker-compose.yml down
```

## Deployment on Windows (PowerShell)

```powershell
Set-Location trading_platform

# Copy example environment files
Copy-Item .env.example .env -ErrorAction SilentlyContinue
Copy-Item conf\secrets.env.example conf\secrets.env -ErrorAction SilentlyContinue

# Build images and start the services
docker compose -f docker/docker-compose.yml build --no-cache
docker compose -f docker/docker-compose.yml up -d

# Run smoke tests
docker compose -f docker/docker-compose.yml run --rm workers python scripts/backtest.py --config conf/config.yaml --out ./artifacts/backtests
docker compose -f docker/docker-compose.yml run --rm workers python scripts/paper_trade.py --config conf/config.yaml --log ./artifacts/paper
docker compose -f docker/docker-compose.yml run --rm workers python scripts/live.py --config conf/config.live-btc.yaml --log ./artifacts/live

# Inspect logs
Get-ChildItem -Recurse .\artifacts

# Tear down
docker compose -f docker/docker-compose.yml down
```

## Verifying configuration

To quickly check whether your environment variables and secrets are set,
run the bundled health check:

```bash
python scripts/health_check.py
```

It will print a list of important keys and whether they are present.

## Notes

* **Never commit real secrets** into version control.  The `conf/` directory
  contains example files only.  Replace the placeholder contents with your
  own values before running in production.
* **Live trading** is disabled by default and guarded by `DRY_RUN` and
  `SAFE_MODE`.  You must explicitly flip these flags and run the `enable-live`
  script to send real orders.
