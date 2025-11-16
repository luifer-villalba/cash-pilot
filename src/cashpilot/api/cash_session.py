"""CashSession API endpoints for shift management."""

from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.core.audit import log_session_edit
from cashpilot.core.db import get_db
from cashpilot.core.errors import ConflictError, InvalidStateError, NotFoundError
from cashpilot.core.validation import check_session_overlap, validate_session_dates
from cashpilot.models import (
    Business,
    CashSession,
    CashSessionAuditLog,
    CashSessionCreate,
    CashSessionPatchClosed,
    CashSessionPatchOpen,
    CashSessionRead,
    CashSessionUpdate,
)
from cashpilot.models.enums import SessionStatus

FREEZE_PERIOD_DAYS = 30

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


@router.patch("/{session_id}/edit-open", response_model=CashSessionRead)
async def edit_open_session(
    session_id: str,
    patch: CashSessionPatchOpen,
    changed_by: str = "system",  # TODO: extract from auth context
    db: AsyncSession = Depends(get_db),
):
    """Edit an OPEN session (cashier_name, initial_cash, opened_time, expenses)."""
    stmt = select(CashSession).where(CashSession.id == UUID(session_id))
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise NotFoundError("CashSession", session_id)

    if session.status != "OPEN":
        raise InvalidStateError(
            f"Session must be OPEN to edit with this endpoint (current: {session.status})"
        )

    # Check freeze period (soft warning, not hard blocker)
    session_age = datetime.now().date() - session.session_date
    session_age > timedelta(days=FREEZE_PERIOD_DAYS)

    # Capture old values
    old_values = {
        "cashier_name": session.cashier_name,
        "initial_cash": session.initial_cash,
        "opened_time": session.opened_time,
        "expenses": session.expenses,
    }

    # Apply updates
    if patch.cashier_name is not None:
        session.cashier_name = patch.cashier_name
    if patch.initial_cash is not None:
        session.initial_cash = patch.initial_cash
    if patch.opened_time is not None:
        session.opened_time = patch.opened_time
    if patch.expenses is not None:
        session.expenses = patch.expenses

    # Update audit fields
    session.last_modified_at = datetime.now()
    session.last_modified_by = changed_by

    # Capture new values
    new_values = {
        "cashier_name": session.cashier_name,
        "initial_cash": session.initial_cash,
        "opened_time": session.opened_time,
        "expenses": session.expenses,
    }

    # Log to audit trail
    await log_session_edit(
        db,
        session,
        changed_by,
        "EDIT_OPEN",
        old_values,
        new_values,
        reason=patch.reason,
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    return session


@router.patch("/{session_id}/edit-closed", response_model=CashSessionRead)
async def edit_closed_session(
    session_id: str,
    patch: CashSessionPatchClosed,
    changed_by: str = "system",  # TODO: extract from auth context (require manager/admin)
    db: AsyncSession = Depends(get_db),
):
    """Edit a CLOSED session (manager/admin only). Shows warning if >30 days old."""
    stmt = select(CashSession).where(CashSession.id == UUID(session_id))
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise NotFoundError("CashSession", session_id)

    if session.status != "CLOSED":
        raise InvalidStateError(
            f"Session must be CLOSED to edit with this endpoint (current: {session.status})"
        )

    # Check freeze period (soft warning, not hard blocker)
    session_age = datetime.now().date() - session.session_date
    session_age > timedelta(days=FREEZE_PERIOD_DAYS)

    # Capture old values
    old_values = {
        "final_cash": session.final_cash,
        "envelope_amount": session.envelope_amount,
        "credit_card_total": session.credit_card_total,
        "debit_card_total": session.debit_card_total,
        "bank_transfer_total": session.bank_transfer_total,
        "expenses": session.expenses,
        "notes": session.notes,
    }

    # Apply updates
    if patch.final_cash is not None:
        session.final_cash = patch.final_cash
    if patch.envelope_amount is not None:
        session.envelope_amount = patch.envelope_amount
    if patch.credit_card_total is not None:
        session.credit_card_total = patch.credit_card_total
    if patch.debit_card_total is not None:
        session.debit_card_total = patch.debit_card_total
    if patch.bank_transfer_total is not None:
        session.bank_transfer_total = patch.bank_transfer_total
    if patch.expenses is not None:
        session.expenses = patch.expenses
    if patch.notes is not None:
        session.notes = patch.notes

    # Update audit fields
    session.last_modified_at = datetime.now()
    session.last_modified_by = changed_by

    # Capture new values
    new_values = {
        "final_cash": session.final_cash,
        "envelope_amount": session.envelope_amount,
        "credit_card_total": session.credit_card_total,
        "debit_card_total": session.debit_card_total,
        "bank_transfer_total": session.bank_transfer_total,
        "expenses": session.expenses,
        "notes": session.notes,
    }

    # Log to audit trail
    await log_session_edit(
        db,
        session,
        changed_by,
        "EDIT_CLOSED",
        old_values,
        new_values,
        reason=patch.reason,
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    return session


@router.get("/{session_id}/audit-logs", response_model=list[dict])
async def get_session_audit_logs(
    session_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=250),
    db: AsyncSession = Depends(get_db),
):
    """Get audit log history for a cash session.

    Returns all edits made to the session with:
    - Who made the change (changed_by)
    - When it was made (changed_at)
    - What action (EDIT_OPEN, EDIT_CLOSED)
    - Which fields changed
    - Old and new values
    - Optional reason for the edit
    """
    # Verify session exists
    stmt = select(CashSession).where(CashSession.id == UUID(session_id))
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise NotFoundError("CashSession", session_id)

    # Get audit logs for this session
    audit_stmt = (
        select(CashSessionAuditLog)
        .where(CashSessionAuditLog.session_id == UUID(session_id))
        .order_by(CashSessionAuditLog.changed_at.desc())
        .offset(skip)
        .limit(limit)
    )
    audit_result = await db.execute(audit_stmt)
    audit_logs = audit_result.scalars().all()

    # Format response
    return [
        {
            "id": str(log.id),
            "session_id": str(log.session_id),
            "action": log.action,
            "changed_by": log.changed_by,
            "changed_at": log.changed_at.isoformat(),
            "changed_fields": log.changed_fields,
            "old_values": log.old_values,
            "new_values": log.new_values,
            "reason": log.reason,
        }
        for log in audit_logs
    ]
