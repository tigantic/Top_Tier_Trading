"""
Database Initialization Script
==============================

This script initializes the database schema for the trading platform.
It leverages the ``DatabaseStateStore`` class to create the necessary
tables (exposures, positions and daily_pnl) when using a PostgreSQL
backend.  If you are running with the in‑memory JSON state store,
this script is not required.

Usage
-----

Run this script from the project root with a valid database URI:

.. code-block:: bash

    python scripts/init_db.py --uri postgresql+asyncpg://user:pass@localhost:5432/trading

The script connects to the database, creates tables if they do not
exist and then exits.  No data is modified or deleted if the tables
already exist.

Note
----

For production deployments, consider using a proper migration tool
such as Alembic to manage database schema changes over time.
"""

from __future__ import annotations

import argparse
import asyncio

from workers.services.db_state_store import DatabaseStateStore


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Initialize the trading platform database schema.")
    ap.add_argument(
        "--uri",
        required=True,
        help="SQLAlchemy database URI (e.g. postgresql+asyncpg://user:pass@host:5432/db)",
    )
    return ap.parse_args()


async def main_async(uri: str) -> None:
    store = DatabaseStateStore.from_uri(uri)
    await store.init_db()
    print(f"Database initialized successfully for URI: {uri}")


def main() -> None:
    args = parse_args()
    asyncio.run(main_async(args.uri))


if __name__ == "__main__":  # pragma: no cover
    main()
