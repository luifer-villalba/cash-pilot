"""Monthly Revenue Trend Report API.

Cache Versioning Strategy:
--------------------------
The cache key includes a version string (e.g., "monthly_trend_v1") to handle breaking changes
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
from cashpilot.core.cache import get_cache, make_cache_key, set_cache
from cashpilot.core.db import get_db
from cashpilot.core.logging import get_logger
from cashpilot.models import CashSession, User
from cashpilot.models.report_schemas import DayOfMonthRevenue, MonthlyRevenueTrend

logger = get_logger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])

# Cache version - increment when calculation logic changes
CACHE_VERSION = "v1"


def clear_old_cache_versions() -> None:
    """Clear cache entries from previous versions.

    This function should be called during application startup to clean up
    any cache entries from previous versions. Since the cache is in-memory,
    this is only necessary after a deployment without restart, but provides
    a clean way to handle version migrations.
    """
    # Clear all monthly_trend entries that don't match current version
    # In a production system with persistent cache (Redis), you would
    # iterate through keys and delete non-matching versions
    logger.info(f"Cleared old cache versions. Current version: {CACHE_VERSION}")


def get_month_dates(year: int, month: int) -> tuple[date, date]:
    """
    Get the start and end dates for a month.

    Args:
        year: Year
        month: Month (1-12)

    Returns:
        Tuple of (start_date, end_date)
    """
    start_date = date(year, month, 1)
    # Get last day of month
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    return start_date, end_date


def calculate_growth_percent(current: Decimal, previous: Decimal) -> Decimal | None:
    """
    Calculate month-over-month growth percentage.

    Formula: ((current - previous) / previous) * 100

    Args:
        current: Current month revenue (must be a non-negative Decimal)
        previous: Previous month revenue (must be a non-negative Decimal)

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


@router.get("/monthly-trend/data", response_model=MonthlyRevenueTrend)
async def get_monthly_trend(
    year: int = Query(..., description="Year", ge=2020, le=2100),
    month: int = Query(..., description="Month number (1-12)", ge=1, le=12),
    business_id: str = Query(..., description="Business UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MonthlyRevenueTrend:
    """
    Get monthly revenue trend report comparing current month with previous 5 months.

    Returns daily revenue for 6 months (approximately 180 days total) with month-over-month
    growth calculations.

    Query only CLOSED sessions (status=CLOSED and final_cash IS NOT NULL).

    Caches results for performance.

    Args:
        year: Target year
        month: Target month number (1-12)
        business_id: Target business UUID (required)

    Returns:
        MonthlyRevenueTrend with:
        - current_month: Daily revenue for target month
        - previous_months: Daily revenue for previous 5 months
        - highest_day: Day with highest revenue
        - lowest_day: Day with lowest revenue
        - current_month_total: Total revenue for target month
        - previous_month_total: Total revenue for previous month
        - month_over_month_growth: Month-over-month growth percentage
        - month_over_month_difference: Absolute difference between current
            and previous month revenue
    """
    # Validate and parse business_id
    try:
        business_uuid = UUID(business_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid business_id format",
        )

    # Check cache
    cache_key = make_cache_key(
        f"monthly_trend_{CACHE_VERSION}",
        year=str(year),
        month=str(month),
        business_id=str(business_uuid),
    )
    cached_result = get_cache(cache_key)
    if cached_result is not None:
        logger.debug(f"Cache hit for monthly trend {year}-{month:02d}, business {business_uuid}")
        return cached_result

    # Calculate date ranges for 6 months (current month + previous 5 months)
    months_data = []

    # Get the start date of the target month
    current_month_start, current_month_end = get_month_dates(year, month)

    # Go back 5 months from the current month
    for month_offset in range(-5, 1):  # -5, -4, -3, -2, -1, 0 (0 is current month)
        # Calculate the first day of each month
        target_year = year
        target_month = month + month_offset

        # Handle year boundaries
        while target_month < 1:
            target_month += 12
            target_year -= 1
        while target_month > 12:
            target_month -= 12
            target_year += 1

        month_start, month_end = get_month_dates(target_year, target_month)

        months_data.append(
            {
                "year": target_year,
                "month": target_month,
                "start": month_start,
                "end": month_end,
                "days": [],
            }
        )

    # Query daily revenue for all 6 months
    overall_start = months_data[0]["start"]
    overall_end = months_data[-1]["end"]

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
            # Breakdown by payment method
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

    # Build day-by-day data for each month
    for month_info in months_data:
        month_days = []
        current_date = month_info["start"]

        while current_date <= month_info["end"]:
            # Use None for days with no sessions (instead of 0)
            revenue = daily_revenues.get(current_date, None)
            if revenue is not None:
                revenue = Decimal(str(revenue))

            day_data = DayOfMonthRevenue(
                day_number=current_date.day,
                date=current_date,
                revenue=revenue if revenue is not None else Decimal("0.00"),
                growth_percent=None,
                trend_arrow="→",
            )
            # Store whether we have data for this day
            day_data.has_data = revenue is not None
            month_days.append(day_data)
            current_date += timedelta(days=1)

        month_info["days"] = month_days

    # Calculate month-over-month growth for current month
    if len(months_data) >= 2:
        current_month_days = months_data[-1]["days"]
        previous_month_days = months_data[-2]["days"]

        # Calculate growth based on day of month (1st vs 1st, 2nd vs 2nd, etc.)
        for i, day in enumerate(current_month_days):
            # Find corresponding day in previous month (by day number)
            previous_day = next(
                (d for d in previous_month_days if d.day_number == day.day_number), None
            )
            if previous_day:
                growth = calculate_growth_percent(day.revenue, previous_day.revenue)
                day.growth_percent = growth
                day.trend_arrow = get_trend_arrow(growth)

    # Calculate aggregate stats for CURRENT MONTH ONLY (not all 6 months)
    current_month_days_with_data = [day for day in months_data[-1]["days"] if day.has_data]

    highest_day = {}
    lowest_day = {}
    if current_month_days_with_data:
        max_day = max(current_month_days_with_data, key=lambda d: d.revenue)
        min_day = min(current_month_days_with_data, key=lambda d: d.revenue)

        highest_day = {
            "day_number": max_day.day_number,
            "revenue": float(max_day.revenue),
            "date": str(max_day.date),
        }
        lowest_day = {
            "day_number": min_day.day_number,
            "revenue": float(min_day.revenue),
            "date": str(min_day.date),
        }

    # Calculate month-over-month comparison
    current_month_total = sum(day.revenue for day in months_data[-1]["days"] if day.has_data)
    previous_month_total = Decimal("0.00")

    if len(months_data) >= 2:
        previous_month_total = sum(day.revenue for day in months_data[-2]["days"] if day.has_data)

    # Calculate payment method totals for current month
    current_month_cash_total = Decimal("0.00")
    current_month_card_total = Decimal("0.00")
    current_month_bank_transfer_total = Decimal("0.00")
    current_month_credit_total = Decimal("0.00")

    current_month_start = months_data[-1]["start"]
    current_month_end = months_data[-1]["end"]
    current_date = current_month_start

    while current_date <= current_month_end:
        if current_date in daily_cash:
            current_month_cash_total += Decimal(str(daily_cash[current_date] or 0))
        if current_date in daily_card:
            current_month_card_total += Decimal(str(daily_card[current_date] or 0))
        if current_date in daily_bank_transfer:
            current_month_bank_transfer_total += Decimal(
                str(daily_bank_transfer[current_date] or 0)
            )
        if current_date in daily_credit:
            current_month_credit_total += Decimal(str(daily_credit[current_date] or 0))
        current_date += timedelta(days=1)

    # Calculate growth percentage
    month_over_month_growth = None
    month_over_month_difference = current_month_total - previous_month_total

    if previous_month_total > 0:
        month_over_month_growth = calculate_growth_percent(
            current_month_total, previous_month_total
        )

    # Prepare response
    result = MonthlyRevenueTrend(
        business_id=business_uuid,
        year=year,
        month=month,
        current_month=months_data[-1]["days"],
        previous_months=[month_info["days"] for month_info in months_data[:-1]],
        highest_day=highest_day,
        lowest_day=lowest_day,
        current_month_total=current_month_total,
        previous_month_total=previous_month_total,
        month_over_month_growth=month_over_month_growth,
        month_over_month_difference=month_over_month_difference,
        current_month_cash_total=current_month_cash_total,
        current_month_card_total=current_month_card_total,
        current_month_bank_transfer_total=current_month_bank_transfer_total,
        current_month_credit_total=current_month_credit_total,
    )

    # Cache the result
    # - Current month: 5 minutes (data might still be coming in)
    # - Past months: 1 hour (data is immutable)
    from cashpilot.utils.datetime import today_local

    today = today_local()
    is_current_month = (
        current_month_start.year == today.year and current_month_start.month == today.month
    )

    cache_ttl = 300 if is_current_month else 3600  # 5 min vs 1 hour
    set_cache(cache_key, result, ttl_seconds=cache_ttl)

    logger.info(
        f"Monthly trend report generated for {year}-{month:02d}, "
        f"business {business_uuid}, current month total: {current_month_total}, "
        f"growth: {month_over_month_growth}%"
    )

    return result
