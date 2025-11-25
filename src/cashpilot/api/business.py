"""Business API endpoints for pharmacy location management."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.api.auth import get_current_user
from cashpilot.api.auth_helpers import require_admin
from cashpilot.core.db import get_db
from cashpilot.core.errors import NotFoundError
from cashpilot.core.logging import get_logger
from cashpilot.models import Business, BusinessCreate, BusinessRead, BusinessUpdate
from cashpilot.models.user import User

logger = get_logger(__name__)

router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.get("", response_model=list[BusinessRead])
async def list_businesses(
    skip: int = 0,
    limit: int = 50,
    is_active: bool | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all businesses with pagination and optional filtering."""
    stmt = select(Business)

    if is_active is not None:
        stmt = stmt.where(Business.is_active == is_active)

    stmt = stmt.offset(skip).limit(limit).order_by(Business.name)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=BusinessRead, status_code=status.HTTP_201_CREATED)
async def create_business(
    business: BusinessCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new business (pharmacy location). Admin only."""
    business_obj = Business(**business.model_dump())
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
    """Get business details by ID. All roles can read."""
    # Skip if it's a special route keyword
    if business_id in ["create", "new", "list"]:
        raise NotFoundError("Business", business_id)

    stmt = select(Business).where(Business.id == UUID(business_id))
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
    """Update business details. Admin only."""
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


@router.get("/{business_id}/cashiers")
async def get_cashiers(
    business_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get cashier list for a business. All roles can read."""
    stmt = select(Business).where(Business.id == UUID(business_id))
    result = await db.execute(stmt)
    business_obj = result.scalar_one_or_none()

    if not business_obj:
        raise NotFoundError("Business", business_id)

    return {
        "business_id": str(business_obj.id),
        "business_name": business_obj.name,
        "cashiers": business_obj.cashiers or [],
    }


@router.post("/{business_id}/cashiers", status_code=status.HTTP_200_OK)
async def add_cashier(
    business_id: str,
    cashier_name: str = Query(...),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Add a cashier to the business's cashier list. Admin only."""
    stmt = select(Business).where(Business.id == UUID(business_id))
    result = await db.execute(stmt)
    business_obj = result.scalar_one_or_none()

    if not business_obj:
        raise NotFoundError("Business", business_id)

    if cashier_name.strip() not in business_obj.cashiers:
        business_obj.cashiers.append(cashier_name.strip())
        db.add(business_obj)
        await db.commit()
        await db.refresh(business_obj)
        logger.info(
            "business.cashier_added",
            business_id=str(business_obj.id),
            cashier_name=cashier_name,
            added_by=str(current_user.id),
        )

    return {
        "business_id": str(business_obj.id),
        "cashiers": business_obj.cashiers,
    }


@router.delete("/{business_id}/cashiers/{cashier_name}", status_code=status.HTTP_200_OK)
async def remove_cashier(
    business_id: str,
    cashier_name: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Remove a cashier from the business's cashier list. Admin only."""
    stmt = select(Business).where(Business.id == UUID(business_id))
    result = await db.execute(stmt)
    business_obj = result.scalar_one_or_none()

    if not business_obj:
        raise NotFoundError("Business", business_id)

    if cashier_name in business_obj.cashiers:
        business_obj.cashiers.remove(cashier_name)
        db.add(business_obj)
        await db.commit()
        await db.refresh(business_obj)
        logger.info(
            "business.cashier_removed",
            business_id=str(business_obj.id),
            cashier_name=cashier_name,
            removed_by=str(current_user.id),
        )

    return {
        "business_id": str(business_obj.id),
        "cashiers": business_obj.cashiers,
    }
