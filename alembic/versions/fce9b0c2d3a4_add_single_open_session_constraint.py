"""add_single_open_session_constraint

Enforce single open session per cashier/business (CP-DATA-02).

Revision ID: fce9b0c2d3a4
Revises: c1d4e5f6a7b8
Create Date: 2026-02-06 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fce9b0c2d3a4'
down_revision: Union[str, None] = 'c1d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add unique constraint for single open session per cashier/business.
    
    This constraint prevents a cashier from having multiple concurrent OPEN
    sessions in the same business, supporting the CP-DATA-02 requirement.
    
    The constraint is partial (WHERE status = 'OPEN') so it only applies to
    open sessions. Closed sessions do not block new open sessions.
    """
    # Create unique index (partial, PostgreSQL syntax)
    # This index will enforce that only one row with status='OPEN' can exist
    # for a given (cashier_id, business_id) pair.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_cash_sessions_one_open_per_cashier_business
        ON cash_sessions(cashier_id, business_id)
        WHERE status = 'OPEN';
        """
    )


def downgrade() -> None:
    """Remove the single open session constraint."""
    op.execute(
        "DROP INDEX IF EXISTS uq_cash_sessions_one_open_per_cashier_business;"
    )
