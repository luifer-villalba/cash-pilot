from datetime import date, time
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models import CashSession


async def check_session_overlap(
        db: AsyncSession,
        business_id: UUID,
        cashier_id: UUID,  # NEW: Required parameter
        session_date: date,
        exclude_session_id: UUID | None = None,
) -> CashSession | None:
    """Check if there's an overlapping session for the same cashier/business/date.

    Args:
        db: Database session
        business_id: Business ID
        cashier_id: Cashier user ID
        session_date: Date of the session
        exclude_session_id: Session ID to exclude from check (for updates)

    Returns:
        Overlapping session if found, None otherwise
    """
    stmt = select(CashSession).where(
        and_(
            CashSession.business_id == business_id,
            CashSession.cashier_id == cashier_id,  # NEW
            CashSession.session_date == session_date,
            ~CashSession.is_deleted,
        )
    )

    if exclude_session_id:
        stmt = stmt.where(CashSession.id != exclude_session_id)

    result = await db.execute(stmt)
    return result.scalar_one_or_none()


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
