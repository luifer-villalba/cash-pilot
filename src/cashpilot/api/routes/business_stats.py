# File: src/cashpilot/api/routes/business_stats.py
"""Business statistics report route."""

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.api.auth_helpers import require_admin
from cashpilot.api.utils import (
    format_currency_py,
    get_active_businesses,
    get_locale,
    get_translation_function,
)
from cashpilot.core.db import get_db
from cashpilot.models import Business, CashSession
from cashpilot.models.user import User
from cashpilot.utils.datetime import today_local

TEMPLATES_DIR = Path("/app/templates")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

templates.env.filters["format_currency_py"] = format_currency_py

router = APIRouter(prefix="/reports", tags=["reports"])


def calculate_date_range(view: str, from_date: str | None = None, to_date: str | None = None) -> tuple[date, date]:
    """Calculate date range based on view type."""
    today = today_local()
    
    if view == "today":
        return today, today
    elif view == "yesterday":
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    elif view == "week":
        # Last 7 days: today - 6 days to today (7 days total)
        week_start = today - timedelta(days=6)
        return week_start, today
    elif view == "month":
        # Last 30 days: today - 29 days to today (30 days total)
        month_start = today - timedelta(days=29)
        return month_start, today
    elif view == "custom" and from_date and to_date:
        # Custom range
        try:
            from_dt = date.fromisoformat(from_date)
            to_dt = date.fromisoformat(to_date)
            return from_dt, to_dt
        except ValueError:
            # Fallback to today if invalid
            return today, today
    else:
        # Default to today
        return today, today


def calculate_previous_period(from_date: date, to_date: date) -> tuple[date, date]:
    """Calculate previous period of same duration."""
    duration = (to_date - from_date).days
    prev_to = from_date - timedelta(days=1)
    prev_from = prev_to - timedelta(days=duration)
    return prev_from, prev_to


async def aggregate_business_metrics(
    db: AsyncSession,
    from_date: date,
    to_date: date,
) -> dict[str, dict]:
    """Aggregate metrics by business for given date range. Returns dict keyed by business_id."""
    # Base filters: closed sessions only, not deleted
    base_filters = [
        CashSession.status == "CLOSED",
        CashSession.final_cash.is_not(None),
        ~CashSession.is_deleted,
        CashSession.session_date >= from_date,
        CashSession.session_date <= to_date,
    ]

    # Aggregate by business_id
    stmt = select(
        CashSession.business_id,
        # Total Sales
        func.sum(
            case(
                (
                    CashSession.final_cash.is_not(None),
                    (CashSession.final_cash - CashSession.initial_cash)
                    + func.coalesce(CashSession.envelope_amount, 0)
                    + func.coalesce(CashSession.expenses, 0)
                    - func.coalesce(CashSession.credit_payments_collected, 0)
                    + func.coalesce(CashSession.credit_card_total, 0)
                    + func.coalesce(CashSession.debit_card_total, 0)
                    + func.coalesce(CashSession.bank_transfer_total, 0)
                    + func.coalesce(CashSession.credit_sales_total, 0),
                ),
                else_=0,
            )
        ).label("total_sales"),
        # Cash Sales
        func.sum(
            case(
                (
                    CashSession.final_cash.is_not(None),
                    (CashSession.final_cash - CashSession.initial_cash)
                    + func.coalesce(CashSession.envelope_amount, 0)
                    + func.coalesce(CashSession.expenses, 0)
                    - func.coalesce(CashSession.credit_payments_collected, 0),
                ),
                else_=0,
            )
        ).label("cash_sales"),
        # Card Payments (credit + debit combined)
        func.sum(
            func.coalesce(CashSession.credit_card_total, 0) + func.coalesce(CashSession.debit_card_total, 0)
        ).label("card_payments"),
        # Cash Profit (cash sales - expenses)
        func.sum(
            case(
                (
                    CashSession.final_cash.is_not(None),
                    (CashSession.final_cash - CashSession.initial_cash)
                    + func.coalesce(CashSession.envelope_amount, 0)
                    - func.coalesce(CashSession.credit_payments_collected, 0)
                    - func.coalesce(CashSession.expenses, 0),
                ),
                else_=0,
            )
        ).label("cash_profit"),
        # Cash on Hand (final cash)
        func.sum(func.coalesce(CashSession.final_cash, 0)).label("register"),
        # Envelope (cash removed)
        func.sum(func.coalesce(CashSession.envelope_amount, 0)).label("envelope"),
        # Credit Sales (pending payments)
        func.sum(func.coalesce(CashSession.credit_sales_total, 0)).label("credit_sales"),
        # Collections (credit payments collected)
        func.sum(func.coalesce(CashSession.credit_payments_collected, 0)).label("collections"),
        # Bank Transfers
        func.sum(func.coalesce(CashSession.bank_transfer_total, 0)).label("bank_transfers"),
        # Total Expenses
        func.sum(func.coalesce(CashSession.expenses, 0)).label("total_expenses"),
        # Net Profit (total_sales - expenses)
        func.sum(
            case(
                (
                    CashSession.final_cash.is_not(None),
                    (CashSession.final_cash - CashSession.initial_cash)
                    + func.coalesce(CashSession.envelope_amount, 0)
                    + func.coalesce(CashSession.expenses, 0)
                    - func.coalesce(CashSession.credit_payments_collected, 0)
                    + func.coalesce(CashSession.credit_card_total, 0)
                    + func.coalesce(CashSession.debit_card_total, 0)
                    + func.coalesce(CashSession.bank_transfer_total, 0)
                    + func.coalesce(CashSession.credit_sales_total, 0)
                    - func.coalesce(CashSession.expenses, 0),
                ),
                else_=0,
            )
        ).label("net_profit"),
    ).where(and_(*base_filters)).group_by(CashSession.business_id)

    result = await db.execute(stmt)
    rows = result.all()

    metrics_by_business = {}
    for row in rows:
        business_id = str(row.business_id)
        total_sales = Decimal(row.total_sales or 0)
        cash_sales = Decimal(row.cash_sales or 0)
        card_payments = Decimal(row.card_payments or 0)
        cash_profit = Decimal(row.cash_profit or 0)
        register = Decimal(row.register or 0)
        envelope = Decimal(row.envelope or 0)
        credit_sales = Decimal(row.credit_sales or 0)
        collections = Decimal(row.collections or 0)
        bank_transfers = Decimal(row.bank_transfers or 0)
        total_expenses = Decimal(row.total_expenses or 0)
        net_profit = Decimal(row.net_profit or 0)
        
        # Calculate financial ratios
        profit_margin = (net_profit / total_sales * 100) if total_sales > 0 else Decimal("0")
        expense_ratio = (total_expenses / total_sales * 100) if total_sales > 0 else Decimal("0")
        collection_rate = (collections / credit_sales * 100) if credit_sales > 0 else Decimal("0")
        operating_cash_flow = cash_sales + collections - total_expenses
        
        metrics_by_business[business_id] = {
            "total_revenue": total_sales,
            "cash_revenue": cash_sales,
            "card_revenue": card_payments,
            "cash_profit": cash_profit,
            "cash_on_hand": register,
            "cash_withdrawn": envelope,
            "accounts_receivable": credit_sales,
            "collections": collections,
            "bank_deposits": bank_transfers,
            "operating_expenses": total_expenses,
            "net_profit": net_profit,
            "profit_margin": profit_margin,
            "expense_ratio": expense_ratio,
            "collection_rate": collection_rate,
            "operating_cash_flow": operating_cash_flow,
        }

    return metrics_by_business


def calculate_delta(current: Decimal | int, previous: Decimal | int) -> dict:
    """Calculate delta percentage and direction. Returns dict with value, percent, direction, color."""
    # Convert to Decimal for calculations
    current_decimal = Decimal(str(current))
    previous_decimal = Decimal(str(previous))
    
    if previous_decimal == 0:
        if current_decimal == 0:
            return {"value": Decimal("0"), "percent": Decimal("0"), "direction": "neutral", "color": "neutral"}
        else:
            return {"value": current_decimal, "percent": Decimal("100"), "direction": "up", "color": "success"}
    
    delta_value = current_decimal - previous_decimal
    delta_percent = (delta_value / previous_decimal) * 100
    
    # Round to 1 decimal place
    delta_percent = round(float(delta_percent), 1)
    
    # Determine direction and color
    if abs(delta_percent) <= 3:
        direction = "neutral"
        color = "neutral"
    elif delta_percent > 0:
        direction = "up"
        color = "success"
    else:
        direction = "down"
        color = "error"
    
    return {
        "value": delta_value,
        "percent": Decimal(str(delta_percent)),
        "direction": direction,
        "color": color,
    }


@router.get("/business-stats", response_class=HTMLResponse)
async def business_stats(
    request: Request,
    view: str = Query("today", regex="^(today|yesterday|week|month|custom)$"),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Multi-business statistics dashboard. Admin only."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    # Calculate current period date range
    current_from, current_to = calculate_date_range(view, from_date, to_date)
    
    # Calculate previous period for comparison
    prev_from, prev_to = calculate_previous_period(current_from, current_to)

    # Aggregate metrics for current and previous periods
    current_metrics = await aggregate_business_metrics(db, current_from, current_to)
    previous_metrics = await aggregate_business_metrics(db, prev_from, prev_to)

    # Get all businesses
    businesses = await get_active_businesses(db)

    # Build business stats with deltas
    business_stats_list = []
    totals_current = {
        "total_revenue": Decimal("0"),
        "cash_revenue": Decimal("0"),
        "card_revenue": Decimal("0"),
        "cash_profit": Decimal("0"),
        "cash_on_hand": Decimal("0"),
        "cash_withdrawn": Decimal("0"),
        "accounts_receivable": Decimal("0"),
        "collections": Decimal("0"),
        "bank_deposits": Decimal("0"),
        "operating_expenses": Decimal("0"),
        "net_profit": Decimal("0"),
        "profit_margin": Decimal("0"),
        "expense_ratio": Decimal("0"),
        "collection_rate": Decimal("0"),
        "operating_cash_flow": Decimal("0"),
    }
    totals_previous = {
        "total_revenue": Decimal("0"),
        "cash_revenue": Decimal("0"),
        "card_revenue": Decimal("0"),
        "cash_profit": Decimal("0"),
        "cash_on_hand": Decimal("0"),
        "cash_withdrawn": Decimal("0"),
        "accounts_receivable": Decimal("0"),
        "collections": Decimal("0"),
        "bank_deposits": Decimal("0"),
        "operating_expenses": Decimal("0"),
        "net_profit": Decimal("0"),
        "profit_margin": Decimal("0"),
        "expense_ratio": Decimal("0"),
        "collection_rate": Decimal("0"),
        "operating_cash_flow": Decimal("0"),
    }

    for business in businesses:
        business_id = str(business.id)
        current_raw = current_metrics.get(business_id, {})
        previous_raw = previous_metrics.get(business_id, {})

        # Initialize current and previous with all required keys (default to 0)
        current = {}
        previous = {}
        for key in totals_current.keys():
            if key in ["profit_margin", "expense_ratio", "collection_rate"]:
                # These are calculated, not from raw data
                current[key] = Decimal("0")
                previous[key] = Decimal("0")
            else:
                current[key] = current_raw.get(key, Decimal("0"))
                previous[key] = previous_raw.get(key, Decimal("0"))

        # Calculate financial ratios for this business
        if current["total_revenue"] > 0:
            current["profit_margin"] = (current["net_profit"] / current["total_revenue"]) * 100
            current["expense_ratio"] = (current["operating_expenses"] / current["total_revenue"]) * 100
        if current["accounts_receivable"] > 0:
            current["collection_rate"] = (current["collections"] / current["accounts_receivable"]) * 100
        current["operating_cash_flow"] = current["cash_revenue"] + current["collections"] - current["operating_expenses"]

        if previous["total_revenue"] > 0:
            previous["profit_margin"] = (previous["net_profit"] / previous["total_revenue"]) * 100
            previous["expense_ratio"] = (previous["operating_expenses"] / previous["total_revenue"]) * 100
        if previous["accounts_receivable"] > 0:
            previous["collection_rate"] = (previous["collections"] / previous["accounts_receivable"]) * 100
        previous["operating_cash_flow"] = previous["cash_revenue"] + previous["collections"] - previous["operating_expenses"]

        # Calculate deltas for all metrics
        deltas = {}
        for key in totals_current.keys():
            current_val = current[key]
            previous_val = previous[key]
            deltas[key] = calculate_delta(current_val, previous_val)
            # Add to totals (except ratios which are calculated separately)
            if key not in ["profit_margin", "expense_ratio", "collection_rate", "operating_cash_flow"]:
                totals_current[key] += current_val
                totals_previous[key] += previous_val

        business_stats_list.append({
            "business": business,
            "current": current,
            "previous": previous,
            "deltas": deltas,
        })

    # Recalculate ratios for totals (they can't be summed, must be calculated from totals)
    if totals_current["total_revenue"] > 0:
        totals_current["profit_margin"] = (totals_current["net_profit"] / totals_current["total_revenue"]) * 100
        totals_current["expense_ratio"] = (totals_current["operating_expenses"] / totals_current["total_revenue"]) * 100
    if totals_current["accounts_receivable"] > 0:
        totals_current["collection_rate"] = (totals_current["collections"] / totals_current["accounts_receivable"]) * 100
    totals_current["operating_cash_flow"] = totals_current["cash_revenue"] + totals_current["collections"] - totals_current["operating_expenses"]
    
    if totals_previous["total_revenue"] > 0:
        totals_previous["profit_margin"] = (totals_previous["net_profit"] / totals_previous["total_revenue"]) * 100
        totals_previous["expense_ratio"] = (totals_previous["operating_expenses"] / totals_previous["total_revenue"]) * 100
    if totals_previous["accounts_receivable"] > 0:
        totals_previous["collection_rate"] = (totals_previous["collections"] / totals_previous["accounts_receivable"]) * 100
    totals_previous["operating_cash_flow"] = totals_previous["cash_revenue"] + totals_previous["collections"] - totals_previous["operating_expenses"]
    
    # Calculate totals deltas
    totals_deltas = {}
    for key in totals_current.keys():
        totals_deltas[key] = calculate_delta(totals_current[key], totals_previous[key])

    # Format dates for display - more readable format
    def format_date_short(d: date) -> str:
        """Format date as 'Mon Dec 31' for single days, or 'Dec 25 - Dec 31' for ranges."""
        return d.strftime("%b %d")
    
    def format_date_range(from_d: date, to_d: date) -> str:
        """Format date range concisely."""
        if from_d == to_d:
            # Single day: "Dec 31, 2025"
            return from_d.strftime("%b %d, %Y")
        else:
            # Range: "Dec 25 - Dec 31, 2025" (only show year once)
            if from_d.year == to_d.year:
                return f"{from_d.strftime('%b %d')} - {to_d.strftime('%b %d, %Y')}"
            else:
                return f"{from_d.strftime('%b %d, %Y')} - {to_d.strftime('%b %d, %Y')}"
    
    current_period_label = format_date_range(current_from, current_to)
    previous_period_label = format_date_range(prev_from, prev_to)

    return templates.TemplateResponse(
        "reports/business-stats.html",
        {
            "request": request,
            "current_user": current_user,
            "view": view,
            "from_date": from_date,
            "to_date": to_date,
            "current_from": current_from,
            "current_to": current_to,
            "prev_from": prev_from,
            "prev_to": prev_to,
            "current_period_label": current_period_label,
            "previous_period_label": previous_period_label,
            "businesses": business_stats_list,
            "totals_current": totals_current,
            "totals_previous": totals_previous,
            "totals_deltas": totals_deltas,
            "locale": locale,
            "_": _,
        },
    )

