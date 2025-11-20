"""

Revision ID: 8bbddfd667b9
Revises: c82ffb22695f
Create Date: 2025-11-20 17:09:51.102632

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8bbddfd667b9'
down_revision: Union[str, None] = 'c82ffb22695f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('cash_sessions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'))
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('deleted_by', sa.String(100), nullable=True))
        batch_op.create_index(batch_op.f('ix_cash_sessions_is_deleted'), ['is_deleted'], unique=False)

def downgrade() -> None:
    with op.batch_alter_table('cash_sessions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_cash_sessions_is_deleted'))
        batch_op.drop_column('deleted_by')
        batch_op.drop_column('deleted_at')
        batch_op.drop_column('is_deleted')
