from __future__ import annotations

from typing import Optional

try:
    from workers.services.risk_service import RiskService  # type: ignore
except Exception:  # pragma: no cover
    from workers.src.workers.services.risk_service import RiskService  # type: ignore


def main() -> None:
    state_store = None
    event_bus: Optional[object] = None  # defined symbol

    _ = RiskService(state_store=state_store, event_bus=event_bus)  # silence F841 by using throwaway

    print("Worker started")


if __name__ == "__main__":
    main()
