# File: tests/test_session_flagging.py
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models import CashSession, CashSessionAuditLog
from tests.factories import BusinessFactory, CashSessionFactory

@pytest.mark.asyncio
async def test_flag_session_creates_audit_log(
        admin_client: AsyncClient, db_session: AsyncSession
):
    """AC-02/AC-07: Admin flagging creates audit log entry and redirects."""
    business = await BusinessFactory.create(db_session)
    session = await CashSessionFactory.create(
        db_session, business_id=business.id, status="CLOSED", flagged=False
    )

    response = await admin_client.post(
        f"/cash-sessions/{session.id}/flag",
        data={
            "flagged": "true",
            "flag_reason": "High cash discrepancy detected",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert f"/sessions/{session.id}" in response.headers["location"]

    # Verify DB updated
    await db_session.refresh(session)
    assert session.flagged is True
    assert session.flag_reason == "High cash discrepancy detected"

    # Verify audit log
    audit_stmt = select(CashSessionAuditLog).where(
        CashSessionAuditLog.session_id == session.id
    )
    audit_result = await db_session.execute(audit_stmt)
    audit_log = audit_result.scalar_one_or_none()

    assert audit_log is not None
    assert audit_log.action == "FLAG_SESSION"
    assert "flagged" in audit_log.changed_fields


@pytest.mark.asyncio
async def test_unflag_session_redirects(
        admin_client: AsyncClient, db_session: AsyncSession
):
    """AC-02/AC-07: Admin unflagging clears flag data and redirects."""
    business = await BusinessFactory.create(db_session)
    session = await CashSessionFactory.create(
        db_session,
        business_id=business.id,
        status="CLOSED",
        flagged=True,
        flag_reason="Test reason",
        flagged_by="test@example.com",
    )

    response = await admin_client.post(
        f"/cash-sessions/{session.id}/flag",
        data={"flagged": "false"},
        follow_redirects=False,
    )

    assert response.status_code == 302

    await db_session.refresh(session)
    assert session.flagged is False
    assert session.flag_reason is None
    assert session.flagged_by is None


@pytest.mark.asyncio
async def test_cashier_cannot_flag_session(
        client: AsyncClient, db_session: AsyncSession
):
    """AC-02: Cashier is denied flagging a session."""
    business = await BusinessFactory.create(db_session)
    session = await CashSessionFactory.create(
        db_session, business_id=business.id, status="CLOSED", flagged=False
    )

    response = await client.post(
        f"/cash-sessions/{session.id}/flag",
        data={
            "flagged": "true",
            "flag_reason": "High cash discrepancy detected",
        },
        follow_redirects=False,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_view_audit_logs(
        admin_client: AsyncClient, db_session: AsyncSession
):
    """AC-02/AC-07: Admin can fetch audit logs for a session."""
    business = await BusinessFactory.create(db_session)
    session = await CashSessionFactory.create(
        db_session, business_id=business.id, status="CLOSED", flagged=False
    )

    response = await admin_client.get(f"/cash-sessions/{session.id}/audit-logs")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_cashier_cannot_view_audit_logs(
        client: AsyncClient, db_session: AsyncSession
):
    """AC-02: Cashier is denied audit log access."""
    business = await BusinessFactory.create(db_session)
    session = await CashSessionFactory.create(
        db_session, business_id=business.id, status="CLOSED", flagged=False
    )

    response = await client.get(f"/cash-sessions/{session.id}/audit-logs")

    assert response.status_code == 403
