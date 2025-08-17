"""
Strategy modules for the trading platform.

Each strategy exposes an async `start()` function which runs
indefinitely, reads market data via `get_last_price`, applies a trading
rule, and enqueues `OrderRequest` objects via the execution engine's
`submit_order()` API.  Strategies should be kept simple and rely on
external services (risk engine, execution engine) for validation and
order placement.
"""

from .simple_strategy import start as start_simple_strategy  # noqa: F401
