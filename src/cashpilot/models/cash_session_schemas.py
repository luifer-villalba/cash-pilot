# File: src/cashpilot/models/cash_session_schemas.py
"""Pydantic schemas for CashSession API."""

from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from cashpilot.core.validators import sanitize_html, validate_currency, validate_no_future_date
from cashpilot.models.user_schemas import UserResponse


class CashSessionCreate(BaseModel):
    """Schema for creating a new cash session."""

    business_id: UUID
    for_cashier_id: UUID | None = Field(
        None, description="Admin: create session for another cashier"
    )
    initial_cash: Decimal = Field(..., ge=0, decimal_places=2)
    expenses: Decimal = Field(Decimal("0.00"), ge=0, decimal_places=2)
    notes: str | None = Field(None, max_length=1000)

    session_date: date | None = Field(
        None, description="Optional: override session date (default: today)"
    )
    opened_time: time | None = Field(
        None, description="Optional: override open time (default: now)"
    )
    allow_overlap: bool = Field(False, description="Override conflict check if true")

    @field_validator("initial_cash", "expenses")
    @classmethod
    def validate_currency_fields(cls, v: Decimal) -> Decimal:
        """Validate currency values."""
        return validate_currency(v)

    @field_validator("session_date")
    @classmethod
    def validate_session_date(cls, v: date | None) -> date | None:
        """Ensure session date is not in the future."""
        if v is None:
            return None
        return validate_no_future_date(v, "Session date")


class CashSessionPatchOpen(BaseModel):
    """Schema for editing an OPEN session."""

    initial_cash: Decimal | None = Field(None, ge=0, decimal_places=2)
    opened_time: time | None = Field(None)
    expenses: Decimal | None = Field(None, ge=0, decimal_places=2)
    credit_sales_total: Decimal | None = Field(None, ge=0, decimal_places=2)
    credit_payments_collected: Decimal | None = Field(None, ge=0, decimal_places=2)
    notes: str | None = Field(None, max_length=1000)
    reason: str | None = Field(None, max_length=500, description="Reason for edit")

    @field_validator(
        "initial_cash",
        "expenses",
        "credit_sales_total",
        "credit_payments_collected",
    )
    @classmethod
    def validate_currency_fields(cls, v: Decimal | None) -> Decimal | None:
        """Validate currency values."""
        if v is None:
            return None
        return validate_currency(v)

    @field_validator("reason", "notes")
    @classmethod
    def validate_reason(cls, v: str | None) -> str | None:
        """Sanitize reason field."""
        return sanitize_html(v)


class CashSessionPatchClosed(BaseModel):
    """Schema for editing a CLOSED session (manager/admin only)."""

    final_cash: Decimal | None = Field(None, ge=0, decimal_places=2)
    envelope_amount: Decimal | None = Field(None, ge=0, decimal_places=2)
    credit_card_total: Decimal | None = Field(None, ge=0, decimal_places=2)
    debit_card_total: Decimal | None = Field(None, ge=0, decimal_places=2)
    bank_transfer_total: Decimal | None = Field(None, ge=0, decimal_places=2)
    expenses: Decimal | None = Field(None, ge=0, decimal_places=2)
    credit_sales_total: Decimal | None = Field(None, ge=0, decimal_places=2)
    credit_payments_collected: Decimal | None = Field(None, ge=0, decimal_places=2)
    notes: str | None = Field(None, max_length=1000)
    reason: str | None = Field(None, max_length=500, description="Reason for edit")

    @field_validator(
        "final_cash",
        "envelope_amount",
        "credit_card_total",
        "debit_card_total",
        "bank_transfer_total",
        "expenses",
        "credit_sales_total",
        "credit_payments_collected",
    )
    @classmethod
    def validate_currency_fields(cls, v: Decimal | None) -> Decimal | None:
        """Validate currency values."""
        if v is None:
            return None
        return validate_currency(v)

    @field_validator("notes", "reason")
    @classmethod
    def validate_text_fields(cls, v: str | None) -> str | None:
        """Sanitize text fields."""
        return sanitize_html(v)


class CashSessionUpdate(BaseModel):
    """Schema for closing/updating a cash session."""

    final_cash: Decimal = Field(..., ge=0, decimal_places=2)
    envelope_amount: Decimal = Field(Decimal("0.00"), ge=0, decimal_places=2)
    credit_card_total: Decimal = Field(Decimal("0.00"), ge=0, decimal_places=2)
    debit_card_total: Decimal = Field(Decimal("0.00"), ge=0, decimal_places=2)
    bank_transfer_total: Decimal = Field(Decimal("0.00"), ge=0, decimal_places=2)
    expenses: Decimal = Field(Decimal("0.00"), ge=0, decimal_places=2)
    credit_sales_total: Decimal = Field(Decimal("0.00"), ge=0, decimal_places=2)
    credit_payments_collected: Decimal = Field(Decimal("0.00"), ge=0, decimal_places=2)
    closed_time: time | None = Field(None)
    closing_ticket: str | None = Field(None, max_length=50)
    notes: str | None = Field(None, max_length=1000)

    @field_validator(
        "final_cash",
        "envelope_amount",
        "credit_card_total",
        "debit_card_total",
        "bank_transfer_total",
        "expenses",
        "credit_sales_total",
        "credit_payments_collected",
    )
    @classmethod
    def validate_currency_fields(cls, v: Decimal) -> Decimal:
        """Validate currency values."""
        return validate_currency(v)

    @field_validator("closing_ticket")
    @classmethod
    def validate_closing_ticket(cls, v: str | None) -> str | None:
        """Validate closing ticket format."""
        if not v:
            return None

        cleaned = v.strip()

        # Alphanumeric + hyphens only
        import re

        if not re.match(r"^[a-zA-Z0-9\-]+$", cleaned):
            raise ValueError("Closing ticket can only contain letters, numbers, and hyphens")

        return cleaned

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: str | None) -> str | None:
        """Sanitize notes field."""
        return sanitize_html(v)


class CashSessionRead(BaseModel):
    """Schema for reading a cash session from the database."""

    id: UUID
    business_id: UUID
    session_number: int
    cashier_id: UUID
    cashier: UserResponse
    created_by_user: UserResponse | None = None
    status: str

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
    credit_sales_total: Decimal
    credit_payments_collected: Decimal
    closing_ticket: str | None
    notes: str | None

    # Soft delete fields
    is_deleted: bool = False
    deleted_at: datetime | None = None
    deleted_by: str | None = None

    # Calculated properties
    cash_sales: Decimal = Field(...)
    total_sales: Decimal = Field(...)
    net_earnings: Decimal = Field(...)

    model_config = ConfigDict(from_attributes=True)
