"""
Alembic environment configuration for atlas-trader.

This file sets up the context for running Alembic migrations.  It reads
the database connection URL from the ``STATE_STORE_URI`` environment
variable if provided, falling back to the value in ``alembic.ini``.
It imports the SQLAlchemy ``metadata`` from the database state store
so that Alembic can autogenerate migrations if needed.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# this is the Alembic Config object, which provides access to the values
# within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.  This line sets up
# loggers basically.
fileConfig(config.config_file_name)

# Modify sys.path so that project modules can be imported.  We append
# the parent directory of this file's parent (``trading_platform``) so
# that imports like ``trading_platform.workers.src.workers.services``
# succeed when this script runs from within the Alembic context.
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

# Import metadata from the database state store to define the target
# for migrations.  If this import fails, migrations will not know
# about our tables.  Note: importing inside try/except to avoid
# breaking Alembic if optional dependencies are missing.
try:
    from trading_platform.workers.src.workers.services.db_state_store import metadata  # type: ignore
    target_metadata = metadata
except Exception:
    target_metadata = None  # type: ignore


def get_url() -> str:
    """
    Determine the database URL for Alembic.

    Priority:
    1. ``STATE_STORE_URI`` environment variable.
    2. ``sqlalchemy.url`` from the Alembic configuration.
    """
    url = os.getenv("STATE_STORE_URI")
    if url:
        return url
    return config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL.  No Engine is created
    in this mode.  Calls to context.execute() here emit the given
    string to the script output.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a
    connection with the context.
    """
    configuration = config.get_section(config.config_ini_section)
    if configuration is None:
        configuration = {}
    url = get_url()
    configuration["sqlalchemy.url"] = url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()