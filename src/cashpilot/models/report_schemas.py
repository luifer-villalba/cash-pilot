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
