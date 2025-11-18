# File: src/cashpilot/api/frontend.py
"""Frontend routes for HTML templates with i18n support."""

import gettext
from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from cashpilot.api.auth import get_current_user, logger
from cashpilot.core.db import get_db
from cashpilot.models import Business, CashSession
from cashpilot.models.user import User

TEMPLATES_DIR = Path("/app/templates")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Translations directory
TRANSLATIONS_DIR = Path("/app/translations")

router = APIRouter(tags=["frontend"])


def get_locale(request: Request) -> str:
    """Get locale from query param (?lang=es) or Accept-Language header. Default: en."""
    lang = request.query_params.get("lang", "").lower()
    if lang in ["es", "en"]:
        return lang

    accept_lang = request.headers.get("accept-language", "").split(",")[0].split("-")[0].lower()
    if accept_lang == "es":
        return "es"

    return "en"


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
    return lambda x: x


@router.get("/login", response_class=HTMLResponse)
async def login_page():
    """Render login page (public)."""
    template_path = Path("/app/templates/login.html")
    with open(template_path, "r") as f:
        return f.read()


# Dashboard (list view)
@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    cashier_name: str | None = Query(None),
    business_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Dashboard with paginated, filterable session list."""
    logger.info("dashboard.accessed", current_user_id=str(current_user.id))  # ADD THIS

    locale = get_locale(request)
    _ = get_translation_function(locale)

    per_page = 10
    skip = (page - 1) * per_page

    # Build filter query
    stmt = select(CashSession).options(joinedload(CashSession.business))

    filters = []

    if from_date:
        try:
            from_dt = datetime.fromisoformat(from_date).date()
            filters.append(CashSession.session_date >= from_dt)
        except ValueError:
            pass

    if to_date:
        try:
            to_dt = datetime.fromisoformat(to_date).date()
            filters.append(CashSession.session_date <= to_dt)
        except ValueError:
            pass

    if cashier_name and cashier_name.strip():
        filters.append(CashSession.cashier_name.ilike(f"%{cashier_name}%"))

    if business_id and business_id.strip():
        try:
            filters.append(CashSession.business_id == UUID(business_id))
        except ValueError:
            pass

    # Apply filters to main query
    for f in filters:
        stmt = stmt.where(f)

    # Count total matching
    count_stmt = select(func.count(CashSession.id))
    for f in filters:
        count_stmt = count_stmt.where(f)
    count_result = await db.execute(count_stmt)
    total_sessions = count_result.scalar() or 0
    total_pages = (total_sessions + per_page - 1) // per_page

    # Get paginated results
    stmt = (
        stmt.order_by(CashSession.session_date.desc(), CashSession.opened_time.desc())
        .offset(skip)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    sessions = result.scalars().unique().all()

    # Get active sessions count
    stmt_active = select(func.count(CashSession.id)).where(CashSession.status == "OPEN")
    result_active = await db.execute(stmt_active)
    active_count = result_active.scalar() or 0

    # Get businesses for dropdown
    stmt_businesses = select(Business).where(Business.is_active).order_by(Business.name)
    result_businesses = await db.execute(stmt_businesses)
    businesses = result_businesses.scalars().all()
    businesses_count = len(list(businesses))

    # Calculate today's revenue (sessions closed today by session_date)
    today = date_type.today()
    stmt_today = select(
        func.sum(
            CashSession.final_cash
            + CashSession.envelope_amount
            + CashSession.credit_card_total
            + CashSession.debit_card_total
            + CashSession.bank_transfer_total
            - CashSession.initial_cash
        )
    ).where(CashSession.session_date == today, CashSession.status == "CLOSED")
    result_today = await db.execute(stmt_today)
    total_revenue = result_today.scalar() or Decimal("0.00")

    # Build active filters display
    active_filters = {}
    if from_date:
        active_filters["from_date"] = from_date
    if to_date:
        active_filters["to_date"] = to_date
    if cashier_name:
        active_filters["cashier_name"] = cashier_name
    if business_id:
        active_filters["business_id"] = business_id

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "current_user": current_user,
            "sessions": sessions,
            "active_sessions_count": active_count,
            "businesses_count": businesses_count,
            "businesses": businesses,
            "page": page,
            "total_pages": total_pages,
            "total_sessions": total_sessions,
            "total_revenue": total_revenue,
            "discrepancies_count": 0,
            "active_filters": active_filters,
            "current_filters": {
                "from_date": from_date,
                "to_date": to_date,
                "cashier_name": cashier_name,
                "business_id": business_id,
            },
            "locale": locale,
            "_": _,
        },
    )


# SPECIFIC ROUTES FIRST (before parametrized routes)


@router.get("/sessions/create", response_class=HTMLResponse)
async def create_session_form(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Form to create new cash session."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    stmt = select(Business).where(Business.is_active).order_by(Business.name)
    result = await db.execute(stmt)
    businesses = list(result.scalars().all())

    return templates.TemplateResponse(
        "sessions/create_session.html",
        {
            "request": request,
            "current_user": current_user,
            "businesses": businesses,
            "locale": locale,
            "_": _,
        },
    )


@router.post("/sessions", response_class=HTMLResponse)
async def create_session_post(
    request: Request,
    current_user: User = Depends(get_current_user),
    business_id: str = Form(...),
    cashier_name: str = Form(...),
    initial_cash: str = Form(...),
    session_date: str | None = Form(None),
    opened_time: str | None = Form(None),
    allow_overlap: bool = Form(False),
    db: AsyncSession = Depends(get_db),
):
    """Handle session creation form submission."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    try:
        initial_cash_val = Decimal(initial_cash.replace(",", "").replace(".", ""))
        session_date_val = (
            datetime.fromisoformat(session_date).date() if session_date else date_type.today()
        )
        opened_time_val = (
            datetime.strptime(opened_time, "%H:%M").time() if opened_time else datetime.now().time()
        )

        session = CashSession(
            business_id=UUID(business_id),
            cashier_name=cashier_name,
            initial_cash=initial_cash_val,
            session_date=session_date_val,
            opened_time=opened_time_val,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        return RedirectResponse(url=f"/sessions/{session.id}", status_code=302)

    except Exception as e:
        stmt = select(Business).where(Business.is_active).order_by(Business.name)
        result = await db.execute(stmt)
        businesses = list(result.scalars().all())

        return templates.TemplateResponse(
            "sessions/create_session.html",
            {
                "request": request,
                "current_user": current_user,
                "businesses": businesses,
                "error": str(e),
                "locale": locale,
                "_": _,
            },
            status_code=400,
        )


@router.get("/sessions/{session_id}", response_class=HTMLResponse)
async def session_detail(
    request: Request,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Display single session details."""
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
        return RedirectResponse(url="/", status_code=302)

    return templates.TemplateResponse(
        "sessions/session_detail.html",
        {
            "request": request,
            "current_user": current_user,
            "session": session,
            "locale": locale,
            "_": _,
        },
    )


@router.get("/sessions/{session_id}/edit", response_class=HTMLResponse)
async def edit_session_form(
    request: Request,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Form to close/edit cash session."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    stmt = select(CashSession).where(CashSession.id == UUID(session_id))
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        return RedirectResponse(url="/", status_code=302)

    return templates.TemplateResponse(
        "sessions/edit_session.html",
        {
            "request": request,
            "current_user": current_user,
            "session": session,
            "locale": locale,
            "_": _,
        },
    )


@router.get("/sessions/{session_id}/edit-open", response_class=HTMLResponse)
async def edit_open_session_form(
    request: Request,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Form to edit an OPEN cash session."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    stmt = select(CashSession).where(CashSession.id == UUID(session_id))
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        return RedirectResponse(url="/", status_code=302)

    if session.status != "OPEN":
        return RedirectResponse(url=f"/sessions/{session_id}", status_code=302)

    return templates.TemplateResponse(
        "sessions/edit_open_session.html",
        {
            "request": request,
            "current_user": current_user,
            "session": session,
            "locale": locale,
            "_": _,
        },
    )


@router.post("/sessions/{session_id}/edit-open", response_class=HTMLResponse)
async def edit_open_session_post(
    request: Request,
    session_id: str,
    current_user: User = Depends(get_current_user),
    cashier_name: str | None = Form(None),
    initial_cash: str | None = Form(None),
    opened_time: str | None = Form(None),
    expenses: str | None = Form(None),
    reason: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Handle edit open session form submission."""
    try:
        stmt = select(CashSession).where(CashSession.id == UUID(session_id))
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            return RedirectResponse(url="/", status_code=302)

        if session.status != "OPEN":
            return RedirectResponse(url=f"/sessions/{session_id}", status_code=302)

        # Update fields if provided
        if cashier_name:
            session.cashier_name = cashier_name
        if initial_cash:
            session.initial_cash = Decimal(initial_cash.replace(",", "").replace(".", ""))
        if opened_time:
            session.opened_time = datetime.strptime(opened_time, "%H:%M").time()
        if expenses:
            session.expenses = Decimal(expenses.replace(",", "").replace(".", ""))

        db.add(session)
        await db.commit()

        return RedirectResponse(url=f"/sessions/{session_id}", status_code=302)

    except ValueError as e:
        locale = get_locale(request)
        _ = get_translation_function(locale)

        stmt = select(CashSession).where(CashSession.id == UUID(session_id))
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        return templates.TemplateResponse(
            "sessions/edit_open_session.html",
            {
                "request": request,
                "current_user": current_user,
                "session": session,
                "error": f"Invalid input: {str(e)}",
                "locale": locale,
                "_": _,
            },
            status_code=400,
        )


@router.post("/sessions/{session_id}", response_class=HTMLResponse)
async def close_session_post(
    request: Request,
    session_id: str,
    current_user: User = Depends(get_current_user),
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
    """Handle session close form submission."""
    try:
        stmt = select(CashSession).where(CashSession.id == UUID(session_id))
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            return RedirectResponse(url="/", status_code=302)

        # Update session
        session.final_cash = Decimal(final_cash.replace(",", "").replace(".", ""))
        session.envelope_amount = Decimal(envelope_amount.replace(",", "").replace(".", ""))
        session.credit_card_total = Decimal(credit_card_total.replace(",", "").replace(".", ""))
        session.debit_card_total = Decimal(debit_card_total.replace(",", "").replace(".", ""))
        session.bank_transfer_total = Decimal(bank_transfer_total.replace(",", "").replace(".", ""))
        session.expenses = Decimal(expenses.replace(",", "").replace(".", "") or "0")
        session.closed_time = datetime.strptime(closed_time, "%H:%M").time()
        session.closing_ticket = closing_ticket
        session.notes = notes
        session.status = "CLOSED"

        db.add(session)
        await db.commit()

        return RedirectResponse(url=f"/sessions/{session_id}", status_code=302)
    except Exception as e:
        # Re-render form with error
        locale = get_locale(request)
        _ = get_translation_function(locale)

        stmt = select(CashSession).where(CashSession.id == UUID(session_id))
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        return templates.TemplateResponse(
            "sessions/edit_session.html",
            {
                "request": request,
                "current_user": current_user,
                "session": session,
                "error": str(e),
                "locale": locale,
                "_": _,
            },
            status_code=400,
        )


@router.get("/businesses", response_class=HTMLResponse)
async def businesses_list(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all businesses (pharmacy locations)."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    stmt = select(Business).where(Business.is_active).order_by(Business.name)
    result = await db.execute(stmt)
    businesses = result.scalars().all()

    return templates.TemplateResponse(
        "businesses/list.html",
        {
            "request": request,
            "current_user": current_user,
            "businesses": businesses,
            "locale": locale,
            "_": _,
        },
    )


@router.get("/businesses/create", response_class=HTMLResponse)
async def create_business_form(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Form to create new business."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    return templates.TemplateResponse(
        "businesses/create.html",
        {
            "request": request,
            "current_user": current_user,
            "locale": locale,
            "_": _,
        },
    )


@router.post("/businesses", response_class=HTMLResponse)
async def create_business_post(
    request: Request,
    current_user: User = Depends(get_current_user),
    name: str = Form(...),
    address: str | None = Form(None),
    phone: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Handle business creation."""
    try:
        business = Business(
            name=name,
            address=address,
            phone=phone,
            is_active=True,
        )
        db.add(business)
        await db.commit()

        return RedirectResponse(url="/businesses", status_code=302)
    except Exception as e:
        locale = get_locale(request)
        _ = get_translation_function(locale)

        return templates.TemplateResponse(
            "businesses/create.html",
            {
                "request": request,
                "current_user": current_user,
                "error": str(e),
                "locale": locale,
                "_": _,
            },
            status_code=400,
        )
