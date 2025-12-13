"""Authentication endpoints and dependencies."""

from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from cashpilot.core.db import get_db
from cashpilot.core.logging import get_logger
from cashpilot.core.security import verify_password
from cashpilot.models.user import User

logger = get_logger(__name__)

router = APIRouter(tags=["auth"])


# Configurable inactivity timeout for CASHIER role (seconds)
CASHIER_TIMEOUT = 30 * 60


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency to get current authenticated user from session."""
    user_id = request.session.get("user_id")
    user_role = request.session.get("user_role")

    # Enforce role-based inactivity timeout for cashiers only
    if user_id and user_role == "CASHIER":
        now = datetime.now()
        last_activity_raw = request.session.get("last_activity")
        try:
            last_activity = datetime.fromisoformat(last_activity_raw) if last_activity_raw else None
        except Exception:
            last_activity = None

        if last_activity and (now - last_activity) > timedelta(seconds=CASHIER_TIMEOUT):
            # Expired: clear session and redirect to login with message
            request.session.clear()
            raise HTTPException(
                status_code=302,
                detail="Session expired",
                headers={"Location": "/login?expired=1"},
            )
        else:
            # Refresh last_activity on each authenticated request
            request.session["last_activity"] = now.isoformat()

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        user_uuid = UUID(user_id)
    except ValueError:
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
    stmt = select(User).where(User.email == form_data.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning("auth.login_failed", email=form_data.username)
        return RedirectResponse(url="/login?error=1", status_code=302)

    if not user.is_active:
        logger.warning("auth.login_disabled_account", email=user.email, user_id=str(user.id))
        return RedirectResponse(
            url="/login?error=disabled", status_code=302
        )  # ← Changed from HTTPException

    # Store user_id and role in session
    request.session["user_id"] = str(user.id)
    request.session["user_role"] = user.role
    request.session["user_display_name"] = user.display_name
    # Set last_activity only for cashier role
    if user.role == "CASHIER":
        request.session["last_activity"] = datetime.now().isoformat()
    logger.info(
        "auth.login_success",
        email=user.email,
        user_id=str(user.id),
        role=user.role,
    )
    return RedirectResponse(url="/", status_code=302)


@router.post("/logout")
async def logout(request: Request):
    """Logout endpoint - clears session."""
    user_id = request.session.get("user_id")
    if user_id:
        logger.info("auth.logout", user_id=user_id)

    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)


@router.get("/logout")
async def logout_get(request: Request):
    """Logout GET endpoint for browser compatibility."""
    return await logout(request)
