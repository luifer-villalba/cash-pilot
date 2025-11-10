"""Pydantic schemas for CashSession API."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CashSessionCreate(BaseModel):
    """Schema for creating a new cash session."""

    business_id: UUID
    cashier_name: str = Field(..., min_length=2, max_length=100)
    initial_cash: Decimal = Field(..., ge=0, decimal_places=2)
    opened_at: datetime | None = Field(
        None, description="Optional: override opened_at (default: now)"
    )
    allow_overlap: bool = Field(False, description="Override conflict check if true")


class CashSessionUpdate(BaseModel):
    """Schema for closing/updating a cash session."""

    final_cash: Decimal | None = Field(None, ge=0, decimal_places=2)
    envelope_amount: Decimal | None = Field(None, ge=0, decimal_places=2)
    credit_card_total: Decimal | None = Field(None, ge=0, decimal_places=2)
    debit_card_total: Decimal | None = Field(None, ge=0, decimal_places=2)
    bank_transfer_total: Decimal | None = Field(None, ge=0, decimal_places=2)
    closing_ticket: str | None = Field(None, max_length=50)
    notes: str | None = None


class CashSessionRead(BaseModel):
    """Schema for reading a cash session from the database."""

    id: UUID
    business_id: UUID
    status: str
    cashier_name: str
    opened_at: datetime
    closed_at: datetime | None
    initial_cash: Decimal
    final_cash: Decimal | None
    envelope_amount: Decimal
    credit_card_total: Decimal
    debit_card_total: Decimal
    bank_transfer_total: Decimal
    closing_ticket: str | None
    notes: str | None

    # Calculated properties
    cash_sales: Decimal = Field(...)
    total_sales: Decimal = Field(...)
    difference: Decimal = Field(...)

    model_config = ConfigDict(from_attributes=True)
