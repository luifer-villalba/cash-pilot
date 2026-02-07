# File: src/cashpilot/api/routes/sessions.py
"""Session management routes (HTML endpoints)."""

from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.api.auth import get_current_user
from cashpilot.api.auth_helpers import (
    get_open_session_for_cashier_business,
    require_business_assignment,
    require_own_session,
)
from cashpilot.api.utils import (
    _get_session_calculations,
    get_assigned_businesses,
    get_locale,
    get_translation_function,
    parse_currency,
    templates,
)
from cashpilot.core.db import get_db
from cashpilot.core.logging import get_logger
from cashpilot.core.validators import validate_currency
from cashpilot.models import CashSession
from cashpilot.models.user import User, UserRole
from cashpilot.utils.datetime import current_time_local, now_utc, today_local

logger = get_logger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions-frontend"])

# ─────── CREATE SESSION ────────


@router.get("/create", response_class=HTMLResponse)
async def create_session_form(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Form to create new cash session (AC-01, AC-02)."""
    locale = get_locale(request)
    _ = get_translation_function(locale)
    # Filter businesses: admin sees all, cashier sees only assigned (AC-01)
    businesses = await get_assigned_businesses(current_user, db)

    # Load user's businesses relationship (needed for template logic)
    # For cashiers: shows assigned businesses
    # For admins: not used, but we load it anyway to avoid template errors
    await db.refresh(current_user, ["businesses"])

    existing_session = None
    block_new_session = False
    if current_user.role == UserRole.CASHIER and len(current_user.businesses) == 1:
        existing_session = await get_open_session_for_cashier_business(
            current_user.id,
            current_user.businesses[0].id,
            db,
        )
        block_new_session = existing_session is not None

    return templates.TemplateResponse(
        request,
        "sessions/create_session.html",
        {
            "current_user": current_user,
            "businesses": businesses,
            "existing_session": existing_session,
            "block_new_session": block_new_session,
            "locale": locale,
            "_": _,
            "today": today_local().isoformat(),
        },
    )


@router.post("", response_class=HTMLResponse)
async def create_session_post(
    request: Request,
    current_user: User = Depends(get_current_user),
    business_id: str = Form(...),
    initial_cash: str = Form(...),
    session_date: str | None = Form(None),
    opened_time: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Handle session creation form submission (AC-01, AC-02).

    Enforces business assignment check: cashiers can only create sessions
    for assigned businesses. Admins can create for any business.
    """
    locale = get_locale(request)
    _ = get_translation_function(locale)
    # Cache user info to avoid lazy-loading issues in error handlers
    user_id = str(current_user.id)
    user_role = current_user.role

    try:
        # Enforce business assignment (AC-01, AC-02)
        business_uuid = await require_business_assignment(business_id, current_user, db)

        # Prevent duplicate open sessions per cashier/business (CP-DATA-02)
        existing_session = await get_open_session_for_cashier_business(
            current_user.id,
            business_uuid,
            db,
        )
        if existing_session:
            await db.refresh(current_user, ["businesses"])
            await db.refresh(current_user, ["businesses"])
            block_new_session = user_role == UserRole.CASHIER and len(current_user.businesses) == 1
            businesses = await get_assigned_businesses(current_user, db)
            return templates.TemplateResponse(
                request,
                "sessions/create_session.html",
                {
                    "current_user": current_user,
                    "businesses": businesses,
                    "error": _("You already have an open session for this business."),
                    "existing_session": existing_session,
                    "block_new_session": block_new_session,
                    "locale": locale,
                    "_": _,
                },
                status_code=400,
            )

        # Business logic: parse currency format (es-PY specific)
        initial_cash_val = parse_currency(initial_cash)
        if initial_cash_val is None:
            raise ValueError("Initial cash required")
        # Validate that the value doesn't exceed NUMERIC(12, 2) limit
        validate_currency(initial_cash_val)

        # Business logic: parse date/time formats
        if session_date:
            try:
                session_date_val = datetime.fromisoformat(session_date).date()
            except (ValueError, TypeError):
                raise ValueError("Invalid session_date format")
        else:
            session_date_val = today_local()

        if opened_time:
            try:
                opened_time_val = datetime.strptime(opened_time, "%H:%M").time()
            except (ValueError, TypeError):
                raise ValueError("Invalid opened_time format (expected HH:MM)")
        else:
            opened_time_val = current_time_local()

        session = CashSession(
            business_id=business_uuid,
            cashier_id=current_user.id,
            initial_cash=initial_cash_val,
            session_date=session_date_val,
            opened_time=opened_time_val,
            created_by=current_user.id,
        )
        db.add(session)
        try:
            await db.commit()
            await db.refresh(session)
        except IntegrityError:
            await db.rollback()
            existing_session = await get_open_session_for_cashier_business(
                current_user.id,
                business_uuid,
                db,
            )
            await db.refresh(current_user, ["businesses"])
            block_new_session = user_role == UserRole.CASHIER and len(current_user.businesses) == 1
            businesses = await get_assigned_businesses(current_user, db)
            return templates.TemplateResponse(
                request,
                "sessions/create_session.html",
                {
                    "current_user": current_user,
                    "businesses": businesses,
                    "error": _("You already have an open session for this business."),
                    "existing_session": existing_session,
                    "block_new_session": block_new_session,
                    "locale": locale,
                    "_": _,
                },
                status_code=409,
            )

        logger.info(
            "session.created",
            session_id=str(session.id),
            created_by=user_id,
        )

        return RedirectResponse(url=f"/sessions/{session.id}", status_code=302)

    except ValueError as e:
        # Handle validation errors (like currency format or max value exceeded)
        error_message = str(e)
        # Make the error message more user-friendly
        if "exceeds maximum" in error_message:
            error_message = _("Currency value too large. Maximum allowed: 9,999,999,999.99")
        elif "Invalid" in error_message and "format" in error_message:
            error_message = _("Invalid number format. Please enter a valid amount.")

        await db.rollback()

        logger.warning("session.create_validation_failed", error=str(e), user_id=user_id)
        await db.refresh(current_user, ["businesses"])
        block_new_session = user_role == UserRole.CASHIER and len(current_user.businesses) == 1
        businesses = await get_assigned_businesses(current_user, db)
        return templates.TemplateResponse(
            request,
            "sessions/create_session.html",
            {
                "current_user": current_user,
                "businesses": businesses,
                "error": error_message,
                "block_new_session": block_new_session,
                "locale": locale,
                "_": _,
            },
            status_code=400,
        )
    except HTTPException:
        # Re-raise HTTP exceptions (403, NotFoundError, etc.)
        raise
    except Exception as e:
        await db.rollback()
        logger.error("session.create_failed", error=str(e), user_id=user_id)
        await db.refresh(current_user, ["businesses"])
        block_new_session = user_role == UserRole.CASHIER and len(current_user.businesses) == 1
        businesses = await get_assigned_businesses(current_user, db)
        return templates.TemplateResponse(
            request,
            "sessions/create_session.html",
            {
                "current_user": current_user,
                "businesses": businesses,
                "error": str(e),
                "block_new_session": block_new_session,
                "locale": locale,
                "_": _,
            },
            status_code=400,
        )


@router.get("/{session_id}", response_class=HTMLResponse)
async def session_detail(
    request: Request,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Display single session details (with permission check)."""

    from cashpilot.api.auth_helpers import require_view_session
    from cashpilot.core.errors import NotFoundError

    locale = get_locale(request)
    _ = get_translation_function(locale)

    try:
        # Try to get session with VIEW permission (no edit window restriction)
        session = await require_view_session(session_id, current_user, db)
    except NotFoundError:
        # Session doesn't exist
        return templates.TemplateResponse(
            request,
            "sessions/error.html",
            {
                "current_user": current_user,
                "error_type": "not_found",
                "session_id": session_id,
                "locale": locale,
                "_": _,
            },
            status_code=404,
        )
    except HTTPException as e:
        if e.status_code == 404:
            # Check if it's a deleted session or not owned
            from uuid import UUID

            from sqlalchemy import select

            try:
                stmt = select(CashSession).where(CashSession.id == UUID(session_id))
                result = await db.execute(stmt)
                session_check = result.scalar_one_or_none()

                if session_check and session_check.is_deleted:
                    # Deleted session - cashiers can't access
                    return templates.TemplateResponse(
                        request,
                        "sessions/error.html",
                        {
                            "current_user": current_user,
                            "error_type": "deleted",
                            "session_id": session_id,
                            "locale": locale,
                            "_": _,
                        },
                        status_code=404,
                    )
                elif session_check and session_check.cashier_id != current_user.id:
                    # Not owned by cashier
                    return templates.TemplateResponse(
                        request,
                        "sessions/error.html",
                        {
                            "current_user": current_user,
                            "error_type": "not_owned",
                            "session_id": session_id,
                            "locale": locale,
                            "_": _,
                        },
                        status_code=403,
                    )
            except (ValueError, TypeError):
                # If session_id is not a valid UUID (or a related type error occurs),
                # fall through to the generic "not_owned" error handling below.
                logger.debug(
                    "Invalid session_id '%s' while checking session permissions",
                    session_id,
                )

        # Generic permission denied
        return templates.TemplateResponse(
            request,
            "sessions/error.html",
            {
                "current_user": current_user,
                "error_type": "not_owned",
                "session_id": session_id,
                "locale": locale,
                "_": _,
            },
            status_code=403,
        )

    # Ensure business is loaded (eager load to avoid template lazy loading)
    await db.refresh(session, ["business"])

    # Calculate edit window for closed sessions
    can_edit = False
    edit_expired_msg = None

    if session.status == "CLOSED":
        if current_user.role == UserRole.ADMIN:
            # Admins can always edit closed sessions
            can_edit = True
        elif current_user.id == session.cashier_id:
            # Cashiers can edit their own closed sessions within 32 hours
            # Check if closed_time is set (required for closed sessions)
            if session.closed_time:
                # Use closed_at property (combines session_date + closed_time with timezone)
                closed_at = session.closed_at
                if closed_at:
                    time_since_close = now_utc() - closed_at
                    if time_since_close <= timedelta(hours=32):
                        can_edit = True
                    else:
                        can_edit = False
                        edit_expired_msg = _("Edit window expired (32 hours passed)")
                else:
                    # closed_at property returned None (timezone issue?),
                    # but closed_time exists, so allow editing (session was just closed)
                    can_edit = True
            else:
                # Session is closed but has no closed_time (shouldn't happen normally)
                can_edit = False

    calcs = _get_session_calculations(session)
    return templates.TemplateResponse(
        request,
        "sessions/session_detail.html",
        {
            "current_user": current_user,
            "session": session,
            **calcs,
            "locale": locale,
            "_": _,
            "editable": False,
            "can_edit": can_edit,
            "edit_expired_msg": edit_expired_msg,
        },
    )


# ─────── CLOSE SESSION ────────


@router.get("/{session_id}/edit", response_class=HTMLResponse)
async def edit_session_form(
    request: Request,
    session_id: str,
    current_user: User = Depends(get_current_user),
    session: CashSession = Depends(require_own_session),
    db: AsyncSession = Depends(get_db),
):
    """Form to close/edit cash session (with permission check, AC-01, AC-02)."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    try:
        # Enforce business assignment before rendering form (AC-01, AC-02)
        await require_business_assignment(str(session.business_id), current_user, db)
    except HTTPException:
        # Re-raise 403/404 exceptions (already handled by require_business_assignment)
        raise

    return templates.TemplateResponse(
        request,
        "sessions/close_session.html",
        {
            "current_user": current_user,
            "session": session,
            "locale": locale,
            "_": _,
            "editable": True,
        },
    )


@router.post("/{session_id}", response_class=HTMLResponse)
async def close_session_post(
    request: Request,
    session_id: str,
    current_user: User = Depends(get_current_user),
    session: CashSession = Depends(require_own_session),
    final_cash: str = Form(...),
    envelope_amount: str = Form("0"),
    card_total: str = Form("0"),
    credit_sales_total: str = Form("0"),
    credit_payments_collected: str = Form("0"),
    closed_time: str = Form(...),
    closing_ticket: str | None = Form(None),
    notes: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Handle session close form submission (with permission check, AC-01, AC-02, AC-05)."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    try:
        # Enforce business assignment before any state changes (AC-01, AC-02)
        await require_business_assignment(str(session.business_id), current_user, db)

        # Business logic: parse currency formats (es-PY specific)
        # Note: envelope_amount and card_total have Form("0") defaults,
        # so parse_currency will receive "0" if not provided. parse_currency handles "0" correctly
        # and returns Decimal("0"), with fallback to Decimal("0") if parsing fails.
        final_cash_val = parse_currency(final_cash)
        if final_cash_val is None:
            raise ValueError("Invalid final_cash format")
        # Validate that the value doesn't exceed NUMERIC(12, 2) limit
        validate_currency(final_cash_val)
        session.final_cash = final_cash_val

        envelope_val = parse_currency(envelope_amount)
        envelope_val = envelope_val if envelope_val is not None else Decimal("0")
        validate_currency(envelope_val)
        session.envelope_amount = envelope_val

        card_val = parse_currency(card_total)
        card_val = card_val if card_val is not None else Decimal("0")
        validate_currency(card_val)
        session.card_total = card_val

        credit_sales_val = parse_currency(credit_sales_total)
        credit_sales_val = credit_sales_val if credit_sales_val is not None else Decimal("0")
        validate_currency(credit_sales_val)
        session.credit_sales_total = credit_sales_val

        credit_payments_val = parse_currency(credit_payments_collected)
        credit_payments_val = (
            credit_payments_val if credit_payments_val is not None else Decimal("0")
        )
        validate_currency(credit_payments_val)
        session.credit_payments_collected = credit_payments_val

        # Business logic: parse time format
        try:
            session.closed_time = datetime.strptime(closed_time, "%H:%M").time()
        except (ValueError, TypeError):
            raise ValueError("Invalid closed_time format (expected HH:MM)")

        # Optional fields: normalize empty strings to None
        session.closing_ticket = closing_ticket or None
        session.notes = notes or None
        session.status = "CLOSED"

        db.add(session)
        await db.commit()

        logger.info(
            "session.closed",
            session_id=str(session.id),
            closed_by=str(current_user.id),
        )

        return RedirectResponse(url=f"/sessions/{session_id}", status_code=302)
    except HTTPException:
        # Re-raise HTTP exceptions (403, 404, etc.) without catching them
        raise
    except ValueError as e:
        # Handle validation errors (like currency format or max value exceeded)
        error_message = str(e)
        # Make the error message more user-friendly
        if "exceeds maximum" in error_message:
            error_message = _("Currency value too large. Maximum allowed: 9,999,999,999.99")
        elif "Invalid" in error_message and "format" in error_message:
            error_message = _("Invalid number format. Please enter a valid amount.")

        await db.rollback()
        await db.refresh(session)

        logger.warning(
            "session.close_validation_failed",
            session_id=session_id,
            error=str(e),
            user_id=str(current_user.id),
        )
        return templates.TemplateResponse(
            request,
            "sessions/close_session.html",
            {
                "current_user": current_user,
                "session": session,
                "error": error_message,
            },
        )
    except Exception as e:
        await db.rollback()
        await db.refresh(session)
        logger.error(
            "session.close_failed",
            session_id=session_id,
            error=str(e),
            user_id=str(current_user.id),
        )
        return templates.TemplateResponse(
            request,
            "sessions/close_session.html",
            {
                "current_user": current_user,
                "session": session,
                "error": str(e),
                "locale": locale,
                "editable": True,
                "_": _,
            },
            status_code=400,
        )
