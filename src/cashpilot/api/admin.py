# File: src/cashpilot/api/admin.py
import secrets
import string
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cashpilot.api.auth_helpers import require_admin
from cashpilot.api.utils import get_locale, get_translation_function
from cashpilot.core.db import get_db
from cashpilot.core.logging import get_logger
from cashpilot.core.security import hash_password
from cashpilot.models.business import Business
from cashpilot.models.user import User
from cashpilot.models.user_business import UserBusiness

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


class AssignBusinessesRequest(BaseModel):
    business_ids: list[UUID]


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
    """List all users with their assigned businesses (admin-only)."""
    result = await db.execute(
        select(User).options(selectinload(User.businesses)).order_by(User.created_at.desc())
    )
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
                "businesses": [
                    {
                        "id": str(business.id),
                        "name": business.name,
                        "is_active": business.is_active,
                    }
                    for business in user.businesses
                ],
            }
            for user in users
        ]
    }


@router.get("/businesses")
async def list_businesses_for_assignment(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """List all active businesses for assignment dropdown (admin-only)."""
    result = await db.execute(
        select(Business).where(Business.is_active == True).order_by(Business.name)  # noqa: E712
    )
    businesses = result.scalars().all()

    return {
        "businesses": [
            {
                "id": str(business.id),
                "name": business.name,
            }
            for business in businesses
        ]
    }


@router.post("/users/{user_id}/businesses")
async def assign_businesses(
    user_id: UUID,
    request: AssignBusinessesRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Assign multiple businesses to a user (admin-only)."""
    # Verify user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify all businesses exist and are active
    if request.business_ids:
        business_result = await db.execute(
            select(Business).where(
                Business.id.in_(request.business_ids),
                Business.is_active == True,  # noqa: E712
            )
        )
        businesses = business_result.scalars().all()
        if len(businesses) != len(request.business_ids):
            raise HTTPException(
                status_code=404,
                detail="One or more businesses not found or inactive",
            )

    # Remove existing assignments not in the new list
    if request.business_ids:
        delete_stmt = delete(UserBusiness).where(
            UserBusiness.user_id == user_id, ~UserBusiness.business_id.in_(request.business_ids)
        )
    else:
        delete_stmt = delete(UserBusiness).where(UserBusiness.user_id == user_id)

    await db.execute(delete_stmt)

    # Add new assignments (skip if already exists)
    for business_id in request.business_ids:
        existing = await db.execute(
            select(UserBusiness).where(
                UserBusiness.user_id == user_id,
                UserBusiness.business_id == business_id,
            )
        )
        if not existing.scalar_one_or_none():
            assignment = UserBusiness(user_id=user_id, business_id=business_id)
            db.add(assignment)

    await db.commit()

    # Refresh and return updated user with businesses
    await db.refresh(user, ["businesses"])

    logger.info(
        "user.businesses.assigned",
        user_id=str(user_id),
        business_ids=[str(bid) for bid in request.business_ids],
        assigned_by=str(admin_user.id),
    )

    return {
        "user_id": str(user.id),
        "username": user.display_name,
        "businesses": [
            {
                "id": str(business.id),
                "name": business.name,
                "is_active": business.is_active,
            }
            for business in user.businesses
        ],
    }


@router.delete("/users/{user_id}/businesses/{business_id}")
async def unassign_business(
    user_id: UUID,
    business_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Remove a business assignment from a user (admin-only)."""
    # Verify user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Delete the specific assignment
    result = await db.execute(
        select(UserBusiness).where(
            UserBusiness.user_id == user_id,
            UserBusiness.business_id == business_id,
        )
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Business assignment not found")

    await db.delete(assignment)
    await db.commit()

    logger.info(
        "user.business.unassigned",
        user_id=str(user_id),
        business_id=str(business_id),
        unassigned_by=str(admin_user.id),
    )

    return {"message": "Business unassigned successfully"}


@router.post("/users/{user_id}/reset-password", response_model=PasswordResetResponse)
async def reset_user_password(
    user_id: str,
    request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Reset a user's password (admin-only). Returns generated password if requested."""
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Generate or use provided password
    if request.generate:
        new_password = generate_password()
    elif request.new_password:
        new_password = request.new_password
    else:
        raise HTTPException(
            status_code=400,
            detail="Must provide new_password or set generate=true",
        )

    # Update password
    user.hashed_password = hash_password(new_password)
    db.add(user)
    await db.commit()

    logger.info(
        "user.password.reset",
        user_id=user_id,
        reset_by=str(admin_user.id),
        generated=request.generate,
    )

    return PasswordResetResponse(
        user_id=user_id,
        username=user.display_name,
        new_password=new_password if request.generate else None,
        message="Password reset successfully",
    )


@router.post("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: str,
    request: ToggleActiveRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Toggle user active status (admin-only)."""
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = request.is_active
    db.add(user)
    await db.commit()

    logger.info(
        "user.active.toggled",
        user_id=user_id,
        is_active=request.is_active,
        toggled_by=str(admin_user.id),
    )

    return {
        "user_id": user_id,
        "username": user.display_name,
        "is_active": user.is_active,
    }
