"""add_reconciliation_audit_fields

Revision ID: a2b3c4d5e6f7
Revises: fce9b0c2d3a4
Create Date: 2026-02-13 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = 'fce9b0c2d3a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add audit fields to daily_reconciliations
    op.add_column(
        "daily_reconciliations",
        sa.Column("last_modified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "daily_reconciliations",
        sa.Column("last_modified_by", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    # Remove audit fields
    op.drop_column("daily_reconciliations", "last_modified_by")
    op.drop_column("daily_reconciliations", "last_modified_at")
