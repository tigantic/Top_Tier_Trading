"""
Execution engine worker.

This module implements the order submission logic for the trading
platform.  Orders are received via an asynchronous queue, passed
through the risk engine for pre‑trade validation, and—if approved—
submitted to the Coinbase Advanced Trade REST API using the
`HttpExchangeClient`.  Orders failing risk checks are rejected with
warnings.  After submission, the execution engine updates the
risk engine's state to reflect new exposures and settlements.

Key features:

* An `order_queue` to decouple order placement from strategy logic.
* Pre‑trade checks via `risk_engine.pre_trade_check` enforcing
  allowed markets, notional caps, rate limits, open order caps,
  price bands, and kill switch.
* Idempotent `client_order_id` generation using UUID4.
* Optional inclusion of `retail_portfolio_id` on spot orders when
  using OAuth, as required by Coinbase Advanced Trade【8†L1-L6】.
* Automatic registration of orders and settlement handling in the
  risk engine.
* DRY_RUN support: when `DRY_RUN=true` the HTTP client includes
  the `X‑Sandbox: true` header so requests hit the static sandbox【8†L1-L6】.

Note: This implementation does not yet listen for asynchronous order
fills or cancellations from the user channel.  It assumes orders are
immediately settled with zero PnL.  Future iterations should wire
user channel events to update `risk_engine.post_trade()` with the
actual realized PnL.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from typing import Optional

from .clients.http_exchange import HttpExchangeClient
from .clients.paper_exchange import PaperExchangeClient
from .risk_engine import OrderRequest, risk_engine
from .market_data import get_last_price


logger = logging.getLogger(__name__)

# A global asyncio queue onto which strategies can enqueue OrderRequest
# instances for execution.  The execution engine listens on this queue
# and processes orders in the order they are received.
order_queue: asyncio.Queue[OrderRequest] = asyncio.Queue()


async def submit_order(order: OrderRequest) -> None:
    """Public API for submitting an order request.

    Strategies or other agents should call this coroutine to enqueue
    orders for processing by the execution engine.  It does not block
    until the order is executed; it only places the order on the
    internal queue.

    :param order: OrderRequest describing the desired trade
    """
    await order_queue.put(order)


def _build_order_payload(order: OrderRequest, client_order_id: str) -> dict:
    """Construct the payload for the REST API create order call.

    Coinbase Advanced Trade uses a nested JSON structure to describe
    orders.  For a simple limit order the configuration includes the
    limit price, size, and time in force.  This helper builds a
    minimal payload matching the API specification.  This function
    assumes spot orders and DRY_RUN mode; modifications may be needed
    for margin or advanced order types.

    :param order: OrderRequest containing product_id, side, size, price
    :param client_order_id: A unique idempotent identifier for this order
    :return: JSON payload for the API
    """
    order_cfg = {
        "limit_limit_gtc": {
            "base_size": str(order.size),
            "limit_price": str(order.price),
            "post_only": False,
        }
    }
    payload = {
        "client_order_id": client_order_id,
        "product_id": order.product_id,
        "side": order.side.lower(),
        "order_configuration": order_cfg,
    }
    return payload


async def _process_orders(client: HttpExchangeClient) -> None:
    """Internal coroutine that processes orders from the queue.

    This coroutine runs in an infinite loop, pulling orders from
    `order_queue`, performing risk checks, registering the order,
    submitting it to the REST API, and then marking it as settled.
    It logs the outcome of each stage.

    :param client: Initialized HttpExchangeClient for API calls
    """
    while True:
        order: OrderRequest = await order_queue.get()
        # For price band checks, look up the most recent ticker price from market data.
        # If unavailable, `get_last_price` returns None and the risk engine will skip
        # the band check.
        reference_price: Optional[float] = get_last_price(order.product_id)
        if not risk_engine.pre_trade_check(order, reference_price):
            logger.warning("Risk check failed for order %s %s@%s", order.product_id, order.size, order.price)
            continue
        # Generate idempotent client order id
        client_order_id = str(uuid.uuid4())
        payload = _build_order_payload(order, client_order_id)
        # Include retail_portfolio_id if using OAuth and provided
        account_mode = os.environ.get("ACCOUNT_AUTH_MODE", "api_keys").lower()
        if account_mode == "oauth":
            # Coinbase requires a retail portfolio ID for OAuth orders; use the environment
            # variable name consistent with our configuration files.
            portfolio_id = os.environ.get("COINBASE_RETAIL_PORTFOLIO_ID")
            if portfolio_id:
                payload["retail_portfolio_id"] = portfolio_id
        # Register order before sending (opens exposure and counts)
        risk_engine.register_order(order)
        try:
            # Submit order via HTTP client (respects DRY_RUN)
            response = await client.create_order(payload)
            logger.info("Submitted order %s: response=%s", client_order_id, response)
        except Exception as exc:
            logger.error("Error submitting order %s: %s", client_order_id, exc)
        finally:
            # Regardless of outcome, mark order as settled.  In a real system this
            # should be updated upon fill/cancel notification from the user channel.
            risk_engine.settle_order()
            # No realized PnL information is available; pass zero
            risk_engine.post_trade(0.0)


async def start() -> None:
    """Start the execution engine loop.

    This function initializes the HTTP client using environment
    variables, then launches the order processing coroutine.  It also
    periodically logs that the execution engine is running.  In a
    production system, this function would likely be orchestrated by
    an outer supervisor alongside other workers.
    """
    logger.info("Execution engine starting")
    # Read API credentials from environment using names consistent with .env.example
    api_key = os.environ.get("COINBASE_API_KEY", "")
    # Attempt to load the API secret directly from env; if blank, HttpExchangeClient will load from COINBASE_API_SECRET_FILE
    api_secret = os.environ.get("COINBASE_API_SECRET", "")
    passphrase = os.environ.get("COINBASE_PASSPHRASE", "")
    base_url = os.environ.get("COINBASE_BASE_URL", "https://api.exchange.coinbase.com")
    dry_run_env = os.environ.get("DRY_RUN", "true").lower()
    dry_run = dry_run_env not in ("false", "0", "no")
    max_per_min = int(os.environ.get("MAX_ORDERS_PER_MINUTE", os.environ.get("MAX_REQUESTS_PER_MINUTE", "120")))
    # Determine whether to use the paper trading client or live HTTP client.
    paper_env = os.environ.get("PAPER_TRADING", "true").lower()
    paper_mode = paper_env not in ("false", "0", "no") or dry_run
    if paper_mode:
        client = PaperExchangeClient()
    else:
        # Pass api_secret even if blank; HttpExchangeClient will attempt to load secret from file if missing.
        client = HttpExchangeClient(
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            base_url=base_url,
            dry_run=dry_run,
            max_requests_per_minute=max_per_min,
        )
    # Launch the order processing loop
    asyncio.create_task(_process_orders(client))
    # Keep the coroutine alive and periodically log health
    while True:
        logger.debug("Execution engine heartbeat: queue size=%d", order_queue.qsize())
        await asyncio.sleep(30)
