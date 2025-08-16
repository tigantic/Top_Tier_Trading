"""
Workers package for the crypto trading platform.

This package contains long‑running services responsible for ingesting market data,
running trading strategies, enforcing risk limits, executing orders, managing
portfolios, and collecting telemetry.  Each module exposes an asynchronous
`start()` function that is invoked by the central worker manager in
`worker_main.py`.
"""

from .market_data import start as start_market_data  # noqa: F401
from .risk_engine import start as start_risk_engine  # noqa: F401
from .execution import start as start_execution  # noqa: F401
from .portfolio import start as start_portfolio  # noqa: F401
from .telemetry import start as start_telemetry  # noqa: F401
from .user_channel import start as start_user_channel  # noqa: F401
from .strategies import start_simple_strategy  # noqa: F401
