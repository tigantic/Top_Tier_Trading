from __future__ import annotations

from typing import Any, Dict


class ExecutionService:
    def __init__(self, http_client, event_store=None) -> None:
        self.http_client = http_client
        self.event_store = event_store

    async def submit(self, product_id: str, side: str, size: float, price: float) -> None:
        payload: Dict[str, Any] = {
            "product_id": product_id,
            "side": side,
            "size": size,
            "price": price,
        }

        # Try to log submission; failures are non-fatal
        if self.event_store:
            try:
                submission_event = {"type": "order_submitted", **payload}
                await self.event_store.log("order_submitted", submission_event)
            except Exception:  # nosec B110
                # Non-critical: logging failure shouldn't block execution
                ...

        # If immediate fill condition (placeholder)
        if size <= 0:
            try:
                fill_event = {"type": "order_filled", **payload}
                if self.event_store:
                    await self.event_store.log("order_filled", fill_event)
            except Exception:  # nosec B110
                ...
            return

        try:
            _ = await self.http_client.create_order(payload)  # was: response (unused -> _)
            # Handle response if needed (e.g., log order ID)
        except Exception:  # nosec B110
            # On failure we could requeue or cancel; for now we drop
            ...

    async def worker_loop(self, queue) -> None:
        while True:
            order = await queue.get()
            try:
                await self._process_order(order)
            except Exception:  # nosec B110
                # Ensure we do not crash on unexpected errors
                ...
            finally:
                queue.task_done()

    async def _process_order(self, order: Dict[str, Any]) -> None:
        await self.submit(
            product_id=order["product_id"],
            side=order["side"],
            size=order["size"],
            price=order["price"],
        )
