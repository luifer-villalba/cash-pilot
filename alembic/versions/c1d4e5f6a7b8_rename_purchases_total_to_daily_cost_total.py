"""rename_purchases_total_to_daily_cost_total

Revision ID: c1d4e5f6a7b8
Revises: b6c8d9e0f123
Create Date: 2026-01-13 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c1d4e5f6a7b8"
down_revision: Union[str, None] = "b6c8d9e0f123"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename purchases_total column to daily_cost_total
    with op.batch_alter_table("daily_reconciliations", schema=None) as batch_op:
        batch_op.alter_column(
            "purchases_total",
            new_column_name="daily_cost_total",
            existing_type=sa.BigInteger(),
        )


def downgrade() -> None:
    # Rename daily_cost_total column back to purchases_total
    with op.batch_alter_table("daily_reconciliations", schema=None) as batch_op:
        batch_op.alter_column(
            "daily_cost_total",
            new_column_name="purchases_total",
            existing_type=sa.BigInteger(),
        )
