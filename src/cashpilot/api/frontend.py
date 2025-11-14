# File: src/cashpilot/api/frontend.py
"""Frontend routes for HTML templates with i18n support."""

import gettext
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from cashpilot.core.db import get_db
from cashpilot.models import Business, CashSession

# Configure templates
templates = Jinja2Templates(directory="src/cashpilot/templates")

# Translations directory
TRANSLATIONS_DIR = Path(__file__).parent.parent / "translations"

router = APIRouter(tags=["frontend"])


def get_locale(request: Request) -> str:
    """Get locale from query param (?lang=es) or Accept-Language header. Default: en."""
    # Check query param first
    lang = request.query_params.get("lang", "").lower()
    if lang in ["es", "en"]:
        return lang

    # Check Accept-Language header
    accept_lang = request.headers.get("accept-language", "").split(",")[0].split("-")[0].lower()
    if accept_lang == "es":
        return "es"

    return "en"  # Default


def get_translation_function(locale: str):
    """Get gettext translation function for locale."""
    if locale == "es":
        try:
            translation = gettext.translation(
                "messages",
                localedir=str(TRANSLATIONS_DIR),
                languages=["es_PY"],
                fallback=True,
            )
            return translation.gettext
        except Exception:
            return lambda x: x
    return lambda x: x  # English: identity function


# Dashboard (list view)
@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    page: int = 1,
    db: AsyncSession = Depends(get_db),
):
    """Dashboard homepage with paginated session list."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    per_page = 50
    skip = (page - 1) * per_page

    # Get total count
    count_stmt = select(CashSession)
    count_result = await db.execute(count_stmt)
    total_sessions = len(count_result.scalars().all())
    total_pages = (total_sessions + per_page - 1) // per_page

    # Get paginated sessions
    stmt_sessions = (
        select(CashSession)
        .options(joinedload(CashSession.business))
        .order_by(CashSession.opened_at.desc())
        .offset(skip)
        .limit(per_page)
    )
    result = await db.execute(stmt_sessions)
    sessions = result.scalars().unique().all()

    # Get active sessions count
    stmt_active = select(CashSession).where(CashSession.status == "OPEN")
    result = await db.execute(stmt_active)
    active_count = len(result.scalars().all())

    # Get businesses count
    stmt_businesses = select(Business).where(Business.is_active)
    result = await db.execute(stmt_businesses)
    businesses_count = len(result.scalars().all())

    # Calculate today's revenue
    today = datetime.now().date()
    stmt_today = select(CashSession).where(
        CashSession.closed_at >= datetime.combine(today, datetime.min.time())
    )
    result = await db.execute(stmt_today)
    today_sessions = result.scalars().all()
    total_revenue = (
        sum(s.total_sales for s in today_sessions) if today_sessions else Decimal("0.00")
    )

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "sessions": sessions,
            "active_sessions_count": active_count,
            "businesses_count": businesses_count,
            "page": page,
            "total_pages": total_pages,
            "total_sessions": total_sessions,
            "total_revenue": total_revenue,
            "discrepancies_count": 0,
            "locale": locale,
            "_": _,
        },
    )


# Create session flow
@router.get("/sessions/create", response_class=HTMLResponse)
async def create_session_form(request: Request, db: AsyncSession = Depends(get_db)):
    """Form to create new cash session."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    stmt = select(Business).where(Business.is_active).order_by(Business.name)
    result = await db.execute(stmt)
    businesses = list(result.scalars().all())

    return templates.TemplateResponse(
        "create_session.html",
        {
            "request": request,
            "businesses": businesses,
            "locale": locale,
            "_": _,
        },
    )


@router.post("/sessions", response_class=HTMLResponse)
async def create_session(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle session creation form submission."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    form_data = await request.form()

    try:
        session_obj = CashSession(
            business_id=UUID(form_data["business_id"]),
            cashier_name=form_data["cashier_name"],
            initial_cash=Decimal(form_data["initial_cash"]),
            opened_at=(
                datetime.fromisoformat(form_data["opened_at"])
                if form_data.get("opened_at")
                else datetime.now()
            ),
        )
        db.add(session_obj)
        await db.commit()
        await db.refresh(session_obj)

        return RedirectResponse(url=f"/sessions/{session_obj.id}", status_code=303)
    except Exception as e:
        # Reload businesses for error case
        stmt = select(Business).where(Business.is_active).order_by(Business.name)
        result = await db.execute(stmt)
        businesses = list(result.scalars().all())

        return templates.TemplateResponse(
            "create_session.html",
            {
                "request": request,
                "error": str(e),
                "businesses": businesses,
                "locale": locale,
                "_": _,
            },
        )


# View session details
@router.get("/sessions/{session_id}", response_class=HTMLResponse)
async def view_session(
    request: Request,
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """View single session details."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    stmt = (
        select(CashSession)
        .options(joinedload(CashSession.business))
        .where(CashSession.id == UUID(session_id))
    )
    result = await db.execute(stmt)
    session_obj = result.scalar_one_or_none()

    if not session_obj:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

    return templates.TemplateResponse(
        "session_detail.html",
        {
            "request": request,
            "session": session_obj,
            "locale": locale,
            "_": _,
        },
    )


# Close session flow
@router.get("/sessions/{session_id}/edit", response_class=HTMLResponse)
async def edit_session_form(
    request: Request,
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Form to edit/close cash session."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    stmt = (
        select(CashSession)
        .options(joinedload(CashSession.business))
        .where(CashSession.id == UUID(session_id))
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        return templates.TemplateResponse(
            "404.html",
            {
                "request": request,
                "message": "Session not found",
            },
            status_code=404,
        )

    return templates.TemplateResponse(
        "edit_session.html",
        {
            "request": request,
            "session": session,
            "locale": locale,
            "_": _,
        },
    )


@router.post("/sessions/{session_id}", response_class=HTMLResponse)
async def close_session(
    request: Request,
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Handle session close form submission."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    form_data = await request.form()

    try:
        stmt = (
            select(CashSession)
            .options(joinedload(CashSession.business))
            .where(CashSession.id == UUID(session_id))
        )
        result = await db.execute(stmt)
        session_obj = result.scalar_one_or_none()

        if not session_obj:
            return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

        # Update session
        session_obj.status = "CLOSED"
        session_obj.final_cash = Decimal(form_data["final_cash"])
        session_obj.envelope_amount = Decimal(form_data["envelope_amount"])
        session_obj.credit_card_total = Decimal(form_data.get("credit_card_total", 0))
        session_obj.debit_card_total = Decimal(form_data.get("debit_card_total", 0))
        session_obj.bank_transfer_total = Decimal(form_data.get("bank_transfer_total", 0))
        session_obj.expenses = Decimal(form_data.get("expenses", 0))
        session_obj.closing_ticket = form_data.get("closing_ticket")
        session_obj.notes = form_data.get("notes")
        session_obj.closed_at = datetime.now()

        db.add(session_obj)
        await db.commit()

        return RedirectResponse(url=f"/sessions/{session_id}", status_code=303)
    except Exception as e:
        # Reload session for error case
        stmt = (
            select(CashSession)
            .options(joinedload(CashSession.business))
            .where(CashSession.id == UUID(session_id))
        )
        result = await db.execute(stmt)
        session_obj = result.scalar_one_or_none()

        return templates.TemplateResponse(
            "edit_session.html",
            {
                "request": request,
                "session": session_obj,
                "error": str(e),
                "locale": locale,
                "_": _,
            },
        )
