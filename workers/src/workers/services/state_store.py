"""
Simple file‑based state store for persisting order events, exposures and
PnL.  This implementation writes JSON records to a file path
specified at construction time.  It is not optimized for high
throughput but provides a lightweight persistence layer without
external dependencies.  For production use, replace this with
database-backed implementations (e.g. PostgreSQL or Redis).
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import date
from typing import Any, Dict


class StateStore:
    def __init__(self, path: str = "state_store.json") -> None:
        self.path = path
        # Ensure file exists
        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"orders": [], "pnl": [], "resets": []}, f)
        self._lock = asyncio.Lock()

    async def _load(self) -> Dict[str, Any]:
        async with self._lock:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self._read_file)

    async def _save(self, data: Dict[str, Any]) -> None:
        async with self._lock:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._write_file, data)

    def _read_file(self) -> Dict[str, Any]:
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_file(self, data: Dict[str, Any]) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    async def save_order(
        self,
        client_order_id: str,
        product_id: str,
        side: str,
        size: float,
        price: float,
    ) -> None:
        record = {
            "id": client_order_id,
            "product_id": product_id,
            "side": side,
            "size": size,
            "price": price,
        }
        data = await self._load()
        data.setdefault("orders", []).append(record)
        await self._save(data)

    async def settle_order(self, client_order_id: str, fill_price: float, size: float) -> None:
        record = {
            "id": client_order_id,
            "fill_price": fill_price,
            "size": size,
        }
        data = await self._load()
        data.setdefault("settlements", []).append(record)
        await self._save(data)

    async def update_pnl(self, product_id: str, position: float, price: float) -> None:
        record = {
            "product_id": product_id,
            "position": position,
            "price": price,
        }
        data = await self._load()
        data.setdefault("pnl", []).append(record)
        await self._save(data)

    async def reset_daily(self, d: date) -> None:
        data = await self._load()
        data.setdefault("resets", []).append(d.isoformat())
        await self._save(data)
