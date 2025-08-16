"""
Refactored worker entrypoint that orchestrates services using
``asyncio.TaskGroup`` for resilient concurrency.  This file wires
together the data feed, price cache, risk service and execution
service.  Individual tasks are supervised so that if one fails it
does not crash the entire application; instead, the failing task is
restarted after a brief delay.

To use this entrypoint, set the environment variable
``ATLAS_USE_REFACTORED_WORKERS=true`` when starting the worker
container.  Existing modules remain untouched for backward
compatibility.
"""

from __future__ import annotations

import asyncio
import random
import logging
import os
import sys
from typing import Any

from .services.price_cache import PriceCache
from .services.data_feed import DataFeedService
from .services.risk_service import RiskService
from .services.execution_service import ExecutionService


async def start_workers() -> None:
    """Launch the refactored services concurrently."""
    logging.basicConfig(level=logging.INFO)
    # When a database state store is configured we automatically run Alembic
    # migrations at startup.  This keeps the schema in sync without a
    # separate deploy step.  If migrations fail the worker aborts to
    # prevent running against an out of date schema.  Migrations are
    # skipped when STATE_STORE_URI is not set.
    state_store_uri_for_migrations = os.getenv("STATE_STORE_URI")
    if state_store_uri_for_migrations:
        logging.info("STATE_STORE_URI detected; running Alembic migrations")
        # Spawn a subprocess to execute the migrate_db module using the
        # current Python interpreter.  Capture stdout/stderr so we can
        # log any messages on failure.
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "scripts.migrate_db",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            logging.error(
                "Database migrations failed:\n%s", stderr.decode(errors="ignore")
            )
            raise RuntimeError("Database migration failed")
        else:
            logging.info(
                "Database migrations completed successfully:\n%s", stdout.decode(errors="ignore")
            )

    price_cache = PriceCache()
    # Determine state store: prefer database store if URI is provided, otherwise
    # fall back to JSON file store when STATE_STORE_PATH is set.
    state_store = None
    state_uri = os.getenv("STATE_STORE_URI")
    state_path = os.getenv("STATE_STORE_PATH")
    if state_uri:
        try:
            from .services.db_state_store import DatabaseStateStore
            state_store = DatabaseStateStore.from_uri(state_uri)
            # Initialize database tables
            await state_store.init_db()
        except Exception as exc:
            logging.error("Failed to initialize database state store: %s", exc)
            state_store = None
    elif state_path:
        try:
            from .services.state_store import StateStore
            state_store = StateStore(path=state_path)
        except Exception:
            state_store = None

    # Inject the event bus into the risk service so that exposure and PnL
    # updates can be published for real‑time monitoring.  When ``event_bus`` is
    # None the risk service operates silently.
    risk_service = RiskService(state_store=state_store, event_bus=event_bus)

    # Choose event bus implementation.  Preference order:
    # 1. RabbitMQ if RABBITMQ_HOST is set
    # 2. Redis if REDIS_HOST is set
    # 3. In-memory fallback
    event_bus = None
    rabbit_host = os.getenv("RABBITMQ_HOST")
    rabbit_port = os.getenv("RABBITMQ_PORT")
    rabbit_user = os.getenv("RABBITMQ_USERNAME")
    rabbit_pass = os.getenv("RABBITMQ_PASSWORD")
    if rabbit_host:
        try:
            from .services.rabbitmq_event_bus import RabbitMQEventBus  # type: ignore
            event_bus = RabbitMQEventBus(
                host=rabbit_host,
                port=int(rabbit_port) if rabbit_port else 5672,
                username=rabbit_user,
                password=rabbit_pass,
            )
            logging.info("Using RabbitMQEventBus at %s:%s", rabbit_host, rabbit_port or 5672)
        except Exception as exc:
            logging.error("Failed to initialize RabbitMQEventBus: %s", exc)
            event_bus = None
    if event_bus is None:
        from .services.event_bus import EventBus, RedisEventBus
        redis_host = os.getenv("REDIS_HOST")
        redis_port = os.getenv("REDIS_PORT")
        if redis_host and redis_port:
            try:
                event_bus = RedisEventBus(host=redis_host, port=int(redis_port))
                logging.info("Using RedisEventBus at %s:%s", redis_host, redis_port)
            except Exception as exc:
                logging.error("Failed to initialize RedisEventBus: %s", exc)
                event_bus = None
        if event_bus is None:
            event_bus = EventBus()

    # Choose the REST client implementation.  When the environment
    # variable USE_OFFICIAL_SDK is set to ``true`` the worker will
    # attempt to construct an instance of OfficialRestClient from the
    # ``coinbase-advanced-py`` package via our wrapper.  If the import
    # fails or the SDK is unavailable, it will fall back to the
    # existing HttpExchangeClient for compatibility.  Secrets are
    # loaded from environment variables or files (see
    # ``COINBASE_API_SECRET_FILE`` and ``workers/src/workers/clients/http_exchange.py`` for details).
    use_official = os.getenv("USE_OFFICIAL_SDK", "false").lower() in {"true", "1", "yes"}
    http_client = None
    # Load secrets via the default secrets manager.  This will honour
    # environment variables, *_FILE paths or AWS Secrets Manager depending on
    # SECRETS_BACKEND.
    try:
        from .secrets_manager import get_default_secrets_manager  # type: ignore
        secrets_manager = get_default_secrets_manager()
        def get_secret(name: str) -> str:
            val = secrets_manager.get_secret(name)
            return val or ""
    except Exception:
        # Fallback to direct environment lookup
        def get_secret(name: str) -> str:
            return os.getenv(name, "")
    if use_official:
        try:
            from .clients.official_sdk_client import OfficialRestClient  # type: ignore
            # Load API credentials via secrets manager
            api_key = get_secret("COINBASE_API_KEY")
            api_secret = get_secret("COINBASE_API_SECRET")
            if not api_secret:
                # Attempt to load from secret file via secrets manager
                file_path = get_secret("COINBASE_API_SECRET_FILE")
                if file_path:
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            api_secret = f.read().strip()
                    except Exception as exc:
                        logging.error("Failed to read API secret from %s: %s", file_path, exc)
            passphrase = get_secret("COINBASE_PASSPHRASE") or get_secret("COINBASE_API_PASSPHRASE")
            # Determine sandbox mode from USE_STATIC_SANDBOX (true by default)
            sandbox = os.getenv("USE_STATIC_SANDBOX", "true").lower() in {"true", "1", "yes"}
            http_client = OfficialRestClient(api_key=api_key, api_secret=api_secret, passphrase=passphrase, sandbox=sandbox)
            logging.info("Initialized OfficialRestClient (sandbox=%s)", sandbox)
        except Exception as exc:
            logging.error("Failed to initialize OfficialRestClient, falling back to HttpExchangeClient: %s", exc)
            http_client = None
    if http_client is None:
        try:
            from .clients.http_exchange import HttpExchangeClient  # type: ignore
            # Pass secrets manager to HttpExchangeClient if supported in the future
            http_client = HttpExchangeClient()
            logging.info("Initialized HttpExchangeClient")
        except Exception as exc:
            logging.error("Failed to initialize HttpExchangeClient: %s", exc)
            http_client = None

    # Initialize event store if configured.  Events are logged to a JSON lines
    # file specified by EVENT_STORE_PATH.  If the path is not set, no events
    # are persisted but they may still be published to the event bus.
    event_store = None
    event_store_path = os.getenv("EVENT_STORE_PATH")
    if event_store_path:
        try:
            from .services.event_store import EventStore  # type: ignore
            event_store = EventStore(event_store_path)
            logging.info("EventStore enabled at %s", event_store_path)
        except Exception as exc:
            logging.error("Failed to initialize EventStore: %s", exc)
            event_store = None

    exec_service = ExecutionService(
        price_cache=price_cache,
        risk_service=risk_service,
        http_client=http_client,
        event_bus=event_bus,
        event_store=event_store,
        paper_trading=os.getenv("PAPER_TRADING", "true").lower() == "true",
    )
    # Pass risk_service and event_store into the data feed so that it can record prices and log events
    data_feed = DataFeedService(price_cache, event_bus=event_bus, risk_service=risk_service, event_store=event_store)

    async def run_task(name: str, coro_func: Any) -> None:
        """Run a long‑lived coroutine with exponential backoff on failure.

        If the coroutine raises an exception, it will be restarted after a delay
        that doubles on each failure (with jitter) up to a maximum.  On a
        successful run (the coroutine returns normally), the delay is reset.
        """
        delay = 1.0
        max_delay = 60.0
        while True:
            try:
                await coro_func()
                # Reset delay on normal exit (should not normally exit)
                delay = 1.0
            except Exception as exc:
                logging.error("%s task crashed: %s", name, exc)
                # Sleep with jitter and exponential backoff
                jitter = delay * 0.1
                await asyncio.sleep(delay + (random.random() * jitter))
                delay = min(delay * 2, max_delay)

    # Dynamically load strategy classes based on environment variable
    strategy_names = [s.strip() for s in os.getenv("STRATEGIES", "").split(",") if s.strip()]
    strategies = []
    for entry in strategy_names:
        try:
            module_path, class_name = (entry, None)
            if "." in entry:
                module_path, class_name = entry.rsplit(".", 1)
            else:
                # Default to strategies.{entry}
                module_path = f"workers.src.workers.strategies.{entry}"
            mod = __import__(module_path, fromlist=[class_name] if class_name else ["*"])  # type: ignore
            cls = getattr(mod, class_name or "SimpleStrategy", None)
            if cls is not None:
                strategies.append(
                    cls(
                        name=module_path.split(".")[-1],
                        event_bus=event_bus,
                        price_cache=price_cache,
                        execution_service=exec_service,
                    )
                )
        except Exception as exc:
            logging.error("Failed to load strategy %s: %s", entry, exc)

    async with asyncio.TaskGroup() as tg:  # Python 3.11+
        tg.create_task(run_task("data_feed", data_feed.run))
        tg.create_task(run_task("execution", exec_service.run))
        for strat in strategies:
            tg.create_task(run_task(strat.name, strat.run))

        # Start metrics service to export exposures and PnL from event bus into Prometheus.
        try:
            from .services.metrics_service import MetricsService  # type: ignore
            metrics_service = MetricsService(event_bus)
            tg.create_task(run_task("metrics", metrics_service.run))
        except Exception as exc:
            logging.error("Failed to initialize MetricsService: %s", exc)

        # Start alert service to send notifications on kill switch and PnL threshold breaches.
        # The alert service is optional and controlled via ALERT_ENABLE and Slack env vars.
        try:
            from .services.alert_service import AlertService  # type: ignore
            alert_service = AlertService(event_bus)
            if alert_service.enabled:
                tg.create_task(run_task("alerts", alert_service.run))
        except Exception as exc:
            logging.error("Failed to initialize AlertService: %s", exc)


def main() -> None:
    """Entry point for running the refactored worker."""
    asyncio.run(start_workers())


if __name__ == "__main__":
    main()