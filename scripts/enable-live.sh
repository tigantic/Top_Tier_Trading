#!/usr/bin/env bash
set -euo pipefail

echo "WARNING: You are about to enable live trading. This will allow the platform to place real orders on Coinbase."
read -p "Type YES to confirm: " CONFIRM

if [ "$CONFIRM" != "YES" ]; then
  echo "Live trading not enabled."
  exit 1
fi

if grep -q '^LIVE_TRADING_DEFAULT=' .env; then
  sed -i.bak 's/^LIVE_TRADING_DEFAULT=.*/LIVE_TRADING_DEFAULT=true/' .env
  echo "LIVE_TRADING_DEFAULT set to true in .env."
else
  echo "LIVE_TRADING_DEFAULT=true" >> .env
  echo "LIVE_TRADING_DEFAULT inserted into .env."
fi

echo "Live trading has been enabled. Make sure you understand the risks before proceeding."
