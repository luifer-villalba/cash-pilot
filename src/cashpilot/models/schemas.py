"""
Pydantic schemas for API requests and responses.
These schemas ensure data is valid before reaching the database
and provide clean API responses.
"""

from dataclasses import Field
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from cashpilot.models.enums import MovementType


class MovementBase(BaseModel):
    """Base schema with common fields for creation and update"""

    ocurred_at: datetime = Field(
        ...,
        description="When the movement ocurred",
        examples=["2025-10-16T10:30:00Z"],
    )
    type: MovementType = Field(
        ...,
        description="Type of movement: INCOME or EXPENSE",
        examples=["INCOME", "EXPENSE"],
    )
    amount_gs: int = Field(
        ...,
        gt=0,
        description="Amount in Guaraníes (always positive)",
        examples=[150000, 50000],
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional text description of the movement",
        examples=["Salary for October", "Grocery shopping"],
    )
    category: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional category for organization",
        examples=["Salary", "Groceries", "Rent"],
    )


class MovementCreate(MovementBase):
    """Schema for creating a new movement"""

    @field_validator("amount_gs")
    @classmethod
    def amount_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Amount must be a positive integer")
        return v


class MovementRead(MovementBase):
    """Schema for reading a movement from the database"""

    id: UUID = Field(
        ...,
        description="Unique identifier of the movement (UUID v4)",
    )
    created_at: datetime = Field(
        ...,
        description="When the record was created in the database",
        examples=["2025-10-16T10:30:00Z"],
    )
    updated_at: datetime = Field(
        ...,
        description="When the record was last updated in the database",
        examples=["2025-10-16T10:30:00Z"],
    )

    model_config = ConfigDict(from_attributes=True)


class MovementUpdate(BaseModel):
    """Schema for updating a movement (all fields optional)."""

    occurred_at: Optional[datetime] = None
    type: Optional[MovementType] = None
    amount_gs: Optional[int] = Field(None, gt=0)
    description: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = Field(None, max_length=100)

    @field_validator("amount_gs")
    @classmethod
    def amount_must_be_positive(cls, v: Optional[int]) -> Optional[int]:
        """Ensure amount is positive if provided."""
        if v is not None and v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v
