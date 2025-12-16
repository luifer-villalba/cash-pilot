# File: src/cashpilot/utils/datetime.py
"""Timezone-aware datetime utilities for Paraguay local time."""

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

# Paraguay timezone (ZoneInfo handles DST transitions automatically)
# Paraguay timezone: UTC-3 year-round (no DST since 2016)
APP_TIMEZONE = ZoneInfo("America/Asuncion")


def now_local() -> datetime:
    """Get current datetime in Paraguay timezone (UTC-3)."""
    return datetime.now(APP_TIMEZONE)


def today_local() -> date:
    """Get today's date in Paraguay timezone."""
    return now_local().date()


def current_time_local() -> time:
    """Get current time in Paraguay timezone (time only, no tz info)."""
    return now_local().time()


def now_utc() -> datetime:
    """Get current UTC datetime as NAIVE for PostgreSQL storage."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def now_utc_naive() -> datetime:
    """Alias for now_utc() - both return naive UTC for PostgreSQL."""
    return now_utc()
