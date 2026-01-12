"""FastAPI application factory with frontend support + i18n."""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request

from cashpilot.core.logging import configure_logging, get_logger
from cashpilot.core.sentry import init_sentry
from cashpilot.utils.datetime import now_utc

configure_logging()
logger = get_logger(__name__)

# Initialize Sentry (only if DSN is set)
init_sentry()


class AdminRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect /admin and /admin/ to /admin/cash-session/list"""

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ["/admin", "/admin/"]:
            return RedirectResponse(url="/admin/cash-session/list")
        return await call_next(request)


class AuthRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect unauthenticated browser requests to login page."""

    async def dispatch(self, request: Request, call_next):
        # Skip for public routes
        public_paths = ["/login", "/logout", "/static", "/health"]
        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)

        # Check session - SessionMiddleware runs first, so session should be in scope
        session = request.scope.get("session", {})
        user_id = session.get("user_id") if session else None

        if not user_id:
            accept = request.headers.get("accept", "")
            if "text/html" in accept:
                # Browser: redirect to login
                return RedirectResponse(url="/login", status_code=303)
            else:
                # API: return 401 Unauthorized
                from fastapi.responses import JSONResponse

                return JSONResponse({"detail": "Not authenticated"}, status_code=401)

        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager for startup and shutdown events."""
    start_time = now_utc()
    logger.info("app.startup", message="CashPilot starting up", timestamp=start_time.isoformat())

    from cashpilot.api.health import set_app_start_time

    set_app_start_time(start_time)

    yield

    logger.info("app.shutdown", message="CashPilot shutting down gracefully")


def _setup_middleware(app: FastAPI, environment: str, session_secret_key: str) -> None:
    """
    Configure all middleware in correct order.
    Execution order is REVERSE of the order they are added (LIFO).
    """

    # 1. RequestIDMiddleware (Added First, Runs LAST)
    # Sets request_id in context var, which SentryContextMiddleware needs
    from cashpilot.middleware.logging import RequestIDMiddleware

    app.add_middleware(RequestIDMiddleware)

    # 2. SentryContextMiddleware (Added Second, Runs SECOND TO LAST)
    # Runs before RequestIDMiddleware, so must parse request_id from headers first
    from cashpilot.middleware.sentry import SentryContextMiddleware

    app.add_middleware(SentryContextMiddleware)

    # 3. StaticAssetHeadersMiddleware (Runs FOURTH)
    # Adds proper headers for static assets when behind proxy
    # Note: X-Forwarded-* headers are handled by Uvicorn's --proxy-headers flag
    from cashpilot.middleware.proxy import StaticAssetHeadersMiddleware

    app.add_middleware(StaticAssetHeadersMiddleware)

    # 4. AdminRedirectMiddleware (Runs THIRD)
    app.add_middleware(AdminRedirectMiddleware)

    # 5. AuthRedirectMiddleware (Runs SECOND, MUST run AFTER SessionMiddleware)
    # Skip in testing to allow dependency overrides
    if not os.getenv("TESTING"):
        app.add_middleware(AuthRedirectMiddleware)

    # 6. SessionMiddleware (Runs FIRST)
    app.add_middleware(
        SessionMiddleware,
        secret_key=session_secret_key,
        max_age=14 * 24 * 60 * 60,
        https_only=environment == "production",
        same_site="lax",
    )


def _get_static_dir() -> Path:
    """Get the static directory path based on environment."""
    # In production (Railway), use hardcoded path since __file__ points to site-packages
    # In development, calculate from __file__ location
    env = os.getenv("ENVIRONMENT") or os.getenv("RAILWAY_ENVIRONMENT", "development")
    environment = env.lower()
    is_production = environment in {"production", "prod"}

    if is_production:
        # Production: hardcoded path
        static_dir = Path("/app/static")
    else:
        # Development: calculate from __file__
        base_dir = Path(__file__).resolve().parent.parent.parent
        static_dir = base_dir / "static"

    # Allow override via environment variable
    static_env = os.getenv("STATIC_DIR")
    if static_env:
        static_dir = Path(static_env).resolve()

    return static_dir


def _get_environment_info() -> tuple[str, bool]:
    """Get environment information (name and production flag)."""
    env = os.getenv("ENVIRONMENT") or os.getenv("RAILWAY_ENVIRONMENT", "development")
    environment = env.lower()
    is_production = environment in {"production", "prod"}
    return environment, is_production


def _mount_static(app: FastAPI) -> None:
    """Register static files route handler.

    Uses a catch-all route handler instead of mount to ensure it's checked
    as a regular route. The actual fix for static files is in the exception
    handler (exception_handlers.py) which returns plain text instead of JSON
    for /static/* paths.
    """
    static_dir = _get_static_dir()

    if static_dir.exists():
        logger.info(
            "static.mounted",
            path=str(static_dir),
        )

        # Use route handler approach - register a catch-all route for /static/*
        # This ensures it's checked as a regular route and works reliably
        @app.get("/static/{file_path:path}")
        async def serve_static(file_path: str, request: Request):
            """Serve static files from the static directory."""
            from fastapi import HTTPException, status
            from fastapi.responses import FileResponse

            file_path_obj = static_dir / file_path

            # Security: prevent directory traversal and symlink attacks
            try:
                resolved_path = file_path_obj.resolve(strict=True)
                # Verify path is within static directory
                resolved_path.relative_to(static_dir.resolve())
                # Reject symlinks for additional security
                if resolved_path.is_symlink():
                    logger.warning(
                        "static.route_handler.symlink_rejected",
                        requested_path=file_path,
                        resolved_path=str(resolved_path),
                    )
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
            except (ValueError, FileNotFoundError):
                logger.warning(
                    "static.route_handler.security_violation",
                    requested_path=file_path,
                    resolved_path=str(file_path_obj.resolve()) if file_path_obj.exists() else "N/A",
                )
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

            if file_path_obj.exists() and file_path_obj.is_file():
                return FileResponse(
                    path=str(file_path_obj),
                    headers={
                        "Cache-Control": "public, max-age=31536000, immutable",
                    },
                )
            else:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    else:
        environment, is_production = _get_environment_info()
        logger.error(
            "static.missing",
            attempted_path=str(static_dir),
            cwd=os.getcwd(),
            environment=environment,
            file_location=str(Path(__file__).resolve()),
        )

        if is_production:
            raise RuntimeError(f"Static directory not found: {static_dir}")
        else:
            logger.warning(
                "static.missing.non_production",
                message="Continuing without static files in non-production",
            )


def _register_routers(app: FastAPI) -> None:
    """Register all API and frontend routers."""
    # Core/Health
    from cashpilot.api.health import router as health_router

    app.include_router(health_router)

    # Frontend (Dashboard & Auth)
    from cashpilot.api.auth import router as auth_router
    from cashpilot.api.routes import settings
    from cashpilot.api.routes.dashboard import router as dashboard_router

    app.include_router(dashboard_router)
    app.include_router(auth_router)
    app.include_router(settings.router)

    # Cash Sessions (UI)
    from cashpilot.api.routes.line_items import router as line_items_router
    from cashpilot.api.routes.sessions import router as sessions_router
    from cashpilot.api.routes.sessions_edit import router as sessions_edit_router

    app.include_router(sessions_router)
    app.include_router(sessions_edit_router)
    app.include_router(line_items_router)

    # Businesses (UI)
    from cashpilot.api.routes.businesses import router as businesses_router

    app.include_router(businesses_router)

    # Reports (UI + API)
    from cashpilot.api.daily_revenue import router as daily_revenue_router
    from cashpilot.api.monthly_trend import router as monthly_trend_router
    from cashpilot.api.routes.business_stats import router as business_stats_router
    from cashpilot.api.routes.reports import router as reports_router
    from cashpilot.api.weekly_trend import router as weekly_trend_router

    app.include_router(daily_revenue_router)
    app.include_router(weekly_trend_router)
    app.include_router(monthly_trend_router)
    app.include_router(reports_router)
    app.include_router(business_stats_router)

    # Admin (UI + API)
    from cashpilot.api.admin import router as admin_router

    app.include_router(admin_router)

    # API endpoints
    from cashpilot.api.business import router as business_api_router
    from cashpilot.api.cash_session import router as cash_session_router
    from cashpilot.api.cash_session_audit import router as cash_session_audit_router
    from cashpilot.api.cash_session_edit import router as cash_session_edit_router
    from cashpilot.api.export_sessions import router as export_sessions_router
    from cashpilot.api.reconciliation import router as reconciliation_router
    from cashpilot.api.user import router as user_router
    from cashpilot.api.utils import router as utils_router

    app.include_router(utils_router)
    app.include_router(business_api_router)
    app.include_router(cash_session_router)
    app.include_router(cash_session_edit_router)
    app.include_router(cash_session_audit_router)
    app.include_router(reconciliation_router)
    app.include_router(user_router)
    app.include_router(export_sessions_router)


def create_app() -> FastAPI:
    """Application factory for CashPilot."""
    # Get root_path from environment (Railway/Cloudflare may set this)
    root_path = os.getenv("RAILWAY_STATIC_URL", "").rstrip("/") or os.getenv("ROOT_PATH", "")

    app = FastAPI(
        title="CashPilot API",
        description="Business cash register reconciliation system",
        version="0.1.0",
        lifespan=lifespan,
        root_path=root_path if root_path else None,
    )

    session_secret_key = os.getenv("SESSION_SECRET_KEY", "dev-secret-key-change-in-production")
    environment = os.getenv("ENVIRONMENT", "development")

    # Register static files route handler before exception handlers
    # The actual fix is in exception_handlers.py which returns plain text for /static/* paths
    _mount_static(app)

    from cashpilot.core.exception_handlers import register_exception_handlers

    register_exception_handlers(app)

    _setup_middleware(app, environment, session_secret_key)
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
