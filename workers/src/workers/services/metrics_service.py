"""
Metrics Service
===============

This module provides a service that subscribes to the internal event bus
for exposure and PnL updates and publishes these values as Prometheus
metrics.  Unlike the legacy ``telemetry`` module, it does not rely on
global state.  Instead, it listens to ``exposure_update`` and
``pnl_update`` events and updates gauges accordingly.  It can run
alongside other services within the refactored worker and shares the
existing Prometheus HTTP server started by the worker.

Configuration
-------------

The following environment variables influence the service:

* ``PROMETHEUS_PORT`` – port on which to expose the metrics HTTP endpoint.
  If multiple services call ``start_http_server`` on the same port, the
  underlying server is reused.

Metrics
-------

* ``atlas_exposure{product=...}`` – exposure in quote currency per product.
* ``atlas_open_orders`` – number of currently open orders (integer).
* ``atlas_kill_switch`` – 1 if the kill switch is engaged, 0 otherwise.
* ``atlas_daily_pnl`` – cumulative PnL for the current trading day.

Usage
-----

Instantiate ``MetricsService`` with the event bus and call its
``run()`` method inside an asyncio task.  The service runs
indefinitely and updates gauges whenever events arrive.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict

from prometheus_client import Gauge, start_http_server

logger = logging.getLogger(__name__)


class MetricsService:
    """Subscribe to event bus updates and expose metrics for Prometheus."""

    def __init__(self, event_bus: Any) -> None:
        self.event_bus = event_bus
        # Define gauges once; labels are bound on update
        self.exposure_gauge = Gauge(
            "atlas_exposure",
            "Exposure per product in quote currency",
            labelnames=["product"],
        )
        self.open_orders_gauge = Gauge(
            "atlas_open_orders",
            "Current number of open orders",
        )
        self.kill_switch_gauge = Gauge(
            "atlas_kill_switch",
            "Kill switch status (1=on,0=off)",
        )
        self.pnl_gauge = Gauge(
            "atlas_daily_pnl",
            "Cumulative daily PnL",
        )
        # Start Prometheus server if not already running
        port = int(os.environ.get("PROMETHEUS_PORT", "9108"))
        try:
            start_http_server(port)
        except Exception as exc:
            # Likely already started; ignore
            logger.debug("Prometheus server likely already running: %s", exc)

    async def _handle_exposure_updates(self) -> None:
        async for message in self.event_bus.subscribe("exposure_update"):
            if not isinstance(message, dict):
                continue
            exposures: Dict[str, float] = message.get("exposures") or {}
            # Fallback to single product exposure if exposures dict not provided
            product_id = message.get("product_id")
            if exposures and isinstance(exposures, dict):
                for product, exposure in exposures.items():
                    try:
                        self.exposure_gauge.labels(product=product).set(float(exposure))
                    except Exception:
                        pass
            elif product_id:
                try:
                    exposure_val = float(message.get("exposure", 0.0))
                    self.exposure_gauge.labels(product=product_id).set(exposure_val)
                except Exception:
                    pass
            # Update open orders gauge if present
            open_orders = message.get("open_orders")
            if open_orders is not None:
                try:
                    self.open_orders_gauge.set(float(open_orders))
                except Exception:
                    pass

    async def _handle_pnl_updates(self) -> None:
        async for message in self.event_bus.subscribe("pnl_update"):
            if not isinstance(message, dict):
                continue
            daily_pnl = message.get("daily_pnl")
            if daily_pnl is not None:
                try:
                    self.pnl_gauge.set(float(daily_pnl))
                except Exception:
                    pass
            kill_switch = message.get("kill_switch")
            if kill_switch is not None:
                try:
                    self.kill_switch_gauge.set(1 if kill_switch else 0)
                except Exception:
                    pass

    async def run(self) -> None:
        """Run both subscribers concurrently and never return."""
        if self.event_bus is None:
            logger.error("MetricsService requires an event bus")
            return
        # Run both handlers concurrently
        await asyncio.gather(
            self._handle_exposure_updates(),
            self._handle_pnl_updates(),
        )