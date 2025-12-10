"""CashSession edit endpoints (patch open/closed sessions)."""

from datetime import datetime, timedelta
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

FREEZE_PERIOD_DAYS = 30

router = APIRouter(prefix="/cash-sessions", tags=["cash-sessions-edit"])


@router.patch("/{session_id}/edit-open", response_model=CashSessionRead)
async def edit_open_session(
    session_id: str,
    patch: CashSessionPatchOpen,
    changed_by: str = "system",
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


# File: src/cashpilot/api/cash_session_edit.py

@router.patch("/{session_id}/edit-closed", response_model=CashSessionRead)
async def edit_closed_session(
    session_id: str,
    patch: CashSessionPatchClosed,
    changed_by: str = "system",
    db: AsyncSession = Depends(get_db),
):
    """Edit a CLOSED session (manager/admin only)."""
    stmt = select(CashSession).where(CashSession.id == UUID(session_id))
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise NotFoundError("CashSession", session_id)

    if session.status != "CLOSED":
        raise InvalidStateError(
            f"Session must be CLOSED to edit with this endpoint (current: {session.status})"
        )

    # Capture old values
    old_values = {
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
    if patch.credit_sales_total is not None:
        session.credit_sales_total = patch.credit_sales_total
    if patch.credit_payments_collected is not None:
        session.credit_payments_collected = patch.credit_payments_collected
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
        "credit_sales_total": session.credit_sales_total,
        "credit_payments_collected": session.credit_payments_collected,
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
