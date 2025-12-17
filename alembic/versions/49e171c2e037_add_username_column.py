"""add_username_column

Revision ID: 49e171c2e037
Revises: 0a6752260382
Create Date: 2025-12-17 22:44:35.984605

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '49e171c2e037'
down_revision: Union[str, None] = '0a6752260382'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# File: migrations/versions/49e171c2e037_add_username_column.py
def upgrade() -> None:
    # Add column as nullable first
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('username', sa.String(length=50), nullable=True))

    # Populate from email prefix with collision handling
    op.execute("""
               WITH username_candidates AS (SELECT id,
                                                   LOWER(SPLIT_PART(email, '@', 1)) as base_username,
                                                   ROW_NUMBER()                        OVER (PARTITION BY LOWER(SPLIT_PART(email, '@', 1)) ORDER BY created_at) as row_num
                                            FROM users)
               UPDATE users
               SET username = CASE
                                  WHEN uc.row_num = 1 THEN uc.base_username
                                  ELSE uc.base_username || uc.row_num
                   END FROM username_candidates uc
               WHERE users.id = uc.id
               """)

    # Make NOT NULL and add unique index
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('username', nullable=False)
        batch_op.create_index(batch_op.f('ix_users_username'), ['username'], unique=True)


def downgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_username'))
        batch_op.drop_column('username')
