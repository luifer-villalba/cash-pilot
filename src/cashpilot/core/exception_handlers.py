# File: src/cashpilot/core/exception_handlers.py
"""Global exception handlers for FastAPI."""

from fastapi import Request, status
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse, Response
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

    # DEBUG: Log all exceptions to trace static file requests
    logger.info(
        "exception_handler.called",
        path=request.url.path,
        status_code=exc.status_code,
        detail=exc.detail,
        method=request.method,
        is_static=request.url.path.startswith("/static"),
    )

    # CRITICAL: Skip JSON conversion for static file paths
    # StaticFiles should handle its own 404s with proper responses
    # If we get here for a static file path, it means the mount didn't match
    # Return a proper 404 response (not JSON) to allow browsers to handle it correctly
    if request.url.path.startswith("/static"):
        logger.warning(
            "exception_handler.static_path_404",
            path=request.url.path,
            status_code=exc.status_code,
            detail=exc.detail,
            message=(
                "Static file request reached exception handler - "
                "route handler may not have matched"
            ),
        )
        # Return plain text 404 instead of JSON for static file requests
        # This allows the browser to handle the 404 properly
        return PlainTextResponse(
            content="Not Found",
            status_code=status.HTTP_404_NOT_FOUND,
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )

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
