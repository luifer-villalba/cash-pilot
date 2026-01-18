# File: src/cashpilot/api/routes/sessions_edit.py
"""Session edit routes (edit-open, edit-closed)."""

from datetime import timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.api.auth import get_current_user
from cashpilot.api.auth_helpers import require_admin, require_own_session
from cashpilot.api.utils import (
    get_locale,
    get_translation_function,
    templates,
    update_closed_session_fields,
    update_open_session_fields,
)
from cashpilot.core.db import get_db
from cashpilot.core.logging import get_logger
from cashpilot.models import CashSession
from cashpilot.models.cash_session_audit_log import CashSessionAuditLog
from cashpilot.models.user import User, UserRole
from cashpilot.utils.datetime import now_utc

logger = get_logger(__name__)

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
        {
            "current_user": current_user,
            "session": session,
            "locale": locale,
            "_": _,
            "editable": True,
        },
    )


@router.post("/{session_id}/edit-open", response_class=HTMLResponse)
async def edit_open_session_post(
    request: Request,
    session_id: str,
    current_user: User = Depends(get_current_user),
    session: CashSession = Depends(require_own_session),
    initial_cash: str | None = Form(None),
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
        # Handle validation errors (like currency format or max value exceeded)
        error_message = str(e)
        # Make the error message more user-friendly
        if "exceeds maximum" in error_message:
            error_message = _("Currency value too large. Maximum allowed: 9,999,999,999.99")
        elif "Invalid" in error_message and "format" in error_message:
            error_message = _("Invalid number format. Please enter a valid amount.")

        logger.warning(
            "session.edit_open_validation_failed",
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
                "error": error_message,
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
        time_since_close = now_utc() - session.closed_at if session.closed_at else timedelta(0)
        if time_since_close > timedelta(hours=32):
            can_edit = False
            edit_expired_msg = _("Edit window expired (32 hours passed)")

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
            "editable": True,
        },
    )


@router.post("/{session_id}/edit-closed", response_class=HTMLResponse)
async def edit_closed_session_post(
    request: Request,
    session_id: str,
    current_user: User = Depends(get_current_user),
    session: CashSession = Depends(require_own_session),
    initial_cash: str | None = Form(None),
    final_cash: str | None = Form(None),
    envelope_amount: str | None = Form(None),
    card_total: str | None = Form(None),
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

        # Validate: reason is required when editing closed sessions
        if not reason or not reason.strip():
            return templates.TemplateResponse(
                request,
                "sessions/edit_closed_session.html",
                {
                    "current_user": current_user,
                    "session": session,
                    "error": _(
                        "Reason for edit is required when editing closed "
                        "sessions for audit compliance"
                    ),
                    "locale": locale,
                    "_": _,
                },
                status_code=400,
            )

        changed_fields, old_values, new_values = await update_closed_session_fields(
            session,
            initial_cash,
            final_cash,
            envelope_amount,
            card_total,
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
        # Handle validation errors (like currency format or max value exceeded)
        error_message = str(e)
        # Make the error message more user-friendly
        if "exceeds maximum" in error_message:
            error_message = _("Currency value too large. Maximum allowed: 9,999,999,999.99")
        elif "Invalid" in error_message and "format" in error_message:
            error_message = _("Invalid number format. Please enter a valid amount.")

        logger.warning(
            "session.edit_closed_validation_failed",
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
                "error": error_message,
                "locale": locale,
                "_": _,
            },
            status_code=400,
        )


# ─────── RESTORE SESSION ────────


@router.post("/{session_id}/restore", response_class=HTMLResponse)
async def restore_session_post(
    request: Request,
    session_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Restore a deleted cash session. Admin only."""

    from cashpilot.api.cash_session import restore_session as api_restore_session

    locale = get_locale(request)
    _ = get_translation_function(locale)

    try:
        # Use the API endpoint logic
        await api_restore_session(session_id, current_user, db)
        logger.info(
            "session.restored",
            session_id=session_id,
            restored_by=str(current_user.id),
        )
        return RedirectResponse(url=f"/sessions/{session_id}", status_code=302)
    except Exception as e:
        logger.error(
            "session.restore_failed",
            session_id=session_id,
            error=str(e),
            user_id=str(current_user.id),
        )
        # Redirect back to dashboard with error
        return RedirectResponse(url="/?restore_error=true", status_code=302)
