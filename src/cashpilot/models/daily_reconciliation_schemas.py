# File: src/cashpilot/models/daily_reconciliation_schemas.py
"""Pydantic schemas for DailyReconciliation API."""

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from cashpilot.core.validators import validate_currency, validate_no_future_date


class DailyReconciliationCreate(BaseModel):
    """Schema for creating a new daily reconciliation."""

    business_id: UUID
    date: date_type
    cash_sales: Decimal | None = Field(None, ge=0, decimal_places=2)
    credit_sales: Decimal | None = Field(None, ge=0, decimal_places=2)
    card_sales: Decimal | None = Field(None, ge=0, decimal_places=2)
    total_sales: Decimal | None = Field(None, ge=0, decimal_places=2)
    daily_cost_total: int | None = Field(None, ge=0)
    invoice_count: int | None = Field(None, ge=0, description="Number of invoices/transactions")
    is_closed: bool = Field(False, description="Marks location closed that day")

    @field_validator("cash_sales", "credit_sales", "card_sales", "total_sales")
    @classmethod
    def validate_currency_fields(cls, v: Decimal | None) -> Decimal | None:
        """Validate currency values if provided."""
        if v is None:
            return None
        return validate_currency(v)

    @field_validator("daily_cost_total")
    @classmethod
    def validate_daily_cost_total(cls, v: int | None) -> int | None:
        """Validate daily cost total if provided."""
        if v is None:
            return None
        validate_currency(Decimal(v))
        return v

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: date_type) -> date_type:
        """Ensure date is not in the future."""
        return validate_no_future_date(v, "Date")


class DailyReconciliationUpdate(BaseModel):
    """Schema for updating a daily reconciliation."""

    cash_sales: Decimal | None = Field(None, ge=0, decimal_places=2)
    credit_sales: Decimal | None = Field(None, ge=0, decimal_places=2)
    card_sales: Decimal | None = Field(None, ge=0, decimal_places=2)
    total_sales: Decimal | None = Field(None, ge=0, decimal_places=2)
    daily_cost_total: int | None = Field(None, ge=0)
    invoice_count: int | None = Field(None, ge=0, description="Number of invoices/transactions")
    is_closed: bool | None = Field(None)
    reason: str = Field(..., min_length=5, description="Required reason for edit")

    @field_validator("cash_sales", "credit_sales", "card_sales", "total_sales")
    @classmethod
    def validate_currency_fields(cls, v: Decimal | None) -> Decimal | None:
        """Validate currency values if provided."""
        if v is None:
            return None
        return validate_currency(v)

    @field_validator("daily_cost_total")
    @classmethod
    def validate_daily_cost_total(cls, v: int | None) -> int | None:
        """Validate daily cost total if provided."""
        if v is None:
            return None
        validate_currency(Decimal(v))
        return v


class DailyReconciliationRead(BaseModel):
    """Schema for reading a daily reconciliation."""

    id: UUID
    business_id: UUID
    date: date_type
    cash_sales: Decimal | None
    credit_sales: Decimal | None
    card_sales: Decimal | None
    total_sales: Decimal | None
    daily_cost_total: int | None
    invoice_count: int | None
    is_closed: bool
    admin_id: UUID
    created_at: datetime
    deleted_at: datetime | None
    deleted_by: str | None

    model_config = ConfigDict(from_attributes=True)


class DailyReconciliationBulkCreate(BaseModel):
    """Schema for bulk creating daily reconciliations for multiple businesses."""

    date: date_type
    businesses: list[dict] = Field(
        ...,
        description=(
            "List of business data: {business_id, cash_sales, credit_sales, "
            "card_sales, total_sales, daily_cost_total, invoice_count, is_closed}"
        ),
    )

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: date_type) -> date_type:
        """Ensure date is not in the future."""
        return validate_no_future_date(v, "Date")
