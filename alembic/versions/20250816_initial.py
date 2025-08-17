"""
Initial database schema for atlas-trader.

This migration creates the core tables used by the database state
store: exposures, positions and daily_pnl.  These tables track
notional exposure by product, current positions and average price,
and daily profit and loss.  They correspond to the SQLAlchemy
metadata defined in ``workers/src/workers/services/db_state_store.py``.

Revision ID: 20250816_initial
Revises:
Create Date: 2025-08-16
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20250816_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create exposures, positions and daily_pnl tables."""
    op.create_table(
        "exposures",
        sa.Column("product_id", sa.String(), primary_key=True),
        sa.Column(
            "notional",
            sa.Numeric(precision=18, scale=8),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_table(
        "positions",
        sa.Column("product_id", sa.String(), primary_key=True),
        sa.Column(
            "quantity",
            sa.Numeric(precision=18, scale=8),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "average_price",
            sa.Numeric(precision=18, scale=8),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_table(
        "daily_pnl",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("pnl", sa.Numeric(precision=18, scale=8), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    """Drop exposures, positions and daily_pnl tables."""
    op.drop_table("daily_pnl")
    op.drop_table("positions")
    op.drop_table("exposures")
