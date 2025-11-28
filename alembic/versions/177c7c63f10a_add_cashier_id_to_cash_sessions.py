"""add_cashier_id_to_cash_sessions

Revision ID: 177c7c63f10a
Revises: 1dcc0e9e2231
Create Date: 2025-11-28 01:54:19.693776

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '177c7c63f10a'
down_revision: Union[str, None] = '1dcc0e9e2231'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from uuid import uuid4

    # 1. Add cashier_id column (nullable initially)
    op.add_column(
        'cash_sessions',
        sa.Column('cashier_id', postgresql.UUID(as_uuid=True), nullable=True)
    )

    # 2. Create a "System" user for orphaned sessions
    system_user_id = str(uuid4())
    op.execute(f"""
        INSERT INTO users (id, email, hashed_password, first_name, last_name, role, is_active, created_at)
        VALUES (
            '{system_user_id}',
            'system@cashpilot.internal',
            'LEGACY_NO_PASSWORD',
            'Sistema',
            'Legacy',
            'ADMIN',
            false,
            NOW()
        )
        ON CONFLICT (email) DO NOTHING
    """)

    # 3. Backfill: Copy created_by to cashier_id WHERE NOT NULL
    op.execute("""
               UPDATE cash_sessions
               SET cashier_id = created_by
               WHERE created_by IS NOT NULL
               """)

    # 4. Assign orphaned sessions to System user
    op.execute(f"""
        UPDATE cash_sessions
        SET cashier_id = '{system_user_id}'
        WHERE created_by IS NULL
    """)

    # 5. NOW make cashier_id non-nullable
    op.alter_column('cash_sessions', 'cashier_id', nullable=False)

    # 6. Add FK constraint
    op.create_foreign_key(
        'fk_cash_sessions_cashier_id',
        'cash_sessions',
        'users',
        ['cashier_id'],
        ['id']
    )

    # 7. Add indexes
    op.create_index(
        'ix_cash_sessions_cashier_id',
        'cash_sessions',
        ['cashier_id'],
        unique=False
    )
    op.create_index(
        'ix_cash_sessions_business_cashier',
        'cash_sessions',
        ['business_id', 'cashier_id'],
        unique=False
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_cash_sessions_business_cashier', table_name='cash_sessions')
    op.drop_index('ix_cash_sessions_cashier_id', table_name='cash_sessions')

    # Drop FK constraint
    op.drop_constraint('fk_cash_sessions_cashier_id', 'cash_sessions', type_='foreignkey')

    # Drop cashier_id column
    op.drop_column('cash_sessions', 'cashier_id')

    # Delete the System user (optional - comment out if you want to keep it)
    op.execute("""
               DELETE
               FROM users
               WHERE email = 'system@cashpilot.internal'
               """)
