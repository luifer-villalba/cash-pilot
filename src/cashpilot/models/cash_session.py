"""CashSession model for shift tracking and reconciliation."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cashpilot.models.business import Business
    from cashpilot.models.user import User

import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, and_, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
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

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    created_by_user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[created_by],
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="OPEN",
        index=True,
    )

    cashier_name: Mapped[str] = mapped_column(nullable=False)

    session_date: Mapped[date] = mapped_column(
        nullable=False,
        default=lambda: datetime.now().date(),
    )

    opened_time: Mapped[time] = mapped_column(
        nullable=False,
        default=lambda: datetime.now().time(),
    )

    closed_time: Mapped[time | None] = mapped_column(nullable=True)

    closing_ticket: Mapped[str | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(nullable=True)

    # Cash register amounts
    initial_cash: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    final_cash: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    envelope_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))

    has_conflict: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        index=True,
    )

    is_deleted: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        index=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    deleted_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Payment method totals
    credit_card_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    debit_card_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    bank_transfer_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    expenses: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    flagged: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        index=True,
    )

    flag_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    flagged_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # AUDIT FIELDS
    last_modified_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_modified_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # CALCULATED PROPERTIES (reconstructed from date + time)
    @property
    def opened_at(self) -> datetime:
        """Reconstruct datetime from session_date + opened_time (naive, browser timezone)."""
        return datetime.combine(self.session_date, self.opened_time)

    @property
    def closed_at(self) -> datetime | None:
        """Reconstruct datetime from session_date + closed_time (naive, browser timezone)."""
        if self.closed_time is None:
            return None
        return datetime.combine(self.session_date, self.closed_time)

    @property
    def cash_sales(self) -> Decimal:
        if self.final_cash is None:
            return Decimal("0.00")
        return (self.final_cash - self.initial_cash) + self.envelope_amount

    @property
    def cash_debit_transfer_sales(self) -> Decimal:
        """Cash + debit + bank transfer (excludes credit card)."""
        return self.cash_sales + self.debit_card_total + self.bank_transfer_total

    @property
    def total_sales(self) -> Decimal:
        """All revenue across all payment methods."""
        return (
            self.cash_sales
            + self.credit_card_total
            + self.debit_card_total
            + self.bank_transfer_total
        )

    @property
    def net_earnings(self) -> Decimal:
        """Total sales minus business expenses."""
        return self.total_sales - self.expenses

    async def get_conflicting_sessions(self, db: AsyncSession) -> list["CashSession"]:
        """Find all sessions that overlap with this one in same business."""
        stmt = select(CashSession).where(
            and_(
                CashSession.business_id == self.business_id,
                CashSession.id != self.id,
                CashSession.opened_time < (self.closed_time or datetime.now().time()),
                CashSession.closed_time.is_(None) | (CashSession.closed_time > self.opened_time),
            )
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    def __repr__(self) -> str:
        return (
            f"<CashSession(id={self.id}, business_id={self.business_id}, "
            f"session_date={self.session_date}, opened_time={self.opened_time})>"
        )
