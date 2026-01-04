"""Caching utility for reports and frequently accessed data."""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

# Simple in-memory cache with TTL
_cache: dict[str, tuple[Any, datetime]] = {}


def get_cache(key: str) -> Optional[Any]:
    """Get value from cache if it exists and hasn't expired."""
    if key not in _cache:
        return None

    value, expires_at = _cache[key]
    if datetime.now(timezone.utc) > expires_at:
        del _cache[key]
        return None

    return value


def set_cache(key: str, value: Any, ttl_seconds: int = 3600) -> None:
    """Set value in cache with TTL (default 1 hour)."""
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    _cache[key] = (value, expires_at)


def clear_cache(pattern: Optional[str] = None) -> None:
    """Clear cache by pattern or all if pattern is None."""
    if pattern is None:
        _cache.clear()
        return

    keys_to_delete = [key for key in _cache.keys() if pattern in key]
    for key in keys_to_delete:
        del _cache[key]


def make_cache_key(prefix: str, **kwargs) -> str:
    """Generate cache key from prefix and parameters."""
    parts = [prefix]
    for key, value in sorted(kwargs.items()):
        parts.append(f"{key}:{value}")
    return "|".join(parts)
