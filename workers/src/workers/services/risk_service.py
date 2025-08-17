from __future__ import annotations

from typing import Dict


class RiskService:
    def __init__(self, state_store=None, event_bus=None) -> None:
        self.state_store = state_store
        self.event_bus = event_bus
        self.open_orders: Dict[str, float] = {}

    async def on_fill(self, client_order_id: str, fill_price: float, size: float) -> None:
        _ = abs(size * fill_price)  # was: notional (unused), made explicit throwaway
        if client_order_id in self.open_orders:
            _ = self.open_orders.pop(client_order_id)  # was: prev_notional (unused)
        # (rest of your logic)
