# File: src/cashpilot/models/user_business.py
"""UserBusiness junction table for many-to-many User-Business relationship."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cashpilot.core.db import Base
from cashpilot.utils.datetime import now_utc

if TYPE_CHECKING:
    from cashpilot.models.business import Business
    from cashpilot.models.user import User


class UserBusiness(Base):
    """Junction table for User-Business many-to-many relationship."""

    __tablename__ = "user_businesses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="business_assignments",
    )

    business: Mapped["Business"] = relationship(
        "Business",
        back_populates="user_assignments",
    )

    def __repr__(self) -> str:
        return f"<UserBusiness(user_id={self.user_id}, business_id={self.business_id})>"
