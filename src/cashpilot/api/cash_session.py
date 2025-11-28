"""CashSession CRUD endpoints (list, get, open, close)."""

from datetime import datetime, date
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.api.auth import get_current_user
from cashpilot.api.auth_helpers import require_own_session
from cashpilot.core.db import get_db
from cashpilot.core.errors import ConflictError, InvalidStateError, NotFoundError
from cashpilot.core.logging import get_logger
from cashpilot.core.validation import check_session_overlap, validate_session_dates
from cashpilot.models import (
    Business,
    CashSession,
    CashSessionCreate,
    CashSessionRead,
    CashSessionUpdate,
    User,
)
from cashpilot.models.enums import SessionStatus
from cashpilot.models.user import UserRole

logger = get_logger(__name__)

router = APIRouter(prefix="/cash-sessions", tags=["cash-sessions"])


@router.get("", response_model=list[CashSessionRead])
async def list_shifts(
    business_id: str | None = None,
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List cash sessions with optional filtering.

    Admin: sees all sessions
    Cashier: sees only own sessions
    """
    stmt = select(CashSession)

    # Cashier filter: own sessions
    if current_user.role == UserRole.CASHIER:
        stmt = stmt.where(CashSession.created_by == current_user.id)

    if business_id:
        stmt = stmt.where(CashSession.business_id == UUID(business_id))

    if status_filter:
        stmt = stmt.where(CashSession.status == status_filter)

    stmt = stmt.offset(skip).limit(limit).order_by(CashSession.opened_time.desc())
    stmt = stmt.where(~CashSession.is_deleted)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=CashSessionRead, status_code=status.HTTP_201_CREATED)
async def open_shift(
    session_data: CashSessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Open a new cash session (shift).

    Cashier creates session for themselves.
    Admin can create for any cashier via for_cashier_id.
    """
    # Determine who the cashier is
    if session_data.for_cashier_id:
        # Admin creating session for another user
        if current_user.role != UserRole.ADMIN:
            raise InvalidStateError("Only admins can create sessions for other users")
        cashier_id = session_data.for_cashier_id
    else:
        # Cashier creating session for themselves
        cashier_id = current_user.id

    # Verify business exists
    stmt = select(Business).where(Business.id == session_data.business_id)
    result = await db.execute(stmt)
    business = result.scalar_one_or_none()
    if not business:
        raise NotFoundError("Business", str(session_data.business_id))

    # Check for existing OPEN session
    existing = await CashSession.check_open_session(db, session_data.business_id, cashier_id)
    if existing:
        raise ConflictError(
            f"Cashier already has an open session at this business (ID: {existing.id})"
        )

    # Check for overlapping sessions
    overlap = await check_session_overlap(
        db=db,
        business_id=session_data.business_id,
        cashier_id=cashier_id,
        session_date=session_data.session_date or date.today(),
        exclude_session_id=None,
    )
    if overlap:
        raise ConflictError(f"Session overlaps with existing session (ID: {overlap.id})")

    # Create new session
    new_session = CashSession(
        business_id=session_data.business_id,
        cashier_id=cashier_id,
        created_by=current_user.id,
        status=SessionStatus.OPEN.value,
        session_date=session_data.session_date or date.today(),
        initial_cash=session_data.initial_cash,
        notes=session_data.notes,
    )

    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)

    logger.info(
        "cash_session.opened",
        session_id=str(new_session.id),
        business_id=str(new_session.business_id),
        cashier_id=str(cashier_id),
        created_by=str(current_user.id),
    )

    return new_session


@router.get("/{session_id}", response_model=CashSessionRead)
async def get_session(
    session_id: str,
    session: CashSession = Depends(require_own_session),
):
    """Get cash session details."""
    return session


@router.put("/{session_id}", response_model=CashSessionRead)
async def close_shift(
    session_id: str,
    session_update: CashSessionUpdate,
    session: CashSession = Depends(require_own_session),
    db: AsyncSession = Depends(get_db),
):
    """Close a cash session."""
    if session.status != SessionStatus.OPEN.value:
        raise InvalidStateError(
            "Session is not open",
            details={"status": session.status},
        )

    if (
        session_update.final_cash is None
        or session_update.envelope_amount is None
        or session_update.credit_card_total is None
        or session_update.closed_time is None
    ):
        raise InvalidStateError(
            "Cannot close session: final_cash, envelope_amount, credit_card_total, "
            "and closed_time required"
        )

    # Validate closed_time is after opened_time
    date_error = await validate_session_dates(
        session.session_date, session.opened_time, session_update.closed_time
    )
    if date_error:
        raise InvalidStateError(date_error["message"], details=date_error["details"])

    # Update session
    session.status = SessionStatus.CLOSED.value
    session.closed_time = session_update.closed_time
    session.has_conflict = False

    # Apply other updates
    update_data = session_update.model_dump(exclude_unset=True, exclude={"closed_time"})
    for key, value in update_data.items():
        setattr(session, key, value)

    db.add(session)
    await db.flush()
    await db.refresh(session)

    logger.info(
        "session.closed",
        session_id=str(session.id),
        created_by=str(session.created_by),
    )

    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    session: CashSession = Depends(require_own_session),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete a cash session."""
    session.is_deleted = True
    session.deleted_at = datetime.now()
    session.deleted_by = current_user.display_name

    db.add(session)
    await db.commit()

    logger.info(
        "session.deleted",
        session_id=str(session.id),
        deleted_by=str(current_user.id),
    )
