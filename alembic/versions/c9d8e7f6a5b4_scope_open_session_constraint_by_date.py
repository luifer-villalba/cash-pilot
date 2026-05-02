"""scope_open_session_constraint_by_date

Revision ID: c9d8e7f6a5b4
Revises: b7c6d5e4f3a2
Create Date: 2026-05-02 13:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision: str = "c9d8e7f6a5b4"
down_revision: Union[str, None] = "b7c6d5e4f3a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow one open session per cashier/business/date."""
    if not context.is_offline_mode():
        conn = op.get_bind()
        result = conn.execute(sa.text("""
                SELECT cashier_id, business_id, session_date, array_agg(id) AS session_ids,
                       COUNT(*) AS open_count
                FROM cash_sessions
                WHERE status = 'OPEN' AND is_deleted = FALSE
                GROUP BY cashier_id, business_id, session_date
                HAVING COUNT(*) > 1
                """))
        duplicates = result.mappings().all()
        if duplicates:
            msg_lines = [
                "\n[CP-DATA-02] Migration aborted: duplicate open sessions detected.\n",
                "The following cashier/business/date groups have multiple active OPEN sessions:",
            ]
            for row in duplicates:
                msg_lines.append(
                    "  "
                    f"cashier_id={row['cashier_id']}, "
                    f"business_id={row['business_id']}, "
                    f"session_date={row['session_date']}, "
                    f"open_session_ids={row['session_ids']}"
                )
            msg_lines.append(
                "\nClose, delete, or merge those same-day duplicates before re-running."
            )
            raise Exception("\n".join(msg_lines))

    op.execute("DROP INDEX IF EXISTS uq_cash_sessions_one_open_per_cashier_business;")
    op.execute("""
        CREATE UNIQUE INDEX uq_cash_sessions_one_open_per_cashier_business
        ON cash_sessions(cashier_id, business_id, session_date)
        WHERE status = 'OPEN' AND is_deleted = FALSE;
        """)


def downgrade() -> None:
    """Return to one open session per cashier/business across all dates."""
    if not context.is_offline_mode():
        conn = op.get_bind()
        result = conn.execute(sa.text("""
                SELECT cashier_id, business_id, array_agg(id) AS session_ids,
                       COUNT(*) AS open_count
                FROM cash_sessions
                WHERE status = 'OPEN' AND is_deleted = FALSE
                GROUP BY cashier_id, business_id
                HAVING COUNT(*) > 1
                """))
        duplicates = result.mappings().all()
        if duplicates:
            raise Exception(
                "Cannot downgrade while multiple open sessions exist for the same "
                "cashier/business across different dates."
            )

    op.execute("DROP INDEX IF EXISTS uq_cash_sessions_one_open_per_cashier_business;")
    op.execute("""
        CREATE UNIQUE INDEX uq_cash_sessions_one_open_per_cashier_business
        ON cash_sessions(cashier_id, business_id)
        WHERE status = 'OPEN' AND is_deleted = FALSE;
        """)
