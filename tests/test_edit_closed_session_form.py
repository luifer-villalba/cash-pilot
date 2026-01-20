"""Tests for editing CLOSED cash sessions via HTML form."""

from datetime import time
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models.cash_session_audit_log import CashSessionAuditLog
from tests.factories import BusinessFactory, CashSessionFactory


class TestEditClosedSessionFormGET:
    """Test GET /sessions/{id}/edit-closed."""

    @pytest.mark.asyncio
    async def test_admin_sees_business_selector(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test admin sees business dropdown in edit closed form."""
        business_a = await BusinessFactory.create(db_session, name="Business A")
        business_b = await BusinessFactory.create(db_session, name="Business B")
        session = await CashSessionFactory.create(
            db_session,
            business_id=business_a.id,
            cashier_id=admin_client.test_user.id,
            created_by=admin_client.test_user.id,
            status="CLOSED",
            final_cash=Decimal("1500000.00"),
            closed_time=time(18, 30),
        )

        response = await admin_client.get(f"/sessions/{session.id}/edit-closed")

        assert response.status_code == 200
        assert 'name="business_id"' in response.text
        assert "Business A" in response.text
        assert "Business B" in response.text


class TestEditClosedSessionFormPOST:
    """Test POST /sessions/{id}/edit-closed."""

    @pytest.mark.asyncio
    async def test_admin_can_change_business(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test admin can change business for a closed session."""
        business_a = await BusinessFactory.create(db_session, name="Business A")
        business_b = await BusinessFactory.create(db_session, name="Business B")
        session = await CashSessionFactory.create(
            db_session,
            business_id=business_a.id,
            cashier_id=admin_client.test_user.id,
            created_by=admin_client.test_user.id,
            status="CLOSED",
            initial_cash=Decimal("1000000.00"),
            final_cash=Decimal("1500000.00"),
            envelope_amount=Decimal("0.00"),
            card_total=Decimal("0.00"),
            credit_sales_total=Decimal("0.00"),
            credit_payments_collected=Decimal("0.00"),
            closed_time=time(18, 30),
        )

        response = await admin_client.post(
            f"/sessions/{session.id}/edit-closed",
            data={
                "initial_cash": "1000000.00",
                "final_cash": "1500000.00",
                "envelope_amount": "0.00",
                "card_total": "0.00",
                "credit_sales_total": "0.00",
                "credit_payments_collected": "0.00",
                "business_id": str(business_b.id),
                "reason": "Business reassignment",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302

        await db_session.refresh(session)
        assert session.business_id == business_b.id

        stmt = select(CashSessionAuditLog).where(
            CashSessionAuditLog.session_id == session.id
        )
        result = await db_session.execute(stmt)
        logs = result.scalars().all()

        assert logs
        assert "business_id" in logs[-1].changed_fields
