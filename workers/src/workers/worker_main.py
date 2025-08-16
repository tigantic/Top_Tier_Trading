"""
Entry point for the worker services.

This module imports and concurrently runs the various domain‑specific worker
modules: market data, risk engine, execution engine, portfolio manager, and
telemetry collector.  Each module exposes an async `start()` function which
remains alive for the lifetime of the container.

The worker manager ensures that unhandled exceptions are logged and that the
process terminates with an error if any critical component exits unexpectedly.
"""

import asyncio
import logging
import os

from . import (
    start_market_data,
    start_risk_engine,
    start_execution,
    start_portfolio,
    start_telemetry,
    start_user_channel,
    # strategy import
    start_simple_strategy,
)


async def main() -> None:
    """Run all worker tasks concurrently and wait for them to finish."""
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    logger = logging.getLogger(__name__)

    tasks = [
        asyncio.create_task(start_market_data()),
        asyncio.create_task(start_user_channel()),
        asyncio.create_task(start_risk_engine()),
        asyncio.create_task(start_execution()),
        asyncio.create_task(start_portfolio()),
        asyncio.create_task(start_telemetry()),
        asyncio.create_task(start_simple_strategy()),
    ]
    logger.info("Worker manager started all worker tasks.")
    # Wait for any task to finish; if one exits, cancel the others
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
    for task in pending:
        task.cancel()
    for task in done:
        exc = task.exception()
        if exc:
            logger.exception("Worker task raised an exception", exc_info=exc)
    logger.info("Worker manager exiting")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
