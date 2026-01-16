"""Weekly Revenue Trend Report API.

Cache Versioning Strategy:
--------------------------
The cache key includes a version string (e.g., "weekly_trend_v4") to handle breaking changes
in the report calculation logic. When the logic changes:

1. Increment the version in CACHE_VERSION constant
2. Old cache entries with previous versions will naturally expire based on TTL
3. For immediate cleanup, call clear_old_cache_versions() on application startup

This approach avoids serving stale data after deployments while allowing the in-memory
cache to self-clean over time.
"""

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.api.auth import get_current_user
from cashpilot.core.cache import clear_cache, get_cache, make_cache_key, set_cache
from cashpilot.core.db import get_db
from cashpilot.core.logging import get_logger
from cashpilot.models import CashSession, DailyReconciliation, User
from cashpilot.models.report_schemas import DayOfWeekRevenue, WeeklyRevenueTrend

logger = get_logger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])

# Cache version - increment when calculation logic changes
CACHE_VERSION = "v5"


def clear_old_cache_versions() -> None:
    """Clear cache entries from previous versions.

    This function should be called during application startup to clean up
    any cache entries from previous versions. Since the cache is in-memory,
    this is only necessary after a deployment without restart, but provides
    a clean way to handle version migrations.
    """
    # Clear all weekly_trend entries that don't match current version
    # In a production system with persistent cache (Redis), you would
    # iterate through keys and delete non-matching versions
    for old_version in ["v1", "v2", "v3", "v4"]:  # Add old versions here
        clear_cache(f"weekly_trend_{old_version}")
    logger.info(f"Cleared old cache versions. Current version: {CACHE_VERSION}")


def get_week_dates(year: int, week: int) -> tuple[date, date]:
    """
    Get the start (Monday) and end (Sunday) dates for an ISO week.

    Args:
        year: ISO year
        week: ISO week number (1-53)

    Returns:
        Tuple of (start_date, end_date)
    """
    # ISO week date: Jan 4th is always in week 1
    jan4 = date(year, 1, 4)
    week_start = jan4 - timedelta(days=jan4.weekday()) + timedelta(weeks=week - 1)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def calculate_growth_percent(current: Decimal, previous: Decimal) -> Decimal | None:
    """
    Calculate week-over-week growth percentage.

    Formula: ((current - previous) / previous) * 100

    Args:
        current: Current week revenue (must be a non-negative Decimal)
        previous: Previous week revenue (must be a non-negative Decimal)

    Returns:
        Growth percentage or None if previous is 0

    Raises:
        ValueError: If either current or previous is negative.
    """
    if current < 0 or previous < 0:
        raise ValueError("current and previous revenue must be non-negative")
    if previous == 0:
        return None
    return ((current - previous) / previous * 100).quantize(Decimal("0.1"))


def get_trend_arrow(growth: Decimal | None) -> str:
    """
    Get trend arrow based on growth percentage.

    Args:
        growth: Growth percentage

    Returns:
        Trend arrow: ↑ (positive), ↓ (negative), → (zero or None)
    """
    if growth is None:
        return "→"
    if growth > 0:
        return "↑"
    elif growth < 0:
        return "↓"
    return "→"


@router.get("/weekly-trend/data", response_model=WeeklyRevenueTrend)
async def get_weekly_trend(
    year: int = Query(..., description="ISO year", ge=2020, le=2100),
    week: int = Query(..., description="ISO week number", ge=1, le=53),
    business_id: str = Query(..., description="Business UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WeeklyRevenueTrend:
    """
    Get weekly revenue trend report comparing current week with previous 4 weeks.

    Returns daily revenue for 5 weeks (35 days total) with week-over-week growth calculations.

    Query only CLOSED sessions (status=CLOSED and final_cash IS NOT NULL).

    Caches results for performance.

    Args:
        year: Target ISO year
        week: Target ISO week number (1-53)
        business_id: Target business UUID (required)

    Returns:
        WeeklyRevenueTrend with:
        - current_week: Daily revenue for target week
        - previous_weeks: Daily revenue for previous 4 weeks
        - highest_day: Day with highest revenue
        - lowest_day: Day with lowest revenue
        - current_week_total: Total revenue for target week
        - previous_week_total: Total revenue for previous week
        - week_over_week_growth: Week-over-week growth percentage
        - week_over_week_difference: Absolute difference between current and previous week revenue
    """
    # Validate and parse business_id
    try:
        business_uuid = UUID(business_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid business_id format",
        )

    # Check cache (v4 = changed to week-over-week growth instead of 5-week average)
    cache_key = make_cache_key(
        f"weekly_trend_{CACHE_VERSION}",
        year=str(year),
        week=str(week),
        business_id=str(business_uuid),
    )
    cached_result = get_cache(cache_key)
    if cached_result is not None:
        logger.debug(f"Cache hit for weekly trend {year}-W{week:02d}, business {business_uuid}")
        return cached_result

    # Calculate date ranges for 5 weeks (current week + previous 4 weeks)
    # Use actual dates instead of week numbers for more reliable calculation
    weeks_data = []

    # Get the start date of the target week
    current_week_start, _ = get_week_dates(year, week)

    # Go back 4 weeks from the current week
    for week_offset in range(-4, 1):  # -4, -3, -2, -1, 0 (0 is current week)
        # Calculate the Monday of each week by going back week_offset weeks
        week_start = current_week_start + timedelta(weeks=week_offset)
        week_end = week_start + timedelta(days=6)

        # Get the ISO year and week for this date
        iso_calendar = week_start.isocalendar()
        target_year = iso_calendar[0]
        target_week = iso_calendar[1]

        weeks_data.append(
            {
                "year": target_year,
                "week": target_week,
                "start": week_start,
                "end": week_end,
                "days": [],
            }
        )

    # Query daily revenue for all 5 weeks
    overall_start = weeks_data[0]["start"]
    overall_end = weeks_data[-1]["end"]

    stmt = (
        select(
            CashSession.session_date,
            func.sum(
                # Total Revenue Calculation:
                # 1. Cash Sales = (final_cash - initial_cash) + envelope
                #                 - credit_payments_collected + expenses
                #    - Represents net cash movement during the session
                (CashSession.final_cash - CashSession.initial_cash)
                + func.coalesce(CashSession.envelope_amount, 0)
                + func.coalesce(CashSession.expenses, 0)
                - func.coalesce(CashSession.credit_payments_collected, 0)
                # 2. Card Sales
                + func.coalesce(CashSession.card_total, 0)
                # 3. Bank Transfers
                + func.coalesce(CashSession.bank_transfer_total, 0)
                # 4. Credit Sales (sales on account)
                + func.coalesce(CashSession.credit_sales_total, 0)
            ).label("total_revenue"),
            # Separate payment method calculations
            func.sum(
                (CashSession.final_cash - CashSession.initial_cash)
                + func.coalesce(CashSession.envelope_amount, 0)
                + func.coalesce(CashSession.expenses, 0)
                - func.coalesce(CashSession.credit_payments_collected, 0)
            ).label("cash_revenue"),
            func.sum(func.coalesce(CashSession.card_total, 0)).label("card_revenue"),
            func.sum(func.coalesce(CashSession.bank_transfer_total, 0)).label(
                "bank_transfer_revenue"
            ),
            func.sum(func.coalesce(CashSession.credit_sales_total, 0)).label("credit_revenue"),
        )
        .where(
            and_(
                CashSession.business_id == business_uuid,
                CashSession.session_date >= overall_start,
                CashSession.session_date <= overall_end,
                CashSession.status == "CLOSED",
                CashSession.final_cash.is_not(None),
                ~CashSession.is_deleted,
            )
        )
        .group_by(CashSession.session_date)
    )

    result = await db.execute(stmt)
    rows = result.all()
    daily_revenues = {row[0]: row[1] for row in rows}
    daily_cash = {row[0]: row[2] for row in rows}
    daily_card = {row[0]: row[3] for row in rows}
    daily_bank_transfer = {row[0]: row[4] for row in rows}
    daily_credit = {row[0]: row[5] for row in rows}

    cost_stmt = (
        select(
            DailyReconciliation.date,
            func.max(DailyReconciliation.daily_cost_total).label("daily_cost_total"),
        )
        .where(
            and_(
                DailyReconciliation.business_id == business_uuid,
                DailyReconciliation.date >= overall_start,
                DailyReconciliation.date <= overall_end,
                DailyReconciliation.deleted_at.is_(None),
            )
        )
        .group_by(DailyReconciliation.date)
    )
    cost_result = await db.execute(cost_stmt)
    cost_rows = cost_result.all()
    daily_costs = {
        row[0]: Decimal(str(row[1])) if row[1] is not None else None for row in cost_rows
    }
    ticket_stmt = (
        select(
            DailyReconciliation.date,
            func.sum(DailyReconciliation.invoice_count).label("ticket_count"),
        )
        .where(
            and_(
                DailyReconciliation.business_id == business_uuid,
                DailyReconciliation.date >= overall_start,
                DailyReconciliation.date <= overall_end,
                DailyReconciliation.deleted_at.is_(None),
            )
        )
        .group_by(DailyReconciliation.date)
    )
    ticket_result = await db.execute(ticket_stmt)
    ticket_rows = ticket_result.all()
    daily_tickets = {row[0]: row[1] for row in ticket_rows}

    # Build day-by-day data for each week
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    for week_info in weeks_data:
        week_days = []
        for day_offset in range(7):
            current_date = week_info["start"] + timedelta(days=day_offset)
            # Use None for days with no sessions (instead of 0)
            revenue = daily_revenues.get(current_date, None)
            if revenue is not None:
                revenue = Decimal(str(revenue))
            cost_total = daily_costs.get(current_date)
            ticket_count = daily_tickets.get(current_date)

            day_data = DayOfWeekRevenue(
                day_name=day_names[day_offset],
                day_number=day_offset + 1,
                date=current_date,
                revenue=revenue if revenue is not None else Decimal("0.00"),
                cost_total=cost_total,
                ticket_count=int(ticket_count) if ticket_count is not None else None,
                growth_percent=None,
                trend_arrow="→",
            )
            # Store whether we have data for this day
            day_data.has_data = revenue is not None
            week_days.append(day_data)

        week_info["days"] = week_days

    # Calculate week-over-week growth for current week
    if len(weeks_data) >= 2:
        current_week_days = weeks_data[-1]["days"]
        previous_week_days = weeks_data[-2]["days"]

        for i, day in enumerate(current_week_days):
            previous_day = previous_week_days[i]
            growth = calculate_growth_percent(day.revenue, previous_day.revenue)
            day.growth_percent = growth
            day.trend_arrow = get_trend_arrow(growth)

    # Calculate aggregate stats for CURRENT WEEK ONLY (not all 5 weeks)
    current_week_days_with_data = [day for day in weeks_data[-1]["days"] if day.has_data]

    highest_day = {}
    lowest_day = {}
    if current_week_days_with_data:
        max_day = max(current_week_days_with_data, key=lambda d: d.revenue)
        min_day = min(current_week_days_with_data, key=lambda d: d.revenue)

        highest_day = {
            "day_name": max_day.day_name,
            "revenue": float(max_day.revenue),
            "date": str(max_day.date),
        }
        lowest_day = {
            "day_name": min_day.day_name,
            "revenue": float(min_day.revenue),
            "date": str(min_day.date),
        }

    # Calculate payment method totals for current week
    current_week_cash_total = Decimal("0.00")
    current_week_card_total = Decimal("0.00")
    current_week_bank_transfer_total = Decimal("0.00")
    current_week_credit_total = Decimal("0.00")

    for day in weeks_data[-1]["days"]:
        if day.has_data:
            current_week_cash_total += Decimal(str(daily_cash.get(day.date, 0) or 0))
            current_week_card_total += Decimal(str(daily_card.get(day.date, 0) or 0))
            current_week_bank_transfer_total += Decimal(
                str(daily_bank_transfer.get(day.date, 0) or 0)
            )
            current_week_credit_total += Decimal(str(daily_credit.get(day.date, 0) or 0))

    # Calculate week-over-week comparison
    current_week_total = sum(day.revenue for day in weeks_data[-1]["days"] if day.has_data)
    previous_week_total = Decimal("0.00")

    if len(weeks_data) >= 2:
        previous_week_total = sum(day.revenue for day in weeks_data[-2]["days"] if day.has_data)

    # Calculate growth percentage
    week_over_week_growth = None
    week_over_week_difference = current_week_total - previous_week_total

    if previous_week_total > 0:
        week_over_week_growth = calculate_growth_percent(current_week_total, previous_week_total)

    # Prepare response
    result = WeeklyRevenueTrend(
        business_id=business_uuid,
        year=year,
        week=week,
        current_week=weeks_data[-1]["days"],
        previous_weeks=[week_info["days"] for week_info in weeks_data[:-1]],
        highest_day=highest_day,
        lowest_day=lowest_day,
        current_week_total=current_week_total,
        previous_week_total=previous_week_total,
        week_over_week_growth=week_over_week_growth,
        week_over_week_difference=week_over_week_difference,
        current_week_cash_total=current_week_cash_total,
        current_week_card_total=current_week_card_total,
        current_week_bank_transfer_total=current_week_bank_transfer_total,
        current_week_credit_total=current_week_credit_total,
    )

    # Cache the result
    # - Current week: 5 minutes (data might still be coming in)
    # - Past weeks: 1 hour (data is immutable)
    from cashpilot.utils.datetime import today_local

    current_week_start, _ = get_week_dates(year, week)
    today = today_local()
    is_current_week = current_week_start <= today <= current_week_start + timedelta(days=6)

    cache_ttl = 300 if is_current_week else 3600  # 5 min vs 1 hour
    set_cache(cache_key, result, ttl_seconds=cache_ttl)

    logger.info(
        f"Weekly trend report generated for {year}-W{week:02d}, "
        f"business {business_uuid}, current week total: {current_week_total}, "
        f"growth: {week_over_week_growth}%"
    )

    return result
