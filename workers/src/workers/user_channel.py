"""
User channel worker.

Subscribes to the Coinbase Advanced Trade user channel to receive order
acknowledgements, fills, and account updates.  Only one connection per user
is allowed.  JWTs must be refreshed periodically (every ~2 minutes).  In this
scaffolding, the worker connects to the user channel and logs all incoming
messages.  When disconnected, it attempts to reconnect with exponential
backoff.
"""

import asyncio
import json
import logging
import os
from typing import Dict

import websockets
from tenacity import retry, stop_after_attempt, wait_exponential

from .clients.jwt_manager import JwtManager
from typing import Any

# Import normalisation helper for user updates.  This validates and converts
# message fields before publishing to the event bus.  See
# ``workers/src/workers/models_events.py`` for schema details.
from .models_events import UserUpdateEvent  # type: ignore
from .services.publishers import publish_user_update  # type: ignore

try:
    # Attempt to import the SDK user channel wrapper; may be unavailable in offline mode
    from .clients.sdk_user_channel import UserChannelClient  # type: ignore
except Exception:
    UserChannelClient = None  # type: ignore

logger = logging.getLogger(__name__)

_jwt_manager: JwtManager | None = None

# Optional event bus used for publishing authenticated user updates.
# Assign an object implementing ``publish(event_type, data)`` to this variable
# to receive normalised ``user_update`` events when the user channel
# produces data.  Events are dictionaries with at least ``product_id``
# (str) and may include fields such as ``price`` (float), ``side`` (str),
# ``size`` (float) and ``balance`` (float).
event_bus: Any | None = None


def _build_auth_message() -> Dict[str, str]:
    """Construct an authentication message using the current JWT."""
    global _jwt_manager
    if _jwt_manager is None:
        _jwt_manager = JwtManager()
    jwt = _jwt_manager.token
    return {"type": "subscribe", "channel": "user", "jwt": jwt}


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=30))
async def start() -> None:
    """Entry point for the user channel worker."""
    use_sdk = os.getenv("USE_OFFICIAL_SDK", "false").lower() in {"true", "1", "yes"}
    if use_sdk and UserChannelClient is not None:
        # Initialise the SDK user channel client using API credentials
        api_key = os.getenv("COINBASE_API_KEY", "")
        api_secret = os.getenv("COINBASE_API_SECRET", "")
        passphrase = os.getenv("COINBASE_PASSPHRASE", "")
        sandbox = os.getenv("USE_STATIC_SANDBOX", "true").lower() in {"true", "1", "yes"}
        # Pass event_bus into the SDK wrapper
        client = UserChannelClient(
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase or None,
            sandbox=sandbox,
            event_bus=event_bus,
        )
        logger.info("User channel worker using Coinbase SDK wrapper (sandbox=%s)", sandbox)
        async for msg in client.stream():
            # Normalise and publish via helper; skip invalid messages
            try:
                norm: UserUpdateEvent = await publish_user_update(event_bus, msg)
            except Exception:
                continue
            logger.debug("SDK user message: %s", norm)
        return
    # Fallback to raw websocket connection
    uri = "wss://advanced-trade-ws.coinbase.com"
    logger.info("Connecting to Coinbase user WebSocket at %s", uri)
    async for ws in websockets.connect(uri):
        try:
            # Start a background task to refresh the JWT periodically
            global _jwt_manager
            if _jwt_manager is None:
                _jwt_manager = JwtManager()
            refresh_task = asyncio.create_task(_jwt_manager.refresh_token())
            # Send the subscription request with the current JWT
            auth_msg = _build_auth_message()
            await ws.send(json.dumps(auth_msg))
            logger.info("Subscribed to user channel")
            async for message in ws:
                # Log and publish raw JSON messages
                logger.debug("User channel message: %s", message)
                try:
                    data = json.loads(message)
                except Exception:
                    continue
                if event_bus is not None:
                    try:
                        # Normalise and publish via helper
                        await publish_user_update(event_bus, data)
                    except Exception:
                        pass
        except Exception as exc:
            logger.warning("User channel error: %s", exc)
            await asyncio.sleep(5)
            continue
        finally:
            await ws.close()
            if 'refresh_task' in locals():
                refresh_task.cancel()
