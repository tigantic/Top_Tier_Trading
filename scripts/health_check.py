#!/usr/bin/env python
"""Simple health check utility.

This script prints out key configuration symbols and whether required
secrets are present in the environment.  It can be used by operators
to verify that the environment is correctly configured before running
trading agents.
"""

from __future__ import annotations

import os


def main() -> None:
    # List of important environment variables to report
    keys = [
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "REDIS_HOST",
        "REDIS_PORT",
        "COINBASE_API_KEY",
        "COINBASE_API_SECRET_FILE",
        "COINBASE_PASSPHRASE",
        "COINBASE_RETAIL_PORTFOLIO_ID",
        "ALLOWED_MARKETS",
        "LIVE_TRADING_DEFAULT",
        "DRY_RUN",
        "SAFE_MODE",
        "PAPER_TRADING",
    ]
    print("Health Check:")
    for key in keys:
        val = os.environ.get(key)
        status = "set" if val else "missing"
        print(f"{key}: {status}")


if __name__ == "__main__":
    main()
