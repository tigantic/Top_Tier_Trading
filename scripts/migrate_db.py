"""
Database migration entrypoint for atlas-trader.

This script runs Alembic migrations up to the latest head revision.
It reads the database connection URI from the ``STATE_STORE_URI``
environment variable or from ``alembic.ini``.  Use this script in CI
and deployment pipelines to initialise or upgrade the PostgreSQL
schema before starting workers.
"""

from __future__ import annotations

import os
import pathlib

from alembic import command
from alembic.config import Config


def run_migrations() -> None:
    base_dir = pathlib.Path(__file__).resolve().parents[1]
    alembic_ini = base_dir / "alembic.ini"
    cfg = Config(str(alembic_ini))
    # Inject the DB URL into the config if provided via environment
    db_url = os.getenv("STATE_STORE_URI")
    if db_url:
        cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(cfg, "head")


if __name__ == "__main__":
    run_migrations()
