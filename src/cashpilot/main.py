"""
FastAPI application factory and entrypoint.

This module follows the application factory pattern to allow:
- Multiple instances for testing
- Different configurations per environment
- Clean dependency injection
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from cashpilot.core.errors import AppError, ErrorDetail
from cashpilot.core.logging import configure_logging, get_logger
from cashpilot.middleware.logging import RequestIDMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Lifespan context manager for startup and shutdown events.

    Use this to:
    - Initialize database connections
    - Load ML models
    - Start background tasks
    - Clean up resources on shutdown
    """
    # Startup logic
    configure_logging()
    logger = get_logger(__name__)
    logger.info("app.startup", event="CashPilot starting up")

    yield  # Application runs here

    # Shutdown logic
    logger.info("app.shutdown", event="CashPilot shutting down")


def create_app() -> FastAPI:
    """Application factory for CashPilot."""
    app = FastAPI(
        title="CashPilot API",
        description="Pharmacy cash register reconciliation system",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Add request ID middleware FIRST (runs first in chain)
    app.add_middleware(RequestIDMiddleware)

    # Global exception handler for AppError
    @app.exception_handler(AppError)
    async def app_exception_handler(request: Request, exc: AppError) -> JSONResponse:
        """Handle custom app exceptions with logging."""
        logger = get_logger(__name__)
        logger.error(
            "app.error",
            error_code=exc.code,
            message=exc.message,
            details=exc.details,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_response().model_dump(exclude_none=True),
        )

    # Global exception handler for unhandled exceptions
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected errors."""
        logger = get_logger(__name__)
        logger.error(
            "app.unhandled_exception",
            error_type=type(exc).__name__,
            message=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorDetail(
                code="INTERNAL_ERROR",
                message="Internal server error",
            ).model_dump(exclude_none=True),
        )

    # Include routers
    from cashpilot.api.business import router as business_router
    from cashpilot.api.cash_session import router as cash_session_router
    from cashpilot.api.health import router as health_router

    app.include_router(health_router)
    app.include_router(business_router)
    app.include_router(cash_session_router)

    return app


def run() -> None:
    """
    Development server entrypoint.

    This function is registered in pyproject.toml [project.scripts].
    Run with: make run
    """
    uvicorn.run(
        "cashpilot.main:create_app",
        factory=True,  # calls create_app() on reload
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
    )
