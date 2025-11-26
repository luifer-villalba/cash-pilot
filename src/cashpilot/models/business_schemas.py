# File: src/cashpilot/models/business_schemas.py
"""Pydantic schemas for Business API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from cashpilot.core.validators import (
    sanitize_html,
    validate_alphanumeric_with_spaces,
    validate_phone,
)


class BusinessBase(BaseModel):
    """Base schema with common fields."""

    name: str = Field(..., min_length=1, max_length=200)
    address: str | None = Field(None, max_length=500)
    phone: str | None = Field(None, max_length=50)
    cashiers: list[str] = Field(default_factory=list, description="List of cashier names")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate business name."""
        return validate_alphanumeric_with_spaces(
            v,
            field_name="Business name",
            min_length=1,
            max_length=200,
            allow_punctuation=True,
        )

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str | None) -> str | None:
        """Sanitize address to prevent XSS."""
        if not v:
            return None
        return sanitize_html(v)

    @field_validator("phone")
    @classmethod
    def validate_phone_number(cls, v: str | None) -> str | None:
        """Validate phone format."""
        return validate_phone(v)

    @field_validator("cashiers")
    @classmethod
    def validate_cashier_list(cls, v: list[str]) -> list[str]:
        """Validate each cashier name."""
        validated = []
        for cashier in v:
            if cashier and cashier.strip():
                validated_name = validate_alphanumeric_with_spaces(
                    cashier,
                    field_name="Cashier name",
                    min_length=2,
                    max_length=100,
                )
                validated.append(validated_name)
        return validated


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

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        """Validate business name."""
        if v is None:
            return None
        return validate_alphanumeric_with_spaces(
            v,
            field_name="Business name",
            min_length=1,
            max_length=200,
            allow_punctuation=True,
        )

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str | None) -> str | None:
        """Sanitize address to prevent XSS."""
        if not v:
            return None
        return sanitize_html(v)

    @field_validator("phone")
    @classmethod
    def validate_phone_number(cls, v: str | None) -> str | None:
        """Validate phone format."""
        return validate_phone(v)

    @field_validator("cashiers")
    @classmethod
    def validate_cashier_list(cls, v: list[str] | None) -> list[str] | None:
        """Validate each cashier name."""
        if v is None:
            return None

        validated = []
        for cashier in v:
            if cashier and cashier.strip():
                validated_name = validate_alphanumeric_with_spaces(
                    cashier,
                    field_name="Cashier name",
                    min_length=2,
                    max_length=100,
                )
                validated.append(validated_name)
        return validated


class BusinessRead(BusinessBase):
    """Schema for reading a business from the database."""

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
