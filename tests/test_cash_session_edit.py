# File: tests/test_cash_session_edit.py
"""Tests for CashSession edit endpoints."""

from datetime import timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models import CashSessionAuditLog
from cashpilot.utils.datetime import now_utc, utc_to_business
from .factories import BusinessFactory, CashSessionFactory, UserFactory


@pytest.mark.asyncio
async def test_edit_open_session_cannot_edit_closed(
    client: AsyncClient, db_session: AsyncSession
):
    """Test that edit-open endpoint rejects closed sessions."""
    business = await BusinessFactory.create(db_session)
    session = await CashSessionFactory.create(
        db_session,
        business_id=business.id,
        cashier_id=client.test_user.id,
        status="CLOSED",
    )

    response = await client.patch(
        f"/cash-sessions/{session.id}/edit-open",
        json={"initial_cash": "1500.00"},
    )

    assert response.status_code == 400
    data = response.json()
    error_text = data.get("detail") or data.get("message") or str(data)
    assert "OPEN" in error_text


@pytest.mark.asyncio
async def test_edit_open_requires_auth(
    unauthenticated_client: AsyncClient, db_session: AsyncSession
):
    """Test unauthenticated requests are rejected."""
    business = await BusinessFactory.create(db_session)
    session = await CashSessionFactory.create(
        db_session,
        business_id=business.id,
        status="OPEN",
    )

    response = await unauthenticated_client.patch(
        f"/cash-sessions/{session.id}/edit-open",
        json={"initial_cash": "1500.00"},
    )

    assert response.status_code in {401, 403, 303}


@pytest.mark.asyncio
async def test_edit_closed_session_final_cash(client: AsyncClient, db_session: AsyncSession):
    """Test editing final_cash on a closed session."""
    business = await BusinessFactory.create(db_session)
    session = await CashSessionFactory.create(
        db_session,
        business_id=business.id,
        cashier_id=client.test_user.id,
        status="CLOSED",
        final_cash=Decimal("5000.00"),
    )

    response = await client.patch(
        f"/cash-sessions/{session.id}/edit-closed",
        json={"final_cash": "5500.00", "reason": "Recount verification"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["final_cash"] == "5500.00"

    audit_stmt = select(CashSessionAuditLog).where(
        CashSessionAuditLog.session_id == session.id
    )
    audit_result = await db_session.execute(audit_stmt)
    audit_log = audit_result.scalar_one_or_none()
    assert audit_log.action == "EDIT_CLOSED"
    assert audit_log.changed_fields == ["final_cash"]


@pytest.mark.asyncio
async def test_edit_closed_session_payment_totals(
    client: AsyncClient, db_session: AsyncSession
):
    """Test editing payment method totals on a closed session."""
    business = await BusinessFactory.create(db_session)
    session = await CashSessionFactory.create(
        db_session,
        business_id=business.id,
        cashier_id=client.test_user.id,
        status="CLOSED",
        card_total=Decimal("1500.00"),
    )

    response = await client.patch(
        f"/cash-sessions/{session.id}/edit-closed",
        json={
            "card_total": "1800.00",
            "reason": "Payment totals correction",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["card_total"] == "1800.00"


@pytest.mark.asyncio
async def test_edit_closed_session_cannot_edit_open(
    client: AsyncClient, db_session: AsyncSession
):
    """Test that edit-closed endpoint rejects open sessions."""
    business = await BusinessFactory.create(db_session)
    session = await CashSessionFactory.create(
        db_session,
        business_id=business.id,
        cashier_id=client.test_user.id,
        status="OPEN",
    )

    response = await client.patch(
        f"/cash-sessions/{session.id}/edit-closed",
        json={"final_cash": "5000.00", "reason": "Test edit"},
    )

    assert response.status_code == 400
    data = response.json()
    error_text = data.get("detail") or data.get("message") or str(data)
    assert "CLOSED" in error_text


@pytest.mark.asyncio
async def test_audit_log_serializes_decimals(client: AsyncClient, db_session: AsyncSession):
    """Test that audit logs properly serialize Decimal values to strings."""
    business = await BusinessFactory.create(db_session)
    session = await CashSessionFactory.create(
        db_session,
        business_id=business.id,
        cashier_id=client.test_user.id,
        status="CLOSED",
        final_cash=Decimal("1234.56"),
    )

    response = await client.patch(
        f"/cash-sessions/{session.id}/edit-closed",
        json={"final_cash": "1999.99", "reason": "Decimal serialization test"},
    )

    assert response.status_code == 200

    audit_stmt = select(CashSessionAuditLog).where(
        CashSessionAuditLog.session_id == session.id
    )
    audit_result = await db_session.execute(audit_stmt)
    audit_log = audit_result.scalar_one_or_none()

    assert audit_log.old_values["final_cash"] == "1234.56"
    assert audit_log.new_values["final_cash"] == "1999.99"
    assert isinstance(audit_log.old_values["final_cash"], str)


@pytest.mark.asyncio
async def test_cashier_can_edit_own_session(
    client: AsyncClient, db_session: AsyncSession
):
    """AC-02/AC-05: Cashier can edit their own session."""
    business = await BusinessFactory.create(db_session)
    session = await CashSessionFactory.create(
        db_session,
        business_id=business.id,
        cashier_id=client.test_user.id,
        status="OPEN",
    )

    response = await client.patch(
        f"/cash-sessions/{session.id}/edit-open",
        json={"initial_cash": "1500.00"},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_cashier_cannot_edit_other_cashier_session(
    client: AsyncClient, db_session: AsyncSession
):
    """AC-02/AC-05: Cashier cannot edit another cashier's session."""
    business = await BusinessFactory.create(db_session)
    other_cashier = await UserFactory.create(
        db_session,
        email="other_cashier_edit@test.com",
    )
    session = await CashSessionFactory.create(
        db_session,
        business_id=business.id,
        cashier_id=other_cashier.id,
        status="OPEN",
    )

    response = await client.patch(
        f"/cash-sessions/{session.id}/edit-open",
        json={"initial_cash": "1500.00"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cashier_cannot_edit_closed_session_after_32h(
    client: AsyncClient, db_session: AsyncSession
):
    """AC-02/AC-05: Cashier cannot edit CLOSED session after 32 hours."""
    business = await BusinessFactory.create(db_session)
    closed_dt = utc_to_business(now_utc() - timedelta(hours=33))
    session = await CashSessionFactory.create(
        db_session,
        business_id=business.id,
        cashier_id=client.test_user.id,
        status="CLOSED",
        session_date=closed_dt.date(),
        closed_time=closed_dt.time(),
    )

    response = await client.patch(
        f"/cash-sessions/{session.id}/edit-closed",
        json={"final_cash": "5500.00", "reason": "Late correction"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_edit_any_session(
    admin_client: AsyncClient, db_session: AsyncSession
):
    """AC-02/AC-05: Admin can edit any session."""
    business = await BusinessFactory.create(db_session)
    other_cashier = await UserFactory.create(
        db_session,
        email="admin_any_session@test.com",
    )
    session = await CashSessionFactory.create(
        db_session,
        business_id=business.id,
        cashier_id=other_cashier.id,
        status="OPEN",
    )

    response = await admin_client.patch(
        f"/cash-sessions/{session.id}/edit-open",
        json={"initial_cash": "1500.00"},
    )

    assert response.status_code == 200
