"""Pydantic schemas for API requests and responses."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from cashpilot.models.enums import MovementType

if TYPE_CHECKING:
    from cashpilot.models.category_schemas import CategoryRead


class MovementBase(BaseModel):
    """Base schema with common fields."""

    occurred_at: datetime = Field(
        ...,
        description="When the movement occurred",
        examples=["2025-10-16T10:30:00Z"],
    )
    type: MovementType
    amount_gs: int = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=500)
    category_id: Optional[UUID] = None


class MovementCreate(MovementBase):
    """Schema for creating a new movement."""

    @field_validator("amount_gs")
    @classmethod
    def amount_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Amount must be a positive integer")
        return v

    @field_validator("occurred_at")
    @classmethod
    def strip_timezone(cls, v: datetime) -> datetime:
        """Convert to naive UTC datetime for database."""
        if v.tzinfo is not None:
            return v.astimezone(timezone.utc).replace(tzinfo=None)
        return v


class MovementRead(MovementBase):
    """Schema for reading a movement from the database."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    category: Optional["CategoryRead"] = None

    model_config = ConfigDict(from_attributes=True)


class MovementUpdate(BaseModel):
    """Schema for updating a movement."""

    occurred_at: Optional[datetime] = None
    type: Optional[MovementType] = None
    amount_gs: Optional[int] = Field(None, gt=0)
    description: Optional[str] = Field(None, max_length=500)
    category_id: Optional[UUID] = None

    @field_validator("amount_gs")
    @classmethod
    def amount_must_be_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v
