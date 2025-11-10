from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models import CashSession


async def check_session_overlap(
    db: AsyncSession,
    business_id: UUID,
    opened_at: datetime,
    closed_at: datetime | None,
    exclude_session_id: UUID | None = None,
) -> dict | None:
    """
    Check if new session overlaps with existing sessions for same business.

    Returns conflicting session details if overlap found, None if safe.

    Overlap logic:
    - Sessions conflict if: opened_at < other.closed_at AND closed_at > other.opened_at
    - If closed_at is None (session still open), use datetime.now() for comparison
    """
    # Use now if session not closed
    effective_closed_at = closed_at if closed_at else datetime.now()

    # Find overlapping OPEN sessions (closed_at IS NULL, use current time)
    stmt = select(CashSession).where(
        and_(
            CashSession.business_id == business_id,
            CashSession.opened_at < effective_closed_at,
            CashSession.closed_at.is_(None) | (CashSession.closed_at > opened_at),
        )
    )

    # Exclude current session if updating
    if exclude_session_id:
        stmt = stmt.where(CashSession.id != exclude_session_id)

    result = await db.execute(stmt)
    conflicting = result.scalar_one_or_none()

    if conflicting:
        return {
            "cashier_name": conflicting.cashier_name,
            "opened_at": conflicting.opened_at.isoformat(),
            "closed_at": conflicting.closed_at.isoformat() if conflicting.closed_at else None,
            "session_id": str(conflicting.id),
        }

    return None
