"""Service-token authentication for machine-to-machine read-only access (BI integrations).

Separate from the human `get_current_user` session auth in `auth.py` — this is a static
bearer token read from an environment variable, meant for a small number of trusted
internal consumers (e.g. a BI assistant), not a general-purpose API key system.
"""

import os
import secrets
import time
from collections import defaultdict

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from cashpilot.core.logging import get_logger

logger = get_logger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)

# Fixed-window rate limit: max requests per token per window.
# In-memory only (matches core/cache.py's approach) — resets on deploy/restart
# and does not share state across multiple instances. Fine for a handful of
# trusted internal callers; revisit if this token is ever exposed publicly.
_RATE_LIMIT_MAX_REQUESTS = 60
_RATE_LIMIT_WINDOW_SECONDS = 60
_request_log: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(token: str) -> None:
    now = time.monotonic()
    window_start = now - _RATE_LIMIT_WINDOW_SECONDS
    recent = [ts for ts in _request_log[token] if ts > window_start]
    if len(recent) >= _RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for BI service token",
        )
    recent.append(now)
    _request_log[token] = recent


async def get_service_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    """Validate the `Authorization: Bearer <token>` header against BI_READONLY_TOKEN.

    Returns the token string on success (used as the rate-limit key).
    """
    expected_token = os.getenv("BI_READONLY_TOKEN")
    if not expected_token:
        logger.error("service_auth.not_configured", message="BI_READONLY_TOKEN is not set")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="BI service token is not configured",
        )

    if credentials is None or not secrets.compare_digest(credentials.credentials, expected_token):
        logger.warning("service_auth.invalid_token", path=request.url.path)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing service token",
        )

    _check_rate_limit(credentials.credentials)
    return credentials.credentials
