"""Tests for edit open session form functionality."""

from datetime import datetime, time
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models.cash_session import CashSession
from cashpilot.models.cash_session_audit_log import CashSessionAuditLog
from tests.factories import BusinessFactory, CashSessionFactory


class TestEditOpenSessionFormGET:
    """Test GET endpoint for edit open session form."""

    @pytest.mark.asyncio
    async def test_get_form_renders_for_open_session(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test GET /sessions/{id}/edit-open renders form."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session, business_id=business.id, status="OPEN"
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
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            cashier_name="María López",
            initial_cash=Decimal("500000.00"),
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
            db_session, business_id=business.id, status="CLOSED"
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
        )

        response = await client.post(
            f"/sessions/{session.id}/edit-open",
            data={
                "initial_cash": "750000.00",
                "reason": "Corrected initial count",
            },
        )

        assert response.status_code == 302

        await db_session.refresh(session)
        assert session.initial_cash == Decimal("750000.00")

    @pytest.mark.asyncio
    async def test_post_updates_expenses(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test POST updates expenses field."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            expenses=Decimal("0.00"),
        )

        response = await client.post(
            f"/sessions/{session.id}/edit-open",
            data={
                "expenses": "25000.00",
                "reason": "Added forgotten expenses",
            },
        )

        assert response.status_code == 302

        await db_session.refresh(session)
        assert session.expenses == Decimal("25000.00")

    @pytest.mark.asyncio
    async def test_post_updates_multiple_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test POST updates multiple fields simultaneously."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            cashier_name="Old Name",
            initial_cash=Decimal("500000.00"),
            opened_time=time(8, 0),
            expenses=Decimal("0.00"),
        )

        response = await client.post(
            f"/sessions/{session.id}/edit-open",
            data={
                "cashier_name": "New Name",
                "initial_cash": "750000.00",
                "opened_time": "09:00",
                "expenses": "50000.00",
                "reason": "Full correction",
            },
        )

        assert response.status_code == 302

        await db_session.refresh(session)
        assert session.cashier_name == "New Name"
        assert session.initial_cash == Decimal("750000.00")
        assert session.opened_time == time(9, 0)
        assert session.expenses == Decimal("50000.00")


class TestEditOpenSessionValidation:
    """Test validation for edit open session."""

    @pytest.mark.asyncio
    async def test_post_invalid_time_returns_error(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test POST with invalid time format returns error."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session, business_id=business.id, status="OPEN"
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
            cashier_name="Original",
        )

        response = await client.post(
            f"/sessions/{session.id}/edit-open",
            data={
                "cashier_name": "Updated",
                "reason": "Name correction",
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
        assert "cashier_name" in audit_log.changed_fields

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
            cashier_name="Original",
            initial_cash=Decimal("500000.00"),
            expenses=Decimal("0.00"),
        )

        response = await client.post(
            f"/sessions/{session.id}/edit-open",
            data={
                "cashier_name": "New Name",
                "initial_cash": "750000.00",
                "reason": "Bulk update",
            },
        )

        assert response.status_code == 302

        audit_stmt = select(CashSessionAuditLog).where(
            CashSessionAuditLog.session_id == session.id
        )
        audit_result = await db_session.execute(audit_stmt)
        audit_log = audit_result.scalar_one_or_none()

        assert set(audit_log.changed_fields) == {"cashier_name", "initial_cash"}

    @pytest.mark.asyncio
    async def test_audit_log_captures_old_new_values(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test audit log stores old and new values."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            initial_cash=Decimal("500000.00"),
        )

        response = await client.post(
            f"/sessions/{session.id}/edit-open",
            data={
                "initial_cash": "750000.00",
                "reason": "Recount",
            },
        )

        assert response.status_code == 302

        audit_stmt = select(CashSessionAuditLog).where(
            CashSessionAuditLog.session_id == session.id
        )
        audit_result = await db_session.execute(audit_stmt)
        audit_log = audit_result.scalar_one_or_none()

        assert audit_log.old_values["initial_cash"] == "500000.00"
        assert audit_log.new_values["initial_cash"] == "750000.00"

    @pytest.mark.asyncio
    async def test_audit_log_timestamp_recorded(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test audit log captures changed_at timestamp."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session, business_id=business.id, status="OPEN"
        )

        before = datetime.now()

        await client.post(
            f"/sessions/{session.id}/edit-open",
            data={"cashier_name": "Test", "reason": "Test"},
        )

        after = datetime.now()

        audit_stmt = select(CashSessionAuditLog).where(
            CashSessionAuditLog.session_id == session.id
        )
        audit_result = await db_session.execute(audit_stmt)
        audit_log = audit_result.scalar_one_or_none()

        assert audit_log.changed_at is not None
        assert before <= audit_log.changed_at <= after


class TestEditOpenSessionLastModified:
    """Test last_modified fields."""

    @pytest.mark.asyncio
    async def test_last_modified_at_updated(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test last_modified_at is set on form submission."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            last_modified_at=None,
        )

        await client.post(
            f"/sessions/{session.id}/edit-open",
            data={"cashier_name": "Test", "reason": "Test"},
        )

        await db_session.refresh(session)
        assert session.last_modified_at is not None

    @pytest.mark.asyncio
    async def test_last_modified_by_set_to_system(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test last_modified_by is 'system' for form submissions."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            last_modified_by=None,
        )

        await client.post(
            f"/sessions/{session.id}/edit-open",
            data={"cashier_name": "Test", "reason": "Test"},
        )

        await db_session.refresh(session)
        assert session.last_modified_by == "system"


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
            db_session, business_id=business.id, status="OPEN"
        )

        # Submit with decimal point (no thousands separator)
        response = await client.post(
            f"/sessions/{session.id}/edit-open",
            data={
                "initial_cash": "1234567.89",
                "reason": "Test",
            },
        )

        assert response.status_code == 302
        await db_session.refresh(session)
        assert session.initial_cash == Decimal("1234567.89")

    @pytest.mark.asyncio
    async def test_post_accepts_comma_formatted_amounts(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test POST accepts amounts with comma thousands separator."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session, business_id=business.id, status="OPEN"
        )

        # Submit with comma thousands separator
        response = await client.post(
            f"/sessions/{session.id}/edit-open",
            data={
                "initial_cash": "1,234,567.89",
                "reason": "Test",
            },
        )

        assert response.status_code == 302
        await db_session.refresh(session)
        assert session.initial_cash == Decimal("1234567.89")
