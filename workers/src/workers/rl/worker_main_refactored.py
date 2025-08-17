from __future__ import annotations

from typing import Optional

# Try the flat package path first; fall back to src-layout path.
try:
    from workers.services.risk_service import RiskService  # type: ignore
except ImportError:  # pragma: no cover
    from workers.src.workers.services.risk_service import RiskService  # type: ignore


def main() -> None:
    state_store = None  # inject your real state store
    event_bus: Optional[object] = None  # defined so we pass a known symbol

    # Risk service requires an event_bus argument (can be None)
    _ = RiskService(state_store=state_store, event_bus=event_bus)

    # Choose event bus implementation (omitted)
    # ...

    # Rest of your orchestration
    print("Worker started")


if __name__ == "__main__":
    main()
