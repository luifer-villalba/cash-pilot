"""add_envelope_deposit_batches

Revision ID: b7c6d5e4f3a2
Revises: add_transfer_verification
Create Date: 2026-03-04 01:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7c6d5e4f3a2"
down_revision: Union[str, None] = "add_transfer_verification"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "envelope_deposit_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("deposit_date", sa.Date(), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("deposited_by_name", sa.String(length=120), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.CheckConstraint("amount > 0", name="envelope_deposit_event_amount_positive"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["cash_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_envelope_deposit_events_session_id",
        "envelope_deposit_events",
        ["session_id"],
    )
    op.create_index(
        "ix_envelope_deposit_events_created_by",
        "envelope_deposit_events",
        ["created_by"],
    )
    op.create_index(
        "ix_envelope_deposit_events_is_deleted",
        "envelope_deposit_events",
        ["is_deleted"],
    )

    op.create_table(
        "envelope_deposit_batches",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("deposit_date", sa.Date(), nullable=False),
        sa.Column("deposited_by_user_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["deposited_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_envelope_deposit_batches_deposited_by_user_id",
        "envelope_deposit_batches",
        ["deposited_by_user_id"],
    )
    op.create_index(
        "ix_envelope_deposit_batches_created_by",
        "envelope_deposit_batches",
        ["created_by"],
    )

    op.add_column(
        "envelope_deposit_events",
        sa.Column("batch_id", sa.UUID(), nullable=True),
    )
    op.create_index(
        "ix_envelope_deposit_events_batch_id",
        "envelope_deposit_events",
        ["batch_id"],
    )
    op.create_foreign_key(
        "fk_envelope_deposit_events_batch_id",
        "envelope_deposit_events",
        "envelope_deposit_batches",
        ["batch_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_envelope_deposit_events_batch_id",
        "envelope_deposit_events",
        type_="foreignkey",
    )
    op.drop_index("ix_envelope_deposit_events_batch_id", table_name="envelope_deposit_events")
    op.drop_column("envelope_deposit_events", "batch_id")

    op.drop_index(
        "ix_envelope_deposit_batches_created_by",
        table_name="envelope_deposit_batches",
    )
    op.drop_index(
        "ix_envelope_deposit_batches_deposited_by_user_id",
        table_name="envelope_deposit_batches",
    )
    op.drop_table("envelope_deposit_batches")

    op.drop_index("ix_envelope_deposit_events_is_deleted", table_name="envelope_deposit_events")
    op.drop_index("ix_envelope_deposit_events_created_by", table_name="envelope_deposit_events")
    op.drop_index("ix_envelope_deposit_events_session_id", table_name="envelope_deposit_events")
    op.drop_table("envelope_deposit_events")
