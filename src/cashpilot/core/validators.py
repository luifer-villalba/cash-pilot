# File: src/cashpilot/core/validators.py
"""Reusable validation utilities for input sanitization."""

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from cashpilot.utils.datetime import today_local


def validate_currency(
    value: Decimal | float | str, max_value: Decimal = Decimal("9999999999.99")
) -> Decimal:
    """
    Validate currency input.

    Args:
        value: Currency value to validate
        max_value: Maximum allowed value (default: 9,999,999,999.99 to match NUMERIC(12, 2))

    Returns:
        Validated Decimal with max 2 decimal places

    Raises:
        ValueError: If value is negative, exceeds max, or has >2 decimals
    """
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError) as e:
        raise ValueError(f"Invalid currency format: {value}") from e

    if decimal_value < 0:
        raise ValueError("Currency value cannot be negative")

    if decimal_value > max_value:
        raise ValueError(f"Currency value exceeds maximum allowed: {max_value}")

    return decimal_value


def validate_alphanumeric_with_spaces(
    value: str,
    field_name: str = "Field",
    min_length: int = 1,
    max_length: int = 100,
    allow_punctuation: bool = False,
) -> str:
    """
    Validate alphanumeric text with spaces.

    Args:
        value: Text to validate
        field_name: Name for error messages
        min_length: Minimum length
        max_length: Maximum length
        allow_punctuation: Allow basic punctuation (.,-)

    Returns:
        Stripped and validated text

    Raises:
        ValueError: If validation fails
    """
    if not value or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")

    cleaned = value.strip()

    if len(cleaned) < min_length:
        raise ValueError(f"{field_name} must be at least {min_length} characters")

    if len(cleaned) > max_length:
        raise ValueError(f"{field_name} cannot exceed {max_length} characters")

    # Pattern: letters, numbers, spaces, and optionally basic punctuation
    if allow_punctuation:
        pattern = r"^[a-zA-Z0-9\sáéíóúñÁÉÍÓÚÑ.,\-]+$"
    else:
        pattern = r"^[a-zA-Z0-9\sáéíóúñÁÉÍÓÚÑ]+$"

    if not re.match(pattern, cleaned):
        allowed = "letters, numbers, and spaces"
        if allow_punctuation:
            allowed += " (.,- allowed)"
        raise ValueError(f"{field_name} can only contain {allowed}")

    return cleaned


# File: src/cashpilot/core/validators.py (partial update - around line 100)


def validate_phone(value: str | None) -> str | None:
    """
    Validate phone number format.

    Args:
        value: Phone number to validate

    Returns:
        Validated phone or None if empty

    Raises:
        ValueError: If format is invalid
    """
    if not value or not value.strip():
        return None

    cleaned = value.strip()

    # Allow: digits, spaces, +, -, (, )
    pattern = r"^[0-9\s+\-()]+$"
    if not re.match(pattern, cleaned):
        raise ValueError("Phone can only contain digits, spaces, +, -, (, )")

    # Must have at least 5 digits (was allowing letters to pass)
    digits_only = re.sub(r"[^0-9]", "", cleaned)
    if len(digits_only) < 5:
        raise ValueError("Phone must contain at least 5 digits")

    # Additional check: no letters (redundant but explicit)
    if re.search(r"[a-zA-Z]", cleaned):
        raise ValueError("Phone cannot contain letters")

    return cleaned


def validate_no_future_date(value: date, field_name: str = "Date") -> date:
    """
    Ensure date is not in the future.

    Args:
        value: Date to validate
        field_name: Name for error messages

    Returns:
        Validated date

    Raises:
        ValueError: If date is in the future
    """
    if value > today_local():
        raise ValueError(f"{field_name} cannot be in the future")
    return value


def sanitize_html(value: str | None) -> str | None:
    """
    Strip/escape HTML tags to prevent XSS.

    Args:
        value: Text that may contain HTML

    Returns:
        Sanitized text or None if empty
    """
    if not value:
        return None

    # Remove all HTML tags
    cleaned = re.sub(r"<[^>]+>", "", value)

    # Escape remaining special chars
    cleaned = (
        cleaned.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )

    return cleaned.strip() if cleaned.strip() else None


def validate_email(value: str) -> str:
    """
    Basic email format validation.

    Args:
        value: Email to validate

    Returns:
        Lowercase email

    Raises:
        ValueError: If format is invalid
    """
    cleaned = value.strip().lower()

    # Basic email regex
    pattern = r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$"
    if not re.match(pattern, cleaned):
        raise ValueError("Invalid email format")

    return cleaned
