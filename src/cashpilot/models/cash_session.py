"""CashSession model for shift tracking and reconciliation."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cashpilot.core.db import Base


class CashSession(Base):
    __tablename__ = "cash_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id"),
        nullable=False,
        index=True,
    )

    business: Mapped["Business"] = relationship(
        "Business",
        back_populates="cash_sessions",
    )

    opened_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(),
    )

    closed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    initial_cash: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    final_cash: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=True)
    envelope_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    expected_sales: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))

    @property
    def cash_sales(self) -> Decimal:
        """Calculate cash sales: (final + envelope) - initial."""
        if self.final_cash is None:
            return Decimal("0.00")
        return (self.final_cash + self.envelope_amount) - self.initial_cash

    @property
    def difference(self) -> Decimal:
        """Calculate difference: cash_sales - expected_sales."""
        return self.cash_sales - self.expected_sales

    def __repr__(self) -> str:
        return (
            f"<CashSession(id={self.id}, business_id={self.business_id}, "
            f"opened_at={self.opened_at})>"
        )
