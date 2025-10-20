"""
CRUD endpoints for Movement resource.
Implements full REST API with pagination and filtering.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cashpilot.core.db import get_db
from cashpilot.models.enums import MovementType
from cashpilot.models.movement import Movement
from cashpilot.models.schemas import MovementCreate, MovementRead, MovementUpdate

router = APIRouter(prefix="/api/v1/movements", tags=["movements"])


@router.post(
    "",
    response_model=MovementRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new movement",
    description="Create a new cash flow movement (income or expense)",
)
async def create_movement(
    movement_data: MovementCreate,
    db: AsyncSession = Depends(get_db),
) -> Movement:
    """
    Create a new cash flow movement.

    Args:
        movement_data: Movement data from request body
        db: Database session (injected)

    Returns:
        Created movement with generated ID and timestamps
    """
    movement = Movement(**movement_data.model_dump())
    db.add(movement)
    await db.commit()
    await db.refresh(movement, ["category"])

    return movement


@router.get(
    "",
    response_model=list[MovementRead],
    status_code=status.HTTP_200_OK,
    summary="List movements with pagination and filters",
    description="Get a paginated list of movements with optional filters",
)
async def list_movements(
    db: AsyncSession = Depends(get_db),
    # Pagination
    limit: int = Query(
        50,
        ge=1,
        le=100,
        description="Number of results to return (max 100)",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of results to skip",
    ),
    # Filters
    type: Optional[MovementType] = Query(
        None,
        description="Filter by movement type (INCOME or EXPENSE)",
    ),
    category: Optional[str] = Query(
        None,
        description="Filter by category (exact match)",
    ),
    start_date: Optional[str] = Query(
        None,
        description="Filter by start date (YYYY-MM-DD format)",
    ),
    end_date: Optional[str] = Query(
        None,
        description="Filter by end date (YYYY-MM-DD format)",
    ),
) -> list[Movement]:
    """
    List all movements with optional filters and pagination.

    Returns movements sorted by occurred_at (most recent first).

    Args:
        db: Database session (injected)
        limit: Maximum number of results to return
        offset: Number of results to skip (for pagination)
        type: Optional filter by movement type
        category: Optional filter by category
        start_date: Optional filter by start date
        end_date: Optional filter by end date

    Returns:
        List of movements matching the filters
    """
    # Build the base query
    query = select(Movement).options(selectinload(Movement.category))

    # Apply filters if provided
    if type is not None:
        query = query.where(Movement.type == type)

    if category is not None:
        query = query.where(Movement.category == category)

    if start_date is not None:
        # Convert string to datetime for comparison
        start_dt = datetime.fromisoformat(start_date)
        query = query.where(Movement.occurred_at >= start_dt)

    if end_date is not None:
        # Convert string to datetime for comparison
        end_dt = datetime.fromisoformat(end_date)
        query = query.where(Movement.occurred_at <= end_dt)

    # Sort by occurred_at descending (most recent first)
    query = query.order_by(Movement.occurred_at.desc())

    # Apply pagination
    query = query.limit(limit).offset(offset)

    # Execute query
    result = await db.execute(query)
    movements = result.scalars().all()

    return movements


@router.get(
    "/{movement_id}",
    response_model=MovementRead,
    status_code=status.HTTP_200_OK,
    summary="Get a single movement by ID",
    description="Retrieve a specific movement by its UUID",
)
async def get_movement(
    movement_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Movement:
    """
    Get a single movement by UUID.

    Args:
        movement_id: UUID of the movement to retrieve
        db: Database session (injected)

    Returns:
        Movement if found

    Raises:
        HTTPException: 404 if movement not found
    """
    # Query for the movement
    result = await db.execute(
        select(Movement).options(selectinload(Movement.category)).where(Movement.id == movement_id)
    )
    movement = result.scalar_one_or_none()

    # Return 404 if not found
    if movement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movement with id {movement_id} not found",
        )

    return movement


@router.put(
    "/{movement_id}",
    response_model=MovementRead,
    status_code=status.HTTP_200_OK,
    summary="Update a movement",
    description="Update an existing movement by its UUID",
)
async def update_movement(
    movement_id: UUID,
    movement_data: MovementUpdate,
    db: AsyncSession = Depends(get_db),
) -> Movement:
    """
    Update an existing movement.

    Args:
        movement_id: UUID of the movement to update
        movement_data: New data for the movement (partial update allowed)
        db: Database session (injected)

    Returns:
        Updated movement

    Raises:
        HTTPException: 404 if movement not found
    """
    # Find the movement
    result = await db.execute(select(Movement).where(Movement.id == movement_id))
    movement = result.scalar_one_or_none()

    if movement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movement with id {movement_id} not found",
        )

    # Update only provided fields (partial update)
    update_data = movement_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(movement, field, value)

    # Commit changes
    await db.commit()
    await db.refresh(movement)

    return movement


@router.delete(
    "/{movement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a movement",
    description="Permanently delete a movement by its UUID",
)
async def delete_movement(
    movement_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a movement (hard delete).

    Args:
        movement_id: UUID of the movement to delete
        db: Database session (injected)

    Returns:
        None (204 No Content on success)

    Raises:
        HTTPException: 404 if movement not found
    """
    # Find the movement
    result = await db.execute(select(Movement).where(Movement.id == movement_id))
    movement = result.scalar_one_or_none()

    if movement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movement with id {movement_id} not found",
        )

    # Delete the movement
    await db.delete(movement)
    await db.commit()

    # Return nothing (204 No Content)
    return None
