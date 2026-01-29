"""CashSession audit endpoints (logs, flagging)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Form, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.api.auth import get_current_user
from cashpilot.core.audit import log_session_edit
from cashpilot.core.db import get_db
from cashpilot.core.errors import NotFoundError, ValidationError
from cashpilot.models import CashSession, CashSessionRead, User
from cashpilot.models.cash_session_audit_log import CashSessionAuditLog

router = APIRouter(prefix="/cash-sessions", tags=["cash-sessions-audit"])


def _parse_session_uuid(session_id: str) -> UUID:
    try:
        return UUID(session_id)
    except ValueError:
        raise NotFoundError("CashSession", session_id) from None


@router.post("/{session_id}/flag", response_model=CashSessionRead)
async def flag_session(
    session_id: str,
    flagged: bool = Form(...),
    flag_reason: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle session flag status with reason."""
    session_uuid = _parse_session_uuid(session_id)
    stmt = select(CashSession).where(CashSession.id == session_uuid)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise NotFoundError("CashSession", session_id)

    # Validate: reason required when flagging
    if flagged and not flag_reason or (flag_reason and len(flag_reason.strip()) < 5):
        raise ValidationError(
            "Flag reason required (minimum 5 characters)",
            details={"field": "flag_reason", "min_length": 5},
        )

    # Capture old values for audit
    old_flagged = session.flagged
    old_reason = session.flag_reason

    # Update flag status
    session.flagged = flagged
    session.flagged_by = current_user.display_name_email if flagged else None
    session.flag_reason = flag_reason.strip() if flagged and flag_reason else None

    db.add(session)
    await db.flush()

    # Audit log
    changed_fields = []
    old_values = {}
    new_values = {}

    if old_flagged != session.flagged:
        changed_fields.append("flagged")
        old_values["flagged"] = old_flagged
        new_values["flagged"] = session.flagged

    if old_reason != session.flag_reason:
        changed_fields.append("flag_reason")
        old_values["flag_reason"] = old_reason
        new_values["flag_reason"] = session.flag_reason

    if changed_fields:
        await log_session_edit(
            db,
            session,
            changed_by=current_user.email,
            action="FLAG_SESSION",
            old_values=old_values,
            new_values=new_values,
        )

    await db.commit()
    return RedirectResponse(url=f"/sessions/{session_id}", status_code=302)


@router.get("/{session_id}/audit-logs", response_model=list[dict])
async def get_session_audit_logs(
    session_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=250),
    db: AsyncSession = Depends(get_db),
):
    """Get audit log history for a cash session."""
    session_uuid = _parse_session_uuid(session_id)

    # Verify session exists
    stmt = select(CashSession).where(CashSession.id == session_uuid)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise NotFoundError("CashSession", session_id)

    # Get audit logs for this session
    audit_stmt = (
        select(CashSessionAuditLog)
        .where(CashSessionAuditLog.session_id == session_uuid)
        .order_by(CashSessionAuditLog.changed_at.desc())
        .offset(skip)
        .limit(limit)
    )
    audit_result = await db.execute(audit_stmt)
    audit_logs = audit_result.scalars().all()

    # Format response
    return [
        {
            "id": str(log.id),
            "session_id": str(log.session_id),
            "action": log.action,
            "changed_by": log.changed_by,
            "changed_at": log.changed_at.isoformat(),
            "changed_fields": log.changed_fields,
            "old_values": log.old_values,
            "new_values": log.new_values,
            "reason": log.reason,
        }
        for log in audit_logs
    ]
