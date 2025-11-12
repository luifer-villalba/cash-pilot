"""add_expenses_field_and_net_earnings

Revision ID: 1eb24aa32aa5
Revises: 08fb5e4498e4
Create Date: 2025-11-12 13:56:19.214996

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1eb24aa32aa5'
down_revision: Union[str, None] = '08fb5e4498e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add as nullable first
    with op.batch_alter_table('cash_sessions', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('expenses', sa.Numeric(precision=12, scale=2), nullable=True)
        )

    # Set defaults for existing rows
    op.execute("UPDATE cash_sessions SET expenses = 0.00 WHERE expenses IS NULL")

    # Now make NOT NULL
    with op.batch_alter_table('cash_sessions', schema=None) as batch_op:
        batch_op.alter_column('expenses', nullable=False)


def downgrade() -> None:
    with op.batch_alter_table('cash_sessions', schema=None) as batch_op:
        batch_op.drop_column('expenses')
