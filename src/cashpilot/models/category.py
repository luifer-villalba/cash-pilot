"""Category model for organizing movements."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cashpilot.core.db import Base
from cashpilot.models.enums import CategoryType

if TYPE_CHECKING:
    from cashpilot.models.movement import Movement


class Category(Base):
    """
    Categories for organizing income/expense movements.

    A category can be:
    - INCOME only (Salary, Freelance)
    - EXPENSE only (Food, Rent)
    - BOTH (Mixed use - rare but allowed)
    """

    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    type: Mapped[CategoryType] = mapped_column(
        SQLEnum(CategoryType, name="category_type"),
        nullable=False,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        index=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationship
    movements: Mapped[list["Movement"]] = relationship(
        "Movement",
        back_populates="category",
    )

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name={self.name}, type={self.type})>"
