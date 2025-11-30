# File: src/cashpilot/api/routes/sessions.py
"""Session management routes (HTML endpoints)."""

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Request
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

    return templates.TemplateResponse(
        request,
        "sessions/create_session.html",
        {
            "current_user": current_user,
            "businesses": businesses,
            "locale": locale,
            "_": _,
            "today": date_type.today().isoformat(),
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
    locale = get_locale(request)
    _ = get_translation_function(locale)

    try:
        initial_cash_val = parse_currency(initial_cash)
        if not initial_cash_val:
            raise ValueError("Initial cash required")

        session_date_val = (
            datetime.fromisoformat(session_date).date() if session_date else date_type.today()
        )
        opened_time_val = (
            datetime.strptime(opened_time, "%H:%M").time() if opened_time else datetime.now().time()
        )

        session = CashSession(
            business_id=UUID(business_id),
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
        {"current_user": current_user, "session": session, **calcs, "locale": locale, "_": _},
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
        {"current_user": current_user, "session": session, "locale": locale, "_": _},
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
    bank_transfer_total: str = Form(...),
    expenses: str = Form("0"),
    closed_time: str = Form(...),
    closing_ticket: str | None = Form(None),
    notes: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Handle session close form submission (with permission check)."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    try:
        session.final_cash = parse_currency(final_cash)
        session.envelope_amount = parse_currency(envelope_amount) or Decimal("0")
        session.credit_card_total = parse_currency(credit_card_total) or Decimal("0")
        session.debit_card_total = parse_currency(debit_card_total) or Decimal("0")
        session.bank_transfer_total = parse_currency(bank_transfer_total) or Decimal("0")
        session.expenses = parse_currency(expenses) or Decimal("0")
        session.closed_time = datetime.strptime(closed_time, "%H:%M").time()
        session.closing_ticket = closing_ticket
        session.notes = notes
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
                "_": _,
            },
            status_code=400,
        )
