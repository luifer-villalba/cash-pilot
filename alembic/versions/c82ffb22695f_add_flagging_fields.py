"""add_flagging_fields

Revision ID: c82ffb22695f
Revises: 68c3404d57c9
Create Date: 2025-11-20 02:18:09.117267

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c82ffb22695f'
down_revision: Union[str, None] = '68c3404d57c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('cash_sessions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('flagged', sa.Boolean(), nullable=False, server_default='false'))
        batch_op.add_column(sa.Column('flag_reason', sa.String(500), nullable=True))
        batch_op.add_column(sa.Column('flagged_by', sa.String(100), nullable=True))
        batch_op.create_index(batch_op.f('ix_cash_sessions_flagged'), ['flagged'], unique=False)

def downgrade() -> None:
    with op.batch_alter_table('cash_sessions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_cash_sessions_flagged'))
        batch_op.drop_column('flagged_by')
        batch_op.drop_column('flag_reason')
        batch_op.drop_column('flagged')
