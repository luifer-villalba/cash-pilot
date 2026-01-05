# File: src/cashpilot/models/daily_reconciliation_audit_log.py
"""Audit logging model for DailyReconciliation edits."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cashpilot.core.db import Base
from cashpilot.utils.datetime import now_utc

if TYPE_CHECKING:
    from cashpilot.models.daily_reconciliation import DailyReconciliation


class DailyReconciliationAuditLog(Base):
    """Immutable audit trail for all DailyReconciliation modifications."""

    __tablename__ = "daily_reconciliation_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    reconciliation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("daily_reconciliations.id"),
        nullable=False,
        index=True,
    )

    reconciliation: Mapped["DailyReconciliation"] = relationship(
        "DailyReconciliation",
        foreign_keys=[reconciliation_id],
    )

    # WHO
    changed_by: Mapped[str] = mapped_column(String(100), nullable=False)

    # WHEN
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        index=True,
    )

    # WHAT
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # "EDIT", "DELETE"

    # WHICH FIELDS
    changed_fields: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # OLD/NEW VALUES
    old_values: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    new_values: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Required reason for edits
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<DailyReconciliationAuditLog(reconciliation_id={self.reconciliation_id}, "
            f"action={self.action}, changed_by={self.changed_by})>"
        )
