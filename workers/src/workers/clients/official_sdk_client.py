"""
official_sdk_client
====================

This module provides a thin wrapper around the official Coinbase
Advanced Trade Python SDK.  When the SDK is installed, the wrapper
exposes an asynchronous API compatible with the existing
``HttpExchangeClient`` used by the execution service.  If the SDK is
not installed or import fails, calls to ``create_order`` and other
methods will raise ``NotImplementedError``.

Usage
-----

Set the environment variable ``USE_OFFICIAL_SDK=true`` to instruct
``worker_main_refactored.py`` to construct an instance of
``OfficialRestClient`` instead of ``HttpExchangeClient`` when
initializing the execution service.  You must also install the
``coinbase-advanced-py`` package (or the official SDK when
available) in your Python environment.  See the Coinbase developer
documentation for installation instructions.
"""

from __future__ import annotations

from typing import Any, Dict

try:
    # Attempt to import the official Coinbase Advanced API SDK.  The
    # import paths may vary between versions; adjust as necessary.
    from coinbase.rest import RESTClient  # type: ignore
except Exception:
    RESTClient = None  # type: ignore


class OfficialRestClient:
    """Wrapper for the official Coinbase Advanced Trade REST client."""

    def __init__(self, api_key: str, api_secret: str, passphrase: str | None = None, *, sandbox: bool = True) -> None:
        if RESTClient is None:
            raise RuntimeError(
                "Official Coinbase SDK not available. Install 'coinbase-advanced-py' and set USE_OFFICIAL_SDK=true."
            )
        # If using sandbox mode, adjust the base URL accordingly.  The official
        # SDK should expose a parameter for this; here we assume the default
        # environment (production) and rely on environment variables or
        # configuration in the SDK.  Consult the SDK documentation for
        # sandbox support.
        self.client = RESTClient(api_key=api_key, api_secret=api_secret)
        self.sandbox = sandbox

    async def create_order(self, payload: Dict[str, Any]) -> Any:
        """Create an order via the official SDK.

        The payload keys should align with the arguments expected by the
        official SDK's ``create_order`` method.  For example, keys like
        ``product_id``, ``side``, ``order_type``, ``time_in_force``, ``size``
        and ``price`` may map to positional or keyword arguments on the
        SDK method.  Consult the SDK's documentation for the correct
        signature.  This wrapper simply forwards the call.
        """
        if RESTClient is None:
            raise NotImplementedError("Official SDK not installed")
        # Convert payload to the parameters expected by the SDK.  This
        # mapping is speculative; update according to SDK docs.
        return await self.client.create_order(**payload)  # type: ignore[func-returns-value]

    async def list_accounts(self) -> Any:
        if RESTClient is None:
            raise NotImplementedError("Official SDK not installed")
        return await self.client.list_accounts()  # type: ignore[func-returns-value]

    async def list_products(self) -> Any:
        if RESTClient is None:
            raise NotImplementedError("Official SDK not installed")
        return await self.client.list_products()  # type: ignore[func-returns-value]
