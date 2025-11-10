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
from fastapi.responses import RedirectResponse
from sqladmin import Admin
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from cashpilot.core.db import engine
from cashpilot.core.logging import configure_logging, get_logger
from cashpilot.middleware.logging import RequestIDMiddleware

configure_logging()
logger = get_logger(__name__)


class AdminRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect /admin and /admin/ to /admin/cash-session/list"""

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ["/admin", "/admin/"]:
            return RedirectResponse(url="/admin/cash-session/list")
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager for startup and shutdown events."""
    start_time = datetime.now()
    logger.info("app.startup", message="CashPilot starting up", timestamp=start_time.isoformat())

    from cashpilot.api.health import set_app_start_time

    set_app_start_time(start_time)

    yield

    logger.info("app.shutdown", message="CashPilot shutting down gracefully")


def create_app() -> FastAPI:
    """Application factory for CashPilot."""
    app = FastAPI(
        title="CashPilot API",
        description="Pharmacy cash register reconciliation system",
        version="0.1.0",
        lifespan=lifespan,
    )

    from cashpilot.core.exception_handlers import register_exception_handlers

    register_exception_handlers(app)

    # Add admin redirect middleware FIRST
    app.add_middleware(AdminRedirectMiddleware)
    app.add_middleware(RequestIDMiddleware)

    from cashpilot.api.health import router as health_router

    app.include_router(health_router)

    from cashpilot.api.business import router as business_router

    app.include_router(business_router)

    from cashpilot.api.cash_session import router as cash_session_router

    app.include_router(cash_session_router)

    # Setup SQLAdmin
    from cashpilot.admin import BusinessAdmin, CashSessionAdmin

    admin = Admin(app, engine, title="CashPilot Admin", base_url="/admin")
    admin.add_view(CashSessionAdmin)
    admin.add_view(BusinessAdmin)

    logger.info("app.configured", message="FastAPI application created successfully")

    return app


def run() -> None:
    """Development server entrypoint."""
    uvicorn.run(
        "cashpilot.main:create_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
