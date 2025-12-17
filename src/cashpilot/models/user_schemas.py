# File: src/cashpilot/models/user_schemas.py
"""Pydantic schemas for User API."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cashpilot.models.business_schemas import BusinessRead

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from cashpilot.core.validators import validate_email
from cashpilot.models.business_schemas import BusinessRead
from cashpilot.models.user import UserRole


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    email: str = Field(..., min_length=5, max_length=255)
    password: str | None = Field(None, min_length=8, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole = Field(UserRole.CASHIER, description="User role (ADMIN or CASHIER)")

    @field_validator("email")
    @classmethod
    def validate_and_lowercase_email(cls, v: str) -> str:
        """Validate and lowercase email."""
        return validate_email(v).lower()

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_names(cls, v: str, info) -> str:
        """Validate name fields."""
        if not v.strip():
            raise ValueError(f"{info.field_name} cannot be empty")

        cleaned = v.strip()

        # Only letters, spaces, hyphens, apostrophes
        import re

        if not re.match(r"^[a-zA-ZáéíóúñÁÉÍÓÚÑ\s'-]+$", cleaned):
            raise ValueError(
                f"{info.field_name} can only contain letters, spaces, hyphens, and apostrophes"
            )

        return cleaned

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str | None) -> str | None:
        """Ensure password meets minimum requirements."""
        if v is None:
            return None

        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")

        # Check for at least one letter and one number
        import re

        if not re.search(r"[a-zA-Z]", v):
            raise ValueError("Password must contain at least one letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")

        return v


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


class UserWithBusinessesResponse(UserResponse):
    """User schema with assigned businesses (for assignment endpoints only)."""

    businesses: list["BusinessRead"] = []

    model_config = ConfigDict(from_attributes=True)
