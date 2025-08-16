"""Event publisher helpers for market data and user channel events.

This module defines helper functions used by both the raw WebSocket
workers and the Coinbase SDK wrappers to publish normalised events
onto an event bus.  By centralising the normalisation and
publishing logic here, we ensure that all callers emit the same
payload shape and routing keys regardless of the underlying data
source.

Functions defined in this module perform the following steps:

1. Validate and normalise the input message using the shared
   schema contracts (:func:`normalize_ticker_event` and
   :func:`normalize_user_update_event`).  These helpers coerce
   numeric values to floats and enforce the presence of required
   keys.
2. Publish the normalised payload to the provided event bus via
   ``await event_bus.publish(event_type, payload)``.  The
   ``event_type`` is fixed as ``"ticker"`` for ticker events and
   ``"user_update"`` for user updates.
3. Return the normalised payload to the caller.  Callers may
   ignore this return value if not needed.

All functions require an event bus implementing a
``publish(event_type: str, data: Any) -> Awaitable[None]`` method.
If the event bus is ``None``, a ``RuntimeError`` is raised to
prevent silent dropping of events.

"""

from __future__ import annotations

from typing import Any, Dict

from ..models_events import (
    TickerEvent,
    UserUpdateEvent,
    normalize_ticker_event,
    normalize_user_update_event,
)


async def publish_ticker(event_bus: Any, message: Dict[str, Any]) -> TickerEvent:
    """Normalise and publish a ticker event.

    Parameters
    ----------
    event_bus : Any
        An object implementing an asynchronous ``publish`` method.
    message : Dict[str, Any]
        Raw ticker message.  Must include at least the keys
        ``product_id`` (str) and ``price`` (str or float).  Additional
        keys are ignored.  Numeric values are coerced to floats.

    Returns
    -------
    TickerEvent
        A normalised dictionary with ``product_id`` (str) and
        ``price`` (float) keys.

    Raises
    ------
    RuntimeError
        If ``event_bus`` is ``None`` or does not provide a ``publish``
        coroutine.
    Exception
        Propagated from :func:`normalize_ticker_event` when required
        keys are missing or values cannot be converted.
    """
    if event_bus is None or not hasattr(event_bus, "publish"):
        raise RuntimeError("event_bus must implement publish() for ticker events")
    norm: TickerEvent = normalize_ticker_event(message)
    # Pass through optional meta information without altering the contract
    if isinstance(message, dict) and "meta" in message:
        # Copy meta verbatim; downstream consumers should handle this field if present
        norm["meta"] = message["meta"]  # type: ignore[assignment]
    # Publish to the canonical 'ticker' topic
    await event_bus.publish("ticker", norm)
    return norm


async def publish_user_update(event_bus: Any, message: Dict[str, Any]) -> UserUpdateEvent:
    """Normalise and publish a user update event.

    Parameters
    ----------
    event_bus : Any
        An object implementing an asynchronous ``publish`` method.
    message : Dict[str, Any]
        Raw user update message.  Must include at least the key
        ``product_id`` (str).  Optional keys include ``price`` (str
        or float), ``size`` (str or float), ``side`` (str) and
        ``balance`` (str or float).  Numeric values are coerced to
        floats when present.

    Returns
    -------
    UserUpdateEvent
        A normalised dictionary with string and float values.

    Raises
    ------
    RuntimeError
        If ``event_bus`` is ``None`` or does not provide a ``publish``
        coroutine.
    Exception
        Propagated from :func:`normalize_user_update_event` when
        required keys are missing or values cannot be converted.
    """
    if event_bus is None or not hasattr(event_bus, "publish"):
        raise RuntimeError("event_bus must implement publish() for user updates")
    norm: UserUpdateEvent = normalize_user_update_event(message)
    # Preserve optional meta information
    if isinstance(message, dict) and "meta" in message:
        norm["meta"] = message["meta"]  # type: ignore[assignment]
    await event_bus.publish("user_update", norm)
    return norm