# File: src/cashpilot/api/auth.py
"""Authentication endpoints and dependencies."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.api.utils import get_locale, get_translation_function
from cashpilot.core.db import get_db
from cashpilot.core.logging import get_logger
from cashpilot.core.security import verify_password
from cashpilot.models.user import User, UserRole
from cashpilot.utils.datetime import now_utc

logger = get_logger(__name__)

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="templates")

# Configurable inactivity timeout by role (seconds)
ROLE_TIMEOUTS = {
    UserRole.CASHIER: 10 * 60 * 60,  # 10 hours
    UserRole.ADMIN: 2 * 60 * 60,  # 2 hours
}


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, expired: str = None, error: str = None):
    """Show login page."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "lang": locale,
            "expired": expired == "true",
            "error": error == "true",
            "_": _,
        },
    )


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency to get current authenticated user from session."""
    # Get session safely (session middleware may not be configured)
    if not hasattr(request, "session") or not request.session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    user_role = request.session.get("user_role") if request.session else None

    # Enforce role-based inactivity timeout
    if user_role and user_role in ROLE_TIMEOUTS:
        timeout = ROLE_TIMEOUTS[user_role]
        now = now_utc()

        last_activity_raw = request.session.get("last_activity") if request.session else None

        try:
            if last_activity_raw and isinstance(last_activity_raw, str):
                # Parse ISO format string - it should include timezone info
                last_activity = datetime.fromisoformat(last_activity_raw)
                # Ensure it's timezone-aware (backward compatibility)
                if last_activity.tzinfo is None:
                    last_activity = last_activity.replace(tzinfo=timezone.utc)
            else:
                last_activity = None

        except (ValueError, TypeError):
            last_activity = None

        if last_activity and (now - last_activity) > timedelta(seconds=timeout):
            if request.session:
                request.session.clear()

            time_elapsed = now - last_activity
            logger.info(
                "auth.session_expired",
                user_id=user_id,
                role=user_role,
                timeout_seconds=timeout,
                time_elapsed_seconds=round(time_elapsed.total_seconds(), 2),
                last_activity_utc=last_activity.isoformat(),
                current_time_utc=now.isoformat(),
            )

            is_htmx = request.headers.get("HX-Request") == "true" if request.headers else False

            if is_htmx:
                raise HTTPException(
                    status_code=status.HTTP_200_OK,
                    detail="Session expired",
                    headers={"HX-Redirect": "/login?expired=true"},
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_303_SEE_OTHER,
                    detail="Session expired",
                    headers={"Location": "/login?expired=true"},
                )
        else:
            if request.session:
                request.session["last_activity"] = now.isoformat()

    try:
        if not isinstance(user_id, str):
            raise ValueError("user_id must be a string")
        user_uuid = UUID(user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user session",
        )

    stmt = select(User).where((User.id == user_uuid) & (User.is_active))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


@router.post("/login")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Login endpoint - validates credentials and creates session."""
    # Extract credentials from validated form data
    username = form_data.username
    password = form_data.password

    # Basic sanity checks for empty credentials
    if not username or not username.strip():
        logger.warning("auth.login_failed", email="invalid")
        return RedirectResponse(url="/login?error=true", status_code=303)

    if not password:
        logger.warning("auth.login_failed", email=username)
        return RedirectResponse(url="/login?error=true", status_code=303)

    stmt = select(User).where(User.email == username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        logger.warning("auth.login_failed", email=username)
        return RedirectResponse(url="/login?error=true", status_code=303)

    if not user.hashed_password:
        logger.warning("auth.login_failed", email=username)
        return RedirectResponse(url="/login?error=true", status_code=303)

    if not verify_password(password, user.hashed_password):
        logger.warning("auth.login_failed", email=username)
        return RedirectResponse(url="/login?error=true", status_code=303)

    if not user.is_active:
        logger.warning("auth.login_disabled_account", email=user.email, user_id=str(user.id))
        return RedirectResponse(url="/login?error=true", status_code=303)

    # Session should be available via SessionMiddleware, but check safely
    if not hasattr(request, "session"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session middleware not configured",
        )

    # Initialize session if it's None (shouldn't happen with SessionMiddleware, but be safe)
    if request.session is None:
        request.session = {}

    request.session["user_id"] = str(user.id)
    request.session["user_role"] = (
        user.role.value if hasattr(user.role, "value") else str(user.role)
    )
    request.session["user_display_name"] = user.display_name or ""

    if user.role in ROLE_TIMEOUTS:
        request.session["last_activity"] = now_utc().isoformat()

    logger.info(
        "auth.login_success",
        email=user.email,
        user_id=str(user.id),
        role=user.role,
    )
    return RedirectResponse(url="/", status_code=303)


@router.post("/logout")
async def logout(request: Request):
    """Logout endpoint - clears session."""
    user_id = request.session.get("user_id")
    if user_id:
        logger.info("auth.logout", user_id=user_id)

    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@router.get("/logout")
async def logout_get(request: Request):
    """Logout GET endpoint for browser compatibility."""
    return await logout(request)
