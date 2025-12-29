"""CashSession edit endpoints (patch open/closed sessions)."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.core.audit import log_session_edit
from cashpilot.core.db import get_db
from cashpilot.core.errors import InvalidStateError, NotFoundError
from cashpilot.models import (
    CashSession,
    CashSessionPatchClosed,
    CashSessionPatchOpen,
    CashSessionRead,
)
from cashpilot.utils.datetime import now_utc

FREEZE_PERIOD_DAYS = 30

router = APIRouter(prefix="/cash-sessions", tags=["cash-sessions-edit"])


@router.patch("/{session_id}/edit-open", response_model=CashSessionRead)
async def edit_open_session(
    session_id: str,
    patch: CashSessionPatchOpen,
    changed_by: str = "system",
    db: AsyncSession = Depends(get_db),
):
    """Edit an OPEN session (initial_cash, opened_time, expenses, credit fields)."""
    # Validate inputs
    if session_id is None or not isinstance(session_id, str) or not session_id.strip():
        raise NotFoundError("CashSession", session_id or "unknown")
    if patch is None:
        raise InvalidStateError("Patch data is required")
    if db is None:
        raise InvalidStateError("Database connection error")
    if changed_by is None:
        changed_by = "system"
    if not isinstance(changed_by, str):
        changed_by = "system"

    try:
        session_uuid = UUID(session_id)
    except (ValueError, TypeError):
        raise NotFoundError("CashSession", session_id)

    stmt = select(CashSession).where(CashSession.id == session_uuid)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise NotFoundError("CashSession", session_id)

    if session.status is None or session.status != "OPEN":
        raise InvalidStateError(
            f"Session must be OPEN to edit with this endpoint (current: {session.status or 'unknown'})"
        )

    # Capture old values
    old_values = {
        "initial_cash": session.initial_cash,
        "opened_time": session.opened_time,
        "expenses": session.expenses,
        "credit_sales_total": session.credit_sales_total,
        "credit_payments_collected": session.credit_payments_collected,
        "notes": session.notes,
    }

    # Apply updates (with type validation)
    if patch.initial_cash is not None:
        if not isinstance(patch.initial_cash, (int, float, str)):
            raise InvalidStateError("initial_cash must be a number")
        session.initial_cash = patch.initial_cash
    if patch.opened_time is not None:
        if not hasattr(patch.opened_time, 'isoformat'):  # Check if it's a time/datetime object
            raise InvalidStateError("opened_time must be a valid time object")
        session.opened_time = patch.opened_time
    if patch.expenses is not None:
        if not isinstance(patch.expenses, (int, float, str)):
            raise InvalidStateError("expenses must be a number")
        session.expenses = patch.expenses
    if patch.credit_sales_total is not None:
        if not isinstance(patch.credit_sales_total, (int, float, str)):
            raise InvalidStateError("credit_sales_total must be a number")
        session.credit_sales_total = patch.credit_sales_total
    if patch.credit_payments_collected is not None:
        if not isinstance(patch.credit_payments_collected, (int, float, str)):
            raise InvalidStateError("credit_payments_collected must be a number")
        session.credit_payments_collected = patch.credit_payments_collected
    if patch.notes is not None:
        if not isinstance(patch.notes, str):
            raise InvalidStateError("notes must be a string")
        session.notes = patch.notes

    # Update audit fields
    session.last_modified_at = now_utc()
    session.last_modified_by = changed_by

    # Capture new values
    new_values = {
        "initial_cash": session.initial_cash,
        "opened_time": session.opened_time,
        "expenses": session.expenses,
        "credit_sales_total": session.credit_sales_total,
        "credit_payments_collected": session.credit_payments_collected,
        "notes": session.notes,
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


def _capture_session_values(session: CashSession) -> dict:
    """Capture current session values for audit trail."""
    return {
        "final_cash": session.final_cash,
        "envelope_amount": session.envelope_amount,
        "credit_card_total": session.credit_card_total,
        "debit_card_total": session.debit_card_total,
        "bank_transfer_total": session.bank_transfer_total,
        "expenses": session.expenses,
        "credit_sales_total": session.credit_sales_total,
        "credit_payments_collected": session.credit_payments_collected,
        "notes": session.notes,
    }


def _apply_patch_updates(session: CashSession, patch: CashSessionPatchClosed) -> None:
    """Apply patch updates to session."""
    if session is None:
        raise InvalidStateError("Session is required")
    if patch is None:
        raise InvalidStateError("Patch data is required")

    if patch.final_cash is not None:
        if not isinstance(patch.final_cash, (int, float, str)):
            raise InvalidStateError("final_cash must be a number")
        session.final_cash = patch.final_cash
    if patch.envelope_amount is not None:
        if not isinstance(patch.envelope_amount, (int, float, str)):
            raise InvalidStateError("envelope_amount must be a number")
        session.envelope_amount = patch.envelope_amount
    if patch.credit_card_total is not None:
        if not isinstance(patch.credit_card_total, (int, float, str)):
            raise InvalidStateError("credit_card_total must be a number")
        session.credit_card_total = patch.credit_card_total
    if patch.debit_card_total is not None:
        if not isinstance(patch.debit_card_total, (int, float, str)):
            raise InvalidStateError("debit_card_total must be a number")
        session.debit_card_total = patch.debit_card_total
    if patch.bank_transfer_total is not None:
        if not isinstance(patch.bank_transfer_total, (int, float, str)):
            raise InvalidStateError("bank_transfer_total must be a number")
        session.bank_transfer_total = patch.bank_transfer_total
    if patch.expenses is not None:
        if not isinstance(patch.expenses, (int, float, str)):
            raise InvalidStateError("expenses must be a number")
        session.expenses = patch.expenses
    if patch.credit_sales_total is not None:
        if not isinstance(patch.credit_sales_total, (int, float, str)):
            raise InvalidStateError("credit_sales_total must be a number")
        session.credit_sales_total = patch.credit_sales_total
    if patch.credit_payments_collected is not None:
        if not isinstance(patch.credit_payments_collected, (int, float, str)):
            raise InvalidStateError("credit_payments_collected must be a number")
        session.credit_payments_collected = patch.credit_payments_collected
    if patch.notes is not None:
        if not isinstance(patch.notes, str):
            raise InvalidStateError("notes must be a string")
        session.notes = patch.notes


@router.patch("/{session_id}/edit-closed", response_model=CashSessionRead)
async def edit_closed_session(
    session_id: str,
    patch: CashSessionPatchClosed,
    changed_by: str = "system",
    db: AsyncSession = Depends(get_db),
):
    """Edit a CLOSED session (manager/admin only)."""
    # Validate inputs
    if session_id is None or not isinstance(session_id, str) or not session_id.strip():
        raise NotFoundError("CashSession", session_id or "unknown")
    if patch is None:
        raise InvalidStateError("Patch data is required")
    if db is None:
        raise InvalidStateError("Database connection error")
    if changed_by is None:
        changed_by = "system"
    if not isinstance(changed_by, str):
        changed_by = "system"

    try:
        session_uuid = UUID(session_id)
    except (ValueError, TypeError):
        raise NotFoundError("CashSession", session_id)

    stmt = select(CashSession).where(CashSession.id == session_uuid)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise NotFoundError("CashSession", session_id)

    if session.status is None or session.status != "CLOSED":
        raise InvalidStateError(
            f"Session must be CLOSED to edit with this endpoint (current: {session.status or 'unknown'})"
        )

    # Capture old values
    old_values = _capture_session_values(session)

    # Apply updates
    _apply_patch_updates(session, patch)

    # Update audit fields
    session.last_modified_at = now_utc()
    session.last_modified_by = changed_by

    # Capture new values
    new_values = _capture_session_values(session)

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
