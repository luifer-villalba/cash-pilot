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

from cashpilot.core.db import get_db
from cashpilot.models import Business, CashSession

# Configure templates
templates = Jinja2Templates(directory="src/cashpilot/templates")

# Translations directory
TRANSLATIONS_DIR = Path(__file__).parent.parent / "translations"

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


# Dashboard (list view)
@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    page: int = Query(1, ge=1),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    cashier_name: str | None = Query(None),
    business_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Dashboard with paginated, filterable session list."""
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
    from datetime import date as date_type

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
async def create_session_post(
    request: Request,
    business_id: str = Form(...),
    cashier_name: str = Form(...),
    initial_cash: str = Form(...),
    session_date: str | None = Form(None),
    opened_time: str | None = Form(None),
    allow_overlap: bool = Form(False),
    db: AsyncSession = Depends(get_db),
):
    """Handle session creation form submission."""

    from cashpilot.core.errors import ConflictError, InvalidStateError
    from cashpilot.models import CashSessionCreate

    try:
        session_data = CashSessionCreate(
            business_id=UUID(business_id),
            cashier_name=cashier_name,
            initial_cash=Decimal(initial_cash),
            session_date=datetime.fromisoformat(session_date).date() if session_date else None,
            opened_time=datetime.strptime(opened_time, "%H:%M").time() if opened_time else None,
            allow_overlap=allow_overlap,
        )

        # Call API endpoint to create
        from cashpilot.models import CashSession

        # Create session directly
        session_obj = CashSession(
            business_id=session_data.business_id,
            cashier_name=session_data.cashier_name,
            initial_cash=session_data.initial_cash,
            session_date=session_data.session_date or date_type.today(),
            opened_time=session_data.opened_time or datetime.now().time(),
        )
        db.add(session_obj)
        await db.flush()
        await db.refresh(session_obj)

        return RedirectResponse(url=f"/sessions/{session_obj.id}", status_code=302)
    except (ConflictError, InvalidStateError) as e:
        # Re-render form with error
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
                "error": str(e),
                "locale": locale,
                "_": _,
            },
            status_code=400,
        )


@router.get("/sessions/table", response_class=HTMLResponse)
async def sessions_table(
    request: Request,
    page: int = Query(1, ge=1),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    cashier_name: str | None = Query(None),
    business_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Render sessions table with filters and pagination."""
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

    return templates.TemplateResponse(
        "partials/sessions_table.html",
        {
            "request": request,
            "sessions": sessions,
            "page": page,
            "total_pages": total_pages,
            "total_sessions": total_sessions,
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
    session = result.scalar_one_or_none()

    if not session:
        return RedirectResponse(url="/", status_code=302)

    return templates.TemplateResponse(
        "session_detail.html",
        {
            "request": request,
            "session": session,
            "locale": locale,
            "_": _,
        },
    )


@router.get("/sessions/{session_id}/edit", response_class=HTMLResponse)
async def edit_session_form(
    request: Request,
    session_id: str,
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
        "edit_session.html",
        {
            "request": request,
            "session": session,
            "locale": locale,
            "_": _,
        },
    )


@router.post("/sessions/{session_id}", response_class=HTMLResponse)
async def close_session_post(
    request: Request,
    session_id: str,
    final_cash: str = Form(...),
    envelope_amount: str = Form(...),
    credit_card_total: str = Form(...),
    debit_card_total: str = Form(...),
    bank_transfer_total: str = Form(...),
    expenses: str = Form("0.00"),
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
        session.final_cash = Decimal(final_cash)
        session.envelope_amount = Decimal(envelope_amount)
        session.credit_card_total = Decimal(credit_card_total)
        session.debit_card_total = Decimal(debit_card_total)
        session.bank_transfer_total = Decimal(bank_transfer_total)
        session.expenses = Decimal(expenses)
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
            "edit_session.html",
            {
                "request": request,
                "session": session,
                "error": str(e),
                "locale": locale,
                "_": _,
            },
            status_code=400,
        )
