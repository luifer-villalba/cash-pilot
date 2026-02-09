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
    """Add unique constraint for single open (non-deleted) session per cashier/business.
    
    This constraint prevents a cashier from having multiple concurrent OPEN
    sessions in the same business where the session is not soft-deleted,
    supporting the CP-DATA-02 requirement.
    
    The constraint is partial (WHERE status = 'OPEN' AND is_deleted = FALSE) so
    it only applies to open, non-deleted sessions. Closed or soft-deleted
    sessions do not block new open sessions.
    """
    # Pre-check for duplicate open sessions before creating the unique index
    conn = op.get_bind()
    result = conn.execute(
        sa.text('''
            SELECT cashier_id, business_id, array_agg(id) AS session_ids, COUNT(*) AS open_count
            FROM cash_sessions
            WHERE status = 'OPEN' AND is_deleted = FALSE
            GROUP BY cashier_id, business_id
            HAVING COUNT(*) > 1
        ''')
    )
    duplicates = result.mappings().all()
    if duplicates:
        msg_lines = [
            '\n[CP-DATA-02] Migration aborted: Duplicate open sessions detected!\n',
            'The following (cashier_id, business_id) pairs have multiple open sessions (status=OPEN, is_deleted=FALSE):',
        ]
        for row in duplicates:
            msg_lines.append(f"  cashier_id={row['cashier_id']}, business_id={row['business_id']}, open_session_ids={row['session_ids']}")
        msg_lines.append('\nPlease manually close or resolve these sessions before re-running the migration.')
        raise Exception('\n'.join(msg_lines))

    # Create unique index (partial, PostgreSQL syntax)
    # This index will enforce that only one row with status='OPEN' and is_deleted=FALSE can exist
    # for a given (cashier_id, business_id) pair.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_cash_sessions_one_open_per_cashier_business
        ON cash_sessions(cashier_id, business_id)
        WHERE status = 'OPEN' AND is_deleted = FALSE;
        """
    )


def downgrade() -> None:
    """Remove the single open session constraint."""
    op.execute(
        "DROP INDEX IF EXISTS uq_cash_sessions_one_open_per_cashier_business;"
    )
