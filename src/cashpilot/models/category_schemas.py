"""Pydantic schemas for Category API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from cashpilot.models.enums import CategoryType


class CategoryRead(BaseModel):
    """Schema for reading a category."""

    id: UUID
    name: str
    type: CategoryType
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
