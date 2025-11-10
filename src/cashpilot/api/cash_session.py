"""CashSession API endpoints for shift management."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.core.db import get_db
from cashpilot.core.errors import ConflictError, InvalidStateError, NotFoundError
from cashpilot.core.validation import check_session_overlap
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

    stmt = stmt.offset(skip).limit(limit).order_by(CashSession.opened_at.desc())

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

    # Use provided opened_at or now
    opened_at = session.opened_at or datetime.now()

    # Check for overlapping sessions
    if not session.allow_overlap:
        conflict = await check_session_overlap(
            db=db,
            business_id=session.business_id,
            opened_at=opened_at,
            closed_at=None,
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
        opened_at=opened_at,
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
    """
    Close a cash session (shift).

    Requirements:
    - Session must be OPEN
    - final_cash, envelope_amount, credit_card_total required to close
    """
    stmt = select(CashSession).where(CashSession.id == UUID(session_id))
    result = await db.execute(stmt)
    session_obj = result.scalar_one_or_none()

    if not session_obj:
        raise NotFoundError("CashSession", session_id)

    if session_obj.status != SessionStatus.OPEN.value:
        raise InvalidStateError(
            "Session is not open",
            details={"status": session_obj.status, "session_id": str(session_id)},
        )

    # Validate required fields to close
    if (
        session.final_cash is None
        or session.envelope_amount is None
        or session.credit_card_total is None
    ):
        raise InvalidStateError(
            "Cannot close session: final_cash, envelope_amount, and credit_card_total required",
            details={
                "final_cash": session.final_cash,
                "envelope_amount": session.envelope_amount,
                "credit_card_total": session.credit_card_total,
            },
        )

    # Set closed_at and status
    session_obj.closed_at = datetime.now()
    session_obj.status = SessionStatus.CLOSED.value

    # Apply updates
    update_data = session.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(session_obj, key, value)

    db.add(session_obj)
    await db.flush()
    await db.refresh(session_obj)
    return session_obj
