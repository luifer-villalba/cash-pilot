"""add_purchases_total_to_daily_reconciliations

Revision ID: b6c8d9e0f123
Revises: f8e9a0b1c2d3
Create Date: 2026-01-12 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b6c8d9e0f123'
down_revision: Union[str, None] = 'f8e9a0b1c2d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add purchases_total column to daily_reconciliations table
    with op.batch_alter_table('daily_reconciliations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('purchases_total', sa.BigInteger(), nullable=True))


def downgrade() -> None:
    # Remove purchases_total column from daily_reconciliations table
    with op.batch_alter_table('daily_reconciliations', schema=None) as batch_op:
        batch_op.drop_column('purchases_total')
