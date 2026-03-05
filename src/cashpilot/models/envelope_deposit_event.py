"""Envelope deposit event model."""

import uuid
from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from cashpilot.core.db import Base
from cashpilot.utils.datetime import now_utc

if TYPE_CHECKING:
    pass


class EnvelopeDepositEvent(Base):
    """Tracks envelope deposit lifecycle events per cash session."""

    __tablename__ = "envelope_deposit_events"
    __table_args__ = (CheckConstraint("amount > 0", name="envelope_deposit_event_amount_positive"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("envelope_deposit_batches.id"),
        nullable=True,
        index=True,
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cash_sessions.id"),
        nullable=False,
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    deposit_date: Mapped[date_type] = mapped_column(
        Date,
        nullable=False,
    )

    note: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    deposited_by_name: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
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
