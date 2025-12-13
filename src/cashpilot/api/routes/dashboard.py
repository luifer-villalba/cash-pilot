# File: src/cashpilot/api/routes/dashboard.py
"""Dashboard routes (HTML endpoints)."""

from datetime import date as date_type
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_, case, func, select
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
            "current_user": current_user,
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

    # Build filters (reuse logic from sessions table)
    filters = await _build_session_filters(
        from_date, to_date, cashier_name, business_id, status, current_user
    )

    # Use database aggregations for efficiency
    # Count sessions by status and flagged state
    stmt_counts = select(
        func.count(case((CashSession.status == "OPEN", 1))).label("sessions_open"),
        func.count(case((CashSession.status == "CLOSED", 1))).label("sessions_closed"),
        func.count(case((CashSession.flagged == True, 1))).label("sessions_need_review"),
    ).where(and_(*filters))

    result_counts = await db.execute(stmt_counts)
    counts_row = result_counts.one()
    sessions_open = counts_row.sessions_open
    sessions_closed = counts_row.sessions_closed
    sessions_need_review = counts_row.sessions_need_review

    # Calculate financial aggregations for closed sessions only
    # cash_sales = (final_cash - initial_cash) + envelope_amount
    # Note: Only include sessions where final_cash is not NULL
    stmt_aggs = select(
        func.sum(
            case(
                (
                    and_(CashSession.status == "CLOSED", CashSession.final_cash.isnot(None)),
                    (CashSession.final_cash - CashSession.initial_cash)
                    + CashSession.envelope_amount,
                ),
                else_=0,
            )
        ).label("cash_sales"),
        func.sum(
            case((CashSession.status == "CLOSED", CashSession.credit_card_total), else_=0)
        ).label("credit_card_total"),
        func.sum(
            case((CashSession.status == "CLOSED", CashSession.debit_card_total), else_=0)
        ).label("debit_card_total"),
        func.sum(
            case((CashSession.status == "CLOSED", CashSession.bank_transfer_total), else_=0)
        ).label("bank_transfer_total"),
        func.sum(case((CashSession.status == "CLOSED", CashSession.expenses), else_=0)).label(
            "expenses"
        ),
        func.sum(
            case((CashSession.status == "CLOSED", CashSession.credit_sales_total), else_=0)
        ).label("credit_sales_total"),
        func.sum(
            case(
                (CashSession.status == "CLOSED", CashSession.credit_payments_collected), else_=0
            )
        ).label("credit_payments_collected"),
    ).where(and_(*filters))

    result_aggs = await db.execute(stmt_aggs)
    aggs_row = result_aggs.one()

    # Convert to Decimal, handling None from aggregations
    cash_sales_val = Decimal(str(aggs_row.cash_sales or 0))
    credit_card_val = Decimal(str(aggs_row.credit_card_total or 0))
    debit_card_val = Decimal(str(aggs_row.debit_card_total or 0))
    bank_val = Decimal(str(aggs_row.bank_transfer_total or 0))
    expenses_val = Decimal(str(aggs_row.expenses or 0))
    credit_sales_val = Decimal(str(aggs_row.credit_sales_total or 0))
    credit_payments_val = Decimal(str(aggs_row.credit_payments_collected or 0))

    # Card #1: Cash Sales
    # Already calculated as cash_sales_val

    # Card #2: Bank Transfers
    # Already calculated as bank_val

    # Card #3: Total Expenses
    total_expenses = expenses_val

    # Card #4: Cash Profit = cash_sales + bank - expenses
    cash_profit = cash_sales_val + bank_val - expenses_val

    # Card #5: Total Sales = cash + cards + bank
    total_sales = cash_sales_val + credit_card_val + debit_card_val + bank_val

    # Card #6: Card Payments (for collapsible section)
    card_payments_total = credit_card_val + debit_card_val

    # Card #7: Credit Sales (for collapsible section)
    # Already calculated as credit_sales_val

    # Card #8: Credit Payments (for collapsible section)
    # Already calculated as credit_payments_val

    # Card #9: Payment Mix % (for collapsible section)
    total_income = cash_sales_val + credit_card_val + debit_card_val + bank_val
    cash_pct = (cash_sales_val / total_income * 100) if total_income > 0 else 0
    card_pct = (card_payments_total / total_income * 100) if total_income > 0 else 0
    bank_pct = (bank_val / total_income * 100) if total_income > 0 else 0

    # Card #10: Sessions Status (for collapsible section)
    # Already calculated: sessions_open, sessions_closed, sessions_need_review

    return templates.TemplateResponse(
        "partials/stats_row.html",
        {
            "request": request,
            # Card 1-5 (always visible)
            "cash_sales": cash_sales_val,
            "bank_transfer_total": bank_val,
            "total_expenses": total_expenses,
            "cash_profit": cash_profit,
            "total_sales": total_sales,
            # Card 6-10 (collapsible)
            "card_payments_total": card_payments_total,
            "credit_card_total": credit_card_val,
            "debit_card_total": debit_card_val,
            "credit_sales_total": credit_sales_val,
            "credit_payments_collected": credit_payments_val,
            "cash_pct": cash_pct,
            "card_pct": card_pct,
            "bank_pct": bank_pct,
            "sessions_open": sessions_open,
            "sessions_closed": sessions_closed,
            "sessions_need_review": sessions_need_review,
            "locale": locale,
            "_": _,
        },
    )
