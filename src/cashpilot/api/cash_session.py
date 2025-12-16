"""CashSession CRUD endpoints (list, get, open, close)."""

from datetime import date as date_type
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
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
from cashpilot.utils.datetime import today_local, current_time_local, now_utc

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
    Cashier: sees only own sessions (filtered by cashier_id)
    """
    stmt = select(CashSession)

    # Cashier filter: only see sessions where they are the cashier
    if current_user.role == UserRole.CASHIER:
        stmt = stmt.where(CashSession.cashier_id == current_user.id)

    if business_id:
        stmt = stmt.where(CashSession.business_id == UUID(business_id))

    if status_filter:
        stmt = stmt.where(CashSession.status == status_filter)

    stmt = stmt.offset(skip).limit(limit).order_by(CashSession.opened_time.desc())
    stmt = stmt.where(~CashSession.is_deleted)

    result = await db.execute(stmt)
    return result.scalars().all()


# File: src/cashpilot/api/cash_session.py
# Add these helper functions before the open_shift endpoint:


async def _determine_cashier_for_session(
    session: CashSessionCreate,
    current_user: User,
    db: AsyncSession,
) -> tuple[UUID, UUID]:
    """Determine cashier_id and created_by based on user role and RBAC.

    Returns: (cashier_id, created_by)
    """
    if current_user.role == UserRole.ADMIN:
        return await _admin_session_creation(session, current_user, db)
    else:
        return await _cashier_session_creation(session, current_user, db)


async def _admin_session_creation(
    session: CashSessionCreate,
    current_user: User,
    db: AsyncSession,
) -> tuple[UUID, UUID]:
    """Handle admin session creation logic."""
    cashier_id = session.for_cashier_id if session.for_cashier_id else current_user.id
    created_by = current_user.id

    # Verify cashier exists if different from admin
    if cashier_id != current_user.id:
        stmt = select(User).where(User.id == cashier_id)
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            raise NotFoundError("User", str(cashier_id))

    return cashier_id, created_by


async def _cashier_session_creation(
    session: CashSessionCreate,
    current_user: User,
    db: AsyncSession,
) -> tuple[UUID, UUID]:
    """Handle cashier session creation with business assignment validation."""
    if session.for_cashier_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cashiers cannot create sessions for other users",
        )

    # Load cashier's assigned businesses
    stmt = select(User).where(User.id == current_user.id)
    result = await db.execute(stmt)
    user_with_businesses = result.scalar_one()
    await db.refresh(user_with_businesses, ["businesses"])

    assigned_business_ids = {b.id for b in user_with_businesses.businesses}

    # Check if cashier has any assigned businesses
    if not assigned_business_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No businesses assigned. Contact an administrator.",
        )

    # Validate business is assigned
    if session.business_id not in assigned_business_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this business",
        )

    return current_user.id, current_user.id


@router.post("", response_model=CashSessionRead, status_code=status.HTTP_201_CREATED)
async def open_shift(
    session: CashSessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Open a new cash session (shift).

    Admin: Can create for any business/cashier, set for_cashier_id
    Cashier: Can only create for self, using assigned businesses
    """
    # Determine cashier_id and created_by based on RBAC
    cashier_id, created_by = await _determine_cashier_for_session(session, current_user, db)

    # Verify business exists
    stmt = select(Business).where(Business.id == session.business_id)
    result = await db.execute(stmt)
    business = result.scalar_one_or_none()

    if not business:
        raise NotFoundError("Business", str(session.business_id))

    # Check overlap
    if not session.allow_overlap:
        overlap_error = await check_session_overlap(
            db=db,
            business_id=session.business_id,
            session_date=session.session_date or today_local(),
            opened_time=session.opened_time or current_time_local(),
            closed_time=None,
        )
        if overlap_error:
            raise ConflictError(overlap_error)

    # Validate dates
    date_error = await validate_session_dates(
        session.session_date,
        session.opened_time,
        None,
    )
    if date_error:
        raise InvalidStateError(date_error["message"], details=date_error["details"])

    # Create session
    new_session = CashSession(
        business_id=session.business_id,
        cashier_id=cashier_id,
        created_by=created_by,
        initial_cash=session.initial_cash,
        expenses=session.expenses,
        session_date=session.session_date,
        opened_time=session.opened_time,
        notes=session.notes,
    )

    db.add(new_session)
    await db.flush()
    await db.refresh(new_session)

    logger.info(
        "session.opened",
        session_id=str(new_session.id),
        business_id=str(session.business_id),
        cashier_id=str(cashier_id),
        created_by=str(created_by),
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
    session.deleted_at = now_utc()
    session.deleted_by = current_user.display_name

    db.add(session)
    await db.commit()

    logger.info(
        "session.deleted",
        session_id=str(session.id),
        deleted_by=str(current_user.id),
    )
