"""Event schema definitions and normalisation helpers.

This module defines typed event structures for ticker and user updates
emitted by the trading platform.  It also provides helper functions
to normalise incoming messages into these structures before they are
published onto the event bus.  Using a shared contract helps ensure
that both the raw WebSocket implementation and the Coinbase SDK
wrappers produce identical payloads.

The structures are implemented using :class:`typing.TypedDict` to
specify required and optional keys without introducing runtime
dependencies.  The normalisation helpers perform minimal
validation and type coercion; they raise :class:`ValueError` if
required keys are missing.
"""

from __future__ import annotations

from typing import Any, TypedDict, Optional


class TickerEvent(TypedDict):
    """Schema for a ticker event.

    Required keys:

    * ``product_id`` (str): The product identifier, e.g. ``"BTC-USD"``.
    * ``price`` (float): The last traded or quote price as a float.
    """

    product_id: str
    price: float


class UserUpdateEvent(TypedDict, total=False):
    """Schema for an authenticated user update.

    Required keys:

    * ``product_id`` (str): The product associated with the update.

    Optional keys:

    * ``price`` (float): The fill price for order events.
    * ``size`` (float): The quantity filled.
    * ``side`` (str): ``"buy"`` or ``"sell"`` for fills.
    * ``balance`` (float): The updated account balance.
    """

    product_id: str
    price: float
    size: float
    side: str
    balance: float


def normalize_ticker_event(msg: Any) -> TickerEvent:
    """Normalise an arbitrary ticker message into a :class:`TickerEvent`.

    Parameters
    ----------
    msg : Any
        The incoming message, expected to have at least ``product_id``
        and ``price`` keys.  Values may be strings or numeric types.

    Returns
    -------
    TickerEvent
        A dictionary with ``product_id`` as a string and ``price`` as
        a float.

    Raises
    ------
    ValueError
        If ``product_id`` or ``price`` is missing from the message.
    """
    if msg is None or "product_id" not in msg or "price" not in msg:
        raise ValueError("Ticker message missing required keys 'product_id' and 'price'")
    product_id = str(msg["product_id"])
    # Coerce price to float regardless of input type
    price_val = msg["price"]
    price = float(price_val)
    return {"product_id": product_id, "price": price}


def normalize_user_update_event(msg: Any) -> UserUpdateEvent:
    """Normalise an arbitrary user update into a :class:`UserUpdateEvent`.

    Parameters
    ----------
    msg : Any
        The incoming message, expected to have at least ``product_id``.
        Optional numeric fields may be provided as strings and will
        be coerced to floats.

    Returns
    -------
    UserUpdateEvent
        A dictionary with normalised keys.  Only keys present in
        the input are included in the output.

    Raises
    ------
    ValueError
        If ``product_id`` is missing from the message.
    """
    if msg is None or "product_id" not in msg:
        raise ValueError("User update message missing required key 'product_id'")
    event: UserUpdateEvent = {"product_id": str(msg["product_id"])}
    # Normalise optional keys if present
    if "price" in msg and msg["price"] is not None:
        event["price"] = float(msg["price"])
    if "size" in msg and msg["size"] is not None:
        event["size"] = float(msg["size"])
    if "side" in msg and msg["side"] is not None:
        event["side"] = str(msg["side"])
    if "balance" in msg and msg["balance"] is not None:
        event["balance"] = float(msg["balance"])
    return event