"""Daily Revenue Summary Report API."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.api.auth import get_current_user
from cashpilot.core.cache import get_cache, make_cache_key, set_cache
from cashpilot.core.db import get_db
from cashpilot.core.logging import get_logger
from cashpilot.models import CashSession, User
from cashpilot.models.report_schemas import CashierPerformance, DailyRevenueSummary
from cashpilot.utils.datetime import today_local

logger = get_logger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/daily-revenue/data", response_model=DailyRevenueSummary)
async def get_daily_revenue(
    date_param: date = Query(None, alias="date", description="Date in YYYY-MM-DD format"),
    business_id: str = Query(..., description="Business UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DailyRevenueSummary:
    """
    Get daily revenue summary for a specific business and date.

    Returns aggregated sales by payment method, net earnings, and discrepancy counts.

    Query only CLOSED sessions (status=CLOSED and final_cash IS NOT NULL).

    Caches results: Daily data is immutable after close, so caching provides sub-second response.

    Args:
        date: Target date (YYYY-MM-DD format). Defaults to today.
        business_id: Target business UUID (required).

    Returns:
        DailyRevenueSummary with:
        - total_sales, cash_sales, card_sales, bank_sales, credit_sales
        - net_earnings
        - perfect_count, shortage_count, surplus_count (discrepancy status)
    """
    # Validate and parse business_id
    try:
        business_uuid = UUID(business_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid business_id format",
        )

    # Default to today if not provided
    target_date = date_param or today_local()

    # Check cache (use 24-hour TTL for past dates, 1-hour for today)
    cache_key = make_cache_key(
        "daily_revenue", date=str(target_date), business_id=str(business_uuid)
    )
    cached_result = get_cache(cache_key)
    if cached_result is not None:
        return cached_result

    # Determine cache TTL: 24 hours for past dates, 1 hour for today
    is_today = target_date == today_local()
    cache_ttl = 3600 if is_today else 86400

    # Base filter for closed sessions
    base_filters = and_(
        CashSession.business_id == business_uuid,
        CashSession.session_date == target_date,
        CashSession.status == "CLOSED",
        CashSession.final_cash.is_not(None),
        ~CashSession.is_deleted,
    )

    # Query 1: Financial aggregates
    stmt_financial = select(
        # Cash Sales = (final_cash - initial_cash) + envelope + expenses - credit_payments_collected
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
        # Card sales
        func.sum(func.coalesce(CashSession.card_total, 0)).label("card_sales"),
        # Bank transfers
        func.sum(func.coalesce(CashSession.bank_transfer_total, 0)).label("bank_transfer_sales"),
        # Credit sales (on-account)
        func.sum(func.coalesce(CashSession.credit_sales_total, 0)).label("credit_sales"),
        # Total expenses
        func.sum(func.coalesce(CashSession.expenses, 0)).label("total_expenses"),
        # Session count
        func.count(CashSession.id).label("total_sessions"),
    ).where(base_filters)

    result_financial = await db.execute(stmt_financial)
    financial_data = result_financial.one_or_none()

    # Extract financial metrics (handle None values)
    cash_sales = financial_data[0] or Decimal("0.00")
    card_sales = financial_data[1] or Decimal("0.00")
    bank_transfer_sales = financial_data[2] or Decimal("0.00")
    credit_sales = financial_data[3] or Decimal("0.00")
    total_expenses = financial_data[4] or Decimal("0.00")
    total_sessions = financial_data[5] or 0

    # Calculate total sales
    total_sales = cash_sales + card_sales + bank_transfer_sales + credit_sales
    net_earnings = total_sales - total_expenses

    # Query 2: Count discrepancies
    # Load all sessions to calculate shortage/surplus
    stmt_sessions = select(CashSession).where(base_filters)
    result_sessions = await db.execute(stmt_sessions)
    sessions = result_sessions.scalars().all()

    perfect_count = 0
    shortage_count = 0
    surplus_count = 0

    # Dictionary to track cashier performance
    cashier_stats = {}

    for session in sessions:
        # Calculate shortage/surplus
        shortage_surplus = session.final_cash - session.initial_cash - session.cash_sales
        if shortage_surplus == 0:
            perfect_count += 1
        elif shortage_surplus < 0:
            shortage_count += 1
        else:
            surplus_count += 1

        # Track cashier performance
        cashier_id = session.cashier_id
        if cashier_id not in cashier_stats:
            cashier_stats[cashier_id] = {
                "name": session.cashier.display_name,
                "sessions": 0,
                "revenue": Decimal("0.00"),
                "cash_sales": Decimal("0.00"),
                "card_sales": Decimal("0.00"),
                "bank_sales": Decimal("0.00"),
                "total_duration_seconds": 0,
                "total_expenses": Decimal("0.00"),
                "flagged_sessions": 0,
                "earliest_start": None,
                "latest_end": None,
            }

        cashier_stats[cashier_id]["sessions"] += 1
        cashier_stats[cashier_id]["revenue"] += session.total_sales
        cashier_stats[cashier_id]["cash_sales"] += session.cash_sales
        cashier_stats[cashier_id]["card_sales"] += session.card_total or Decimal("0.00")
        cashier_stats[cashier_id]["bank_sales"] += session.bank_transfer_total or Decimal("0.00")
        cashier_stats[cashier_id]["total_expenses"] += session.expenses or Decimal("0.00")

        # Count flagged sessions
        if session.flagged:
            cashier_stats[cashier_id]["flagged_sessions"] += 1

        # Calculate session duration and track shift times
        if session.opened_at and session.closed_at:
            duration = (session.closed_at - session.opened_at).total_seconds()
            cashier_stats[cashier_id]["total_duration_seconds"] += duration

            # Track earliest start and latest end times
            if (
                cashier_stats[cashier_id]["earliest_start"] is None
                or session.opened_at < cashier_stats[cashier_id]["earliest_start"]
            ):
                cashier_stats[cashier_id]["earliest_start"] = session.opened_at
            if (
                cashier_stats[cashier_id]["latest_end"] is None
                or session.closed_at > cashier_stats[cashier_id]["latest_end"]
            ):
                cashier_stats[cashier_id]["latest_end"] = session.closed_at

    # Build cashier performance list
    cashier_performance = []
    for cashier_id, stats in cashier_stats.items():
        avg_revenue = (
            stats["revenue"] / stats["sessions"] if stats["sessions"] > 0 else Decimal("0.00")
        )
        percentage = (stats["revenue"] / total_sales * 100) if total_sales > 0 else Decimal("0.00")

        # Calculate average session duration in hours
        avg_duration_hours = Decimal("0.00")
        if stats["sessions"] > 0 and stats["total_duration_seconds"] > 0:
            avg_duration_hours = Decimal(
                str(stats["total_duration_seconds"] / 3600 / stats["sessions"])
            )
            avg_duration_hours = avg_duration_hours.quantize(Decimal("0.1"))

        # Calculate payment method percentages
        revenue = stats["revenue"]
        cash_pct = (
            (stats["cash_sales"] / revenue * 100).quantize(Decimal("0.1"))
            if revenue > 0
            else Decimal("0.00")
        )
        card_pct = (
            (stats["card_sales"] / revenue * 100).quantize(Decimal("0.1"))
            if revenue > 0
            else Decimal("0.00")
        )
        bank_pct = (
            (stats["bank_sales"] / revenue * 100).quantize(Decimal("0.1"))
            if revenue > 0
            else Decimal("0.00")
        )

        # Determine shift times and label
        shift_start_time = None
        shift_end_time = None
        shift_label = ""

        if stats["earliest_start"] and stats["latest_end"]:
            shift_start_time = stats["earliest_start"].time()
            shift_end_time = stats["latest_end"].time()

            # Classify shift based on start time
            start_hour = stats["earliest_start"].hour
            if 5 <= start_hour < 12:
                shift_label = "Morning"
            elif 12 <= start_hour < 18:
                shift_label = "Afternoon"
            elif 18 <= start_hour < 22:
                shift_label = "Evening"
            else:
                shift_label = "Night"

        cashier_performance.append(
            CashierPerformance(
                cashier_id=cashier_id,
                cashier_name=stats["name"],
                session_count=stats["sessions"],
                total_revenue=stats["revenue"],
                avg_revenue_per_session=avg_revenue,
                percentage_of_total=percentage,
                cash_percentage=cash_pct,
                card_percentage=card_pct,
                bank_percentage=bank_pct,
                avg_session_duration_hours=avg_duration_hours,
                total_expenses=stats["total_expenses"],
                flagged_sessions=stats["flagged_sessions"],
                shift_start=shift_start_time,
                shift_end=shift_end_time,
                shift_label=shift_label,
            )
        )

    # Sort by revenue (highest first)
    cashier_performance.sort(key=lambda x: x.total_revenue, reverse=True)

    result = DailyRevenueSummary(
        date=target_date,
        business_id=business_uuid,
        total_sales=total_sales,
        cash_sales=cash_sales,
        card_sales=card_sales,
        bank_transfer_sales=bank_transfer_sales,
        credit_sales=credit_sales,
        net_earnings=net_earnings,
        total_expenses=total_expenses,
        perfect_count=perfect_count,
        shortage_count=shortage_count,
        surplus_count=surplus_count,
        total_sessions=total_sessions,
        cashier_performance=cashier_performance,
    )

    # Cache the result
    set_cache(cache_key, result, ttl_seconds=cache_ttl)

    return result
