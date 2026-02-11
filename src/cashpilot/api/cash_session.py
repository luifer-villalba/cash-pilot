"""CashSession CRUD endpoints (list, get, open, close)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.api.auth import get_current_user
from cashpilot.api.auth_helpers import (
    get_open_session_for_cashier_business,
    require_admin,
    require_own_session,
    require_view_session,
)
from cashpilot.api.cash_session_helpers import (
    _determine_cashier_for_session,
    _validate_restore_session_inputs,
)
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
from cashpilot.utils.datetime import current_time_local, now_utc, today_local

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
    # Validate skip and limit (range only; FastAPI enforces type and defaults)
    if skip < 0:
        skip = 0
    if limit <= 0:
        limit = 50
    if limit > 1000:  # Prevent excessive queries
        limit = 1000

    stmt = select(CashSession)

    # Cashier filter: only see sessions where they are the cashier
    if current_user.role == UserRole.CASHIER:
        stmt = stmt.where(CashSession.cashier_id == current_user.id)

    if business_id:
        try:
            business_uuid = UUID(business_id)
            stmt = stmt.where(CashSession.business_id == business_uuid)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid business_id format",
            )

    if status_filter:
        stmt = stmt.where(CashSession.status == status_filter)

    stmt = stmt.offset(skip).limit(limit).order_by(CashSession.opened_time.desc())
    stmt = stmt.where(~CashSession.is_deleted)

    result = await db.execute(stmt)
    return result.scalars().all()


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

    # Prevent duplicate open sessions per cashier/business (CP-DATA-02)
    existing_session = await get_open_session_for_cashier_business(
        cashier_id, session.business_id, db
    )
    if existing_session:
        raise ConflictError(
            "Ya existe una sesion abierta para este negocio. "
            "Cierra la sesion existente primero.",
            {
                "session_id": str(existing_session.id),
                "session_number": existing_session.session_number,
                "cashier_id": str(cashier_id),
                "business_id": str(session.business_id),
            },
        )

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
    try:
        await db.flush()
        await db.refresh(new_session)
    except IntegrityError as exc:
        await db.rollback()
        existing_session = await get_open_session_for_cashier_business(
            cashier_id, session.business_id, db
        )
        if existing_session:
            raise ConflictError(
                "Ya existe una sesion abierta para este negocio. "
                "Cierra la sesion existente primero.",
                {
                    "session_id": str(existing_session.id),
                    "session_number": existing_session.session_number,
                    "cashier_id": str(cashier_id),
                    "business_id": str(session.business_id),
                },
            ) from exc
        raise

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
    session: CashSession = Depends(require_view_session),
):
    """Get cash session details (read-only, no edit window restriction)."""
    return session


@router.put("/{session_id}", response_model=CashSessionRead)
async def close_shift(
    session_id: str,
    session_update: CashSessionUpdate,
    session: CashSession = Depends(require_own_session),
    db: AsyncSession = Depends(get_db),
):
    """Close a cash session."""
    # Business logic: session must be OPEN to close
    if session.status != SessionStatus.OPEN.value:
        raise InvalidStateError(
            "Session is not open",
            details={"status": session.status},
        )

    # Business logic: required fields for closing session
    if (
        session_update.final_cash is None
        or session_update.envelope_amount is None
        or session_update.card_total is None
        or session_update.closed_time is None
    ):
        raise InvalidStateError(
            "Cannot close session: final_cash, envelope_amount, card_total, "
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

    # Get display_name with informative fallback if somehow falsy
    display_name = current_user.display_name
    if not display_name:
        logger.warning(
            "User missing display_name when deleting session",
            user_id=str(current_user.id),
            session_id=str(session.id),
        )
        display_name = f"User-{current_user.id}"
    session.deleted_by = display_name

    db.add(session)
    await db.commit()

    logger.info(
        "session.deleted",
        session_id=str(session.id),
        deleted_by=str(current_user.id),
    )


@router.patch("/{session_id}/restore", response_model=CashSessionRead)
async def restore_session(
    session_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted cash session. Admin only."""
    from cashpilot.core.audit import log_session_edit

    # Validate inputs
    _validate_restore_session_inputs(session_id, current_user, db)

    try:
        session_uuid = UUID(session_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session_id format",
        )

    stmt = select(CashSession).where(CashSession.id == session_uuid)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise NotFoundError("CashSession", session_id)

    if not session.is_deleted:
        raise InvalidStateError(
            "Session is not deleted",
            details={"session_id": session_id},
        )

    # Capture old values for audit
    old_values = {
        "is_deleted": True,
    }

    # Restore session (keep deleted_at and deleted_by for audit trail)
    session.is_deleted = False

    # Update audit fields
    session.last_modified_at = now_utc()

    # Get display_name with informative fallback if somehow falsy
    display_name = current_user.display_name
    if not display_name:
        logger.warning(
            "User missing display_name when restoring session",
            user_id=str(current_user.id),
            session_id=str(session.id),
        )
        display_name = f"User-{current_user.id}"
    session.last_modified_by = display_name

    new_values = {
        "is_deleted": False,
    }

    # Log restore to audit trail
    await log_session_edit(
        db,
        session,
        display_name,
        "RESTORE",
        old_values,
        new_values,
        reason=f"Session restored by {display_name}",
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    logger.info(
        "session.restored",
        session_id=str(session.id),
        restored_by=str(current_user.id),
    )

    return session
