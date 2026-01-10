"""remove_refunds_column

Revision ID: f8e9a0b1c2d3
Revises: d5f7e9a2b3c4
Create Date: 2026-01-09 10:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f8e9a0b1c2d3'
down_revision: Union[str, None] = 'd5f7e9a2b3c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove refunds column from daily_reconciliations table
    with op.batch_alter_table('daily_reconciliations', schema=None) as batch_op:
        batch_op.drop_column('refunds')


def downgrade() -> None:
    # Add refunds column back to daily_reconciliations table
    with op.batch_alter_table('daily_reconciliations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('refunds', sa.Numeric(precision=12, scale=2), nullable=True))
