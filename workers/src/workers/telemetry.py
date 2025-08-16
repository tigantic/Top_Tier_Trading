"""
Telemetry collector worker.

This module exposes metrics and sends structured logs to a telemetry back‑end
such as Prometheus and Loki.  It can also dispatch alerts to Slack or email
when anomalous conditions are detected.  The initial implementation simply
logs that it is running.
"""

import asyncio
import logging
import os

from prometheus_client import Gauge, start_http_server

from .market_data import last_prices
from .risk_engine import risk_engine

logger = logging.getLogger(__name__)


async def start() -> None:
    """Start the telemetry collector loop.

    This telemetry worker exposes internal state as Prometheus metrics.  It
    runs an HTTP metrics server on the port defined by the PROMETHEUS_PORT
    environment variable (default 9108) and periodically updates gauges
    reflecting exposures, open orders, kill switch status, and last prices.
    """
    port = int(os.environ.get("PROMETHEUS_PORT", "9108"))
    # Start Prometheus HTTP server (non-blocking)
    try:
        start_http_server(port)
    except Exception as exc:
        logger.warning("Failed to start Prometheus server on port %d: %s", port, exc)
    # Define gauges
    exposure_gauge = Gauge("atlas_exposure", "Exposure per product in quote currency", labelnames=["product"])
    open_orders_gauge = Gauge("atlas_open_orders", "Current number of open orders")
    kill_switch_gauge = Gauge("atlas_kill_switch", "Kill switch status (1=on,0=off)")
    price_gauge = Gauge("atlas_last_price", "Last observed price per product", labelnames=["product"])
    logger.info("Telemetry collector started on port %d", port)
    while True:
        # Update exposure and open order metrics
        for product, exposure in risk_engine.exposure.items():
            exposure_gauge.labels(product=product).set(exposure)
        open_orders_gauge.set(risk_engine.open_orders)
        kill_switch_gauge.set(1 if risk_engine.kill_switch else 0)
        # Update last price gauge
        for product, price in last_prices.items():
            price_gauge.labels(product=product).set(price)
        await asyncio.sleep(15)
