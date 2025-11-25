"""add_user_role_and_names

Revision ID: 3af50337336d
Revises: 8bbddfd667b9
Create Date: 2025-11-25 12:28:45.464652

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3af50337336d'
down_revision: Union[str, None] = '8bbddfd667b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns with defaults
    op.add_column('users', sa.Column('first_name', sa.String(100), nullable=False, server_default=''))
    op.add_column('users', sa.Column('last_name', sa.String(100), nullable=False, server_default=''))
    op.add_column('users', sa.Column('role', sa.String(20), nullable=False, server_default='CASHIER'))
    # Create index on role for faster queries
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_role'), table_name='users')
    op.drop_column('users', 'role')
    op.drop_column('users', 'last_name')
    op.drop_column('users', 'first_name')

    # ### end Alembic commands ###
