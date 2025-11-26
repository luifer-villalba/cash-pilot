# File: src/cashpilot/api/routes/admin.py
"""Admin endpoints for user management."""

import secrets
import string
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from cashpilot.api.auth_helpers import require_admin
from cashpilot.api.utils import get_locale, get_translation_function
from cashpilot.core.db import get_db
from cashpilot.core.logging import get_logger
from cashpilot.core.security import hash_password
from cashpilot.models.user import User, UserRole
from cashpilot.models.user_schemas import UserCreate

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

TEMPLATES_DIR = Path("/app/templates")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def generate_password() -> str:
    """Generate random 8-character alphanumeric password."""
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(8))


@router.get("/users", response_class=HTMLResponse)
async def users_list(
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Render user management page."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    # Fetch all users
    stmt = select(User).order_by(User.created_at.desc())
    result = await db.execute(stmt)
    users = result.scalars().all()

    error = request.query_params.get("error")
    success = request.query_params.get("success")

    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "current_user": current_user,
            "_": _,
            "users": users,
            "error": error,
            "success": success,
        },
    )


@router.post("/reset-password/{user_id}")
async def reset_password(
    user_id: str,
    password: str = Form(None, min_length=1),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Reset user password (admin-only)."""
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        return RedirectResponse(
            url="/admin/users?error=invalid_user_id",
            status_code=302,
        )

    stmt = select(User).where(User.id == user_uuid)
    result = await db.execute(stmt)
    target_user = result.scalar_one_or_none()

    if not target_user:
        return RedirectResponse(
            url="/admin/users?error=user_not_found",
            status_code=302,
        )

    # Generate or use provided password
    new_password = password if password else generate_password()

    # Hash and update
    target_user.hashed_password = hash_password(new_password)
    await db.commit()

    logger.info(
        "password.reset_by_admin",
        admin_id=str(current_user.id),
        admin_email=current_user.email,
        target_user_id=str(target_user.id),
        target_user_email=target_user.email,
    )

    # Return success with password in query (for modal display)
    return RedirectResponse(
        url=f"/admin/users?success=password_reset&user_id={user_id}&password={new_password}",
        status_code=302,
    )


@router.post("/users/{user_id}/disable")
async def disable_user(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Disable a user (admin-only, cannot disable admins or yourself)."""
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        return RedirectResponse(
            url="/admin/users?error=invalid_user_id",
            status_code=302,
        )

    # Prevent disabling yourself
    if user_uuid == current_user.id:
        logger.warning(
            "user.self_disable_attempt",
            admin_id=str(current_user.id),
            admin_email=current_user.email,
        )
        return RedirectResponse(
            url="/admin/users?error=cannot_disable_self",
            status_code=302,
        )

    stmt = select(User).where(User.id == user_uuid)
    result = await db.execute(stmt)
    target_user = result.scalar_one_or_none()

    if not target_user:
        return RedirectResponse(
            url="/admin/users?error=user_not_found",
            status_code=302,
        )

    # Prevent disabling other admins
    if target_user.role == UserRole.ADMIN:
        logger.warning(
            "user.admin_disable_attempt",
            admin_id=str(current_user.id),
            admin_email=current_user.email,
            target_admin_id=str(target_user.id),
            target_admin_email=target_user.email,
        )
        return RedirectResponse(
            url="/admin/users?error=cannot_disable_admin",
            status_code=302,
        )

    target_user.is_active = False
    await db.commit()

    logger.info(
        "user.disabled_by_admin",
        admin_id=str(current_user.id),
        admin_email=current_user.email,
        target_user_id=str(target_user.id),
        target_user_email=target_user.email,
    )

    return RedirectResponse(
        url="/admin/users?success=user_disabled",
        status_code=302,
    )


@router.post("/users/{user_id}/enable")
async def enable_user(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Enable a user (admin-only)."""
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        return RedirectResponse(
            url="/admin/users?error=invalid_user_id",
            status_code=302,
        )

    stmt = select(User).where(User.id == user_uuid)
    result = await db.execute(stmt)
    target_user = result.scalar_one_or_none()

    if not target_user:
        return RedirectResponse(
            url="/admin/users?error=user_not_found",
            status_code=302,
        )

    target_user.is_active = True
    await db.commit()

    logger.info(
        "user.enabled_by_admin",
        admin_id=str(current_user.id),
        admin_email=current_user.email,
        target_user_id=str(target_user.id),
        target_user_email=target_user.email,
    )

    return RedirectResponse(
        url="/admin/users?success=user_enabled",
        status_code=302,
    )


@router.get("/users/create", response_class=HTMLResponse)
async def create_user_form(
    request: Request,
    current_user: User = Depends(require_admin),
):
    """Render create user form."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    error = request.query_params.get("error")

    return templates.TemplateResponse(
        "admin/create_user.html",
        {
            "request": request,
            "current_user": current_user,
            "_": _,
            "error": error,
        },
    )


@router.post("/users")
async def create_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    role: str = Form("CASHIER"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create new user (admin-only)."""
    try:
        # Validate user data
        user_data = UserCreate(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=role,
        )

        # Check if email exists
        stmt = select(User).where(User.email == user_data.email)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            return RedirectResponse(
                url="/admin/users/create?error=email_exists",
                status_code=302,
            )

        # Create user
        new_user = User(
            email=user_data.email,
            hashed_password=hash_password(user_data.password),
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role=user_data.role,
        )
        db.add(new_user)
        await db.commit()

        logger.info(
            "user.created_by_admin",
            admin_id=str(current_user.id),
            admin_email=current_user.email,
            new_user_id=str(new_user.id),
            new_user_email=new_user.email,
        )

        return RedirectResponse(url="/admin/users?success=user_created", status_code=302)

    except ValueError as e:
        logger.warning(
            "user.create_validation_failed",
            admin_id=str(current_user.id),
            error=str(e),
        )
        return RedirectResponse(
            url="/admin/users/create?error=validation_failed",
            status_code=302,
        )
    except Exception as e:
        logger.error(
            "user.create_failed",
            admin_id=str(current_user.id),
            error=str(e),
        )
        return RedirectResponse(
            url="/admin/users/create?error=creation_failed",
            status_code=302,
        )
