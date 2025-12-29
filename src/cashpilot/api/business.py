# File: src/cashpilot/api/business.py
"""Business management API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.api.auth import get_current_user
from cashpilot.api.auth_helpers import require_admin
from cashpilot.core.db import get_db
from cashpilot.core.errors import NotFoundError
from cashpilot.core.logging import get_logger
from cashpilot.models import Business
from cashpilot.models.business_schemas import BusinessCreate, BusinessRead, BusinessUpdate
from cashpilot.models.user import User

logger = get_logger(__name__)

router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.get("", response_model=list[BusinessRead])
async def list_businesses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all businesses. All roles can read."""
    stmt = select(Business).order_by(Business.name)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=BusinessRead, status_code=status.HTTP_201_CREATED)
async def create_business(
    business: BusinessCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new business. Admin only."""
    business_obj = Business(
        name=business.name,
        address=business.address,
        phone=business.phone,
    )
    db.add(business_obj)
    await db.commit()
    await db.refresh(business_obj)
    logger.info(
        "business.created",
        business_id=str(business_obj.id),
        business_name=business_obj.name,
        created_by=str(current_user.id),
    )
    return business_obj


@router.get("/{business_id}", response_model=BusinessRead)
async def get_business(
    business_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single business by ID. All roles can read."""
    try:
        business_uuid = UUID(business_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid business_id format",
        )

    stmt = select(Business).where(Business.id == business_uuid)
    result = await db.execute(stmt)
    business_obj = result.scalar_one_or_none()

    if not business_obj:
        raise NotFoundError("Business", business_id)

    return business_obj


@router.put("/{business_id}", response_model=BusinessRead)
async def update_business(
    business_id: str,
    business: BusinessUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a business. Admin only."""
    try:
        business_uuid = UUID(business_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid business_id format",
        )

    stmt = select(Business).where(Business.id == business_uuid)
    result = await db.execute(stmt)
    business_obj = result.scalar_one_or_none()

    if not business_obj:
        raise NotFoundError("Business", business_id)

    # Update fields (only non-null ones)
    update_data = business.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(business_obj, key, value)

    db.add(business_obj)
    await db.commit()
    await db.refresh(business_obj)
    logger.info(
        "business.updated",
        business_id=str(business_obj.id),
        updated_by=str(current_user.id),
    )
    return business_obj


@router.delete("/{business_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_business(
    business_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete business (sets is_active=False). Admin only."""
    stmt = select(Business).where(Business.id == UUID(business_id))
    result = await db.execute(stmt)
    business_obj = result.scalar_one_or_none()

    if not business_obj:
        raise NotFoundError("Business", business_id)

    business_obj.is_active = False
    db.add(business_obj)
    await db.commit()
    logger.info(
        "business.deleted",
        business_id=str(business_obj.id),
        deleted_by=str(current_user.id),
    )
