from datetime import date, time
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models import CashSession


async def check_session_overlap(
    db: AsyncSession,
    business_id: UUID,
    session_date: date,
    opened_time: time,
    closed_time: time | None,
    exclude_session_id: UUID | None = None,
) -> dict | None:
    """
    Check if new session overlaps with existing sessions for same business on same date.

    Returns conflicting session details if overlap found, None if safe.

    Overlap logic (same date only):
    - Sessions conflict if: opened_time < other.closed_time AND closed_time > other.opened_time
    - If closed_time is None (session still open), use 23:59:59 for comparison
    """
    # Use 23:59:59 if session not closed (open sessions block entire rest of day)
    effective_closed_time = closed_time if closed_time else time(23, 59, 59)

    # Find overlapping sessions on SAME DATE
    stmt = select(CashSession).where(
        and_(
            CashSession.business_id == business_id,
            CashSession.session_date == session_date,  # Same day only
            CashSession.opened_time < effective_closed_time,
            CashSession.closed_time.is_(None) | (CashSession.closed_time > opened_time),
        )
    )

    # Exclude current session if updating
    if exclude_session_id:
        stmt = stmt.where(CashSession.id != exclude_session_id)

    result = await db.execute(stmt)
    conflicting = result.scalar_one_or_none()

    if conflicting:
        cashier_name = None
        if conflicting.cashier:
            cashier_name = conflicting.cashier.display_name
        else:
            cashier_name = str(conflicting.cashier_id)

        return {
            "cashier_name": cashier_name,
            "opened_time": conflicting.opened_time.isoformat(),
            "closed_time": conflicting.closed_time.isoformat() if conflicting.closed_time else None,
            "session_date": conflicting.session_date.isoformat(),
            "session_id": str(conflicting.id),
        }

    return None


async def validate_session_dates(
    session_date: date, opened_time: time, closed_time: time | None = None
) -> Optional[Dict[str, Any]]:
    """
    Validate session times on same date. Returns error dict if invalid, None if valid.

    Rules:
    - closed_time must be AFTER opened_time (not equal)
    - closed_time can be None (open session)
    """
    if closed_time is None:
        return None  # Valid: open session

    # Must be strictly after
    if closed_time <= opened_time:
        return {
            "message": "Closed time must be after open time",
            "details": {
                "opened_time": opened_time.isoformat(),
                "closed_time": closed_time.isoformat(),
            },
        }

    return None
