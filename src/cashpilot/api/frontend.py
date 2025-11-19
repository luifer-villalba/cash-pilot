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

from cashpilot.api.auth import get_current_user
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


# File: src/cashpilot/api/frontend.py
def parse_currency(value: str | None) -> Decimal | None:
    """Parse Paraguay currency format (5.000.000 → 5000000 or 750000.00 → 750000.00)."""
    if not value or not value.strip():
        return None

    value = value.strip()

    # Handle decimal point: split on last dot
    if "." in value:
        parts = value.rsplit(".", 1)
        integer_part = parts[0].replace(".", "").replace(",", "")
        decimal_part = parts[1].replace(",", "")

        # If decimal part is 2 digits, it's a decimal; if 3+ it's thousands sep
        if len(decimal_part) <= 2:
            value = f"{integer_part}.{decimal_part}"
        else:
            # Last dot was thousands separator, remove all dots
            value = value.replace(".", "").replace(",", "")
    else:
        # No dots, just remove commas
        value = value.replace(",", "")

    if not value or value == ".":
        return None

    return Decimal(value)


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
    page: int = Query(1, ge=1),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    cashier_name: str | None = Query(None),
    business_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Dashboard with paginated, filterable session list."""
    # Redirect to login if not authenticated
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)

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

    # Calculate today's revenue
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

    # Fetch current user for navbar
    current_user = None
    user_id = request.session.get("user_id")
    if user_id:
        stmt_user = select(User).where(User.id == UUID(user_id))
        result_user = await db.execute(stmt_user)
        current_user = result_user.scalar_one_or_none()

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
        request,
        "sessions/create_session.html",
        {
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
        request,
        "sessions/session_detail.html",
        {
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
        request,
        "sessions/edit_session.html",
        {
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
        request,
        "sessions/edit_open_session.html",
        {
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

        # Track changes for audit log
        from cashpilot.models.cash_session_audit_log import CashSessionAuditLog

        changed_fields = []
        old_values = {}
        new_values = {}

        # Update fields if provided
        if cashier_name and cashier_name != session.cashier_name:
            changed_fields.append("cashier_name")
            old_values["cashier_name"] = session.cashier_name
            new_values["cashier_name"] = cashier_name
            session.cashier_name = cashier_name

        if initial_cash:
            initial_cash_val = parse_currency(initial_cash)
            if initial_cash_val and initial_cash_val != session.initial_cash:
                changed_fields.append("initial_cash")
                old_values["initial_cash"] = str(session.initial_cash)
                new_values["initial_cash"] = str(initial_cash_val)
                session.initial_cash = initial_cash_val

        if opened_time:
            opened_time_obj = datetime.strptime(opened_time, "%H:%M").time()
            if opened_time_obj != session.opened_time:
                changed_fields.append("opened_time")
                old_values["opened_time"] = str(session.opened_time)
                new_values["opened_time"] = str(opened_time_obj)
                session.opened_time = opened_time_obj

        if expenses:
            expenses_val = parse_currency(expenses)
            if expenses_val and expenses_val != session.expenses:
                changed_fields.append("expenses")
                old_values["expenses"] = str(session.expenses)
                new_values["expenses"] = str(expenses_val)
                session.expenses = expenses_val

        # Set audit tracking fields
        session.last_modified_at = datetime.now()
        session.last_modified_by = "system"

        db.add(session)
        await db.commit()

        # Create audit log if changes were made
        if changed_fields:
            audit_log = CashSessionAuditLog(
                session_id=session.id,
                action="edit",
                changed_fields=changed_fields,
                old_values=old_values,
                new_values=new_values,
                changed_by="system",
                reason=reason,
            )
            db.add(audit_log)
            await db.commit()

        return RedirectResponse(url=f"/sessions/{session_id}", status_code=302)

    except ValueError as e:
        locale = get_locale(request)
        _ = get_translation_function(locale)

        stmt = select(CashSession).where(CashSession.id == UUID(session_id))
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

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

        return RedirectResponse(url=f"/sessions/{session_id}", status_code=302)
    except Exception as e:
        # Re-render form with error
        locale = get_locale(request)
        _ = get_translation_function(locale)

        stmt = select(CashSession).where(CashSession.id == UUID(session_id))
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        return templates.TemplateResponse(
            request,
            "sessions/edit_session.html",
            {
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
        request,
        "businesses/list.html",
        {
            "current_user": current_user,
            "businesses": businesses,
            "locale": locale,
            "_": _,
        },
    )


# ========== BUSINESS MANAGEMENT ROUTES ==========


@router.get("/businesses", response_class=HTMLResponse)
async def list_businesses(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """List all businesses with management options."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    stmt = select(Business).order_by(Business.name)
    result = await db.execute(stmt)
    businesses = result.scalars().all()

    return templates.TemplateResponse(
        request,
        "businesses/list.html",
        {
            "businesses": businesses,
            "locale": locale,
            "_": _,
        },
    )


@router.get("/businesses/new", response_class=HTMLResponse)
async def create_business_form(request: Request):
    """Form to create new business."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    return templates.TemplateResponse(
        request,
        "businesses/create.html",
        {
            "locale": locale,
            "_": _,
        },
    )


@router.post("/businesses")
async def create_business_post(
    request: Request,
    name: str = Form(...),
    address: str | None = Form(None),
    phone: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Handle business creation form submission."""
    business = Business(
        name=name.strip(),
        address=address.strip() if address else None,
        phone=phone.strip() if phone else None,
        cashiers=[],
    )
    db.add(business)
    await db.commit()
    await db.refresh(business)

    return RedirectResponse(url=f"/businesses/{business.id}/edit", status_code=302)


@router.get("/businesses/{business_id}/edit", response_class=HTMLResponse)
async def edit_business_form(
    request: Request,
    business_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Form to edit business and manage cashiers."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    stmt = select(Business).where(Business.id == UUID(business_id))
    result = await db.execute(stmt)
    business = result.scalar_one_or_none()

    if not business:
        return RedirectResponse(url="/businesses", status_code=302)

    return templates.TemplateResponse(
        request,
        "businesses/edit.html",
        {
            "business": business,
            "locale": locale,
            "_": _,
        },
    )


@router.post("/businesses/{business_id}")
async def update_business_post(
    request: Request,
    business_id: str,
    name: str = Form(...),
    address: str | None = Form(None),
    phone: str | None = Form(None),
    is_active: bool = Form(True),
    db: AsyncSession = Depends(get_db),
):
    """Handle business update form submission."""
    stmt = select(Business).where(Business.id == UUID(business_id))
    result = await db.execute(stmt)
    business = result.scalar_one_or_none()

    if not business:
        return RedirectResponse(url="/businesses", status_code=302)

    business.name = name.strip()
    business.address = address.strip() if address else None
    business.phone = phone.strip() if phone else None
    business.is_active = is_active

    db.add(business)
    await db.commit()

    return RedirectResponse(url=f"/businesses/{business.id}/edit", status_code=302)


@router.post("/businesses/{business_id}/cashiers/add")
async def add_cashier_form(
    business_id: str,
    cashier_name: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Handle adding cashier via form."""
    stmt = select(Business).where(Business.id == UUID(business_id))
    result = await db.execute(stmt)
    business = result.scalar_one_or_none()

    if not business:
        return RedirectResponse(url="/businesses", status_code=302)

    cashier_clean = cashier_name.strip()
    if cashier_clean and cashier_clean not in business.cashiers:
        business.cashiers.append(cashier_clean)
        db.add(business)
        await db.commit()

    return RedirectResponse(url=f"/businesses/{business.id}/edit", status_code=302)


@router.post("/businesses/{business_id}/cashiers/remove")
async def remove_cashier_form(
    business_id: str,
    cashier_name: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Handle removing cashier via form."""
    stmt = select(Business).where(Business.id == UUID(business_id))
    result = await db.execute(stmt)
    business = result.scalar_one_or_none()

    if not business:
        return RedirectResponse(url="/businesses", status_code=302)

    if cashier_name in business.cashiers:
        business.cashiers.remove(cashier_name)
        db.add(business)
        await db.commit()

    return RedirectResponse(url=f"/businesses/{business.id}/edit", status_code=302)


@router.delete("/businesses/{business_id}", response_class=HTMLResponse)
async def delete_business(
    business_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete business (sets is_active=False)."""
    stmt = select(Business).where(Business.id == UUID(business_id))
    result = await db.execute(stmt)
    business = result.scalar_one_or_none()

    if not business:
        return RedirectResponse(url="/businesses", status_code=302)

    business.is_active = False
    db.add(business)
    await db.commit()

    return RedirectResponse(url="/businesses", status_code=302)
