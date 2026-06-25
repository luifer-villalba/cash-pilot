"""drop envelope deposit tables

Revision ID: a9f3b2c1d0e5
Revises: b7c6d5e4f3a2
Create Date: 2026-06-25 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "a9f3b2c1d0e5"
down_revision = "c9d8e7f6a5b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("envelope_deposit_events")
    op.drop_table("envelope_deposit_batches")


def downgrade() -> None:
    op.create_table(
        "envelope_deposit_batches",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("deposit_date", sa.Date(), nullable=False),
        sa.Column("deposited_by_user_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["deposited_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "envelope_deposit_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("batch_id", sa.UUID(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("deposit_date", sa.Date(), nullable=False),
        sa.Column("deposited_by_name", sa.String(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.CheckConstraint("amount > 0", name="envelope_deposit_event_amount_positive"),
        sa.ForeignKeyConstraint(["batch_id"], ["envelope_deposit_batches.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["cash_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
