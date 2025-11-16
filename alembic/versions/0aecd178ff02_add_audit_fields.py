"""add_audit_fields

Revision ID: 0aecd178ff02
Revises: 9f6320c9ee99
Create Date: 2025-11-16 01:01:20.300529

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0aecd178ff02'
down_revision: Union[str, None] = '9f6320c9ee99'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add audit fields to cash_sessions
    op.add_column(
        "cash_sessions",
        sa.Column("last_modified_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "cash_sessions",
        sa.Column("last_modified_by", sa.String(100), nullable=True),
    )

    # Create cash_session_audit_logs table
    op.create_table(
        "cash_session_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("changed_by", sa.String(100), nullable=False),
        sa.Column("changed_at", sa.DateTime(), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("changed_fields", postgresql.JSONB(), nullable=False),
        sa.Column("old_values", postgresql.JSONB(), nullable=False),
        sa.Column("new_values", postgresql.JSONB(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["cash_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cash_session_audit_logs_session_id",
        "cash_session_audit_logs",
        ["session_id"],
    )
    op.create_index(
        "ix_cash_session_audit_logs_changed_at",
        "cash_session_audit_logs",
        ["changed_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cash_session_audit_logs_changed_at",
        table_name="cash_session_audit_logs",
    )
    op.drop_index(
        "ix_cash_session_audit_logs_session_id",
        table_name="cash_session_audit_logs",
    )
    op.drop_table("cash_session_audit_logs")
    op.drop_column("cash_sessions", "last_modified_by")
    op.drop_column("cash_sessions", "last_modified_at")
