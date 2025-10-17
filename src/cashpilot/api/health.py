"""
Health check endpoint for monitoring and orchestration.

Used by:
- Docker health checks
- Kubernetes liveness/readiness probes
- Load balancers
- Monitoring systems (Datadog, New Relic, etc.)
"""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Returns API health status. Use for monitoring and orchestration.",
)
async def health_check() -> JSONResponse:
    """
    Simple health check endpoint.

    Returns:
        JSON with status key set to "ok"

    Future enhancements:
    - Check database connectivity
    - Verify external service dependencies
    - Return detailed subsystem status
    """
    return JSONResponse(
        content={"status": "ok"},
        status_code=status.HTTP_200_OK,
    )
