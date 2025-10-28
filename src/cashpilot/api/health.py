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

import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.core.db import get_db

router = APIRouter(tags=["health"])

# Global app start time (set in lifespan)
_app_start_time: datetime | None = None


def set_app_start_time(start_time: datetime) -> None:
    """Called by lifespan to track when app started."""
    global _app_start_time
    _app_start_time = start_time


def get_uptime_seconds() -> int:
    """Calculate seconds since app start."""
    if _app_start_time is None:
        return 0
    return int((datetime.now() - _app_start_time).total_seconds())


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
    status_code=status.HTTP_200_OK,
    summary="Enhanced health check",
    description=(
        "Returns API health status including uptime and dependency checks. "
        "Returns 200 regardless of degraded dependencies (for graceful degradation)."
    ),
)
async def health_check(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """
    Enhanced health check endpoint.

    Returns:
        - status: "ok" if all checks pass, "degraded" if some fail
        - uptime_seconds: how long app has been running
        - checks: detailed status of each dependency

    Example response (healthy):
        {
            "status": "ok",
            "uptime_seconds": 3600,
            "checks": {
                "database": {"status": "ok", "response_time_ms": 5}
            }
        }

    Example response (degraded):
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

    return JSONResponse(
        content=response,
        status_code=status.HTTP_200_OK,
    )
