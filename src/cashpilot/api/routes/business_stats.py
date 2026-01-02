# File: src/cashpilot/api/routes/business_stats.py
"""Business statistics report route."""

import asyncio
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
from cashpilot.core.logging import get_logger
from cashpilot.models import CashSession
from cashpilot.models.user import User
from cashpilot.utils.datetime import today_local

logger = get_logger(__name__)

# Threshold for determining neutral delta direction (percentage)
NEUTRAL_DELTA_THRESHOLD_PERCENT = 3

TEMPLATES_DIR = Path("/app/templates")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

templates.env.filters["format_currency_py"] = format_currency_py

router = APIRouter(prefix="/reports", tags=["reports"])


def calculate_date_range(
    view: str, from_date: str | None = None, to_date: str | None = None
) -> tuple[date, date]:
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
        except ValueError as e:
            # Invalid date format
            raise ValueError("Invalid date format. Please use YYYY-MM-DD format.") from e

        # Validate date range
        if to_dt > today:
            raise ValueError("End date cannot be in the future.")

        if from_dt > to_dt:
            # Invalid range: from_date after to_date
            raise ValueError("Start date must be before or equal to end date.")

        # Limit date range to prevent performance issues
        range_days = (to_dt - from_dt).days
        if range_days > 365:
            raise ValueError("Date range cannot exceed 365 days. Please select a smaller range.")

        return from_dt, to_dt
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
    # Base filters for financial metrics: closed sessions only, not deleted
    financial_filters = [
        CashSession.status == "CLOSED",
        CashSession.final_cash.is_not(None),
        ~CashSession.is_deleted,
        CashSession.session_date >= from_date,
        CashSession.session_date <= to_date,
    ]

    # Base filters for session counts: all sessions (open + closed), not deleted
    count_filters = [
        ~CashSession.is_deleted,
        CashSession.session_date >= from_date,
        CashSession.session_date <= to_date,
    ]

    # Query 1: Financial metrics (closed sessions only)
    stmt_financial = (
        select(
            CashSession.business_id,
            # Cash Sales = (final_cash - initial_cash) + envelope + expenses
            # - credit_payments_collected
            # Note: bank_transfer_total is NOT included in cash_sales
            # (it's a separate payment method)
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
            # Card Payments Total = credit_card + debit_card
            func.sum(
                func.coalesce(CashSession.credit_card_total, 0)
                + func.coalesce(CashSession.debit_card_total, 0)
            ).label("card_payments_total"),
            # Credit Card Total (breakdown)
            func.sum(func.coalesce(CashSession.credit_card_total, 0)).label("credit_card_total"),
            # Debit Card Total (breakdown)
            func.sum(func.coalesce(CashSession.debit_card_total, 0)).label("debit_card_total"),
            # Credit Sales Total (pending credit sales)
            func.sum(func.coalesce(CashSession.credit_sales_total, 0)).label("credit_sales_total"),
            # Credit Payments Collected
            func.sum(func.coalesce(CashSession.credit_payments_collected, 0)).label(
                "credit_payments_collected"
            ),
            # Bank Transfer Total
            func.sum(func.coalesce(CashSession.bank_transfer_total, 0)).label(
                "bank_transfer_total"
            ),
            # Total Expenses
            func.sum(func.coalesce(CashSession.expenses, 0)).label("total_expenses"),
        )
        .where(and_(*financial_filters))
        .group_by(CashSession.business_id)
    )

    # Query 2: Session counts (all sessions)
    stmt_counts = (
        select(
            CashSession.business_id,
            func.sum(case((CashSession.status == "OPEN", 1), else_=0)).label("sessions_count_open"),
            func.sum(case((CashSession.status == "CLOSED", 1), else_=0)).label(
                "sessions_count_closed"
            ),
            func.sum(case((CashSession.flagged, 1), else_=0)).label("sessions_need_review"),
        )
        .where(and_(*count_filters))
        .group_by(CashSession.business_id)
    )

    # Execute both queries concurrently for better performance
    result_financial, result_counts = await asyncio.gather(
        db.execute(stmt_financial),
        db.execute(stmt_counts),
    )
    financial_rows = result_financial.all()
    count_rows = result_counts.all()

    # Build count dict by business_id
    counts_by_business = {}
    for row in count_rows:
        business_id = str(row.business_id)
        counts_by_business[business_id] = {
            "sessions_count_open": int(row.sessions_count_open or 0),
            "sessions_count_closed": int(row.sessions_count_closed or 0),
            "sessions_need_review": int(row.sessions_need_review or 0),
        }

    # Build financial metrics dict
    financial_by_business = {}
    for row in financial_rows:
        business_id = str(row.business_id)
        cash_sales = Decimal(row.cash_sales or 0)
        card_payments_total = Decimal(row.card_payments_total or 0)
        credit_card_total = Decimal(row.credit_card_total or 0)
        debit_card_total = Decimal(row.debit_card_total or 0)
        credit_sales_total = Decimal(row.credit_sales_total or 0)
        credit_payments_collected = Decimal(row.credit_payments_collected or 0)
        bank_transfer_total = Decimal(row.bank_transfer_total or 0)
        total_expenses = Decimal(row.total_expenses or 0)

        # Total Sales = cash_sales + card_payments_total + bank_transfer_total
        total_sales = cash_sales + card_payments_total + bank_transfer_total

        # Cash Profit = cash_sales - expenses
        cash_profit = cash_sales - total_expenses

        # Calculate payment method % mix
        payment_method_mix = {}
        if total_sales > 0:
            payment_method_mix["cash_percent"] = cash_sales / total_sales * 100
            payment_method_mix["card_percent"] = card_payments_total / total_sales * 100
            payment_method_mix["bank_percent"] = bank_transfer_total / total_sales * 100
        else:
            payment_method_mix["cash_percent"] = Decimal("0")
            payment_method_mix["card_percent"] = Decimal("0")
            payment_method_mix["bank_percent"] = Decimal("0")

        financial_by_business[business_id] = {
            # Core 6 metrics
            "total_sales": total_sales,
            "cash_sales": cash_sales,
            "card_payments_total": card_payments_total,
            "credit_sales_total": credit_sales_total,
            "credit_payments_collected": credit_payments_collected,
            "bank_transfer_total": bank_transfer_total,
            # Secondary metrics
            "cash_profit": cash_profit,
            "credit_card_total": credit_card_total,
            "debit_card_total": debit_card_total,
            "total_expenses": total_expenses,
            "payment_method_mix": payment_method_mix,
        }

    # Combine financial metrics with session counts
    # Include all businesses that have either financial data or session counts
    all_business_ids = set(financial_by_business.keys()) | set(counts_by_business.keys())

    metrics_by_business = {}
    for business_id in all_business_ids:
        financial = financial_by_business.get(business_id, {})
        counts = counts_by_business.get(
            business_id,
            {
                "sessions_count_open": 0,
                "sessions_count_closed": 0,
                "sessions_need_review": 0,
            },
        )

        # Merge financial metrics with session counts
        metrics_by_business[business_id] = {
            **financial,
            "sessions_count_open": counts["sessions_count_open"],
            "sessions_count_closed": counts["sessions_count_closed"],
            "sessions_need_review": counts["sessions_need_review"],
        }

        # Ensure all required keys exist with defaults
        defaults = {
            "total_sales": Decimal("0"),
            "cash_sales": Decimal("0"),
            "card_payments_total": Decimal("0"),
            "credit_sales_total": Decimal("0"),
            "credit_payments_collected": Decimal("0"),
            "bank_transfer_total": Decimal("0"),
            "cash_profit": Decimal("0"),
            "credit_card_total": Decimal("0"),
            "debit_card_total": Decimal("0"),
            "total_expenses": Decimal("0"),
            "payment_method_mix": {
                "cash_percent": Decimal("0"),
                "card_percent": Decimal("0"),
                "bank_percent": Decimal("0"),
            },
        }

        for key, default_value in defaults.items():
            if key not in metrics_by_business[business_id]:
                metrics_by_business[business_id][key] = default_value

    return metrics_by_business


def calculate_delta(current: Decimal | int, previous: Decimal | int) -> dict:
    """Calculate delta percentage and direction.

    Returns dict with value, percent, direction, color.
    """
    # Convert to Decimal for calculations
    current_decimal = Decimal(str(current))
    previous_decimal = Decimal(str(previous))

    if previous_decimal == 0:
        if current_decimal == 0:
            return {
                "value": Decimal("0"),
                "percent": Decimal("0"),
                "direction": "neutral",
                "color": "neutral",
            }
        else:
            return {
                "value": current_decimal,
                "percent": Decimal("100"),
                "direction": "up",
                "color": "success",
            }

    delta_value = current_decimal - previous_decimal
    delta_percent = (delta_value / previous_decimal) * 100

    # Round to 1 decimal place using Decimal to avoid float precision issues
    delta_percent = delta_percent.quantize(Decimal("0.1"))

    # Determine direction and color
    if abs(delta_percent) <= NEUTRAL_DELTA_THRESHOLD_PERCENT:
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
    view: str = Query("today", pattern="^(today|yesterday|week|month|custom)$"),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Multi-business statistics dashboard. Admin only."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    # Calculate current period date range
    date_error = None
    try:
        current_from, current_to = calculate_date_range(view, from_date, to_date)
    except ValueError as e:
        # Log the original exception for debugging
        logger.warning(
            "Invalid date range in business stats",
            extra={
                "view": view,
                "from_date": from_date,
                "to_date": to_date,
                "error": str(e),
            },
        )
        # Invalid date range - show specific error message and fallback to today
        error_msg = str(e)
        if error_msg:
            date_error = _(error_msg)
        else:
            date_error = _("Invalid date range. Please check your dates and try again.")
        today = today_local()
        current_from, current_to = today, today

    # Calculate previous period for comparison
    prev_from, prev_to = calculate_previous_period(current_from, current_to)

    # Aggregate metrics for current and previous periods concurrently
    current_metrics, previous_metrics = await asyncio.gather(
        aggregate_business_metrics(db, current_from, current_to),
        aggregate_business_metrics(db, prev_from, prev_to),
    )

    # Get all businesses
    businesses = await get_active_businesses(db)

    # Build business stats with deltas
    business_stats_list = []

    # Initialize totals with all metrics
    metric_keys = [
        "total_sales",
        "cash_sales",
        "card_payments_total",
        "credit_sales_total",
        "credit_payments_collected",
        "bank_transfer_total",
        "cash_profit",
        "credit_card_total",
        "debit_card_total",
        "total_expenses",
        "sessions_count_open",
        "sessions_count_closed",
        "sessions_need_review",
    ]

    totals_current = {key: Decimal("0") for key in metric_keys}
    totals_previous = {key: Decimal("0") for key in metric_keys}

    # Payment method mix for totals (calculated separately)
    totals_current["payment_method_mix"] = {
        "cash_percent": Decimal("0"),
        "card_percent": Decimal("0"),
        "bank_percent": Decimal("0"),
    }
    totals_previous["payment_method_mix"] = {
        "cash_percent": Decimal("0"),
        "card_percent": Decimal("0"),
        "bank_percent": Decimal("0"),
    }

    for business in businesses:
        business_id = str(business.id)
        current_raw = current_metrics.get(business_id, {})
        previous_raw = previous_metrics.get(business_id, {})

        # Initialize current and previous with all required keys (default to 0)
        current = {}
        previous = {}
        for key in metric_keys:
            if key.startswith("sessions_"):
                current[key] = current_raw.get(key, 0)
                previous[key] = previous_raw.get(key, 0)
            else:
                current[key] = current_raw.get(key, Decimal("0"))
                previous[key] = previous_raw.get(key, Decimal("0"))

        # Ensure payment_method_mix is always present
        current["payment_method_mix"] = current_raw.get(
            "payment_method_mix",
            {
                "cash_percent": Decimal("0"),
                "card_percent": Decimal("0"),
                "bank_percent": Decimal("0"),
            },
        )
        previous["payment_method_mix"] = previous_raw.get(
            "payment_method_mix",
            {
                "cash_percent": Decimal("0"),
                "card_percent": Decimal("0"),
                "bank_percent": Decimal("0"),
            },
        )

        # Calculate deltas for all metrics
        deltas = {}
        for key in metric_keys:
            if key == "payment_method_mix":
                # Skip payment method mix for deltas (it's a percentage breakdown)
                continue
            current_val = current[key]
            previous_val = previous[key]
            deltas[key] = calculate_delta(current_val, previous_val)
            # Add to totals (convert integers to Decimal for consistency)
            if key.startswith("sessions_"):
                totals_current[key] = Decimal(str(int(totals_current[key]) + int(current_val)))
                totals_previous[key] = Decimal(str(int(totals_previous[key]) + int(previous_val)))
            else:
                totals_current[key] += current_val
                totals_previous[key] += previous_val

        business_stats_list.append(
            {
                "business": business,
                "current": current,
                "previous": previous,
                "deltas": deltas,
            }
        )

    # Calculate payment method mix for totals
    if totals_current["total_sales"] > 0:
        totals_current["payment_method_mix"]["cash_percent"] = (
            totals_current["cash_sales"] / totals_current["total_sales"] * 100
        )
        totals_current["payment_method_mix"]["card_percent"] = (
            totals_current["card_payments_total"] / totals_current["total_sales"] * 100
        )
        totals_current["payment_method_mix"]["bank_percent"] = (
            totals_current["bank_transfer_total"] / totals_current["total_sales"] * 100
        )

    if totals_previous["total_sales"] > 0:
        totals_previous["payment_method_mix"]["cash_percent"] = (
            totals_previous["cash_sales"] / totals_previous["total_sales"] * 100
        )
        totals_previous["payment_method_mix"]["card_percent"] = (
            totals_previous["card_payments_total"] / totals_previous["total_sales"] * 100
        )
        totals_previous["payment_method_mix"]["bank_percent"] = (
            totals_previous["bank_transfer_total"] / totals_previous["total_sales"] * 100
        )

    # Calculate totals deltas
    totals_deltas = {}
    for key in metric_keys:
        if key == "payment_method_mix":
            continue
        totals_deltas[key] = calculate_delta(totals_current[key], totals_previous[key])

    # Format dates for display - more readable format
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
            "date_error": date_error,
        },
    )
