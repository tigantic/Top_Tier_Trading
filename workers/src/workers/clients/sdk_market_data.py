"""Coinbase SDK Market Data Wrapper (Stub).

This module defines a lightweight wrapper around the official Coinbase
Advanced Trade SDK for streaming market data.  In environments where
the SDK is not available (such as offline development or CI), the
wrapper falls back to a no‑op implementation that yields no data.  At
runtime, the worker should detect ``USE_OFFICIAL_SDK=true`` and call
``MarketDataClient.stream()`` instead of connecting to the raw
WebSocket.

Developers integrating with the real SDK should replace the stub
implementations below with actual calls to the SDK’s WebSocket or
REST API (e.g. ``client.market_data.stream_trades(...)``).  See the
Coinbase Advanced Trade API documentation for details.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncGenerator, Dict, Iterable, Optional

logger = logging.getLogger(__name__)

try:
    # Attempt to import the official Coinbase SDK.  This import will
    # fail in offline environments; in that case the client will be a
    # stub and produce no data.
    from coinbase.rest import RESTClient  # type: ignore
    from coinbase.websocket import WebSocketClient  # type: ignore
except Exception:
    RESTClient = None  # type: ignore
    WebSocketClient = None  # type: ignore


class MarketDataClient:
    """Wrapper around the Coinbase SDK for market data.

    This client normalises incoming ticker messages from the Coinbase
    SDK and publishes them via the internal event bus.  When
    ``event_bus`` is provided, each normalised event is sent to
    ``event_type='ticker'`` by calling
    ``await event_bus.publish('ticker', payload)``.  This makes the
    client drop‑in compatible with the raw WebSocket implementation
    used when ``USE_OFFICIAL_SDK=false``.

    Parameters
    ----------
    api_key : str
        API key for authentication.
    api_secret : str
        API secret for authentication.
    passphrase : str
        API passphrase (may be None depending on auth mode).
    sandbox : bool
        Whether to use the sandbox environment.
    products : Iterable[str]
        Product IDs to subscribe to (e.g., ["BTC-USD", "ETH-USD"]).

    Notes
    -----
    In offline mode the ``stream`` method yields no events.  In a real
    deployment, replace the stub in ``stream`` with a call to the SDK’s
    WebSocket client (e.g., ``WebSocketClient(...).subscribe(...)``).
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        passphrase: Optional[str] = None,
        *,
        sandbox: bool = True,
        products: Iterable[str] = (),
        event_bus: Optional[Any] = None,
    ) -> None:
        """
        Initialise the market data client.

        Parameters
        ----------
        api_key : str
            Coinbase API key.
        api_secret : str
            Coinbase API secret.
        passphrase : str, optional
            API passphrase if required by the key.
        sandbox : bool, optional
            Use the sandbox environment (default ``True``).  Note that in offline mode
            this flag has no effect but is present for parity with the real SDK.
        products : Iterable[str], optional
            List of product IDs to subscribe to.  Defaults to empty list.
        event_bus : Any, optional
            Optional event bus implementing a ``publish`` coroutine.  When provided
            the client will publish each ticker message to ``event_type='ticker'``
            via the bus in addition to yielding it.  This allows downstream
            consumers to receive a normalised event stream regardless of
            whether the SDK or raw WebSocket is used.
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.sandbox = sandbox
        self.products = list(products)
        self.event_bus = event_bus
        self._client: Any = None
        if RESTClient and WebSocketClient:
            try:
                # Initialise REST client; WebSocket client may depend on SDK version
                self._client = RESTClient(api_key=api_key, api_secret=api_secret)
            except Exception as exc:
                logger.error("Failed to initialise Coinbase REST client: %s", exc)
                self._client = None

    async def stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Yield ticker events as dictionaries.

        In online mode this connects to the Coinbase WebSocket via the SDK
        and yields **normalised** ticker events with ``product_id`` and
        ``price`` keys as defined in the event contract.  Before
        publishing to the event bus and yielding, each incoming message
        is passed through :func:`normalize_ticker_event` to coerce types
        and validate required fields.  In offline mode this yields
        nothing but sleeps briefly.

        **Payload schema**: see :mod:`workers.src.workers.models_events`.
        """
        if self._client is None or WebSocketClient is None:
            logger.warning(
                "Official SDK not available or failed to initialise; MarketDataClient will yield no data."
            )
            while True:
                await asyncio.sleep(1)
                if False:
                    yield {}  # pragma: no cover
        else:
            # Placeholder: replace with real subscription code in a production environment
            async with WebSocketClient(api_key=self.api_key, api_secret=self.api_secret) as ws:  # type: ignore[call-arg]
                await ws.subscribe(product_ids=self.products, channels=["ticker"])
                async for msg in ws.messages():
                    try:
                        # Normalise and publish via shared helper
                        from ..services.publishers import (
                            publish_ticker,
                        )  # local import to avoid cycles

                        norm = await publish_ticker(self.event_bus, msg)
                    except Exception:
                        continue
                    # Yield the normalised message to the caller
                    yield norm  # type: ignore[misc]
