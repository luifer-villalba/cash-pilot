# File: src/cashpilot/api/admin.py
from datetime import UTC, datetime
import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.api.auth_helpers import require_admin
from cashpilot.api.utils import get_locale, get_translation_function
from cashpilot.core.db import get_db
from cashpilot.core.logging import get_logger
from cashpilot.core.security import hash_password
from cashpilot.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])
logger = get_logger(__name__)
templates = Jinja2Templates(directory="/app/templates")


# ===== SCHEMAS =====
class PasswordResetRequest(BaseModel):
    new_password: str | None = Field(None, min_length=8, max_length=128)
    generate: bool = False


class PasswordResetResponse(BaseModel):
    user_id: str
    username: str
    new_password: str | None = None
    message: str


class ToggleActiveRequest(BaseModel):
    is_active: bool


# ===== HELPERS =====
def generate_password(length: int = 12) -> str:
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ===== FRONTEND ROUTES =====
@router.get("/users-page", response_class=HTMLResponse)
async def users_management_page(
    request: Request,
    admin_user: User = Depends(require_admin),
):
    """Render user management page."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    return templates.TemplateResponse(
        request,
        "admin/users.html",
        {
            "current_user": admin_user,
            "locale": locale,
            "_": _,
        },
    )


# ===== API ENDPOINTS =====
@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """List all users (admin-only)."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()

    return {
        "users": [
            {
                "id": str(user.id),
                "username": user.display_name,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat(),
            }
            for user in users
        ]
    }


@router.post("/users/{user_id}/reset-password", response_model=PasswordResetResponse)
async def reset_user_password(
    user_id: str,
    request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Reset a user's password (admin-only). Returns generated password if requested."""
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Determine new password
    if request.generate:
        new_password = generate_password()
    elif request.new_password:
        new_password = request.new_password
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide new_password or set generate=true",
        )

    # Hash and update
    target_user.hashed_password = hash_password(new_password)
    target_user.updated_at = datetime.now(UTC)
    await db.commit()

    # Log event
    logger.info(
        "password.reset_by_admin",
        extra={
            "admin_user_id": str(admin_user.id),
            "admin_display_name": admin_user.display_name,
            "target_user_id": str(target_user.id),
            "target_display_name": target_user.display_name,
            "password_generated": request.generate,
        },
    )

    return PasswordResetResponse(
        user_id=str(target_user.id),
        username=target_user.display_name,
        new_password=new_password if request.generate else None,
        message="Password reset successfully",
    )


@router.patch("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: str,
    request: ToggleActiveRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Enable or disable a user account (admin-only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Prevent admin from disabling themselves
    if target_user.id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable your own account",
        )

    target_user.is_active = request.is_active
    target_user.updated_at = datetime.now(UTC)
    await db.commit()

    action = "enabled" if request.is_active else "disabled"
    logger.info(
        f"user.{action}_by_admin",
        extra={
            "admin_user_id": str(admin_user.id),
            "admin_display_name": admin_user.display_name,
            "target_user_id": str(target_user.id),
            "target_display_name": target_user.display_name,
            "is_active": request.is_active,
        },
    )

    return {
        "user_id": str(target_user.id),
        "username": target_user.display_name,
        "is_active": target_user.is_active,
        "message": f"User {action} successfully",
    }
