"""
Pydantic schemas for Movement API.

Separates API contracts from database models.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from cashpilot.core.db import Base
from cashpilot.models.enums import MovementType


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

    category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    def __repr__(self) -> str:
        """String representation of the Movement."""
        return (
            f"<Movement(id={self.id}, occurred_at={self.occurred_at}, "
            f"type={self.type}, amount_gs={self.amount_gs}, "
            f"description={self.description}, category={self.category})>"
        )
