"""Pydantic schemas for reports API."""

from datetime import date as date_type
from datetime import time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CashierPerformance(BaseModel):
    """Cashier performance metrics."""

    cashier_id: UUID
    cashier_name: str
    session_count: int
    total_revenue: Decimal
    avg_revenue_per_session: Decimal
    percentage_of_total: Decimal

    # Payment method breakdown (percentages)
    cash_percentage: Decimal = Field(
        default=Decimal("0.00"), description="Percentage of revenue from cash"
    )
    debit_percentage: Decimal = Field(
        default=Decimal("0.00"), description="Percentage of revenue from debit cards"
    )
    credit_percentage: Decimal = Field(
        default=Decimal("0.00"), description="Percentage of revenue from credit cards"
    )
    bank_percentage: Decimal = Field(
        default=Decimal("0.00"), description="Percentage of revenue from bank transfers"
    )

    # Additional metrics
    avg_session_duration_hours: Decimal = Field(
        default=Decimal("0.00"), description="Average session duration in hours"
    )
    total_expenses: Decimal = Field(
        default=Decimal("0.00"), description="Total expenses during shifts"
    )
    flagged_sessions: int = Field(default=0, description="Number of flagged/problematic sessions")

    # Shift time information
    shift_start: time | None = Field(default=None, description="Earliest session start time")
    shift_end: time | None = Field(default=None, description="Latest session end time")
    shift_label: str = Field(
        default="", description="Shift classification (Morning/Afternoon/Evening/Night)"
    )


class DailyRevenueSummary(BaseModel):
    """Daily revenue summary for a single date and business."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date": "2026-01-02",
                "business_id": "550e8400-e29b-41d4-a716-446655440000",
                "total_sales": 5000.00,
                "cash_sales": 2000.00,
                "credit_card_sales": 2500.00,
                "debit_card_sales": 500.00,
                "bank_transfer_sales": 0.00,
                "credit_sales": 0.00,
                "net_earnings": 4800.00,
                "total_expenses": 200.00,
                "perfect_count": 8,
                "shortage_count": 1,
                "surplus_count": 1,
                "total_sessions": 10,
                "cashier_performance": [],
            }
        }
    )

    date: date_type = Field(..., description="The date of the report")
    business_id: UUID = Field(..., description="The business ID")

    # Sales totals by payment method
    total_sales: Decimal = Field(
        default=Decimal("0.00"), description="Total sales across all methods"
    )
    cash_sales: Decimal = Field(default=Decimal("0.00"), description="Cash sales")
    credit_card_sales: Decimal = Field(default=Decimal("0.00"), description="Credit card sales")
    debit_card_sales: Decimal = Field(default=Decimal("0.00"), description="Debit card sales")
    bank_transfer_sales: Decimal = Field(default=Decimal("0.00"), description="Bank transfer sales")
    credit_sales: Decimal = Field(default=Decimal("0.00"), description="Credit/on-account sales")

    # Financial summary
    net_earnings: Decimal = Field(default=Decimal("0.00"), description="Total sales minus expenses")
    total_expenses: Decimal = Field(default=Decimal("0.00"), description="Total business expenses")

    # Discrepancy counts
    perfect_count: int = Field(default=0, description="Number of sessions with no discrepancy")
    shortage_count: int = Field(default=0, description="Number of sessions with cash shortage")
    surplus_count: int = Field(default=0, description="Number of sessions with cash surplus")

    # Session counts
    total_sessions: int = Field(default=0, description="Total number of closed sessions")

    # Cashier performance
    cashier_performance: list[CashierPerformance] = Field(
        default=[], description="Performance by cashier"
    )


class DayOfWeekRevenue(BaseModel):
    """Revenue data for a single day of the week."""

    day_name: str = Field(..., description="Name of the day (Monday, Tuesday, etc.)")
    day_number: int = Field(..., description="ISO weekday number (1=Monday, 7=Sunday)")
    date: date_type = Field(..., description="The specific date")
    revenue: Decimal = Field(default=Decimal("0.00"), description="Total revenue for the day")
    has_data: bool = Field(default=True, description="Whether we have session data for this day")
    growth_percent: Decimal | None = Field(None, description="Week-over-week growth percentage")
    trend_arrow: str = Field(default="→", description="Trend indicator (↑, ↓, →)")


class WeeklyRevenueTrend(BaseModel):
    """Weekly revenue trend report comparing current week with previous weeks."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "business_id": "550e8400-e29b-41d4-a716-446655440000",
                "year": 2025,
                "week": 1,
                "current_week": [],
                "previous_weeks": [],
                "highest_day": {
                    "day_name": "Friday",
                    "revenue": 10000.00,
                    "date": "2025-01-03",
                },
                "lowest_day": {
                    "day_name": "Monday",
                    "revenue": 3000.00,
                    "date": "2024-12-30",
                },
                "avg_weekly_revenue": 45000.00,
            }
        }
    )

    business_id: UUID = Field(..., description="The business ID")
    year: int = Field(..., description="Year of the target week")
    week: int = Field(..., description="ISO week number (1-53)")

    # Current week data (7 days)
    current_week: list[DayOfWeekRevenue] = Field(
        default=[], description="Revenue data for each day of the current week"
    )

    # Previous 4 weeks data (28 days total, grouped by week)
    previous_weeks: list[list[DayOfWeekRevenue]] = Field(
        default=[], description="Revenue data for previous 4 weeks"
    )

    # Aggregate stats
    highest_day: dict = Field(default={}, description="Day with highest revenue in current week")
    lowest_day: dict = Field(default={}, description="Day with lowest revenue in current week")

    # Week-over-week comparison
    current_week_total: Decimal = Field(
        default=Decimal("0.00"), description="Total revenue for current week"
    )
    previous_week_total: Decimal = Field(
        default=Decimal("0.00"), description="Total revenue for previous week"
    )
    week_over_week_growth: Decimal | None = Field(
        None, description="Week-over-week growth percentage"
    )
    week_over_week_difference: Decimal = Field(
        default=Decimal("0.00"), description="Absolute difference in revenue (current - previous)"
    )
