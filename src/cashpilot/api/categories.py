"""Category CRUD endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.core.db import get_db
from cashpilot.models import Category, CategoryType

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_category(
    name: str,
    type: CategoryType,
    db: AsyncSession = Depends(get_db),
):
    """Create a new category."""

    # Check for duplicate name+type
    result = await db.execute(
        select(Category).where(
            Category.name == name,
            Category.type == type,
            Category.is_active is True,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category '{name}' with type {type.value} already exists",
        )

    category = Category(name=name, type=type)
    db.add(category)
    await db.commit()
    await db.refresh(category)

    return category


@router.get("/")
async def list_categories(
    type: CategoryType | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List all active categories, optionally filtered by type."""

    query = select(Category).where(Category.is_active is True)

    if type:
        query = query.where(Category.type == type)

    result = await db.execute(query.order_by(Category.name))
    categories = result.scalars().all()

    return categories


@router.get("/{category_id}")
async def get_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single category by ID."""

    category = await db.get(Category, category_id)

    if not category or not category.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    return category
