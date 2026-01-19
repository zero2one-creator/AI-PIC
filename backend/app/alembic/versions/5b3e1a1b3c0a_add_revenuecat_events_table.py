"""Add RevenueCat webhook events table

Revision ID: 5b3e1a1b3c0a
Revises: 3f3b0d1a9c61
Create Date: 2026-01-19

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5b3e1a1b3c0a"
down_revision = "3f3b0d1a9c61"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "revenuecat_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("event_id", name="uq_revenuecat_events_event_id"),
    )
    op.create_index("ix_revenuecat_events_event_id", "revenuecat_events", ["event_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_revenuecat_events_event_id", table_name="revenuecat_events")
    op.drop_table("revenuecat_events")

