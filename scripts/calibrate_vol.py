"""Calibrate volatility parameters from event logs.

This utility analyses a JSON Lines event log produced by the ``EventStore``
and computes simple volatility statistics for each traded product.  It
examines price series to estimate standard deviation, exponential weighted
moving average (EWMA) of returns, and average true range (ATR).  The
results are written to a Markdown report summarising recommended window
sizes and multiplier values for configuring volatility bands in the risk
engine.

The script is designed to run offline.  It does not require any
third‑party packages beyond the Python standard library.  In production,
you might extend this tool to perform GARCH estimation or more advanced
volatility modelling, but this stub provides sensible defaults based on
historical price variance.

Example usage::

    python calibrate_vol.py \
        --input artifacts/events/events.jsonl \
        --output artifacts/calibration/report.md

The ``--input`` argument may be omitted if the ``EVENT_STORE_PATH``
environment variable is set.  The output directory will be created
automatically if it does not exist.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Calibrate volatility parameters from event logs")
    parser.add_argument(
        "--input",
        "-i",
        default=os.environ.get("EVENT_STORE_PATH"),
        help="Path to the JSON Lines event log.  Defaults to EVENT_STORE_PATH environment variable.",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="artifacts/calibration/report.md",
        help="Path to the Markdown report to write.  Defaults to artifacts/calibration/report.md",
    )
    return parser.parse_args()


def read_prices(path: str) -> Dict[str, List[float]]:
    """Read price series per product from the event log.

    The event log is expected to contain entries with ``type`` set to
    ``"market_data"`` or ``"ticker"`` and a ``data`` section containing
    ``product_id`` and ``price`` keys.  The function returns a mapping
    from product ID to a list of float prices in order of appearance.
    Missing or malformed entries are ignored.
    """
    series: Dict[str, List[float]] = defaultdict(list)
    if not path or not os.path.exists(path):
        return series
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            event_type = obj.get("type")
            data = obj.get("data", {})
            if event_type in {"market_data", "ticker"} and isinstance(data, dict):
                product = data.get("product_id")
                price_str = data.get("price") or data.get("last_trade_price")
                if product and price_str:
                    try:
                        price = float(price_str)
                    except Exception:
                        continue
                    series[product].append(price)
    return series


def compute_metrics(prices: List[float]) -> Tuple[float, float, float]:
    """Compute standard deviation, EWMA and ATR for a price series.

    Returns a tuple of (std_dev, ewma, atr), where:

    * ``std_dev`` is the sample standard deviation of log returns.
    * ``ewma`` is the exponentially weighted moving average of absolute returns with alpha=0.94.
    * ``atr`` is the average true range computed as the average of absolute percentage changes.
    """
    if len(prices) < 2:
        return (0.0, 0.0, 0.0)
    returns = []
    for prev, curr in zip(prices[:-1], prices[1:]):
        if prev != 0:
            returns.append((curr - prev) / prev)
    if not returns:
        return (0.0, 0.0, 0.0)
    # Standard deviation of returns
    try:
        std_dev = statistics.stdev(returns)
    except Exception:
        std_dev = 0.0
    # EWMA of absolute returns with alpha=0.94
    alpha = 0.94
    ewma_val: float = abs(returns[0])
    for r in returns[1:]:
        ewma_val = alpha * ewma_val + (1 - alpha) * abs(r)
    # ATR as average of absolute returns
    atr_val = sum(abs(r) for r in returns) / len(returns)
    return (std_dev, ewma_val, atr_val)


def write_report(output_path: str, metrics: Dict[str, Tuple[float, float, float]]) -> None:
    """Write a Markdown report summarising volatility metrics.

    The report lists each product with its computed standard deviation,
    EWMA and ATR, and suggests default window sizes and multipliers based
    on simple heuristics.  Users should review these recommendations
    before applying them to production settings.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    lines.append("# Volatility Calibration Report\n")
    lines.append("This report summarises volatility statistics derived from the event log.\n")
    lines.append("For each product we compute the sample standard deviation of log returns,\n" "the exponentially weighted moving average (EWMA) of absolute returns with \n" "alpha=0.94, and the average true range (ATR).  These values can be used to\n" "inform the configuration of volatility bands in the risk engine.\n")
    lines.append("\n| Product | Std Dev | EWMA | ATR | Suggested Window | Suggested Multiplier |\n")
    lines.append("|--------|--------:|-----:|-----:|----------------:|--------------------:|\n")
    for product, (std_dev, ewma_val, atr_val) in sorted(metrics.items()):
        # Suggest window inversely proportional to volatility magnitude
        window = max(5, int(1 / max(std_dev, 1e-6)))
        # Suggest multiplier as 2 * volatility
        mult = round(std_dev * 2, 4)
        lines.append(f"| {product} | {std_dev:.6f} | {ewma_val:.6f} | {atr_val:.6f} | {window} | {mult} |\n")
    with open(out, "w", encoding="utf-8") as f:
        f.write("".join(lines))


def main() -> None:
    args = parse_args()
    input_path = args.input
    if not input_path:
        raise SystemExit("Input file must be specified via --input or EVENT_STORE_PATH")
    prices_by_product = read_prices(input_path)
    metrics: Dict[str, Tuple[float, float, float]] = {}
    for product, series in prices_by_product.items():
        metrics[product] = compute_metrics(series)
    write_report(args.output, metrics)
    print(f"Wrote volatility calibration report to {args.output}")


if __name__ == "__main__":  # pragma: no cover
    main()