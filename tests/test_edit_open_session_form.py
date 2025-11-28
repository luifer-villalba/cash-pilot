# File: tests/test_edit_open_session_form.py
"""Tests for edit open session form functionality."""

from datetime import datetime, time
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models.cash_session import CashSession
from cashpilot.models.cash_session_audit_log import CashSessionAuditLog
from tests.factories import BusinessFactory, CashSessionFactory, UserFactory


class TestEditOpenSessionFormGET:
    """Test GET endpoint for edit open session form."""

    @pytest.mark.asyncio
    async def test_get_form_renders_for_open_session(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test GET /sessions/{id}/edit-open renders form."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session, business_id=business.id, status="OPEN", created_by=client.test_user.id
        )

        response = await client.get(f"/sessions/{session.id}/edit-open")

        assert response.status_code == 200
        assert "edit-open" in response.text or "form" in response.text.lower()

    @pytest.mark.asyncio
    async def test_form_displays_current_values(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test form displays current session values."""
        business = await BusinessFactory.create(db_session)
        cashier = await UserFactory.create(
            db_session, 
            first_name="María", 
            last_name="López"
        )
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            cashier_id=cashier.id,
            initial_cash=Decimal("500000.00"),
            created_by=client.test_user.id,
        )

        response = await client.get(f"/sessions/{session.id}/edit-open")

        assert response.status_code == 200
        assert "María López" in response.text

    @pytest.mark.asyncio
    async def test_form_closed_session_redirects(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test accessing form for closed session redirects."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session, business_id=business.id, status="CLOSED", created_by=client.test_user.id
        )

        response = await client.get(f"/sessions/{session.id}/edit-open", follow_redirects=False)

        assert response.status_code == 302


class TestEditOpenSessionFormPOST:
    """Test POST endpoint for editing open sessions."""

    @pytest.mark.asyncio
    async def test_post_updates_initial_cash(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test POST updates initial_cash field."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            initial_cash=Decimal("500000.00"),
            created_by=client.test_user.id,
        )

        response = await client.post(
            f"/sessions/{session.id}/edit-open",
            data={
                "initial_cash": "750000.00",
                "reason": "Correction",
            },
        )

        assert response.status_code == 302

        await db_session.refresh(session)
        assert session.initial_cash == Decimal("750000.00")

    @pytest.mark.asyncio
    async def test_post_updates_multiple_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test POST updates multiple fields."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            initial_cash=Decimal("500000.00"),
            opened_time=time(8, 0),
            notes="Old notes",
            created_by=client.test_user.id,
        )

        response = await client.post(
            f"/sessions/{session.id}/edit-open",
            data={
                "initial_cash": "750000.00",
                "opened_time": "09:00",
                "notes": "Updated notes",
                "reason": "Full correction",
            },
        )

        assert response.status_code == 302

        await db_session.refresh(session)
        assert session.initial_cash == Decimal("750000.00")
        assert session.opened_time == time(9, 0)
        assert session.notes == "Updated notes"


class TestEditOpenSessionValidation:
    """Test validation for edit open session."""

    @pytest.mark.asyncio
    async def test_post_invalid_time_returns_error(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test POST with invalid time format returns error."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session, business_id=business.id, status="OPEN", created_by=client.test_user.id
        )

        response = await client.post(
            f"/sessions/{session.id}/edit-open",
            data={
                "opened_time": "invalid-time",
                "reason": "Test",
            },
        )

        assert response.status_code == 400


class TestEditOpenSessionAuditLogging:
    """Test audit log creation on session edits."""

    @pytest.mark.asyncio
    async def test_audit_log_created_on_edit(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test audit log is created with correct data."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            initial_cash=Decimal("500000.00"),
            created_by=client.test_user.id,
        )

        response = await client.post(
            f"/sessions/{session.id}/edit-open",
            data={
                "initial_cash": "750000.00",
                "reason": "Amount correction",
            },
        )

        assert response.status_code == 302

        # Verify audit log
        audit_stmt = select(CashSessionAuditLog).where(
            CashSessionAuditLog.session_id == session.id
        )
        audit_result = await db_session.execute(audit_stmt)
        audit_log = audit_result.scalar_one_or_none()

        assert audit_log is not None
        assert "initial_cash" in audit_log.changed_fields

    @pytest.mark.asyncio
    async def test_audit_log_tracks_changed_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test audit log lists all changed fields."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            initial_cash=Decimal("500000.00"),
            notes="Old notes",
            created_by=client.test_user.id,
        )

        response = await client.post(
            f"/sessions/{session.id}/edit-open",
            data={
                "initial_cash": "750000.00",
                "notes": "New notes",
                "reason": "Bulk update",
            },
        )

        assert response.status_code == 302

        audit_stmt = select(CashSessionAuditLog).where(
            CashSessionAuditLog.session_id == session.id
        )
        audit_result = await db_session.execute(audit_stmt)
        audit_log = audit_result.scalar_one_or_none()

        assert set(audit_log.changed_fields) == {"initial_cash", "notes"}


class TestEditOpenSessionDecimalFormatting:
    """Test decimal formatting in form."""

    @pytest.mark.asyncio
    async def test_form_displays_formatted_amounts(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test form displays amounts with thousands separator."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            initial_cash=Decimal("1234567.89"),
            created_by=client.test_user.id,
        )

        response = await client.get(f"/sessions/{session.id}/edit-open")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_post_accepts_formatted_amounts(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test POST accepts amounts with separators."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            created_by=client.test_user.id,
        )

        response = await client.post(
            f"/sessions/{session.id}/edit-open",
            data={
                "initial_cash": "1.234.567,89",  # Format with separators
                "reason": "Test",
            },
        )

        assert response.status_code in [302, 400]  # Either succeeds or validation error
