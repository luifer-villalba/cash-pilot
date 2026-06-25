# File: src/cashpilot/api/routes/business_stats.py
"""Business statistics report route."""

import asyncio
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.api.auth import get_current_user
from cashpilot.api.utils import (
    get_assigned_businesses,
    get_locale,
    get_translation_function,
    templates,
)
from cashpilot.core.cache import get_cache, make_cache_key, set_cache
from cashpilot.core.db import get_db
from cashpilot.core.logging import get_logger
from cashpilot.models import CashSession, DailyReconciliation
from cashpilot.models.user import User
from cashpilot.services.insights import generate_alerts, generate_business_stats_summary
from cashpilot.services.report_utils import (
    calculate_comparison_range,
    calculate_date_range,
    calculate_delta,
    format_date_range,
)
from cashpilot.utils.datetime import today_local

logger = get_logger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])

BUSINESS_STATS_CACHE_VERSION = "v1"


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

    # Base filters for daily reconciliation metrics (costs/tickets)
    recon_filters = [
        DailyReconciliation.date >= from_date,
        DailyReconciliation.date <= to_date,
        DailyReconciliation.deleted_at.is_(None),
    ]

    # Query 1: Financial metrics (closed sessions only)
    stmt_financial = (
        select(
            CashSession.business_id,
            # Cash Sales = (final_cash - initial_cash) + envelope + expenses
            # - credit_payments_collected + bank_transfer_total
            # Note: bank_transfer_total IS included in cash_sales
            # (transferencias are part of cash sales, but shown separately for info)
            func.sum(
                case(
                    (
                        CashSession.final_cash.is_not(None),
                        (CashSession.final_cash - CashSession.initial_cash)
                        + func.coalesce(CashSession.envelope_amount, 0)
                        + func.coalesce(CashSession.expenses, 0)
                        - func.coalesce(CashSession.credit_payments_collected, 0)
                        + func.coalesce(CashSession.bank_transfer_total, 0),
                    ),
                    else_=0,
                )
            ).label("cash_sales"),
            # Card Payments Total
            func.sum(func.coalesce(CashSession.card_total, 0)).label("card_payments_total"),
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

    # Query 3: Daily reconciliation metrics (cost + tickets)
    stmt_recon = (
        select(
            DailyReconciliation.business_id,
            func.sum(func.coalesce(DailyReconciliation.daily_cost_total, 0)).label(
                "daily_cost_total"
            ),
            func.sum(func.coalesce(DailyReconciliation.invoice_count, 0)).label("invoice_count"),
        )
        .where(and_(*recon_filters))
        .group_by(DailyReconciliation.business_id)
    )

    # Execute all queries concurrently for better performance
    result_financial, result_counts, result_recon = await asyncio.gather(
        db.execute(stmt_financial),
        db.execute(stmt_counts),
        db.execute(stmt_recon),
    )
    financial_rows = result_financial.all()
    count_rows = result_counts.all()
    recon_rows = result_recon.all()

    # Build count dict by business_id
    counts_by_business = {}
    for row in count_rows:
        business_id = str(row.business_id)
        counts_by_business[business_id] = {
            "sessions_count_open": int(row.sessions_count_open or 0),
            "sessions_count_closed": int(row.sessions_count_closed or 0),
            "sessions_need_review": int(row.sessions_need_review or 0),
        }

    # Build daily reconciliation dict by business_id
    recon_by_business = {}
    for row in recon_rows:
        business_id = str(row.business_id)
        recon_by_business[business_id] = {
            "daily_cost_total": Decimal(row.daily_cost_total or 0),
            "invoice_count": int(row.invoice_count or 0),
        }

    # Build financial metrics dict
    financial_by_business = {}
    for row in financial_rows:
        business_id = str(row.business_id)
        cash_sales = Decimal(row.cash_sales or 0)
        card_payments_total = Decimal(row.card_payments_total or 0)
        credit_sales_total = Decimal(row.credit_sales_total or 0)
        credit_payments_collected = Decimal(row.credit_payments_collected or 0)
        bank_transfer_total = Decimal(row.bank_transfer_total or 0)
        total_expenses = Decimal(row.total_expenses or 0)

        # Total Sales = cash_sales + card_payments_total + credit_sales_total
        # Note: bank_transfer_total is already included in cash_sales, so we don't add it again
        # The bank_transfer_total column is shown separately for informational purposes only
        total_sales = cash_sales + card_payments_total + credit_sales_total

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
            "total_expenses": total_expenses,
            "payment_method_mix": payment_method_mix,
        }

    # Combine financial metrics with session counts
    # Include all businesses that have either financial data, session counts, or recon data
    all_business_ids = (
        set(financial_by_business.keys())
        | set(counts_by_business.keys())
        | set(recon_by_business.keys())
    )

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
        recon = recon_by_business.get(
            business_id,
            {
                "daily_cost_total": Decimal("0"),
                "invoice_count": 0,
            },
        )

        # Merge financial metrics with session counts
        metrics_by_business[business_id] = {
            **financial,
            "sessions_count_open": counts["sessions_count_open"],
            "sessions_count_closed": counts["sessions_count_closed"],
            "sessions_need_review": counts["sessions_need_review"],
            "daily_cost_total": recon["daily_cost_total"],
            "invoice_count": recon["invoice_count"],
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
            "total_expenses": Decimal("0"),
            "daily_cost_total": Decimal("0"),
            "invoice_count": 0,
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


@router.get("/business-stats", response_class=HTMLResponse)
async def business_stats(
    request: Request,
    view: str = Query(
        "this_month",
        pattern="^(today|yesterday|this_week|last_week|this_month|last_month|custom|week|month)$",
    ),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Multi-business statistics dashboard (AC-01, AC-02).

    Admin sees stats for all businesses.
    Cashier sees stats only for assigned businesses.
    """
    locale = get_locale(request)
    _ = get_translation_function(locale)

    # Normalize legacy view names
    if view == "week":
        view = "this_week"
    elif view == "month":
        view = "this_month"

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
    prev_from, prev_to = calculate_comparison_range(view, current_from, current_to)

    # Aggregate metrics for current and previous periods concurrently
    # Cache keyed by date range (not user — RBAC filtering happens after)
    today_date = today_local()

    def _metrics_cache_key(fd: date, td: date) -> str:
        return make_cache_key(
            f"biz_stats_{BUSINESS_STATS_CACHE_VERSION}",
            from_date=str(fd),
            to_date=str(td),
        )

    def _metrics_cache_ttl(fd: date, td: date) -> int:
        # 5 min if the range includes today, 1 hour otherwise (historical = immutable)
        return 300 if td >= today_date else 3600

    async def _get_or_fetch_metrics(fd: date, td: date) -> dict:
        key = _metrics_cache_key(fd, td)
        cached = get_cache(key)
        if cached is not None:
            return cached
        result = await aggregate_business_metrics(db, fd, td)
        set_cache(key, result, ttl_seconds=_metrics_cache_ttl(fd, td))
        return result

    current_metrics, previous_metrics = await asyncio.gather(
        _get_or_fetch_metrics(current_from, current_to),
        _get_or_fetch_metrics(prev_from, prev_to),
    )

    # Filter businesses by user role (AC-01, AC-02)
    businesses = await get_assigned_businesses(current_user, db)

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
        "total_expenses",
        "daily_cost_total",
        "gross_margin",
        "invoice_count",
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
            if key.startswith("sessions_") or key == "invoice_count":
                current[key] = current_raw.get(key, 0)
                previous[key] = previous_raw.get(key, 0)
            else:
                current[key] = current_raw.get(key, Decimal("0"))
                previous[key] = previous_raw.get(key, Decimal("0"))

        # Derived margin metrics
        current["gross_margin"] = current["total_sales"] - current["daily_cost_total"]
        previous["gross_margin"] = previous["total_sales"] - previous["daily_cost_total"]
        current["gross_margin_percent"] = (
            (current["gross_margin"] / current["total_sales"] * 100)
            if current["total_sales"] > 0
            else Decimal("0")
        )
        previous["gross_margin_percent"] = (
            (previous["gross_margin"] / previous["total_sales"] * 100)
            if previous["total_sales"] > 0
            else Decimal("0")
        )

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
            if key.startswith("sessions_") or key == "invoice_count":
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

    # Sort by current total sales for ranking display
    business_stats_list.sort(key=lambda item: item["current"]["total_sales"], reverse=True)

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

    # Calculate gross margin percent for totals
    totals_current["gross_margin_percent"] = (
        (totals_current["gross_margin"] / totals_current["total_sales"] * 100)
        if totals_current["total_sales"] > 0
        else Decimal("0")
    )
    totals_previous["gross_margin_percent"] = (
        (totals_previous["gross_margin"] / totals_previous["total_sales"] * 100)
        if totals_previous["total_sales"] > 0
        else Decimal("0")
    )

    # Calculate totals deltas
    totals_deltas = {}
    for key in metric_keys:
        if key == "payment_method_mix":
            continue
        totals_deltas[key] = calculate_delta(totals_current[key], totals_previous[key])

    current_period_label = format_date_range(current_from, current_to)
    previous_period_label = format_date_range(prev_from, prev_to)

    comparison_label_map = {
        "today": _("Compared to the same weekday last week"),
        "yesterday": _("Compared to the same weekday last week"),
        "this_week": _("Compared to last week (same weekday range)"),
        "last_week": _("Compared to the week prior"),
        "this_month": _("Compared to last month MTD"),
        "last_month": _("Compared to the month prior"),
        "custom": _("Compared to the previous period"),
    }

    comparison_label = comparison_label_map.get(view, _("Compared to the previous period"))

    # --- Insights ---
    totals_growth = totals_deltas.get("total_sales", {}).get("percent")
    top_business_name = business_stats_list[0]["business"].name if business_stats_list else ""
    summary = generate_business_stats_summary(
        total_sales=totals_current["total_sales"],
        previous_sales=totals_previous["total_sales"],
        growth_percent=totals_growth,
        business_count=len(business_stats_list),
        period_label=current_period_label,
        top_business_name=top_business_name,
    )
    alerts = generate_alerts(
        growth_percent=totals_growth,
        period_label=previous_period_label,
    )

    return templates.TemplateResponse(
        request,
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
            "comparison_label": comparison_label,
            "businesses": business_stats_list,
            "totals_current": totals_current,
            "totals_previous": totals_previous,
            "totals_deltas": totals_deltas,
            "locale": locale,
            "_": _,
            "date_error": date_error,
            "summary": summary,
            "alerts": alerts,
        },
    )
