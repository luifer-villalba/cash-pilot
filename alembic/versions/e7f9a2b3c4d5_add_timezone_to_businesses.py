"""add_timezone_to_businesses

Revision ID: e7f9a2b3c4d5
Revises: d84bc1f3a8f1
Create Date: 2026-01-03 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7f9a2b3c4d5'
down_revision: Union[str, None] = 'd84bc1f3a8f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add timezone column to businesses table
    op.add_column('businesses', sa.Column('timezone', sa.String(length=64), nullable=False, server_default='America/Asuncion'))
    
    # Remove server_default after adding column (so new rows require explicit value)
    with op.batch_alter_table('businesses', schema=None) as batch_op:
        batch_op.alter_column('timezone', server_default=None)


def downgrade() -> None:
    # Remove timezone column
    op.drop_column('businesses', 'timezone')
