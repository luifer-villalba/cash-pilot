"""add_created_by_to_cash_sessions

Revision ID: 85f44c4614fb
Revises: 3af50337336d
Create Date: 2025-11-25 13:16:53.146763

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '85f44c4614fb'
down_revision: Union[str, None] = '3af50337336d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add created_by column
    op.add_column('cash_sessions', sa.Column('created_by', sa.UUID(), nullable=True))

    # Create foreign key constraint
    op.create_foreign_key(
        'fk_cash_sessions_created_by_users',
        'cash_sessions',
        'users',
        ['created_by'],
        ['id']
    )

    # Create index for filtering by created_by
    op.create_index('ix_cash_sessions_created_by', 'cash_sessions', ['created_by'])


def downgrade() -> None:
    op.drop_index('ix_cash_sessions_created_by', table_name='cash_sessions')
    op.drop_constraint('fk_cash_sessions_created_by_users', 'cash_sessions', type_='foreignkey')
    op.drop_column('cash_sessions', 'created_by')

    # ### end Alembic commands ###
