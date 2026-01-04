# File: src/cashpilot/models/expense_item.py
"""Expense line item model."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from cashpilot.core.db import Base
from cashpilot.utils.datetime import now_utc

if TYPE_CHECKING:
    from cashpilot.models.cash_session import CashSession


class ExpenseItem(Base):
    """Expense line item."""

    __tablename__ = "expense_items"
    __table_args__ = (CheckConstraint("amount >= 0", name="expense_item_amount_non_negative"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cash_sessions.id"),
        nullable=False,
        index=True,
    )

    description: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
    )

    is_deleted: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        index=True,
    )

    # Relationships
    session: Mapped["CashSession"] = relationship(
        "CashSession",
        back_populates="expense_items",
    )

    @validates("amount")
    def validate_amount(self, key: str, value: Decimal) -> Decimal:
        """Validate that amount is non-negative."""
        if value < 0:
            raise ValueError("Expense amount cannot be negative")
        return value

    @property
    def formatted_amount(self) -> str:
        """Return formatted amount with currency symbol (Paraguay format)."""
        return f"Gs {self.amount:,.0f}".replace(",", ".")

    @property
    def display_amount(self) -> str:
        """Return formatted amount for display (alias for formatted_amount)."""
        return self.formatted_amount

    def is_valid(self) -> bool:
        """Check if the expense item is valid."""
        return (
            self.amount >= 0
            and bool(self.description and self.description.strip())
            and not self.is_deleted
        )

    def __repr__(self) -> str:
        desc = self.description[:20] if self.description else ""
        return f"<ExpenseItem(id={self.id}, amount={self.amount}, description={desc})>"
