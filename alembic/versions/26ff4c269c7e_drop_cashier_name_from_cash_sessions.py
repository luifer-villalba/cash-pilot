"""drop_cashier_name_from_cash_sessions

Revision ID: 26ff4c269c7e
Revises: 177c7c63f10a
Create Date: 2025-11-28 01:58:45.461846

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '26ff4c269c7e'
down_revision: Union[str, None] = '177c7c63f10a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('cash_sessions', 'cashier_name')


def downgrade() -> None:
    op.add_column(
        'cash_sessions',
        sa.Column('cashier_name', sa.String(), nullable=True)
    )
    # Backfill from cashier relationship
    op.execute("""
        UPDATE cash_sessions cs
        SET cashier_name = u.first_name || ' ' || u.last_name
        FROM users u
        WHERE cs.cashier_id = u.id
    """)
