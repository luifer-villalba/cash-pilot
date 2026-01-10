"""add_invoice_count_to_daily_reconciliations

Revision ID: d5f7e9a2b3c4
Revises: e7f8a9b0c1d2
Create Date: 2026-01-09 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd5f7e9a2b3c4'
down_revision: Union[str, None] = 'e7f8a9b0c1d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add invoice_count column to daily_reconciliations table
    with op.batch_alter_table('daily_reconciliations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('invoice_count', sa.Integer(), nullable=True))


def downgrade() -> None:
    # Remove invoice_count column from daily_reconciliations table
    with op.batch_alter_table('daily_reconciliations', schema=None) as batch_op:
        batch_op.drop_column('invoice_count')
