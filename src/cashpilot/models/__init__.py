"""Domain models package."""

from cashpilot.models.category import Category
from cashpilot.models.category_schemas import CategoryRead
from cashpilot.models.enums import CategoryType, MovementType
from cashpilot.models.movement import Movement
from cashpilot.models.schemas import MovementCreate, MovementRead, MovementUpdate

# Rebuild MovementRead to resolve CategoryRead forward reference
MovementRead.model_rebuild()

__all__ = [
    "Category",
    "CategoryRead",
    "CategoryType",
    "Movement",
    "MovementType",
    "MovementCreate",
    "MovementRead",
    "MovementUpdate",
]
