"""
Portfolio manager worker.

This module maintains the current account balances, open positions, and
historical trades.  It periodically queries the Coinbase Advanced Trade
REST API to refresh balances and positions.  When using OAuth, it will
ensure that a portfolio ID is attached to order requests; with API keys
it omits the portfolio ID.

The scaffolding implementation here merely logs that it is running.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


async def start() -> None:
    """Start the portfolio manager loop."""
    logger.info("Portfolio manager started")
    while True:
        # In a full implementation, query account balances and update state.
        await asyncio.sleep(300)
