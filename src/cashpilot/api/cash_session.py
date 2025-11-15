"""CashSession API endpoints for shift management."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.core.db import get_db
from cashpilot.core.errors import ConflictError, InvalidStateError, NotFoundError
from cashpilot.core.validation import check_session_overlap, validate_session_dates
from cashpilot.models import (
    Business,
    CashSession,
    CashSessionCreate,
    CashSessionRead,
    CashSessionUpdate,
)
from cashpilot.models.enums import SessionStatus

router = APIRouter(prefix="/cash-sessions", tags=["cash-sessions"])


@router.get("", response_model=list[CashSessionRead])
async def list_shifts(
    business_id: str | None = None,
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List cash sessions with optional filtering."""
    stmt = select(CashSession)

    if business_id:
        stmt = stmt.where(CashSession.business_id == UUID(business_id))

    if status_filter:
        stmt = stmt.where(CashSession.status == status_filter)

    stmt = stmt.offset(skip).limit(limit).order_by(CashSession.opened_time.desc())

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=CashSessionRead, status_code=status.HTTP_201_CREATED)
async def open_shift(session: CashSessionCreate, db: AsyncSession = Depends(get_db)):
    """
    Open a new cash session (shift).

    Validation:
    - Business must exist
    - No overlapping open sessions unless allow_overlap=True
    """
    # Verify business exists
    business = await db.execute(select(Business).where(Business.id == session.business_id))
    if not business.scalar_one_or_none():
        raise NotFoundError("Business", str(session.business_id))

    from datetime import date as date_type

    session_date = session.session_date or date_type.today()
    opened_time = session.opened_time or datetime.now().time()

    # Check for overlapping sessions
    if not session.allow_overlap:
        conflict = await check_session_overlap(
            db=db,
            business_id=session.business_id,
            session_date=session_date,
            opened_time=opened_time,
            closed_time=None,
        )
        if conflict:
            raise ConflictError(
                f"Session overlaps with {conflict['cashier_name']}'s shift",
                details=conflict,
            )

    session_obj = CashSession(
        business_id=session.business_id,
        cashier_name=session.cashier_name,
        initial_cash=session.initial_cash,
        session_date=session_date,
        opened_time=opened_time,
    )
    db.add(session_obj)
    await db.flush()
    await db.refresh(session_obj)
    return session_obj


@router.get("/{session_id}", response_model=CashSessionRead)
async def get_shift(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get cash session details."""
    stmt = select(CashSession).where(CashSession.id == UUID(session_id))
    result = await db.execute(stmt)
    session_obj = result.scalar_one_or_none()

    if not session_obj:
        raise NotFoundError("CashSession", session_id)

    return session_obj


@router.put("/{session_id}", response_model=CashSessionRead)
async def close_shift(
    session_id: str, session: CashSessionUpdate, db: AsyncSession = Depends(get_db)
):
    """Close a cash session."""
    stmt = select(CashSession).where(CashSession.id == UUID(session_id))
    result = await db.execute(stmt)
    session_obj = result.scalar_one_or_none()

    if not session_obj:
        raise NotFoundError("CashSession", session_id)

    if session_obj.status != SessionStatus.OPEN.value:
        raise InvalidStateError("Session is not open", details={"status": session_obj.status})

    if (
        session.final_cash is None
        or session.envelope_amount is None
        or session.credit_card_total is None
        or session.closed_time is None  # NEW: require closed_time
    ):
        raise InvalidStateError(
            "Cannot close session: final_cash, envelope_amount, credit_card_total, "
            "and closed_time required"
        )

    # Validate closed_time is after opened_time (same date)
    date_error = await validate_session_dates(
        session_obj.session_date, session_obj.opened_time, session.closed_time
    )
    if date_error:
        raise InvalidStateError(date_error["message"], details=date_error["details"])

    # Update session
    session_obj.status = SessionStatus.CLOSED.value
    session_obj.closed_time = session.closed_time
    session_obj.has_conflict = False

    # Apply other updates
    update_data = session.model_dump(exclude_unset=True, exclude={"closed_time"})
    for key, value in update_data.items():
        setattr(session_obj, key, value)

    db.add(session_obj)
    await db.flush()
    await db.refresh(session_obj)
    return session_obj
