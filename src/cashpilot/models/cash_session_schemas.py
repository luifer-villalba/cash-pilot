"""Pydantic schemas for CashSession API."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CashSessionBase(BaseModel):
    """Base schema with common fields."""

    initial_cash: Decimal = Field(..., gt=0, decimal_places=2)
    final_cash: Decimal | None = Field(None, decimal_places=2)
    envelope_amount: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    expected_sales: Decimal = Field(default=Decimal("0.00"), decimal_places=2)


class CashSessionCreate(CashSessionBase):
    """Schema for creating a new cash session."""

    business_id: UUID


class CashSessionUpdate(BaseModel):
    """Schema for updating a cash session (partial update allowed)."""

    final_cash: Decimal | None = Field(None, decimal_places=2)
    envelope_amount: Decimal | None = Field(None, decimal_places=2)
    expected_sales: Decimal | None = Field(None, decimal_places=2)


class CashSessionRead(CashSessionBase):
    """Schema for reading a cash session from the database."""

    id: UUID
    business_id: UUID
    opened_at: datetime
    closed_at: datetime | None
    cash_sales: Decimal
    difference: Decimal

    model_config = ConfigDict(from_attributes=True)