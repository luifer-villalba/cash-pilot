"""CashSession model for shift tracking and reconciliation."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cashpilot.models.business import Business

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
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

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="OPEN",
        index=True,
    )

    cashier_name: Mapped[str] = mapped_column(nullable=False)
    shift_hours: Mapped[str | None] = mapped_column(nullable=True)

    opened_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(),
    )
    closed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    closing_ticket: Mapped[str | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(nullable=True)

    # Cash register amounts
    initial_cash: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    final_cash: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    envelope_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))

    # Payment method totals (reported at end of shift)
    credit_card_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    debit_card_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    bank_transfer_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    @property
    def cash_sales(self) -> Decimal:
        """
        Calculate cash sales: (final_cash - initial_cash) + envelope_amount.

        Represents total cash that should be in drawer at end of shift.

        Example:
            initial_cash = 500,000
            final_cash = 1,200,000
            envelope_amount = 300,000
            cash_sales = (1,200,000 - 500,000) + 300,000 = 1,000,000
        """
        if self.final_cash is None:
            return Decimal("0.00")
        return (self.final_cash - self.initial_cash) + self.envelope_amount

    @property
    def total_sales(self) -> Decimal:
        """
        Calculate total sales across all payment methods.

        total_sales = cash_sales + credit_card + debit_card + bank_transfer

        Example:
            cash_sales = 1,000,000
            credit_card_total = 800,000
            debit_card_total = 450,000
            bank_transfer_total = 150,000
            total_sales = 1,000,000 + 800,000 + 450,000 + 150,000 = 2,400,000
        """
        return (
            self.cash_sales
            + self.credit_card_total
            + self.debit_card_total
            + self.bank_transfer_total
        )

    @property
    def difference(self) -> Decimal:
        """
        Calculate reconciliation difference.

        difference = total_sales - cash_sales

        Interpretation:
            Positive = shortage (missing cash, should investigate)
            Negative = overage (extra cash in drawer)
            Zero = perfect match (ideal state)

        Example:
            total_sales = 2,400,000
            cash_sales = 1,000,000
            difference = 2,400,000 - 1,000,000 = 1,400,000
            (This indicates all non-cash payments, which is correct)
        """
        return self.total_sales - self.cash_sales

    def __repr__(self) -> str:
        return (
            f"<CashSession(id={self.id}, business_id={self.business_id}, "
            f"opened_at={self.opened_at})>"
        )
