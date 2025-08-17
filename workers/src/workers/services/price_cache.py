"""
Price cache service for storing and retrieving the latest prices for
traded products.  This service is designed to be thread‑safe and
asynchronous so it can be shared across multiple coroutines without
locking issues.  Consumers should await ``update_price`` when new
ticker data arrives and ``get_price`` when needing the most recent
value.

The cache does not enforce any expiry; callers may implement their
own timeouts if stale prices are undesirable.
"""

from __future__ import annotations

import asyncio
from typing import Dict, Optional


class PriceCache:
    """Maintain a mapping of product IDs to their latest price.

    The cache uses an asyncio lock to ensure concurrent updates and
    reads are properly synchronized.  Prices are stored as floats.
    """

    def __init__(self) -> None:
        self._prices: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def update_price(self, product_id: str, price: float) -> None:
        """Store the latest price for a product.

        Args:
            product_id: The product symbol (e.g., ``"BTC-USD"``).
            price: The new price to record.
        """
        async with self._lock:
            self._prices[product_id] = price

    async def get_price(self, product_id: str) -> Optional[float]:
        """Retrieve the most recent price for a product.

        Args:
            product_id: The product symbol.

        Returns:
            The latest price if available, otherwise ``None``.
        """
        async with self._lock:
            return self._prices.get(product_id)

    async def all_prices(self) -> Dict[str, float]:
        """Snapshot all stored prices.

        Returns a copy of the current price map.  Callers must not
        mutate the returned dictionary.
        """
        async with self._lock:
            return dict(self._prices)
