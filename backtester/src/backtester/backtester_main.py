"""
Backtester CLI entry point.

This module loads historical price data from a CSV file, runs a selected
trading strategy over the specified time range, and computes performance
metrics including total PnL, annualised Sharpe ratio, and maximum
drawdown.  Currently only a simple momentum strategy is implemented.

CSV format requirements:

* Must contain at least a `timestamp` column (ISO 8601) and a `price` or `close`
  column representing the market price in the quote currency.
* Additional columns are ignored.

Environment variables influence strategy parameters:

* STRATEGY_PRICE_DELTA_PCT: percentage change threshold to trigger trades (default 0.2%).
* STRATEGY_SIZE: size of each trade in base currency (default 0.001).

Example usage:

    python -m backtester.backtester_main simple_strategy data.csv 2024-01-01T00:00:00 2024-01-31T00:00:00
"""

from __future__ import annotations

import argparse
import logging
import os
from typing import List, Tuple

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run backtests against historical data")
    parser.add_argument(
        "strategy",
        help="Name of the strategy to backtest (only 'simple_strategy' is supported)",
    )
    parser.add_argument("data_file", help="Path to CSV file containing historical prices")
    parser.add_argument("start", help="Start timestamp (ISO 8601)")
    parser.add_argument("end", help="End timestamp (ISO 8601)")
    return parser.parse_args()


def load_price_series(data_file: str, start: str, end: str) -> pd.Series:
    """Load a price time series from a CSV file within the specified range.

    :param data_file: path to CSV with columns `timestamp` and `price` or `close`
    :param start: ISO start timestamp
    :param end: ISO end timestamp
    :return: pandas Series indexed by datetime with float prices
    """
    df = pd.read_csv(data_file)
    if "price" in df.columns:
        price_col = "price"
    elif "close" in df.columns:
        price_col = "close"
    else:
        raise ValueError("CSV must contain a 'price' or 'close' column")
    # Parse timestamps
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    start_ts = pd.to_datetime(start)
    end_ts = pd.to_datetime(end)
    df = df[(df["timestamp"] >= start_ts) & (df["timestamp"] <= end_ts)].copy()
    df.sort_values("timestamp", inplace=True)
    series = pd.Series(df[price_col].astype(float).values, index=df["timestamp"], name="price")
    return series


def run_momentum_backtest(
    price_series: pd.Series,
) -> Tuple[float, List[float], List[float]]:
    """Execute a naive momentum strategy over a price series.

    The strategy buys when the price increases by more than the threshold
    and sells when it decreases below the negative threshold.  It allows
    both long and short positions and tracks realised PnL on each trade.

    :param price_series: pandas Series of prices indexed by datetime
    :return: total PnL, list of per‑trade returns, list of equity curve values
    """
    threshold = float(os.environ.get("STRATEGY_PRICE_DELTA_PCT", "0.2")) / 100.0
    size = float(os.environ.get("STRATEGY_SIZE", "0.001"))
    position = 0.0  # positive for long, negative for short
    entry_price: float | None = None
    cash = 0.0
    returns: List[float] = []
    equity_curve: List[float] = []
    last_price: float | None = None
    for ts, price in price_series.items():
        if last_price is not None and last_price > 0:
            change = (price - last_price) / last_price
            if position == 0:
                if change > threshold:
                    # open long
                    position = size
                    entry_price = price
                elif change < -threshold:
                    # open short
                    position = -size
                    entry_price = price
            elif position > 0:
                # long position open
                if change < -threshold:
                    # close long
                    pnl = (price - entry_price) * position
                    cash += pnl
                    returns.append(pnl / (entry_price * abs(position)))
                    position = 0.0
                    entry_price = None
            elif position < 0:
                # short position open
                if change > threshold:
                    # close short
                    pnl = (entry_price - price) * abs(position)
                    cash += pnl
                    returns.append(pnl / (entry_price * abs(position)))
                    position = 0.0
                    entry_price = None
        last_price = price
        # Mark equity after each price tick (including unrealised PnL)
        unrealised = 0.0
        if position != 0 and entry_price is not None:
            if position > 0:
                unrealised = (price - entry_price) * position
            else:
                unrealised = (entry_price - price) * abs(position)
        equity_curve.append(cash + unrealised)
    # Close any open position at final price
    if position != 0 and entry_price is not None and last_price is not None:
        if position > 0:
            pnl = (last_price - entry_price) * position
        else:
            pnl = (entry_price - last_price) * abs(position)
        cash += pnl
        returns.append(pnl / (entry_price * abs(position)))
        equity_curve.append(cash)
    total_pnl = cash
    return total_pnl, returns, equity_curve


def compute_sharpe_ratio(returns: List[float], period: str = "daily") -> float:
    """Compute annualised Sharpe ratio from a list of returns.

    :param returns: list of period returns (e.g., per trade)
    :param period: 'daily' or 'hourly' etc.  Daily assumed for annualisation.
    :return: Sharpe ratio (float); 0 if insufficient data or zero variance.
    """
    if not returns:
        return 0.0
    returns_arr = np.array(returns)
    mean = returns_arr.mean()
    std = returns_arr.std()
    if std == 0:
        return 0.0
    # Annualisation factor: assume ~252 trading days per year
    factor = np.sqrt(252)
    return (mean / std) * factor


def compute_max_drawdown(equity_curve: List[float]) -> float:
    """Compute maximum drawdown from an equity curve.

    :param equity_curve: list of cumulative PnL values
    :return: max drawdown as a positive float
    """
    if not equity_curve:
        return 0.0
    cum = np.array(equity_curve)
    peak = np.maximum.accumulate(cum)
    drawdown = peak - cum
    return float(drawdown.max())


def compute_win_rate(returns: List[float]) -> float:
    """Compute the proportion of winning trades.

    :param returns: list of per‑trade returns (positive or negative)
    :return: win rate as a float between 0 and 1
    """
    if not returns:
        return 0.0
    wins = sum(1 for r in returns if r > 0)
    return wins / len(returns)


def run_backtest(strategy: str, data_file: str, start: str, end: str) -> None:
    if strategy != "simple_strategy":
        raise NotImplementedError("Only 'simple_strategy' is currently supported")
    logging.info("Loading data from %s", data_file)
    price_series = load_price_series(data_file, start, end)
    logging.info("Running momentum backtest on %d ticks", len(price_series))
    total_pnl, returns, equity_curve = run_momentum_backtest(price_series)
    sharpe = compute_sharpe_ratio(returns)
    max_dd = compute_max_drawdown(equity_curve)
    win_rate = compute_win_rate(returns)
    logging.info(
        "Backtest complete: total PnL=%.2f, Sharpe=%.3f, Max Drawdown=%.2f, Win Rate=%.2f%%",
        total_pnl,
        sharpe,
        max_dd,
        win_rate * 100,
    )
    print(f"Total PnL: {total_pnl:.2f}")
    print(f"Sharpe Ratio: {sharpe:.3f}")
    print(f"Max Drawdown: {max_dd:.2f}")
    print(f"Win Rate: {win_rate * 100:.2f}%")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = parse_args()
    run_backtest(args.strategy, args.data_file, args.start, args.end)


if __name__ == "__main__":
    main()
