"""
FastAPI application factory and entrypoint.

This module follows the application factory pattern to allow:
- Multiple instances for testing
- Different configurations per environment
- Clean dependency injection
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI

from cashpilot.core.logging import configure_logging, get_logger
from cashpilot.middleware.logging import RequestIDMiddleware

# Configure logging at module level (before any loggers are used)
configure_logging()

logger = get_logger(__name__)


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
    start_time = datetime.now()
    logger.info("app.startup", message="CashPilot starting up", timestamp=start_time.isoformat())

    # Set app start time for health check uptime tracking
    from cashpilot.api.health import set_app_start_time

    set_app_start_time(start_time)

    yield  # Application runs here

    # Shutdown logic
    logger.info("app.shutdown", message="CashPilot shutting down gracefully")


def create_app() -> FastAPI:
    """Application factory for CashPilot."""
    app = FastAPI(
        title="CashPilot API",
        description="Pharmacy cash register reconciliation system",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Register global exception handlers
    from cashpilot.core.exception_handlers import register_exception_handlers

    register_exception_handlers(app)

    # Add request ID middleware (injects X-Request-ID header)
    app.add_middleware(RequestIDMiddleware)

    # Register routers
    from cashpilot.api.health import router as health_router

    app.include_router(health_router)

    from cashpilot.api.business import router as business_router

    app.include_router(business_router)

    from cashpilot.api.cash_session import router as cash_session_router

    app.include_router(cash_session_router)

    logger.info("app.configured", message="FastAPI application created successfully")

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
