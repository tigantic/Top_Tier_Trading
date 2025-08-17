"""SDK Integration Test Harness (Offline Stub).

This script demonstrates how to initialise and run the Coinbase SDK
wrappers provided in :mod:`workers.src.workers.clients.sdk_market_data`
and :mod:`workers.src.workers.clients.sdk_user_channel`.  In an
offline development environment where the official SDK cannot be
installed or network access is unavailable, the wrappers will
yield no data.  Nevertheless, this harness shows how to wire them
together and provides clear guidance on replacing the stubbed
implementations with real SDK calls once deployed in a live
environment.

Usage
-----

Run the script directly to start streaming market data and user
events.  The harness reads API credentials and configuration from
environment variables:

``COINBASE_API_KEY``
    Your Coinbase Advanced Trade API key.

``COINBASE_API_SECRET``
    Your Coinbase Advanced Trade API secret.

``COINBASE_PASSPHRASE``
    (Optional) Passphrase for API key if required.

``ALLOWED_MARKETS``
    Comma‑separated list of product IDs to subscribe to (e.g. ``BTC-USD,ETH-USD``).

``USE_STATIC_SANDBOX``
    Set to ``true`` to use the sandbox endpoints.  Defaults to ``true`` in this
    offline harness.

Notes
-----

* In offline mode the SDK wrappers will log a warning and
  yield no events.  This harness still consumes those events and
  prints them for demonstration purposes.
* To integrate with the real Coinbase SDK, ensure the
  ``coinbase-advanced-py`` (or equivalent) package is installed and
  network access is permitted.  Replace the placeholder code in
  ``sdk_market_data.py`` and ``sdk_user_channel.py`` with real SDK
  calls.  Then this harness will stream live market data and user
  account updates.
"""

from __future__ import annotations

import asyncio
import os

try:
    # Import the stubs; when the real SDK is installed these will proxy
    # through to the actual SDK calls.
    from workers.src.workers.clients.sdk_market_data import MarketDataClient  # type: ignore
    from workers.src.workers.clients.sdk_user_channel import UserChannelClient  # type: ignore
except Exception as exc:
    raise SystemExit(f"Failed to import SDK wrappers: {exc}")


async def run_market_data() -> None:
    """Stream market data and print each event."""
    products = os.environ.get("ALLOWED_MARKETS", "BTC-USD").split(",")
    api_key = os.getenv("COINBASE_API_KEY", "")
    api_secret = os.getenv("COINBASE_API_SECRET", "")
    passphrase = os.getenv("COINBASE_PASSPHRASE") or None
    sandbox = os.getenv("USE_STATIC_SANDBOX", "true").lower() in {"true", "1", "yes"}
    client = MarketDataClient(
        api_key=api_key,
        api_secret=api_secret,
        passphrase=passphrase,
        sandbox=sandbox,
        products=products,
    )
    async for event in client.stream():
        # event is expected to be a dict with at least product_id and price
        print(f"Market event: {event}")


async def run_user_channel() -> None:
    """Stream user channel events (balances, fills) and print each event."""
    api_key = os.getenv("COINBASE_API_KEY", "")
    api_secret = os.getenv("COINBASE_API_SECRET", "")
    passphrase = os.getenv("COINBASE_PASSPHRASE") or None
    sandbox = os.getenv("USE_STATIC_SANDBOX", "true").lower() in {"true", "1", "yes"}
    client = UserChannelClient(
        api_key=api_key, api_secret=api_secret, passphrase=passphrase, sandbox=sandbox
    )
    async for event in client.stream():
        # event is expected to contain authenticated user data (fills, account updates)
        print(f"User event: {event}")


async def main() -> None:
    """Launch market data and user channel concurrently."""
    await asyncio.gather(run_market_data(), run_user_channel())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
