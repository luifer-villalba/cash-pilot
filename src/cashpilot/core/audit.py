"""Audit logging utilities for tracking CashSession changes."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models.cash_session import CashSession
from cashpilot.models.cash_session_audit_log import CashSessionAuditLog
from cashpilot.utils.datetime import now_utc


async def log_session_edit(
    db: AsyncSession,
    session: CashSession,
    changed_by: str,
    action: str,
    old_values: dict[str, Any],
    new_values: dict[str, Any],
    reason: str | None = None,
) -> CashSessionAuditLog:
    """Log a CashSession edit to audit trail.

    Args:
        db: Database session
        session: The CashSession being modified
        changed_by: User/system identifier making the change
        action: "EDIT_OPEN" or "EDIT_CLOSED"
        old_values: Dict of {field_name: old_value}
        new_values: Dict of {field_name: new_value}
        reason: Optional reason for the edit

    Returns:
        Created CashSessionAuditLog record
    """
    # Only include fields that actually changed
    changed_fields = [k for k in old_values.keys() if old_values[k] != new_values.get(k)]

    # Convert Decimal to string for JSON serialization
    def serialize_value(v: Any) -> Any:
        if isinstance(v, Decimal):
            return str(v)
        return v

    audit_log = CashSessionAuditLog(
        session_id=session.id,
        changed_by=changed_by,
        action=action,
        changed_fields=changed_fields,
        old_values={k: serialize_value(old_values[k]) for k in changed_fields},
        new_values={k: serialize_value(new_values.get(k)) for k in changed_fields},
        reason=reason,
        changed_at=now_utc(),
    )

    db.add(audit_log)
    return audit_log
