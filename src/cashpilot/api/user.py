# File: src/cashpilot/api/user.py
"""User management API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.api.auth import get_current_user
from cashpilot.api.auth_helpers import require_admin
from cashpilot.core.db import get_db
from cashpilot.core.errors import NotFoundError
from cashpilot.core.logging import get_logger
from cashpilot.core.security import hash_password
from cashpilot.models import (
    Business,
    User,
    UserBusiness,
    UserCreate,
    UserResponse,
    UserRole,
    UserWithBusinessesResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


class AssignBusinessesRequest(BaseModel):
    """Request body for assigning businesses to a user."""

    business_ids: list[UUID]


@router.post("", response_model=UserWithBusinessesResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate,
    business_ids: list[UUID] | None = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new user with optional business assignments. Admin only."""
    # Check email uniqueness
    stmt = select(User).where(User.email == user.email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    user_obj = User(
        email=user.email,
        hashed_password=hash_password(user.password),
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
    )
    db.add(user_obj)
    await db.flush()

    # Assign businesses if provided
    if business_ids:
        await _assign_businesses(user_obj.id, business_ids, db)

    await db.commit()
    await db.refresh(user_obj, ["businesses"])

    logger.info(
        "user.created",
        user_id=str(user_obj.id),
        email=user_obj.email,
        role=user_obj.role,
        created_by=str(current_user.id),
        business_count=len(business_ids) if business_ids else 0,
    )

    return user_obj


@router.post("/{user_id}/assign-businesses", response_model=UserWithBusinessesResponse)
async def assign_businesses_to_user(
    user_id: UUID,
    request: AssignBusinessesRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Replace user's business assignments. Admin only."""
    # Verify user exists
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user_obj = result.scalar_one_or_none()

    if not user_obj:
        raise NotFoundError("User", str(user_id))

    # Replace assignments
    await _assign_businesses(user_id, request.business_ids, db)

    await db.commit()
    await db.refresh(user_obj, ["businesses"])

    logger.info(
        "user.businesses_assigned",
        user_id=str(user_id),
        business_count=len(request.business_ids),
        assigned_by=str(current_user.id),
    )

    return user_obj


async def _assign_businesses(
    user_id: UUID,
    business_ids: list[UUID],
    db: AsyncSession,
) -> None:
    """Helper to replace user's business assignments."""
    # Validate all businesses exist
    stmt = select(Business).where(Business.id.in_(business_ids))
    result = await db.execute(stmt)
    found_businesses = result.scalars().all()

    if len(found_businesses) != len(business_ids):
        found_ids = {b.id for b in found_businesses}
        missing_ids = set(business_ids) - found_ids
        raise NotFoundError("Business", str(list(missing_ids)[0]))

    # Delete existing assignments
    stmt = select(UserBusiness).where(UserBusiness.user_id == user_id)
    result = await db.execute(stmt)
    existing = result.scalars().all()

    for assignment in existing:
        await db.delete(assignment)

    # Create new assignments
    for business_id in business_ids:
        assignment = UserBusiness(
            user_id=user_id,
            business_id=business_id,
        )
        db.add(assignment)


@router.get("", response_model=list[UserResponse])
async def list_users(
    role: UserRole | None = Query(None, description="Filter by role"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all active users, optionally filtered by role. Admin only for now."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    stmt = select(User).where(User.is_active is True)
    if role:
        stmt = stmt.where(User.role == role)

    stmt = stmt.order_by(User.first_name, User.last_name)

    result = await db.execute(stmt)
    users = result.scalars().all()

    return users
