"""Coinbase SDK User Channel Wrapper (Stub).

This module provides a stubbed interface for accessing authenticated
user data (accounts, balances, transactions) via the official
Coinbase Advanced Trade SDK.  In offline environments the
``UserChannelClient`` yields no events.  When the SDK is installed
and network access is available, developers should replace the stub
implementation with calls to the SDK’s user channels (for example,
``WebSocketClient(...).subscribe_user_channels(...)`` or REST API
calls such as ``client.list_accounts()``).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncGenerator, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from coinbase.rest import RESTClient  # type: ignore
    from coinbase.websocket import WebSocketClient  # type: ignore
except Exception:
    RESTClient = None  # type: ignore
    WebSocketClient = None  # type: ignore


class UserChannelClient:
    """Wrapper around the Coinbase SDK user/channel API.

    This client normalises incoming user update messages from the
    Coinbase SDK and publishes them via the internal event bus when
    provided.  It calls ``await event_bus.publish('user_update', payload)``
    for each normalised event.  This ensures parity with the raw
    WebSocket path used when ``USE_OFFICIAL_SDK=false``.

    Parameters
    ----------
    api_key : str
        API key for authentication.
    api_secret : str
        API secret for authentication.
    passphrase : str
        API passphrase (may be optional depending on auth mode).
    sandbox : bool
        Whether to use the sandbox environment.

    Notes
    -----
    In offline mode the ``stream`` method yields no events.  In a
    production deployment, this should connect to the user WebSocket
    channel or make periodic REST calls to fetch balances and
    transactions.  See Coinbase’s documentation for details.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        passphrase: Optional[str] = None,
        *,
        sandbox: bool = True,
        event_bus: Optional[Any] = None,
    ) -> None:
        """
        Initialise the user channel client.

        Parameters
        ----------
        api_key : str
            Coinbase API key.
        api_secret : str
            Coinbase API secret.
        passphrase : str, optional
            API passphrase if required.
        sandbox : bool, optional
            Use the sandbox environment (default ``True``).
        event_bus : Any, optional
            Optional event bus implementing a ``publish`` coroutine.  When provided
            the client will publish each user update to ``event_type='user_update'``
            via the bus in addition to yielding it.
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.sandbox = sandbox
        self.event_bus = event_bus
        self._client: Any = None
        if RESTClient:
            try:
                self._client = RESTClient(api_key=api_key, api_secret=api_secret)
            except Exception as exc:
                logger.error("Failed to initialise Coinbase REST client: %s", exc)
                self._client = None

    async def stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Yield authenticated user events (balances, fills).

        In online mode this connects to the SDK's user channel and
        yields **normalised** user update events.  Each incoming message
        is passed through :func:`normalize_user_update_event` to coerce
        numeric values to floats and validate required keys.  The
        normalised event is published to the event bus (if provided)
        before yielding.  In offline mode this yields nothing.

        **Payload schema**: see :mod:`workers.src.workers.models_events`.
        """
        from ..models_events import normalize_user_update_event  # import lazily
        if self._client is None or WebSocketClient is None:
            logger.warning(
                "Official SDK not available or failed to initialise; UserChannelClient will yield no data."
            )
            while True:
                await asyncio.sleep(1)
                if False:
                    yield {}  # pragma: no cover
        else:
            # Placeholder: subscribe to user channels via WebSocket client
            async with WebSocketClient(api_key=self.api_key, api_secret=self.api_secret) as ws:  # type: ignore[call-arg]
                await ws.subscribe(channels=["user"])
                async for msg in ws.messages():
                    try:
                        from ..services.publishers import publish_user_update  # import lazily
                        norm = await publish_user_update(self.event_bus, msg)
                    except Exception:
                        continue
                    yield norm  # type: ignore[misc]