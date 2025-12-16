"""Audit logging model for CashSession edits."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cashpilot.core.db import Base
from cashpilot.utils.datetime import now_utc, now_utc_naive

if TYPE_CHECKING:
    from cashpilot.models.cash_session import CashSession


class CashSessionAuditLog(Base):
    """Immutable audit trail for all CashSession modifications."""

    __tablename__ = "cash_session_audit_logs"

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

    session: Mapped["CashSession"] = relationship(
        "CashSession",
        foreign_keys=[session_id],
    )

    # WHO
    changed_by: Mapped[str] = mapped_column(String(100), nullable=False)

    # WHEN
    changed_at: Mapped[datetime] = mapped_column(
        default=now_utc_naive,
    )

    # WHAT
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # "EDIT_OPEN", "EDIT_CLOSED"

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

    # Optional: reason/notes
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<CashSessionAuditLog(session_id={self.session_id}, "
            f"action={self.action}, changed_by={self.changed_by})>"
        )
