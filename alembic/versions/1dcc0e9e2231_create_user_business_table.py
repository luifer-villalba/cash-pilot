"""create_user_business_table

Revision ID: 1dcc0e9e2231
Revises: 85f44c4614fb
Create Date: 2025-11-28 01:52:02.108352

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '1dcc0e9e2231'
down_revision: Union[str, None] = '85f44c4614fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_businesses junction table
    op.create_table(
        'user_businesses',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('business_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'business_id')
    )
    op.create_index('ix_user_businesses_user_id', 'user_businesses', ['user_id'], unique=False)
    op.create_index('ix_user_businesses_business_id', 'user_businesses', ['business_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_user_businesses_business_id', table_name='user_businesses')
    op.drop_index('ix_user_businesses_user_id', table_name='user_businesses')
    op.drop_table('user_businesses')
