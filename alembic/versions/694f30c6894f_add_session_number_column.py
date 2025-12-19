# File: alembic/versions/694f30c6894f_add_session_number_column.py

"""add session_number column

Revision ID: 694f30c6894f
Revises: 0a6752260382
Create Date: 2025-12-19 14:12:25.686341

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '694f30c6894f'
down_revision: Union[str, None] = '0a6752260382'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create sequence
    op.execute("CREATE SEQUENCE IF NOT EXISTS cash_session_number_seq")

    # Step 1: Add column as NULLABLE (allows existing rows)
    with op.batch_alter_table('cash_sessions', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'session_number',
                sa.Integer(),
                nullable=True,  # Nullable initially
            )
        )
        batch_op.create_index(batch_op.f('ix_cash_sessions_session_number'), ['session_number'], unique=False)

    # Step 2: Backfill existing sessions with sequential numbers
    connection = op.get_bind()

    sessions = connection.execute(
        sa.text("""
                SELECT id
                FROM cash_sessions
                ORDER BY session_date, opened_time
                """)
    ).fetchall()

    for idx, (session_id,) in enumerate(sessions, start=1):
        connection.execute(
            sa.text("""
                    UPDATE cash_sessions
                    SET session_number = :number
                    WHERE id = :session_id
                    """),
            {"number": idx, "session_id": session_id}
        )

    # Update sequence to continue from last assigned number
    if sessions:
        connection.execute(
            sa.text("SELECT setval('cash_session_number_seq', :count)"),
            {"count": len(sessions)},
        )

    # Step 3: Make column NOT NULL after backfill
    with op.batch_alter_table('cash_sessions', schema=None) as batch_op:
        batch_op.alter_column('session_number', nullable=False)


def downgrade() -> None:
    with op.batch_alter_table('cash_sessions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_cash_sessions_session_number'))
        batch_op.drop_column('session_number')

    op.execute('DROP SEQUENCE IF EXISTS cash_session_number_seq')
