"""
db_state_store
===============

This module implements a persistent state store using PostgreSQL via
SQLAlchemy's async engine.  It provides a drop-in replacement for
``state_store.py`` that persists exposures, open orders, positions, and
daily profit and loss to a relational database.  The store can be used
by the ``RiskService`` to maintain state across restarts and provide a
reliable audit trail.  To enable the database store, set the
``STATE_STORE_URI`` environment variable to a valid SQLAlchemy URL
(e.g., ``postgresql+asyncpg://user:password@host:5432/trading``) and
pass an instance of ``DatabaseStateStore`` to ``RiskService`` at
initialization.

Tables:
  - exposures(product_id TEXT PRIMARY KEY, notional NUMERIC)
  - positions(product_id TEXT PRIMARY KEY, quantity NUMERIC, average_price NUMERIC)
  - daily_pnl(id SERIAL PRIMARY KEY, trade_date DATE, pnl NUMERIC)

Note: Database schema migration and versioning are beyond the scope of
this example.  In a real system, use Alembic or a similar tool to
manage migrations.
"""

from __future__ import annotations

import asyncio
import datetime as dt
from decimal import Decimal
from typing import Dict, Optional

from sqlalchemy import (
    Column,
    Date,
    Numeric,
    String,
    Integer,
    MetaData,
    Table,
    insert,
    select,
    update,
    delete,
)
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy.orm import registry, mapped_column


# Define SQLAlchemy tables using classical mapping for clarity
metadata = MetaData()

exposures_table = Table(
    "exposures",
    metadata,
    Column("product_id", String, primary_key=True),
    Column("notional", Numeric(precision=18, scale=8), nullable=False, default=0),
)

positions_table = Table(
    "positions",
    metadata,
    Column("product_id", String, primary_key=True),
    Column("quantity", Numeric(precision=18, scale=8), nullable=False, default=0),
    Column("average_price", Numeric(precision=18, scale=8), nullable=False, default=0),
)

daily_pnl_table = Table(
    "daily_pnl",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("trade_date", Date, nullable=False),
    Column("pnl", Numeric(precision=18, scale=8), nullable=False, default=0),
)


class DatabaseStateStore:
    """Persistent state store backed by PostgreSQL using SQLAlchemy."""

    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    @classmethod
    def from_uri(cls, uri: str) -> "DatabaseStateStore":
        """Create a state store from a SQLAlchemy database URI."""
        engine = create_async_engine(uri, echo=False, future=True)
        return cls(engine)

    async def init_db(self) -> None:
        """Create tables if they do not exist."""
        async with self.engine.begin() as conn:
            await conn.run_sync(metadata.create_all)

    async def save_order(self, product_id: str, notional: float) -> None:
        """Increment exposure for a new order."""
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                # Upsert exposure
                result = await session.execute(
                    select(exposures_table.c.notional).where(
                        exposures_table.c.product_id == product_id
                    )
                )
                row = result.fetchone()
                if row is None:
                    await session.execute(
                        insert(exposures_table).values(
                            product_id=product_id, notional=Decimal(notional)
                        )
                    )
                else:
                    current = row[0] or Decimal(0)
                    await session.execute(
                        update(exposures_table)
                        .where(exposures_table.c.product_id == product_id)
                        .values(notional=current + Decimal(notional))
                    )

    async def settle_order(self, product_id: str, notional: float) -> None:
        """Decrement exposure when an order is filled or cancelled."""
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                result = await session.execute(
                    select(exposures_table.c.notional).where(
                        exposures_table.c.product_id == product_id
                    )
                )
                row = result.fetchone()
                if row:
                    current = row[0] or Decimal(0)
                    new_value = current - Decimal(notional)
                    if new_value <= 0:
                        await session.execute(
                            delete(exposures_table).where(
                                exposures_table.c.product_id == product_id
                            )
                        )
                    else:
                        await session.execute(
                            update(exposures_table)
                            .where(exposures_table.c.product_id == product_id)
                            .values(notional=new_value)
                        )

    async def update_position(
        self, product_id: str, quantity: float, average_price: float
    ) -> None:
        """Upsert a position for a product."""
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                result = await session.execute(
                    select(positions_table.c.quantity, positions_table.c.average_price).where(
                        positions_table.c.product_id == product_id
                    )
                )
                row = result.fetchone()
                if row is None:
                    await session.execute(
                        insert(positions_table).values(
                            product_id=product_id,
                            quantity=Decimal(quantity),
                            average_price=Decimal(average_price),
                        )
                    )
                else:
                    await session.execute(
                        update(positions_table)
                        .where(positions_table.c.product_id == product_id)
                        .values(
                            quantity=Decimal(quantity),
                            average_price=Decimal(average_price),
                        )
                    )

    async def update_daily_pnl(self, trade_date: dt.date, pnl: float) -> None:
        """Append a daily PnL entry."""
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                await session.execute(
                    insert(daily_pnl_table).values(
                        trade_date=trade_date, pnl=Decimal(pnl)
                    )
                )

    async def reset_daily(self) -> None:
        """Reset exposures and positions for the new day.

        This method does not delete historical PnL records.
        """
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                await session.execute(delete(exposures_table))
                await session.execute(delete(positions_table))

    async def get_exposures(self) -> Dict[str, float]:
        """Return a mapping of product_id to total notional exposure."""
        async with AsyncSession(self.engine) as session:
            result = await session.execute(select(exposures_table))
            exposures = {
                row.product_id: float(row.notional)
                for row in result.mappings().all()
            }
            return exposures

    async def get_positions(self) -> Dict[str, Dict[str, float]]:
        """Return a mapping of product_id to position info."""
        async with AsyncSession(self.engine) as session:
            result = await session.execute(select(positions_table))
            return {
                row.product_id: {
                    "quantity": float(row.quantity),
                    "average_price": float(row.average_price),
                }
                for row in result.mappings().all()
            }