"""Authentication endpoints and dependencies."""

from datetime import datetime, timedelta, timezone
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
from cashpilot.models.user import User, UserRole
from cashpilot.utils.datetime import now_utc_naive # <--- ADDED IMPORT

logger = get_logger(__name__)

router = APIRouter(tags=["auth"])


# Configurable inactivity timeout by role (seconds)
ROLE_TIMEOUTS = {
    UserRole.CASHIER: 30 * 60,  # 30 minutes
    UserRole.ADMIN: 2 * 60 * 60,  # 2 hours
}


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency to get current authenticated user from session."""
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    user_role = request.session.get("user_role")

    # Enforce role-based inactivity timeout for roles with configured timeouts
    if user_role in ROLE_TIMEOUTS:
        timeout = ROLE_TIMEOUTS[user_role]
        # CHANGE: Use now_utc_naive() instead of datetime.now(timezone.utc)
        now_naive = now_utc_naive() # <--- MODIFIED

        last_activity_raw = request.session.get("last_activity")

        try:
            # Note: We continue to use datetime.fromisoformat which handles the ISO string correctly.
            last_activity_naive = datetime.fromisoformat(last_activity_raw) if last_activity_raw else None

            # The session value is stored as naive UTC (now_utc_naive().isoformat() or datetime.now(timezone.utc).isoformat()).
            # The issue with old sessions having naive values is still relevant.
            # We must ensure both `now` and `last_activity` are comparable (either both naive or both timezone-aware)
            # to calculate the timedelta. Since `now_utc_naive()` returns naive, we should convert both to timezone-aware UTC
            # for *robust comparison*, especially if the stored `last_activity` *might* have been tz-aware in the past, or if we want to
            # strictly follow time rules for subtraction.

            # For comparison: Convert naive times to aware UTC for accurate subtraction
            now = now_naive.replace(tzinfo=timezone.utc) # <--- MODIFIED

            if last_activity_naive:
                # Ensure it's treated as UTC for comparison, whether it was stored naive or maybe had a timezone string
                last_activity = last_activity_naive.replace(tzinfo=timezone.utc)
            else:
                last_activity = None

        except (ValueError, TypeError):
            last_activity = None

        if last_activity and (now - last_activity) > timedelta(seconds=timeout): # Comparison remains the same
            # Expired: clear session and redirect to login with message
            request.session.clear()

            # --- START DEBUGGER CODE ---
            # 💡 SESSION EXPIRATION DEBUGGER LOGGING
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
            # --- END DEBUGGER CODE ---

            # Detect if HTMX request
            is_htmx = request.headers.get("HX-Request") == "true"

            if is_htmx:
                # HTMX requires HX-Redirect header
                raise HTTPException(
                    status_code=status.HTTP_200_OK,
                    detail="Session expired",
                    headers={"HX-Redirect": "/login?expired=1"},
                )
            else:
                # Regular request: use 303 See Other
                raise HTTPException(
                    status_code=status.HTTP_303_SEE_OTHER,
                    detail="Session expired",
                    headers={"Location": "/login?expired=1"},
                )
        else:
            # Refresh last_activity on each authenticated request
            # Store NAIVE time's ISO format
            request.session["last_activity"] = now_naive.isoformat() # <--- MODIFIED

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
        return RedirectResponse(url="/login?error=disabled", status_code=302)

    # Store user_id and role in session
    request.session["user_id"] = str(user.id)
    request.session["user_role"] = user.role
    request.session["user_display_name"] = user.display_name
    # Set last_activity for roles with configured timeouts
    if user.role in ROLE_TIMEOUTS:
        # CHANGE: Use now_utc_naive() instead of datetime.now(timezone.utc)
        request.session["last_activity"] = now_utc_naive().isoformat() # <--- MODIFIED

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
