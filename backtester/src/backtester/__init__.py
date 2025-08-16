"""
Backtester package for the crypto trading platform.

Contains modules for running event‑driven simulations against historical
market data.  The backtester can replay real market feeds, execute
strategies defined in the `strategies` package, and produce performance
metrics such as PnL, Sharpe ratio, and maximum drawdown.
"""

__all__ = ["backtester_main"]
