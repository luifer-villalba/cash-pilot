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
    page: int = 1,
    from_date: str | None = None,
    to_date: str | None = None,
    cashier_name: str | None = None,
    business_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Dashboard with paginated, filterable session list."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    per_page = 50
    skip = (page - 1) * per_page

    # Build filter query
    stmt = select(CashSession).options(joinedload(CashSession.business))

    if from_date:
        try:
            from_dt = datetime.fromisoformat(from_date)
            stmt = stmt.where(CashSession.opened_at >= from_dt)
        except ValueError:
            pass

    if to_date:
        try:
            to_dt = datetime.fromisoformat(to_date)
            to_dt = to_dt.replace(hour=23, minute=59, second=59)
            stmt = stmt.where(CashSession.opened_at <= to_dt)
        except ValueError:
            pass

    if cashier_name and cashier_name.strip():
        stmt = stmt.where(CashSession.cashier_name.ilike(f"%{cashier_name}%"))

    if business_id and business_id.strip():
        try:
            stmt = stmt.where(CashSession.business_id == UUID(business_id))
        except ValueError:
            pass

    # Count total matching
    count_stmt = select(CashSession).where(
        stmt.whereclause if hasattr(stmt, "whereclause") else True
    )
    count_result = await db.execute(count_stmt)
    total_sessions = len(count_result.scalars().all())
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
    stmt_active = select(CashSession).where(CashSession.status == "OPEN")
    result = await db.execute(stmt_active)
    active_count = len(result.scalars().all())

    # Get businesses for dropdown
    stmt_businesses = select(Business).where(Business.is_active).order_by(Business.name)
    result = await db.execute(stmt_businesses)
    businesses = result.scalars().all()

    # Get businesses count
    businesses_count = len(list(businesses))

    # Calculate today's revenue (sessions closed today by session_date)
    today = datetime.now().date()
    stmt_today = select(CashSession).where(CashSession.session_date == today)
    result = await db.execute(stmt_today)
    today_sessions = result.scalars().all()
    total_revenue = (
        sum(s.total_sales for s in today_sessions) if today_sessions else Decimal("0.00")
    )

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


@router.get("/sessions/table", response_class=HTMLResponse)
async def get_sessions_table(
    request: Request,
    page: int = 1,
    from_date: str | None = None,
    to_date: str | None = None,
    cashier_name: str | None = None,
    business_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Return only the sessions table partial (for HTMX)."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    per_page = 50
    skip = (page - 1) * per_page

    # Build filter query
    stmt = select(CashSession).options(joinedload(CashSession.business))

    if from_date:
        try:
            from_dt = datetime.fromisoformat(from_date).date()
            stmt = stmt.where(CashSession.session_date >= from_dt)
        except ValueError:
            pass

    if to_date:
        try:
            to_dt = datetime.fromisoformat(to_date).date()
            stmt = stmt.where(CashSession.session_date <= to_dt)
        except ValueError:
            pass

    if cashier_name and cashier_name.strip():
        stmt = stmt.where(CashSession.cashier_name.ilike(f"%{cashier_name}%"))

    if business_id and business_id.strip():
        try:
            stmt = stmt.where(CashSession.business_id == UUID(business_id))
        except ValueError:
            pass

    # Count total matching
    count_stmt = stmt.with_only_columns(CashSession.id)
    count_result = await db.execute(count_stmt)
    total_sessions = len(count_result.scalars().all())
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


# PARAMETRIZED ROUTES (catch-all, goes last)


@router.get("/sessions/{session_id}", response_class=HTMLResponse)
async def view_session(
    request: Request,
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """View single session details."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    try:
        stmt = (
            select(CashSession)
            .options(joinedload(CashSession.business))
            .where(CashSession.id == UUID(session_id))
        )
        result = await db.execute(stmt)
        session_obj = result.scalar_one_or_none()
    except ValueError:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

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


@router.get("/sessions/{session_id}/edit", response_class=HTMLResponse)
async def edit_session_form(
    request: Request,
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Form to edit/close cash session."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    try:
        stmt = (
            select(CashSession)
            .options(joinedload(CashSession.business))
            .where(CashSession.id == UUID(session_id))
        )
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
    except ValueError:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

    if not session:
        return templates.TemplateResponse(
            "404.html",
            {"request": request, "message": "Session not found"},
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


@router.post("/sessions", response_class=HTMLResponse)
async def create_session(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle session creation form submission."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    try:
        form_data = await request.form()

        # Parse business_id
        business_id = UUID(form_data["business_id"])

        # Parse cashier name
        cashier_name = form_data["cashier_name"].strip()

        # Parse initial_cash (remove currency formatting)
        initial_cash_str = form_data["initial_cash"].replace(".", "").replace(",", "")
        initial_cash = Decimal(initial_cash_str)

        # Parse session_date (optional, defaults to today)
        session_date_str = form_data.get("session_date", "").strip()
        if session_date_str:
            session_date = datetime.fromisoformat(session_date_str).date()
        else:
            session_date = datetime.now().date()

        # Parse opened_time (optional, defaults to now)
        opened_time_str = form_data.get("opened_time", "").strip()
        if opened_time_str:
            opened_time = datetime.fromisoformat(f"2000-01-01T{opened_time_str}").time()
        else:
            opened_time = datetime.now().time()

        # Create session
        session_obj = CashSession(
            business_id=business_id,
            cashier_name=cashier_name,
            initial_cash=initial_cash,
            session_date=session_date,
            opened_time=opened_time,
        )

        db.add(session_obj)
        await db.commit()
        await db.refresh(session_obj)

        return RedirectResponse(url=f"/sessions/{session_obj.id}", status_code=303)

    except Exception as e:
        stmt = select(Business).where(Business.is_active).order_by(Business.name)
        result = await db.execute(stmt)
        businesses = list(result.scalars().all())

        return templates.TemplateResponse(
            "create_session.html",
            {
                "request": request,
                "error": f"Failed to create session: {str(e)}",
                "businesses": businesses,
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
        session_obj.final_cash = Decimal(form_data["final_cash"].replace(".", "").replace(",", ""))
        session_obj.envelope_amount = Decimal(
            form_data["envelope_amount"].replace(".", "").replace(",", "")
        )
        session_obj.credit_card_total = Decimal(
            form_data.get("credit_card_total", "0").replace(".", "").replace(",", "")
        )
        session_obj.debit_card_total = Decimal(
            form_data.get("debit_card_total", "0").replace(".", "").replace(",", "")
        )
        session_obj.bank_transfer_total = Decimal(
            form_data.get("bank_transfer_total", "0").replace(".", "").replace(",", "")
        )
        session_obj.expenses = Decimal(
            form_data.get("expenses", "0").replace(".", "").replace(",", "")
        )

        closed_time_str = form_data.get("closed_time", "").strip()
        if closed_time_str:
            session_obj.closed_time = datetime.fromisoformat(f"2000-01-01T{closed_time_str}").time()
        else:
            session_obj.closed_time = datetime.now().time()

        session_obj.closing_ticket = form_data.get("closing_ticket")
        session_obj.notes = form_data.get("notes")

        db.add(session_obj)
        await db.commit()

        return RedirectResponse(url=f"/sessions/{session_id}", status_code=303)
    except Exception as e:
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
