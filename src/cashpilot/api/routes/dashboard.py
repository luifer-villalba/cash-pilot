# File: src/cashpilot/api/routes/dashboard.py
"""Dashboard routes (HTML endpoints)."""

from datetime import date as date_type
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import Numeric, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.api.auth import get_current_user
from cashpilot.api.utils import (
    _build_session_filters,
    _get_paginated_sessions,
    format_currency_py,
    get_locale,
    get_translation_function,
)
from cashpilot.core.db import get_db
from cashpilot.models import Business, CashSession
from cashpilot.models.user import User

TEMPLATES_DIR = Path("/app/templates")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

templates.env.filters["format_currency_py"] = format_currency_py

router = APIRouter(tags=["dashboard"])


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    page: int = Query(1, ge=1),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    cashier_name: str | None = Query(None),
    business_id: str | None = Query(None),
    status: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dashboard with paginated, filterable session list."""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)

    locale = get_locale(request)
    _ = get_translation_function(locale)

    # NO server defaults - client handles timezone
    filters = await _build_session_filters(
        from_date, to_date, cashier_name, business_id, status, current_user
    )
    sessions, total_sessions, total_pages = await _get_paginated_sessions(
        db, filters, page=page, per_page=10
    )

    stmt_active = select(func.count(CashSession.id)).where(CashSession.status == "OPEN")
    result_active = await db.execute(stmt_active)
    active_count = result_active.scalar() or 0

    stmt_businesses = select(Business).where(Business.is_active).order_by(Business.name)
    result_businesses = await db.execute(stmt_businesses)
    businesses = result_businesses.scalars().all()
    businesses_count = len(list(businesses))

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

    active_filters = {}
    if from_date:
        active_filters["from_date"] = from_date
    if to_date:
        active_filters["to_date"] = to_date
    if cashier_name:
        active_filters["cashier_name"] = cashier_name
    if business_id:
        active_filters["business_id"] = business_id
    if status:
        active_filters["status"] = status

    current_user = None
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
                "status": status,
            },
            "locale": locale,
            "_": _,
        },
    )


@router.get("/sessions/table", response_class=HTMLResponse)
async def sessions_table(
    request: Request,
    page: int = Query(1, ge=1),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    cashier_name: str | None = Query(None),
    business_id: str | None = Query(None),
    status: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Paginated sessions table partial (HTMX endpoint)."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    filters = await _build_session_filters(
        from_date, to_date, cashier_name, business_id, status, current_user
    )
    sessions, total_sessions, total_pages = await _get_paginated_sessions(
        db, filters, page=page, per_page=10
    )

    query_params = []
    if from_date:
        query_params.append(f"from_date={from_date}")
    if to_date:
        query_params.append(f"to_date={to_date}")
    if cashier_name:
        query_params.append(f"cashier_name={cashier_name}")
    if business_id:
        query_params.append(f"business_id={business_id}")

    query_string = "&".join(query_params)
    if query_string:
        query_string = "&" + query_string

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
                "status": status,
            },
            "query_string": query_string,
            "locale": locale,
            "_": _,
        },
    )


@router.get("/stats", response_class=HTMLResponse)
async def get_dashboard_stats(
    request: Request,
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    cashier_name: str | None = Query(None),
    business_id: str | None = Query(None),
    status: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return dashboard stats as HTML partial."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    filters = await _build_session_filters(
        from_date, to_date, cashier_name, business_id, status, current_user
    )
    filters.append(~CashSession.is_deleted)

    if business_id:
        selected_businesses = 1
    else:
        result = await db.execute(select(func.count(Business.id)).where(Business.is_active))
        selected_businesses = result.scalar() or 0

    active_sessions = await db.execute(
        select(func.count(CashSession.id)).where(and_(CashSession.status == "OPEN", *filters))
    )

    cash_sales = await db.execute(
        select(
            func.sum(
                (
                    CashSession.final_cash + CashSession.envelope_amount - CashSession.initial_cash
                ).cast(Numeric(12, 2))
            )
        ).where(and_(CashSession.status == "CLOSED", *filters))
    )

    credit_card = await db.execute(
        select(func.sum(CashSession.credit_card_total.cast(Numeric(12, 2)))).where(
            and_(CashSession.status == "CLOSED", *filters)
        )
    )

    debit_card = await db.execute(
        select(func.sum(CashSession.debit_card_total.cast(Numeric(12, 2)))).where(
            and_(CashSession.status == "CLOSED", *filters)
        )
    )

    bank_transfer = await db.execute(
        select(func.sum(CashSession.bank_transfer_total.cast(Numeric(12, 2)))).where(
            and_(CashSession.status == "CLOSED", *filters)
        )
    )

    expenses = await db.execute(
        select(func.sum(CashSession.expenses.cast(Numeric(12, 2)))).where(
            and_(CashSession.status == "CLOSED", *filters)
        )
    )

    flagged_count = await db.execute(
        select(func.count(CashSession.id)).where(and_(CashSession.flagged is True, *filters))
    )

    envelope = await db.execute(
        select(func.sum(CashSession.envelope_amount.cast(Numeric(12, 2)))).where(
            and_(CashSession.status == "CLOSED", *filters)
        )
    )

    cash_sales_val = cash_sales.scalar() or Decimal("0.00")
    credit_card_val = credit_card.scalar() or Decimal("0.00")
    debit_card_val = debit_card.scalar() or Decimal("0.00")
    bank_transfer_val = bank_transfer.scalar() or Decimal("0.00")
    expenses_val = expenses.scalar() or Decimal("0.00")
    total_ingresos = cash_sales_val + credit_card_val + debit_card_val + bank_transfer_val

    # Calculate payment mix %
    cash_pct = (cash_sales_val / total_ingresos * 100) if total_ingresos > 0 else 0
    card_pct = (
        ((credit_card_val + debit_card_val) / total_ingresos * 100) if total_ingresos > 0 else 0
    )
    bank_pct = (bank_transfer_val / total_ingresos * 100) if total_ingresos > 0 else 0

    return templates.TemplateResponse(
        "partials/stats_row.html",
        {
            "request": request,
            "selected_businesses": selected_businesses,
            "active_sessions": active_sessions.scalar() or 0,
            "cash_sales": cash_sales_val,
            "envelope_total": envelope.scalar() or Decimal("0.00"),
            "credit_card_total": credit_card_val,
            "debit_card_total": debit_card_val,
            "bank_transfer_total": bank_transfer_val,
            "expenses": expenses_val,
            "total_ingresos": total_ingresos,
            "flagged_count": flagged_count.scalar() or 0,
            "cash_pct": cash_pct,
            "card_pct": card_pct,
            "bank_pct": bank_pct,
            "locale": locale,
            "_": _,
        },
    )
