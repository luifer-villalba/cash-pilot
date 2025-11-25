"""User model for authentication."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from cashpilot.core.db import Base


class UserRole(str, enum.Enum):
    """User role enumeration."""

    ADMIN = "ADMIN"
    CASHIER = "CASHIER"


class User(Base):
    """User model for authentication."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    hashed_password: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="",
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="",
    )

    role: Mapped[UserRole] = mapped_column(
        String(20),
        nullable=False,
        default=UserRole.CASHIER.value,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(),
    )

    @property
    def display_name(self) -> str:
        """Return formatted display name (first_name last_name or email fallback)."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.email

    def __repr__(self) -> str:
        return f"<User(email={self.email}, role={self.role}, is_active={self.is_active})>"
