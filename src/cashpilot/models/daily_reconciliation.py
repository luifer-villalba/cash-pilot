# File: src/cashpilot/models/daily_reconciliation.py
"""DailyReconciliation model for manual daily sales data entry."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cashpilot.models.business import Business
    from cashpilot.models.user import User

import uuid
from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cashpilot.core.db import Base
from cashpilot.utils.datetime import now_utc, today_local


class DailyReconciliation(Base):
    """Daily reconciliation model for manual sales data entry by business location."""

    __tablename__ = "daily_reconciliations"

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
        back_populates="daily_reconciliations",
        lazy="selectin",
    )

    date: Mapped[date_type] = mapped_column(
        nullable=False,
        default=today_local,
        index=True,
    )

    # Sales data
    cash_sales: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    credit_sales: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    card_sales: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    total_sales: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    purchases_total: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    # Number of invoices/transactions
    invoice_count: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    # Closed flag: marks locations closed that day (no cash sessions expected)
    is_closed: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        index=True,
    )

    # Admin who created/entered this data
    admin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    admin: Mapped["User"] = relationship(
        "User",
        foreign_keys=[admin_id],
        lazy="selectin",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
    )

    # Soft delete
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    deleted_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<DailyReconciliation(id={self.id}, business_id={self.business_id}, "
            f"date={self.date}, is_closed={self.is_closed})>"
        )
