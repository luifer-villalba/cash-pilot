"""Shared utilities for all report endpoints.

Centralizes:
- SQLAlchemy expressions for cash sales / total revenue
- Growth percentage and trend arrow calculations
- Date range resolution and comparison period logic
- Period delta calculation
"""

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import case, func

from cashpilot.models.cash_session import CashSession
from cashpilot.utils.datetime import today_local

# ---------------------------------------------------------------------------
# SQL expressions
# ---------------------------------------------------------------------------

NEUTRAL_DELTA_THRESHOLD_PERCENT = 3


def cash_sales_expr():
    """SQLAlchemy column expression for cash sales.

    Formula: (final_cash - initial_cash) + envelope + expenses - credit_payments_collected
    Wrapped in a CASE to guard against NULL final_cash (open sessions).
    """
    return case(
        (
            CashSession.final_cash.is_not(None),
            (CashSession.final_cash - CashSession.initial_cash)
            + func.coalesce(CashSession.envelope_amount, 0)
            + func.coalesce(CashSession.expenses, 0)
            - func.coalesce(CashSession.credit_payments_collected, 0),
        ),
        else_=0,
    )


def total_revenue_expr():
    """SQLAlchemy column expression for total revenue across all payment methods.

    Includes cash + card + bank_transfer + credit_sales.
    """
    return (
        (CashSession.final_cash - CashSession.initial_cash)
        + func.coalesce(CashSession.envelope_amount, 0)
        + func.coalesce(CashSession.expenses, 0)
        - func.coalesce(CashSession.credit_payments_collected, 0)
        + func.coalesce(CashSession.card_total, 0)
        + func.coalesce(CashSession.bank_transfer_total, 0)
        + func.coalesce(CashSession.credit_sales_total, 0)
    )


def cash_component_expr():
    """SQLAlchemy expression for the cash-only component of revenue."""
    return (
        (CashSession.final_cash - CashSession.initial_cash)
        + func.coalesce(CashSession.envelope_amount, 0)
        + func.coalesce(CashSession.expenses, 0)
        - func.coalesce(CashSession.credit_payments_collected, 0)
    )


# ---------------------------------------------------------------------------
# Growth / trend helpers
# ---------------------------------------------------------------------------


def calculate_growth_percent(current: Decimal, previous: Decimal) -> Decimal | None:
    """Calculate period-over-period growth percentage.

    Returns None when previous is 0 (avoids division by zero).
    Raises ValueError for negative inputs.
    """
    if current < 0 or previous < 0:
        raise ValueError("current and previous revenue must be non-negative")
    if previous == 0:
        return None
    return ((current - previous) / previous * 100).quantize(Decimal("0.1"))


def get_trend_arrow(growth: Decimal | None) -> str:
    """Return a Unicode trend arrow for a growth percentage."""
    if growth is None:
        return "→"
    if growth > 0:
        return "↑"
    if growth < 0:
        return "↓"
    return "→"


def calculate_delta(current: Decimal | int, previous: Decimal | int) -> dict:
    """Calculate delta between two period values.

    Returns dict with: value, percent, direction (up/down/neutral), color (success/error/neutral).
    Uses a ±3% neutral band to avoid noise on near-flat periods.
    """
    current_d = Decimal(str(current))
    previous_d = Decimal(str(previous))

    if previous_d == 0:
        if current_d == 0:
            return {
                "value": Decimal("0"),
                "percent": Decimal("0"),
                "direction": "neutral",
                "color": "neutral",
            }
        return {
            "value": current_d,
            "percent": Decimal("100"),
            "direction": "up",
            "color": "success",
        }

    delta_value = current_d - previous_d
    delta_percent = (delta_value / previous_d * 100).quantize(Decimal("0.1"))

    if abs(delta_percent) <= NEUTRAL_DELTA_THRESHOLD_PERCENT:
        direction, color = "neutral", "neutral"
    elif delta_percent > 0:
        direction, color = "up", "success"
    else:
        direction, color = "down", "error"

    return {"value": delta_value, "percent": delta_percent, "direction": direction, "color": color}


# ---------------------------------------------------------------------------
# Date range helpers
# ---------------------------------------------------------------------------


def start_of_week(day: date, week_start: int = 0) -> date:
    """Return the Monday (or custom week_start) of the week containing *day*."""
    return day - timedelta(days=(day.weekday() - week_start) % 7)


def start_of_month(day: date) -> date:
    return day.replace(day=1)


def end_of_month(day: date) -> date:
    last_day = monthrange(day.year, day.month)[1]
    return day.replace(day=last_day)


def previous_month_anchor(day: date) -> tuple[int, int]:
    """Return (year, month) for the month prior to the given date."""
    if day.month == 1:
        return day.year - 1, 12
    return day.year, day.month - 1


def mtd_previous_month_range(today: date) -> tuple[date, date]:
    """Previous month MTD range aligned to today's day-of-month."""
    prev_year, prev_month = previous_month_anchor(today)
    last_day_prev = monthrange(prev_year, prev_month)[1]
    prev_to = date(prev_year, prev_month, min(today.day, last_day_prev))
    return date(prev_year, prev_month, 1), prev_to


def calculate_date_range(
    view: str, from_date: str | None = None, to_date: str | None = None
) -> tuple[date, date]:
    """Resolve a named view or custom date range to (from, to) dates.

    Supported views: today, yesterday, this_week, last_week, this_month, last_month, custom.
    Raises ValueError for invalid inputs or ranges > 365 days.
    """
    today = today_local()

    if view == "today":
        return today, today
    if view == "yesterday":
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    if view == "this_week":
        week_start = start_of_week(today)
        return week_start, today
    if view == "last_week":
        week_start = start_of_week(today) - timedelta(days=7)
        return week_start, week_start + timedelta(days=6)
    if view == "this_month":
        return start_of_month(today), today
    if view == "last_month":
        prev_year, prev_month = previous_month_anchor(today)
        month_start = date(prev_year, prev_month, 1)
        return month_start, end_of_month(month_start)
    if view == "custom" and from_date and to_date:
        try:
            from_dt = date.fromisoformat(from_date)
            to_dt = date.fromisoformat(to_date)
        except ValueError as e:
            raise ValueError("Invalid date format. Please use YYYY-MM-DD format.") from e
        if to_dt > today:
            raise ValueError("End date cannot be in the future.")
        if from_dt > to_dt:
            raise ValueError("Start date must be before or equal to end date.")
        if (to_dt - from_dt).days > 365:
            raise ValueError("Date range cannot exceed 365 days. Please select a smaller range.")
        return from_dt, to_dt

    return today, today


def calculate_previous_period(from_date: date, to_date: date) -> tuple[date, date]:
    """Return the immediately preceding period of the same duration."""
    duration = (to_date - from_date).days
    prev_to = from_date - timedelta(days=1)
    prev_from = prev_to - timedelta(days=duration)
    return prev_from, prev_to


def calculate_comparison_range(
    view: str, current_from: date, current_to: date
) -> tuple[date, date]:
    """Return the comparison period for a given view type."""
    if view in {"today", "yesterday"}:
        prev_day = current_from - timedelta(days=7)
        return prev_day, prev_day
    if view in {"this_week", "last_week"}:
        return current_from - timedelta(days=7), current_to - timedelta(days=7)
    if view == "this_month":
        return mtd_previous_month_range(current_to)
    if view == "last_month":
        prev_year, prev_month = previous_month_anchor(current_from)
        prev_start = date(prev_year, prev_month, 1)
        return prev_start, end_of_month(prev_start)
    return calculate_previous_period(current_from, current_to)


def format_date_range(from_d: date, to_d: date) -> str:
    """Format a date range for display."""
    if from_d == to_d:
        return from_d.strftime("%b %d, %Y")
    if from_d.year == to_d.year:
        return f"{from_d.strftime('%b %d')} - {to_d.strftime('%b %d, %Y')}"
    return f"{from_d.strftime('%b %d, %Y')} - {to_d.strftime('%b %d, %Y')}"
