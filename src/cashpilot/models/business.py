# File: src/cashpilot/models/business.py
"""Business model for pharmacy locations."""

from typing import TYPE_CHECKING

from cashpilot.utils.datetime import now_utc_naive

if TYPE_CHECKING:
    from cashpilot.models.cash_session import CashSession
    from cashpilot.models.user import User
    from cashpilot.models.user_business import UserBusiness

import uuid
from datetime import datetime

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cashpilot.core.db import Base


class Business(Base):
    """
    Represents a pharmacy location.

    Each pharmacy location operates independently with its own:
    - Cash register operations
    - Daily reconciliation
    - Employees (managed via UserBusiness relationship)

    Note: RUC (tax_id) is shared across all locations in Paraguay
    and should be stored at organization level (future implementation).
    """

    __tablename__ = "businesses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )

    address: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=now_utc_naive,
    )

    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=now_utc_naive,
        onupdate=now_utc_naive,
    )

    # Relationships
    cash_sessions: Mapped[list["CashSession"]] = relationship(
        "CashSession",
        back_populates="business",
        cascade="all, delete-orphan",
    )

    user_assignments: Mapped[list["UserBusiness"]] = relationship(
        "UserBusiness",
        back_populates="business",
        cascade="all, delete-orphan",
    )

    users: Mapped[list["User"]] = relationship(
        "User",
        secondary="user_businesses",
        viewonly=True,
    )

    def __repr__(self) -> str:
        return self.name
