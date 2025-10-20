"""Movement database model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cashpilot.core.db import Base
from cashpilot.models.enums import MovementType

if TYPE_CHECKING:
    from cashpilot.models.category import Category


class Movement(Base):
    """
    Represents a single cash flow movement.
    Attributes:
        id: Unique identifier (UUID v4)
        occurred_at: When the movement happened (user-provided date)
        type: Whether this is income or expense
        amount_gs: Amount in Guaraníes (always positive integer)
        description: Optional text description
        category: Optional category for filtering/reporting
        created_at: When record was created in database
        updated_at: When record was last modified
    """

    __tablename__ = "movements"

    # Primary key: UUID v4
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # When the movement occurred (user-provided date)
    occurred_at: Mapped[datetime] = mapped_column(
        nullable=False,
        index=True,
    )

    # Type of movement: INCOME or EXPENSE
    type: Mapped[MovementType] = mapped_column(
        SQLEnum(MovementType, name="movement_type"),
        nullable=False,
        index=True,
    )

    # Amount in Guaraníes (always positive integer)
    amount_gs: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Optional fields
    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id"),
        nullable=True,
        index=True,
    )

    category: Mapped[Optional["Category"]] = relationship(
        "Category",
        back_populates="movements",
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

    def __repr__(self) -> str:
        """String representation of the Movement."""
        return (
            f"<Movement(id={self.id}, occurred_at={self.occurred_at}, "
            f"type={self.type}, amount_gs={self.amount_gs}, "
            f"description={self.description}, category={self.category})>"
        )
