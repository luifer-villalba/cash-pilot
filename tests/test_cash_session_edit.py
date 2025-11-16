"""Tests for CashSession edit endpoints."""

from datetime import date, time
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models import CashSession, CashSessionAuditLog
from .factories import BusinessFactory, CashSessionFactory


@pytest.mark.asyncio
async def test_edit_open_session_cashier_name(client: AsyncClient, db_session: AsyncSession):
    """Test editing cashier_name on an open session."""
    business = await BusinessFactory.create(db_session)
    session = await CashSessionFactory.create(db_session, business_id=business.id, status="OPEN")

    response = await client.patch(
        f"/cash-sessions/{session.id}/edit-open",
        json={"cashier_name": "Updated Cashier", "reason": "Name correction"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["cashier_name"] == "Updated Cashier"
    assert data["last_modified_by"] == "system"
    assert data["last_modified_at"] is not None

    audit_stmt = select(CashSessionAuditLog).where(
        CashSessionAuditLog.session_id == session.id
    )
    audit_result = await db_session.execute(audit_stmt)
    audit_log = audit_result.scalar_one_or_none()
    assert audit_log is not None
    assert audit_log.action == "EDIT_OPEN"
    assert audit_log.changed_fields == ["cashier_name"]
    assert audit_log.reason == "Name correction"


@pytest.mark.asyncio
async def test_edit_open_session_initial_cash(client: AsyncClient, db_session: AsyncSession):
    """Test editing initial_cash on an open session."""
    business = await BusinessFactory.create(db_session)
    session = await CashSessionFactory.create(
        db_session, business_id=business.id, status="OPEN", initial_cash=Decimal("1000.00")
    )

    response = await client.patch(
        f"/cash-sessions/{session.id}/edit-open",
        json={"initial_cash": "1500.00", "reason": "Corrected initial count"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["initial_cash"] == "1500.00"


@pytest.mark.asyncio
async def test_edit_open_session_multiple_fields(
    client: AsyncClient, db_session: AsyncSession
):
    """Test editing multiple fields at once."""
    business = await BusinessFactory.create(db_session)
    session = await CashSessionFactory.create(
        db_session,
        business_id=business.id,
        status="OPEN",
        cashier_name="Old Name",
        initial_cash=Decimal("1000.00"),
        expenses=Decimal("50.00"),
    )

    response = await client.patch(
        f"/cash-sessions/{session.id}/edit-open",
        json={
            "cashier_name": "New Name",
            "initial_cash": "2000.00",
            "expenses": "100.00",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["cashier_name"] == "New Name"
    assert data["initial_cash"] == "2000.00"
    assert data["expenses"] == "100.00"

    audit_stmt = select(CashSessionAuditLog).where(
        CashSessionAuditLog.session_id == session.id
    )
    audit_result = await db_session.execute(audit_stmt)
    audit_log = audit_result.scalar_one_or_none()
    assert set(audit_log.changed_fields) == {"cashier_name", "initial_cash", "expenses"}


@pytest.mark.asyncio
async def test_edit_open_session_cannot_edit_closed(
    client: AsyncClient, db_session: AsyncSession
):
    """Test that edit-open endpoint rejects closed sessions."""
    business = await BusinessFactory.create(db_session)
    session = await CashSessionFactory.create(
        db_session, business_id=business.id, status="CLOSED"
    )

    response = await client.patch(
        f"/cash-sessions/{session.id}/edit-open",
        json={"cashier_name": "New Name"},
    )

    assert response.status_code == 400
    data = response.json()
    error_text = data.get("detail") or data.get("message") or str(data)
    assert "OPEN" in error_text


@pytest.mark.asyncio
async def test_edit_closed_session_final_cash(client: AsyncClient, db_session: AsyncSession):
    """Test editing final_cash on a closed session."""
    business = await BusinessFactory.create(db_session)
    session = await CashSessionFactory.create(
        db_session,
        business_id=business.id,
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
        status="CLOSED",
        credit_card_total=Decimal("1000.00"),
        debit_card_total=Decimal("500.00"),
    )

    response = await client.patch(
        f"/cash-sessions/{session.id}/edit-closed",
        json={
            "credit_card_total": "1200.00",
            "debit_card_total": "600.00",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["credit_card_total"] == "1200.00"
    assert data["debit_card_total"] == "600.00"


@pytest.mark.asyncio
async def test_edit_closed_session_cannot_edit_open(
    client: AsyncClient, db_session: AsyncSession
):
    """Test that edit-closed endpoint rejects open sessions."""
    business = await BusinessFactory.create(db_session)
    session = await CashSessionFactory.create(
        db_session, business_id=business.id, status="OPEN"
    )

    response = await client.patch(
        f"/cash-sessions/{session.id}/edit-closed",
        json={"final_cash": "5000.00"},
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
        status="CLOSED",
        final_cash=Decimal("1234.56"),
    )

    response = await client.patch(
        f"/cash-sessions/{session.id}/edit-closed",
        json={"final_cash": "1999.99"},
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
