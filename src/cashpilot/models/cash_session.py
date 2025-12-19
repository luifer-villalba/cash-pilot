# File: src/cashpilot/models/cash_session.py
"""CashSession model for shift tracking and reconciliation."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cashpilot.models.business import Business
    from cashpilot.models.user import User

import uuid
from datetime import date as date_type
from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, Sequence, String, and_, or_, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cashpilot.core.db import Base
from cashpilot.utils.datetime import current_time_local, today_local


class CashSession(Base):
    """Cash session model for shift tracking and reconciliation."""

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
        lazy="selectin",
    )

    session_number: Mapped[int] = mapped_column(
        Sequence('cash_session_number_seq'),
        nullable=False,
        index=True,
    )

    # Cashier who operated this session
    cashier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    cashier: Mapped["User"] = relationship(
        "User",
        foreign_keys=[cashier_id],
        lazy="selectin",
    )

    # User who created this session (for audit trail)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    created_by_user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[created_by],
        lazy="selectin",
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="OPEN",
        index=True,
    )

    session_date: Mapped[date_type] = mapped_column(
        nullable=False,
        default=today_local,
    )

    opened_time: Mapped[time] = mapped_column(
        nullable=False,
        default=current_time_local,
    )

    closed_time: Mapped[time | None] = mapped_column(nullable=True)

    closing_ticket: Mapped[str | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(nullable=True)

    # Cash register amounts
    initial_cash: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    final_cash: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    envelope_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

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

    credit_sales_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    credit_payments_collected: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    # Session state
    has_conflict: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        index=True,
    )

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        index=True,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    deleted_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Flagging
    flagged: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        index=True,
    )

    flag_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    flagged_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Audit fields
    last_modified_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_modified_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # CALCULATED PROPERTIES
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
        """Calculate cash sales: (final - initial) - envelope.

        Envelope is SUBTRACTED because it's cash removed from register.
        """
        if self.final_cash is None:
            return Decimal("0.00")
        return (self.final_cash - self.initial_cash) + self.envelope_amount

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

    @property
    def shortage_surplus(self) -> Decimal:
        """Calculate cash shortage (-) or surplus (+).

        This is the difference between expected and actual cash.
        Positive = surplus (more cash than expected)
        Negative = shortage (less cash than expected)
        """
        if self.final_cash is None:
            return Decimal("0.00")

        expected_final = self.initial_cash + self.cash_sales
        return self.final_cash - expected_final

    async def get_conflicting_sessions(self, db: AsyncSession) -> list["CashSession"]:
        """Find all sessions that overlap with this one in same business."""
        if self.closed_time is None:
            # Open session: check for any other open sessions
            stmt = select(CashSession).where(
                and_(
                    CashSession.business_id == self.business_id,
                    CashSession.session_date == self.session_date,
                    CashSession.status == "OPEN",
                    CashSession.id != self.id,
                    CashSession.is_deleted is False,
                )
            )
        else:
            # Closed session: check for time overlap
            stmt = select(CashSession).where(
                and_(
                    CashSession.business_id == self.business_id,
                    CashSession.session_date == self.session_date,
                    CashSession.id != self.id,
                    CashSession.is_deleted is False,
                    CashSession.closed_time.isnot(None),
                    # Time overlap logic
                    or_(
                        # Case 1: other session starts during this session
                        and_(
                            CashSession.opened_time >= self.opened_time,
                            CashSession.opened_time < self.closed_time,
                        ),
                        # Case 2: other session ends during this session
                        and_(
                            CashSession.closed_time > self.opened_time,
                            CashSession.closed_time <= self.closed_time,
                        ),
                        # Case 3: other session completely contains this session
                        and_(
                            CashSession.opened_time <= self.opened_time,
                            CashSession.closed_time >= self.closed_time,
                        ),
                    ),
                )
            )

        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def check_open_session(
        business_id: uuid.UUID,
        session_date: date_type,
        cashier_id: uuid.UUID,
        db: AsyncSession,
        exclude_session_id: uuid.UUID | None = None,
    ) -> "CashSession | None":
        """Check if cashier has an open session for this business on this date.

        Args:
            business_id: The business to check
            session_date: The date to check
            cashier_id: The cashier to check for
            db: Database session
            exclude_session_id: Optional session ID to exclude (for updates)

        Returns:
            The open session if found, None otherwise
        """
        stmt = select(CashSession).where(
            and_(
                CashSession.business_id == business_id,
                CashSession.session_date == session_date,
                CashSession.cashier_id == cashier_id,
                CashSession.status == "OPEN",
                CashSession.is_deleted is False,
            )
        )

        if exclude_session_id:
            stmt = stmt.where(CashSession.id != exclude_session_id)

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    def __repr__(self) -> str:
        return (
            f"<CashSession(id={self.id}, business_id={self.business_id}, "
            f"cashier_id={self.cashier_id}, status={self.status})>"
        )
