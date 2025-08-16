"""
Domain models for trading entities using Pydantic.  These models
provide validation and serialization for orders, positions, and
accounts.  By using typed models, we ensure consistent data
structures across Python and TypeScript when combined with JSON
schema codegen.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, validator


class OrderRequest(BaseModel):
    """Request to submit a new order."""

    product_id: str = Field(..., description="The instrument symbol, e.g. BTC-USD")
    side: Literal["buy", "sell"] = Field(..., description="Order side")
    size: float = Field(..., gt=0, description="Order quantity in base currency")
    price: float = Field(..., gt=0, description="Limit price")


class OrderResponse(BaseModel):
    """Response returned by an exchange when placing an order."""

    client_order_id: str
    order_id: Optional[str] = None
    status: str
    error: Optional[str] = None


class Position(BaseModel):
    product_id: str
    size: float
    cost_basis: float


class Account(BaseModel):
    id: str
    currency: str
    balance: float
    available: float
