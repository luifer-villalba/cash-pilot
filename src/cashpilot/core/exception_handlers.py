"""Global exception handlers for FastAPI."""

from fastapi import Request
from fastapi.responses import JSONResponse

from cashpilot.core.errors import AppError


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """
    Handle all AppError exceptions and convert to JSON response.

    Returns standardized error format:
    {
        "code": "NOT_FOUND",
        "message": "Business with ID xyz not found",
        "details": {"resource": "Business", "resource_id": "xyz"}
    }
    """
    error_response = exc.to_response()
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(exclude_none=True),
    )


def register_exception_handlers(app) -> None:
    """Register all custom exception handlers with FastAPI app."""
    app.add_exception_handler(AppError, app_error_handler)
