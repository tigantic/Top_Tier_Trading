#!/usr/bin/env bash
set -euo pipefail

# Run a paper trading simulation using the backtester

STRATEGY=${1:-"ma_crossover"}
START_DATE=${2:-"2023-01-01T00:00:00Z"}
END_DATE=${3:-"2023-12-31T23:59:59Z"}

echo "Running backtest for strategy $STRATEGY from $START_DATE to $END_DATE..."
docker compose run --rm backtester python -m backtester.backtester_main "$STRATEGY" "$START_DATE" "$END_DATE"
