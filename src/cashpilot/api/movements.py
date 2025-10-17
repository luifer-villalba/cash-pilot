"""
Movement CRUD endpoints.
Handles income and expense tracking operations.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.core.db import get_db
from cashpilot.models.movement import Movement
from cashpilot.models.schemas import MovementCreate, MovementRead

# Create router with tags for Swagger documentation
router = APIRouter(
    prefix="/api/v1/movements",
    tags=["movements"],
)


@router.post(
    "",
    response_model=MovementRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new movement",
    description="Create a new income or expense movement.",
)
async def create_movement(
    movement_data: MovementCreate,
    db: AsyncSession = Depends(get_db),
) -> Movement:
    """
    Create a new movement in the database.
    Args:
        movement_data (MovementCreate): Data for the new movement from request body.
        db (AsyncSession): Database session (injected by FastAPI).

    Returns:
        Movement: The created movement object with id and timestamps.

    Raises:
        422: Validation error (handled automatically by Pydantic).
    """
    # Create Movement instance from Pydantic model
    # We use .model_dump() to convert Pydantic model to dict
    new_movement = Movement(**movement_data.model_dump())
    db.add(new_movement)
    await db.commit()
    await db.refresh(new_movement)

    return new_movement
