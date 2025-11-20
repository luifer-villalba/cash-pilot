"""Pydantic schemas for CashSession API."""

from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CashSessionCreate(BaseModel):
    """Schema for creating a new cash session."""

    business_id: UUID
    cashier_name: str = Field(..., min_length=2, max_length=100)
    initial_cash: Decimal = Field(..., ge=0, decimal_places=2)
    expenses: Decimal = Field(Decimal("0.00"), ge=0, decimal_places=2)

    session_date: date | None = Field(
        None, description="Optional: override session date (default: today)"
    )
    opened_time: time | None = Field(
        None, description="Optional: override open time (default: now)"
    )
    allow_overlap: bool = Field(False, description="Override conflict check if true")


class CashSessionPatchOpen(BaseModel):
    """Schema for editing an OPEN session."""

    cashier_name: str | None = Field(None, min_length=2, max_length=100)
    initial_cash: Decimal | None = Field(None, ge=0, decimal_places=2)
    opened_time: time | None = Field(None)
    expenses: Decimal | None = Field(None, ge=0, decimal_places=2)
    reason: str | None = Field(None, max_length=500, description="Reason for edit")


class CashSessionPatchClosed(BaseModel):
    """Schema for editing a CLOSED session (manager/admin only)."""

    final_cash: Decimal | None = Field(None, ge=0, decimal_places=2)
    envelope_amount: Decimal | None = Field(None, ge=0, decimal_places=2)
    credit_card_total: Decimal | None = Field(None, ge=0, decimal_places=2)
    debit_card_total: Decimal | None = Field(None, ge=0, decimal_places=2)
    bank_transfer_total: Decimal | None = Field(None, ge=0, decimal_places=2)
    expenses: Decimal | None = Field(None, ge=0, decimal_places=2)
    notes: str | None = Field(None, max_length=1000)
    reason: str | None = Field(None, max_length=500, description="Reason for edit")


class CashSessionUpdate(BaseModel):
    """Schema for closing/updating a cash session."""

    final_cash: Decimal | None = Field(None, ge=0, decimal_places=2)
    envelope_amount: Decimal | None = Field(None, ge=0, decimal_places=2)
    credit_card_total: Decimal | None = Field(None, ge=0, decimal_places=2)
    debit_card_total: Decimal | None = Field(None, ge=0, decimal_places=2)
    bank_transfer_total: Decimal | None = Field(None, ge=0, decimal_places=2)
    expenses: Decimal | None = Field(None, ge=0, decimal_places=2)
    closing_ticket: str | None = Field(None, max_length=50)
    notes: str | None = None

    closed_time: time | None = Field(None, description="Time session closed")


class CashSessionRead(BaseModel):
    """Schema for reading a cash session from the database."""

    id: UUID
    business_id: UUID
    status: str
    cashier_name: str

    session_date: date
    opened_time: time
    closed_time: time | None

    initial_cash: Decimal
    final_cash: Decimal | None
    envelope_amount: Decimal
    credit_card_total: Decimal
    debit_card_total: Decimal
    bank_transfer_total: Decimal
    expenses: Decimal
    closing_ticket: str | None
    notes: str | None

    last_modified_at: datetime | None = None
    last_modified_by: str | None = None

    # Soft delete fields
    is_deleted: bool = False
    deleted_at: datetime | None = None
    deleted_by: str | None = None

    # Calculated properties
    cash_sales: Decimal = Field(...)
    cash_debit_transfer_sales: Decimal = Field(...)
    total_sales: Decimal = Field(...)
    net_earnings: Decimal = Field(...)

    model_config = ConfigDict(from_attributes=True)
