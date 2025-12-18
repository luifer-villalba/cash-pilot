# File: src/cashpilot/core/exception_handlers.py
"""Global exception handlers for FastAPI."""

from fastapi import Request, status
from fastapi.responses import JSONResponse, RedirectResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from cashpilot.api.auth import logger
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


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with redirect support for session expiration."""

    # Handle 303 redirects (session expiration for regular requests)
    if (
        exc.status_code == status.HTTP_303_SEE_OTHER
        and hasattr(exc, "headers")
        and exc.headers
        and "Location" in exc.headers
    ):
        return RedirectResponse(url=exc.headers["Location"], status_code=303)

    # Handle HTMX redirects (session expiration for HTMX requests)
    if (
        exc.status_code == status.HTTP_200_OK
        and hasattr(exc, "headers")
        and exc.headers
        and "HX-Redirect" in exc.headers
    ):
        return Response(status_code=200, headers={"HX-Redirect": exc.headers["HX-Redirect"]})

    # Default: log and return JSON
    logger.error(
        "http_exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


def register_exception_handlers(app) -> None:
    """Register all custom exception handlers with FastAPI app."""
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
