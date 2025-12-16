# File: src/cashpilot/api/routes/sessions_edit.py
"""Session edit routes (edit-open, edit-closed)."""

from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.api.auth import get_current_user
from cashpilot.api.auth_helpers import require_own_session
from cashpilot.api.utils import (
    get_locale,
    get_translation_function,
    parse_currency,
    update_open_session_fields,
)
from cashpilot.core.db import get_db
from cashpilot.core.logging import get_logger
from cashpilot.models import CashSession
from cashpilot.models.cash_session_audit_log import CashSessionAuditLog
from cashpilot.models.user import User, UserRole
from cashpilot.utils.datetime import now_local, now_utc

logger = get_logger(__name__)

TEMPLATES_DIR = Path("/app/templates")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(prefix="/sessions", tags=["sessions-edit"])


# ─────── EDIT OPEN SESSION ────────


@router.get("/{session_id}/edit-open", response_class=HTMLResponse)
async def edit_open_session_form(
    request: Request,
    session_id: str,
    current_user: User = Depends(get_current_user),
    session: CashSession = Depends(require_own_session),
):
    """Form to edit an OPEN cash session (with permission check)."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    if session.status != "OPEN":
        return RedirectResponse(url=f"/sessions/{session_id}", status_code=302)

    return templates.TemplateResponse(
        request,
        "sessions/edit_open_session.html",
        {"current_user": current_user, "session": session, "locale": locale, "_": _},
    )


@router.post("/{session_id}/edit-open", response_class=HTMLResponse)
async def edit_open_session_post(
    request: Request,
    session_id: str,
    current_user: User = Depends(get_current_user),
    session: CashSession = Depends(require_own_session),
    initial_cash: str | None = Form(None),
    expenses: str | None = Form(None),
    credit_sales_total: str | None = Form(None),
    credit_payments_collected: str | None = Form(None),
    opened_time: str | None = Form(None),
    notes: str | None = Form(None),
    reason: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Handle edit open session form submission (with permission check)."""
    locale = get_locale(request)
    _ = get_translation_function(request)

    try:
        if session.status != "OPEN":
            return RedirectResponse(url=f"/sessions/{session_id}", status_code=302)

        changed_fields, old_values, new_values = await update_open_session_fields(
            session,
            initial_cash,
            expenses,
            credit_sales_total,
            credit_payments_collected,
            opened_time,
            notes,
        )

        session.last_modified_at = now_utc()
        session.last_modified_by = current_user.display_name
        db.add(session)
        await db.commit()

        if changed_fields:
            audit_log = CashSessionAuditLog(
                session_id=session.id,
                action="edit_open",
                changed_fields=changed_fields,
                old_values=old_values,
                new_values=new_values,
                changed_by=current_user.display_name,
                reason=reason,
            )
            db.add(audit_log)
            await db.commit()

            logger.info(
                "session.edit_open",
                session_id=str(session.id),
                edited_by=str(current_user.id),
                fields=changed_fields,
            )

        return RedirectResponse(url=f"/sessions/{session_id}", status_code=302)

    except ValueError as e:
        logger.error(
            "session.edit_open_failed",
            session_id=session_id,
            error=str(e),
            user_id=str(current_user.id),
        )
        return templates.TemplateResponse(
            request,
            "sessions/edit_open_session.html",
            {
                "current_user": current_user,
                "session": session,
                "error": f"Invalid input: {str(e)}",
                "locale": locale,
                "_": _,
            },
            status_code=400,
        )


# ─────── EDIT CLOSED SESSION ────────


@router.get("/{session_id}/edit-closed", response_class=HTMLResponse)
async def edit_closed_session_form(
    request: Request,
    session_id: str,
    current_user: User = Depends(get_current_user),
    session: CashSession = Depends(require_own_session),
):
    """Form to edit a CLOSED cash session (with permission check)."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    if session.status != "CLOSED":
        return RedirectResponse(url=f"/sessions/{session_id}", status_code=302)

    # Calculate edit window for cashiers
    can_edit = True
    edit_expired_msg = None

    if current_user.role == UserRole.CASHIER and session.status == "CLOSED":
        time_since_close = (
            now_utc() - session.closed_at
            if session.closed_at
            else timedelta(0)
        )
        if time_since_close > timedelta(hours=12):
            can_edit = False
            edit_expired_msg = _("Edit window expired (12 hours passed)")

    return templates.TemplateResponse(
        request,
        "sessions/edit_closed_session.html",
        {
            "current_user": current_user,
            "session": session,
            "locale": locale,
            "can_edit": can_edit,
            "edit_expired_msg": edit_expired_msg,
            "_": _,
        },
    )


def _update_field(
    session: CashSession,
    field_name: str,
    new_value: Decimal | str | None,
    current_value: Decimal | str | None,
    changed_fields: list[str],
    old_values: dict,
    new_values: dict,
) -> None:
    """Update a single field and track changes."""
    if new_value is None:
        return

    new_val_str = str(new_value) if new_value else None
    current_val_str = str(current_value) if current_value else None

    if new_val_str != current_val_str:
        changed_fields.append(field_name)
        old_values[field_name] = current_val_str
        new_values[field_name] = new_val_str
        setattr(session, field_name, new_value)


async def update_closed_session_fields(
    session: CashSession,
    final_cash: str | None = None,
    envelope_amount: str | None = None,
    credit_card_total: str | None = None,
    debit_card_total: str | None = None,
    bank_transfer_total: str | None = None,
    expenses: str | None = None,
    credit_sales_total: str | None = None,
    credit_payments_collected: str | None = None,
    closing_ticket: str | None = None,
    notes: str | None = None,
) -> tuple[list[str], dict, dict]:
    """Track field changes for closed session edit."""
    changed_fields = []
    old_values = {}
    new_values = {}

    _update_field(
        session,
        "final_cash",
        parse_currency(final_cash),
        session.final_cash,
        changed_fields,
        old_values,
        new_values,
    )
    _update_field(
        session,
        "envelope_amount",
        parse_currency(envelope_amount) or Decimal("0"),
        session.envelope_amount,
        changed_fields,
        old_values,
        new_values,
    )
    _update_field(
        session,
        "credit_card_total",
        parse_currency(credit_card_total) or Decimal("0"),
        session.credit_card_total,
        changed_fields,
        old_values,
        new_values,
    )
    _update_field(
        session,
        "debit_card_total",
        parse_currency(debit_card_total) or Decimal("0"),
        session.debit_card_total,
        changed_fields,
        old_values,
        new_values,
    )
    _update_field(
        session,
        "bank_transfer_total",
        parse_currency(bank_transfer_total) or Decimal("0"),
        session.bank_transfer_total,
        changed_fields,
        old_values,
        new_values,
    )
    _update_field(
        session,
        "expenses",
        parse_currency(expenses) or Decimal("0"),
        session.expenses,
        changed_fields,
        old_values,
        new_values,
    )
    _update_field(
        session,
        "credit_sales_total",
        parse_currency(credit_sales_total) or Decimal("0"),
        session.credit_sales_total,
        changed_fields,
        old_values,
        new_values,
    )
    _update_field(
        session,
        "credit_payments_collected",
        parse_currency(credit_payments_collected) or Decimal("0"),
        session.credit_payments_collected,
        changed_fields,
        old_values,
        new_values,
    )
    _update_field(
        session,
        "closing_ticket",
        closing_ticket,
        session.closing_ticket,
        changed_fields,
        old_values,
        new_values,
    )
    _update_field(session, "notes", notes, session.notes, changed_fields, old_values, new_values)

    return changed_fields, old_values, new_values


@router.post("/{session_id}/edit-closed", response_class=HTMLResponse)
async def edit_closed_session_post(
    request: Request,
    session_id: str,
    current_user: User = Depends(get_current_user),
    session: CashSession = Depends(require_own_session),
    final_cash: str | None = Form(None),
    envelope_amount: str | None = Form(None),
    credit_card_total: str | None = Form(None),
    debit_card_total: str | None = Form(None),
    bank_transfer_total: str | None = Form(None),
    expenses: str | None = Form(None),
    credit_sales_total: str | None = Form(None),
    credit_payments_collected: str | None = Form(None),
    closing_ticket: str | None = Form(None),
    notes: str | None = Form(None),
    reason: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Handle edit closed session form submission (with permission check)."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    try:
        if session.status != "CLOSED":
            return RedirectResponse(url=f"/sessions/{session_id}", status_code=302)

        changed_fields, old_values, new_values = await update_closed_session_fields(
            session,
            final_cash,
            envelope_amount,
            credit_card_total,
            debit_card_total,
            bank_transfer_total,
            expenses,
            credit_sales_total,
            credit_payments_collected,
            closing_ticket,
            notes,
        )

        session.last_modified_at = now_utc()
        session.last_modified_by = current_user.display_name
        db.add(session)
        await db.commit()

        if changed_fields:
            audit_log = CashSessionAuditLog(
                session_id=session.id,
                action="edit_closed",
                changed_fields=changed_fields,
                old_values=old_values,
                new_values=new_values,
                changed_by=current_user.display_name,
                reason=reason,
            )
            db.add(audit_log)
            await db.commit()

            logger.info(
                "session.edit_closed",
                session_id=str(session.id),
                edited_by=str(current_user.id),
                fields=changed_fields,
            )

        return RedirectResponse(url=f"/sessions/{session_id}", status_code=302)

    except ValueError as e:
        logger.error(
            "session.edit_closed_failed",
            session_id=session_id,
            error=str(e),
            user_id=str(current_user.id),
        )
        return templates.TemplateResponse(
            request,
            "sessions/edit_closed_session.html",
            {
                "current_user": current_user,
                "session": session,
                "error": f"Invalid input: {str(e)}",
                "locale": locale,
                "_": _,
            },
            status_code=400,
        )
