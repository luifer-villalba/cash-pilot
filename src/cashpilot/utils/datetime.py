# File: src/cashpilot/utils/datetime.py
"""Timezone-aware datetime utilities with per-business timezone support."""

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

# Default app timezone (Paraguay)
# Paraguay timezone: UTC-3 year-round (no DST since 2016)
APP_TIMEZONE = "America/Asuncion"


def get_timezone(tz_name: str | None = None) -> ZoneInfo:
    """
    Get ZoneInfo object for the specified timezone.

    Args:
        tz_name: IANA timezone identifier (e.g., "America/New_York")
                If None, uses APP_TIMEZONE default

    Returns:
        ZoneInfo object for the specified timezone
    """
    return ZoneInfo(tz_name or APP_TIMEZONE)


def now_local(business_timezone: str | None = None) -> datetime:
    """
    Get current datetime in the specified timezone.

    Args:
        business_timezone: IANA timezone identifier (e.g., "America/New_York")
                          If None, uses APP_TIMEZONE (America/Asuncion)

    Returns:
        Current datetime in the specified timezone
    """
    tz = get_timezone(business_timezone)
    return datetime.now(tz)


def today_local(business_timezone: str | None = None) -> date:
    """
    Get today's date in the specified timezone.

    Args:
        business_timezone: IANA timezone identifier
                          If None, uses APP_TIMEZONE

    Returns:
        Today's date in the specified timezone
    """
    return now_local(business_timezone).date()


def current_time_local(business_timezone: str | None = None) -> time:
    """
    Get current time in the specified timezone (time only, no tz info).

    Args:
        business_timezone: IANA timezone identifier
                          If None, uses APP_TIMEZONE

    Returns:
        Current time in the specified timezone (naive time object)
    """
    return now_local(business_timezone).time()


def now_utc() -> datetime:
    """Get current UTC datetime as NAIVE for PostgreSQL storage."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def now_utc_naive() -> datetime:
    """Alias for now_utc() - both return naive UTC for PostgreSQL."""
    return now_utc()
