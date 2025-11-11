"""add_has_conflict_field

Revision ID: 08fb5e4498e4
Revises: d84bc1f3a8f1
Create Date: 2025-11-11 17:21:06.791757

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '08fb5e4498e4'
down_revision: Union[str, None] = 'd84bc1f3a8f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('cash_sessions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('has_conflict', sa.Boolean(), nullable=False, server_default='false'))
        batch_op.create_index(batch_op.f('ix_cash_sessions_has_conflict'), ['has_conflict'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('cash_sessions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_cash_sessions_has_conflict'))
        batch_op.drop_column('has_conflict')
