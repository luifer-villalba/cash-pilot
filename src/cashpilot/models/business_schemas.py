"""Pydantic schemas for Business API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BusinessBase(BaseModel):
    """Base schema with common fields."""

    name: str = Field(..., min_length=1, max_length=200)
    address: str | None = Field(None, max_length=500)
    phone: str | None = Field(None, max_length=50)
    cashiers: list[str] = Field(default_factory=list, description="List of cashier names")


class BusinessCreate(BusinessBase):
    """Schema for creating a new business."""

    pass


class BusinessUpdate(BaseModel):
    """Schema for updating a business (partial update allowed)."""

    name: str | None = Field(None, min_length=1, max_length=200)
    address: str | None = Field(None, max_length=500)
    phone: str | None = Field(None, max_length=50)
    cashiers: list[str] | None = Field(None, description="List of cashier names")
    is_active: bool | None = None


class BusinessRead(BusinessBase):
    """Schema for reading a business from the database."""

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
