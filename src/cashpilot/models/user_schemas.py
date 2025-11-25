"""Pydantic schemas for User API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from cashpilot.models.user import UserRole


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole = Field(UserRole.CASHIER, description="User role (ADMIN or CASHIER)")


class UserResponse(BaseModel):
    """Schema for reading a user from the database."""

    id: UUID
    email: str
    first_name: str
    last_name: str
    display_name: str
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)