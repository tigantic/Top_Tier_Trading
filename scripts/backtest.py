#!/usr/bin/env python
"""
Backtest entry point for CI smoke tests.

This script loads a YAML configuration and writes a small JSON summary to
the specified output directory.  It does not depend on external data and
therefore can run in environments without historical price series.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a backtest (stub).")
    parser.add_argument("--config", required=True, help="Path to a YAML config file.")
    parser.add_argument("--out", required=True, help="Directory to write backtest results.")
    args = parser.parse_args()
    # Ensure output directory exists
    os.makedirs(args.out, exist_ok=True)
    # Read config file as raw text
    try:
        with open(args.config, "r", encoding="utf-8") as f:
            config_text = f.read()
    except FileNotFoundError:
        config_text = ""
    # Prepare result structure
    now = datetime.datetime.utcnow().isoformat()
    result = {
        "timestamp": now,
        "config_path": args.config,
        "config_preview": config_text[:200],
        "message": "Backtest completed (stub).",
    }
    out_path = os.path.join(args.out, "result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"Backtest stub complete. Results written to {out_path}")


if __name__ == "__main__":
    main()