# File: src/cashpilot/main.py
"""FastAPI application factory with frontend support + i18n."""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request

from cashpilot.core.logging import configure_logging, get_logger

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

    # Add SessionMiddleware BEFORE other middleware
    session_secret_key = os.getenv("SESSION_SECRET_KEY", "dev-secret-key-change-in-production")
    environment = os.getenv("ENVIRONMENT", "development")

    app.add_middleware(
        SessionMiddleware,
        secret_key=session_secret_key,
        max_age=14 * 24 * 60 * 60,  # 14 days
        https_only=environment == "production",
        same_site="lax",
    )

    # Add other middleware
    app.add_middleware(AdminRedirectMiddleware)
    from cashpilot.middleware.logging import RequestIDMiddleware

    app.add_middleware(RequestIDMiddleware)

    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Include routers
    from cashpilot.api.health import router as health_router

    app.include_router(health_router)

    from cashpilot.api.frontend import router as frontend_router

    app.include_router(frontend_router)

    from cashpilot.api.business import router as business_router

    app.include_router(business_router)

    from cashpilot.api.cash_session import router as cash_session_router

    app.include_router(cash_session_router)

    from cashpilot.api.auth import router as auth_router

    app.include_router(auth_router)

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
