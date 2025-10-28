"""Business API endpoints for pharmacy location management."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.core.db import get_db
from cashpilot.core.errors import NotFoundError
from cashpilot.models import Business, BusinessCreate, BusinessRead, BusinessUpdate

router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.post("", response_model=BusinessRead, status_code=status.HTTP_201_CREATED)
async def create_business(business: BusinessCreate, db: AsyncSession = Depends(get_db)):
    """Create a new business (pharmacy location)."""
    business_obj = Business(**business.model_dump())
    db.add(business_obj)
    await db.commit()
    await db.refresh(business_obj)
    return business_obj


@router.get("/{business_id}", response_model=BusinessRead)
async def get_business(business_id: str, db: AsyncSession = Depends(get_db)):
    """Get business details by ID."""
    stmt = select(Business).where(Business.id == UUID(business_id))
    result = await db.execute(stmt)
    business_obj = result.scalar_one_or_none()

    if not business_obj:
        raise NotFoundError("Business", business_id)

    return business_obj


@router.put("/{business_id}", response_model=BusinessRead)
async def update_business(
        business_id: str, business: BusinessUpdate, db: AsyncSession = Depends(get_db)
):
    """Update business details."""
    stmt = select(Business).where(Business.id == UUID(business_id))
    result = await db.execute(stmt)
    business_obj = result.scalar_one_or_none()

    if not business_obj:
        raise NotFoundError("Business", business_id)

    # Update fields (only non-null ones)
    update_data = business.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(business_obj, key, value)

    db.add(business_obj)
    await db.commit()
    await db.refresh(business_obj)
    return business_obj
