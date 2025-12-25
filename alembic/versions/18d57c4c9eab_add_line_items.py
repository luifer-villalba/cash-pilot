"""add_line_items

Revision ID: 18d57c4c9eab
Revises: 694f30c6894f
Create Date: 2025-12-21 22:55:50.348315

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '18d57c4c9eab'
down_revision: Union[str, None] = '694f30c6894f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create transfer_items table
    op.create_table(
        "transfer_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("description", sa.String(100), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["session_id"], ["cash_sessions.id"]),
    )
    op.create_index("ix_transfer_items_session_id", "transfer_items", ["session_id"])
    op.create_index("ix_transfer_items_is_deleted", "transfer_items", ["is_deleted"])

    # Create expense_items table
    op.create_table(
        "expense_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("description", sa.String(100), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["session_id"], ["cash_sessions.id"]),
    )
    op.create_index("ix_expense_items_session_id", "expense_items", ["session_id"])
    op.create_index("ix_expense_items_is_deleted", "expense_items", ["is_deleted"])

    # Data migration: create generic items for existing sessions
    from sqlalchemy import text

    conn = op.get_bind()

    # Migrate bank_transfer_total
    conn.execute(
        text(
            """
            INSERT INTO transfer_items (id, session_id, description, amount, created_at, is_deleted)
            SELECT 
                gen_random_uuid(),
                id,
                'Transferencias anteriores',
                bank_transfer_total,
                NOW(),
                false
            FROM cash_sessions
            WHERE bank_transfer_total > 0
            """
        )
    )

    # Migrate expenses
    conn.execute(
        text(
            """
            INSERT INTO expense_items (id, session_id, description, amount, created_at, is_deleted)
            SELECT 
                gen_random_uuid(),
                id,
                'Gastos anteriores',
                expenses,
                NOW(),
                false
            FROM cash_sessions
            WHERE expenses > 0
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_expense_items_is_deleted", "expense_items")
    op.drop_index("ix_expense_items_session_id", "expense_items")
    op.drop_table("expense_items")

    op.drop_index("ix_transfer_items_is_deleted", "transfer_items")
    op.drop_index("ix_transfer_items_session_id", "transfer_items")
    op.drop_table("transfer_items")
