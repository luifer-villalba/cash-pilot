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


def _setup_middleware(app: FastAPI, environment: str, session_secret_key: str) -> None:
    """Configure all middleware in correct order."""
    # Add middleware in reverse order (last added = first executed)
    # RequestIDMiddleware LAST so it runs FIRST
    app.add_middleware(
        SessionMiddleware,
        secret_key=session_secret_key,
        max_age=14 * 24 * 60 * 60,
        https_only=environment == "production",
        same_site="lax",
    )
    app.add_middleware(AdminRedirectMiddleware)

    from cashpilot.middleware.logging import RequestIDMiddleware

    app.add_middleware(RequestIDMiddleware)


def _mount_static(app: FastAPI) -> None:
    """Mount static files directory."""
    static_dir = Path(os.getenv("STATIC_DIR", "static")).resolve()
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    else:
        logger.warning(f"Static directory not found: {static_dir}")


def _register_routers(app: FastAPI) -> None:
    """Register all API and frontend routers."""
    # Core/Health
    from cashpilot.api.health import router as health_router

    app.include_router(health_router)

    # Frontend (Dashboard & Auth)
    # Frontend (Dashboard & Auth)
    from cashpilot.api.auth import router as auth_router
    from cashpilot.api.routes import admin, settings
    from cashpilot.api.routes.dashboard import router as dashboard_router

    app.include_router(dashboard_router)
    app.include_router(auth_router)
    app.include_router(settings.router)
    app.include_router(admin.router)
    app.include_router(auth_router)
    app.include_router(settings.router)

    # Cash Sessions (UI)
    from cashpilot.api.routes.sessions import router as sessions_router
    from cashpilot.api.routes.sessions_edit import router as sessions_edit_router

    app.include_router(sessions_router)
    app.include_router(sessions_edit_router)

    # Businesses (UI)
    from cashpilot.api.routes.businesses import router as businesses_router

    app.include_router(businesses_router)

    # API endpoints
    from cashpilot.api.business import router as business_api_router
    from cashpilot.api.cash_session import router as cash_session_router
    from cashpilot.api.cash_session_audit import router as cash_session_audit_router
    from cashpilot.api.cash_session_edit import router as cash_session_edit_router
    from cashpilot.api.utils import router as utils_router

    app.include_router(utils_router)
    app.include_router(business_api_router)
    app.include_router(cash_session_router)
    app.include_router(cash_session_edit_router)
    app.include_router(cash_session_audit_router)


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

    session_secret_key = os.getenv("SESSION_SECRET_KEY", "dev-secret-key-change-in-production")
    environment = os.getenv("ENVIRONMENT", "development")

    _setup_middleware(app, environment, session_secret_key)
    _mount_static(app)
    _register_routers(app)

    session_secret_key = os.getenv("SESSION_SECRET_KEY", "dev-secret-key-change-in-production")
    environment = os.getenv("ENVIRONMENT", "development")

    _setup_middleware(app, environment, session_secret_key)
    _mount_static(app)
    _register_routers(app)

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
