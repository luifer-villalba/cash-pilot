# File: src/cashpilot/api/routes/sessions.py
"""Session management routes (HTML endpoints)."""

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.api.auth import get_current_user
from cashpilot.api.auth_helpers import require_own_session
from cashpilot.api.utils import (
    _get_session_calculations,
    format_currency_py,
    get_active_businesses,
    get_locale,
    get_translation_function,
    parse_currency,
)
from cashpilot.core.db import get_db
from cashpilot.core.logging import get_logger
from cashpilot.models import CashSession
from cashpilot.models.user import User
from cashpilot.utils.datetime import current_time_local, today_local

logger = get_logger(__name__)

TEMPLATES_DIR = Path("/app/templates")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.filters["format_currency_py"] = format_currency_py

router = APIRouter(prefix="/sessions", tags=["sessions-frontend"])

# ─────── CREATE SESSION ────────


@router.get("/create", response_class=HTMLResponse)
async def create_session_form(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Form to create new cash session."""
    locale = get_locale(request)
    _ = get_translation_function(locale)
    businesses = await get_active_businesses(db)

    # Load user's businesses relationship (needed for template logic)
    # For cashiers: shows assigned businesses
    # For admins: not used, but we load it anyway to avoid template errors
    await db.refresh(current_user, ["businesses"])

    return templates.TemplateResponse(
        request,
        "sessions/create_session.html",
        {
            "current_user": current_user,
            "businesses": businesses,
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
    """Handle session creation form submission."""
    # Validate inputs
    if request is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Request object is required",
        )
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User authentication required",
        )
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error",
        )
    if business_id is None or not isinstance(business_id, str) or not business_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="business_id is required",
        )
    if initial_cash is None or not isinstance(initial_cash, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="initial_cash is required",
        )
    
    locale = get_locale(request)
    _ = get_translation_function(locale)

    try:
        initial_cash_val = parse_currency(initial_cash)
        if initial_cash_val is None:
            raise ValueError("Initial cash required")

        # Validate and parse session_date
        if session_date:
            if not isinstance(session_date, str):
                raise ValueError("session_date must be a string")
            try:
                session_date_val = datetime.fromisoformat(session_date).date()
            except (ValueError, TypeError):
                raise ValueError("Invalid session_date format")
        else:
            session_date_val = today_local()
        
        # Validate and parse opened_time
        if opened_time:
            if not isinstance(opened_time, str):
                raise ValueError("opened_time must be a string")
            try:
                opened_time_val = datetime.strptime(opened_time, "%H:%M").time()
            except (ValueError, TypeError):
                raise ValueError("Invalid opened_time format (expected HH:MM)")
        else:
            opened_time_val = current_time_local()
        
        # Validate business_id
        try:
            business_uuid = UUID(business_id)
        except (ValueError, TypeError):
            raise ValueError("Invalid business_id format")
        
        # Validate current_user.id
        if not hasattr(current_user, "id") or current_user.id is None:
            raise ValueError("Invalid user ID")

        session = CashSession(
            business_id=business_uuid,
            cashier_id=current_user.id,
            initial_cash=initial_cash_val,
            session_date=session_date_val,
            opened_time=opened_time_val,
            created_by=current_user.id,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        logger.info(
            "session.created",
            session_id=str(session.id),
            created_by=str(current_user.id),
        )

        return RedirectResponse(url=f"/sessions/{session.id}", status_code=302)

    except Exception as e:
        logger.error("session.create_failed", error=str(e), user_id=str(current_user.id))
        businesses = await get_active_businesses(db)
        return templates.TemplateResponse(
            request,
            "sessions/create_session.html",
            {
                "current_user": current_user,
                "businesses": businesses,
                "error": str(e),
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
    session: CashSession = Depends(require_own_session),
    db: AsyncSession = Depends(get_db),
):
    """Display single session details (with permission check)."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    # Ensure business is loaded (eager load to avoid template lazy loading)
    await db.refresh(session, ["business"])

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
        },
    )


# ─────── CLOSE SESSION ────────


@router.get("/{session_id}/edit", response_class=HTMLResponse)
async def edit_session_form(
    request: Request,
    session_id: str,
    current_user: User = Depends(get_current_user),
    session: CashSession = Depends(require_own_session),
):
    """Form to close/edit cash session (with permission check)."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

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
    envelope_amount: str = Form(...),
    credit_card_total: str = Form(...),
    debit_card_total: str = Form(...),
    credit_sales_total: str = Form("0"),
    credit_payments_collected: str = Form("0"),
    closed_time: str = Form(...),
    closing_ticket: str | None = Form(None),
    notes: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Handle session close form submission (with permission check)."""
    # Validate inputs
    if request is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Request object is required",
        )
    if session_id is None or not isinstance(session_id, str) or not session_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id is required",
        )
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User authentication required",
        )
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error",
        )
    if final_cash is None or not isinstance(final_cash, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="final_cash is required",
        )
    if envelope_amount is None or not isinstance(envelope_amount, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="envelope_amount is required",
        )
    if credit_card_total is None or not isinstance(credit_card_total, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="credit_card_total is required",
        )
    if closed_time is None or not isinstance(closed_time, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="closed_time is required",
        )
    
    locale = get_locale(request)
    _ = get_translation_function(locale)

    try:
        final_cash_val = parse_currency(final_cash)
        if final_cash_val is None:
            raise ValueError("Invalid final_cash format")
        session.final_cash = final_cash_val
        
        envelope_val = parse_currency(envelope_amount)
        session.envelope_amount = envelope_val if envelope_val is not None else Decimal("0")
        
        credit_card_val = parse_currency(credit_card_total)
        session.credit_card_total = credit_card_val if credit_card_val is not None else Decimal("0")
        
        debit_card_val = parse_currency(debit_card_total)
        session.debit_card_total = debit_card_val if debit_card_val is not None else Decimal("0")
        
        credit_sales_val = parse_currency(credit_sales_total)
        session.credit_sales_total = credit_sales_val if credit_sales_val is not None else Decimal("0")
        
        credit_payments_val = parse_currency(credit_payments_collected)
        session.credit_payments_collected = credit_payments_val if credit_payments_val is not None else Decimal("0")
        
        if not isinstance(closed_time, str):
            raise ValueError("closed_time must be a string")
        try:
            session.closed_time = datetime.strptime(closed_time, "%H:%M").time()
        except (ValueError, TypeError):
            raise ValueError("Invalid closed_time format (expected HH:MM)")
        
        session.closing_ticket = closing_ticket if closing_ticket and isinstance(closing_ticket, str) else None
        session.notes = notes if notes and isinstance(notes, str) else None
        session.status = "CLOSED"

        db.add(session)
        await db.commit()

        logger.info(
            "session.closed",
            session_id=str(session.id),
            closed_by=str(current_user.id),
        )

        return RedirectResponse(url=f"/sessions/{session_id}", status_code=302)
    except Exception as e:
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
