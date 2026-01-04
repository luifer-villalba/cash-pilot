"""
Health check endpoint for monitoring and orchestration.

Enhanced with:
- Database connectivity check
- Uptime tracking
- Detailed dependency status

Used by:
- Docker health checks
- Kubernetes liveness/readiness probes
- Load balancers
- Monitoring systems (Datadog, New Relic, etc.)
"""

import os
import time
from datetime import datetime
from typing import Any

import sentry_sdk
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.core.db import get_db
from cashpilot.core.logging import get_logger, get_request_id
from cashpilot.utils.datetime import now_utc

router = APIRouter(tags=["health"])
logger = get_logger(__name__)

# Global app start time (set in lifespan)
_app_start_time: datetime | None = None


def set_app_start_time(start_time: datetime) -> None:
    """Called by lifespan to track when app started.

    Args:
        start_time: Timezone-aware datetime (should use now_utc()).
                   If naive, will be converted to UTC.
    """
    global _app_start_time
    # Ensure timezone-aware (convert naive to UTC if needed)
    if start_time.tzinfo is None:
        from datetime import timezone

        _app_start_time = start_time.replace(tzinfo=timezone.utc)
    else:
        _app_start_time = start_time


def get_uptime_seconds() -> int:
    """Calculate seconds since app start."""
    if _app_start_time is None:
        return 0
    return int((now_utc() - _app_start_time).total_seconds())


async def check_database(db: AsyncSession) -> dict[str, Any]:
    """
    Check database connectivity with timeout.

    Returns: {"status": "ok"|"down", "response_time_ms": N, "error": str (if down)}
    """
    start = time.time()
    try:
        # Simple connectivity check
        await db.execute(text("SELECT 1"))
        response_time_ms = int((time.time() - start) * 1000)
        return {
            "status": "ok",
            "response_time_ms": response_time_ms,
        }
    except Exception as e:
        response_time_ms = int((time.time() - start) * 1000)
        return {
            "status": "down",
            "response_time_ms": response_time_ms,
            "error": str(type(e).__name__),
        }


@router.get(
    "/health",
    summary="Health check endpoint",
    description=(
        "Returns API health status including uptime and dependency checks. "
        "Returns 200 OK only if PostgreSQL connection is active, otherwise 503 Service Unavailable."
    ),
)
async def health_check(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """
    Health check endpoint.

    Returns 200 OK if PostgreSQL connection is active, otherwise 503 Service Unavailable.

    Returns:
        - status: "ok" if all checks pass, "degraded" if some fail
        - uptime_seconds: how long app has been running
        - checks: detailed status of each dependency

    Example response (healthy - 200 OK):
        {
            "status": "ok",
            "uptime_seconds": 3600,
            "checks": {
                "database": {"status": "ok", "response_time_ms": 5}
            }
        }

    Example response (unhealthy - 503 Service Unavailable):
        {
            "status": "degraded",
            "uptime_seconds": 3600,
            "checks": {
                "database": {
                    "status": "down",
                    "response_time_ms": 1000,
                    "error": "OperationalError"
                }
            }
        }
    """
    uptime = get_uptime_seconds()
    db_check = await check_database(db)

    # Determine overall status
    overall_status = "ok" if db_check["status"] == "ok" else "degraded"

    response = {
        "status": overall_status,
        "uptime_seconds": uptime,
        "checks": {
            "database": db_check,
        },
    }

    # Return 200 OK only if PostgreSQL connection is active
    status_code = (
        status.HTTP_200_OK if db_check["status"] == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return JSONResponse(
        content=response,
        status_code=status_code,
    )


@router.get(
    "/test-sentry",
    summary="Test Sentry error tracking (development only)",
    description=(
        "Test endpoint to verify Sentry error tracking is working. "
        "Raises a test exception that should appear in Sentry dashboard within 5 seconds. "
        "⚠️ WARNING: This endpoint intentionally raises an exception. Use only for testing! "
        "⚠️ Only available in development environment."
    ),
)
async def test_sentry(
    request: Request,
) -> None:
    """
    Test endpoint to verify Sentry error tracking.

    **Development only** - Returns 404 in production for security.

    This endpoint intentionally raises a test exception to verify:
    1. Sentry is initialized and capturing errors
    2. Structured context (request_id, user_id) is included
    3. Errors appear in Sentry dashboard within 5 seconds

    ⚠️ WARNING: This will create an error event in Sentry. Clean up test exceptions before demo.

    Example usage (development only):
        curl http://localhost:8000/test-sentry

    The exception will include:
    - request_id: From X-Request-ID header or generated UUID
    - user_id: From session (if authenticated)
    - Additional context: method, path, etc.
    """
    # Restrict to development/test environments only (case-insensitive)
    environment = os.getenv("ENVIRONMENT", "development").lower()
    if environment not in {"development", "dev", "test", "testing"}:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )

    request_id = get_request_id()
    user_id = (
        request.scope.get("session", {}).get("user_id") if request.scope.get("session") else None
    )

    # Log before raising exception (to verify logging integration)
    logger.warning(
        "sentry.test",
        message="Test exception about to be raised for Sentry verification",
        request_id=request_id,
        user_id=user_id,
        path=request.url.path,
    )

    # Set additional context for this test exception (Sentry SDK 2.x compatible)
    # Use isolation scope to ensure test-specific tags don't leak to other errors
    with sentry_sdk.isolation_scope() as scope:
        scope.set_tag("test_endpoint", "true")
        scope.set_context(
            "test",
            {
                "purpose": "Verify Sentry error tracking",
                "request_id": request_id,
                "user_id": user_id,
            },
        )

        # Raise a test exception with context
        # FastAPI integration will automatically capture it
        raise RuntimeError(
            f"Sentry test exception - Request ID: {request_id}, "
            f"User ID: {user_id or 'anonymous'}, "
            f"Path: {request.url.path}"
        )
