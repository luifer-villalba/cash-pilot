# File: alembic/versions/5714760ead58_add_cashier_id_to_cash_sessions_and_backfill.py
"""add_cashier_id_to_cash_sessions_and_backfill

Revision ID: 5714760ead58
Revises: d31d1e1b81de
Create Date: 2025-11-29 22:09:53.425989

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5714760ead58'
down_revision: Union[str, None] = 'd31d1e1b81de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Add cashier_id column (nullable initially)
    with op.batch_alter_table('cash_sessions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cashier_id', postgresql.UUID(as_uuid=True), nullable=True))

    # Step 2: Backfill cashier_id from created_by
    op.execute("""
               UPDATE cash_sessions
               SET cashier_id = created_by
               WHERE created_by IS NOT NULL
               """)

    # Step 2b: Clean up orphaned data (dev only)
    # Delete audit logs for sessions without cashier_id
    op.execute("""
               DELETE
               FROM cash_session_audit_logs
               WHERE session_id IN (SELECT id
                                    FROM cash_sessions
                                    WHERE cashier_id IS NULL)
               """)

    # Delete sessions without cashier_id
    op.execute("""
               DELETE
               FROM cash_sessions
               WHERE cashier_id IS NULL
               """)

    # Step 3: Make cashier_id non-nullable and add FK constraint
    with op.batch_alter_table('cash_sessions', schema=None) as batch_op:
        batch_op.alter_column('cashier_id', nullable=False)
        batch_op.create_foreign_key(
            'fk_cash_sessions_cashier_id_users',
            'users',
            ['cashier_id'],
            ['id']
        )
        batch_op.create_index('ix_cash_sessions_cashier_id', ['cashier_id'])
        batch_op.create_index('ix_cash_sessions_business_cashier', ['business_id', 'cashier_id'])


def downgrade() -> None:
    with op.batch_alter_table('cash_sessions', schema=None) as batch_op:
        batch_op.drop_index('ix_cash_sessions_business_cashier')
        batch_op.drop_index('ix_cash_sessions_cashier_id')
        batch_op.drop_constraint('fk_cash_sessions_cashier_id_users', type_='foreignkey')
        batch_op.drop_column('cashier_id')
