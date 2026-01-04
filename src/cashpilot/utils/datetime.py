# File: src/cashpilot/utils/datetime.py
"""Timezone-aware datetime utilities for UTC-first storage with business timezone display."""

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

# Default business timezone (Paraguay)
# Paraguay timezone: UTC-3 year-round (no DST since 2016)
# This is the DEFAULT timezone - in Phase 3, this will be configurable per business
APP_TIMEZONE = "America/Asuncion"


def now_utc() -> datetime:
    """Get current UTC datetime (timezone-aware).

    Returns timezone-aware datetime in UTC for proper PostgreSQL TIMESTAMPTZ storage.
    This is the PRIMARY function for getting current time - always use this for database operations.
    """
    return datetime.now(timezone.utc)


def now_business(tz: str | None = None) -> datetime:
    """Get current datetime in business timezone (for display only).

    Args:
        tz: IANA timezone string (e.g., "America/Asuncion").
            If None, uses APP_TIMEZONE default.

    Returns:
        Timezone-aware datetime in the specified business timezone.

    Note:
        This is for DISPLAY purposes only. Always store in UTC using now_utc().
    """
    business_tz = ZoneInfo(tz if tz else APP_TIMEZONE)
    return datetime.now(business_tz)


def now_local() -> datetime:
    """Get current datetime in default business timezone (legacy compatibility).

    Deprecated: Use now_business() instead for clarity.
    """
    return now_business(APP_TIMEZONE)


def today_local() -> date:
    """Get today's date in default business timezone."""
    return now_business().date()


def today_business(tz: str | None = None) -> date:
    """Get today's date in business timezone.

    Args:
        tz: IANA timezone string. If None, uses APP_TIMEZONE default.
    """
    return now_business(tz).date()


def current_time_local() -> time:
    """Get current time in default business timezone (time only, no tz info)."""
    return now_business().time()


def utc_to_business(dt: datetime, tz: str | None = None) -> datetime:
    """Convert UTC datetime to business timezone.

    Args:
        dt: Timezone-aware datetime in UTC
        tz: IANA timezone string. If None, uses APP_TIMEZONE default.

    Returns:
        Timezone-aware datetime in business timezone
    """
    if dt.tzinfo is None:
        raise ValueError("Input datetime must be timezone-aware")

    business_tz = ZoneInfo(tz if tz else APP_TIMEZONE)
    return dt.astimezone(business_tz)


def business_to_utc(dt: datetime) -> datetime:
    """Convert business timezone datetime to UTC.

    Args:
        dt: Timezone-aware datetime in any timezone

    Returns:
        Timezone-aware datetime in UTC
    """
    if dt.tzinfo is None:
        raise ValueError("Input datetime must be timezone-aware")

    return dt.astimezone(timezone.utc)


# Legacy compatibility - DEPRECATED, will be removed in future versions
def now_utc_naive() -> datetime:
    """DEPRECATED: Get naive UTC datetime.

    This function is deprecated and exists only for backward compatibility.
    Use now_utc() instead, which returns timezone-aware datetime.

    WARNING: This violates PostgreSQL best practices. Do not use for new code.
    """
    import warnings

    warnings.warn(
        "now_utc_naive() is deprecated. Use now_utc() for timezone-aware datetimes.",
        DeprecationWarning,
        stacklevel=2,
    )
    return datetime.now(timezone.utc).replace(tzinfo=None)
