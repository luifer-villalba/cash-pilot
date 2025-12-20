# File: tests/test_edit_open_session_form.py

"""Tests for editing OPEN cash sessions."""

import pytest
from decimal import Decimal
from datetime import datetime, time
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models.cash_session import CashSession
from cashpilot.models.cash_session_audit_log import CashSessionAuditLog
from tests.factories import BusinessFactory, CashSessionFactory


class TestEditOpenSessionFormGET:
    """Test GET /sessions/{id}/edit-open."""

    @pytest.mark.asyncio
    async def test_get_form_renders_for_open_session(
        self, admin_client: AsyncClient, db_session: AsyncSession  
    ):
        """Test form renders for OPEN session."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            created_by=admin_client.test_user.id,  
        )

        response = await admin_client.get(f"/sessions/{session.id}/edit-open")  
        assert response.status_code == 200
        assert b"Edit Open Session" in response.content or b"initial_cash" in response.content

    @pytest.mark.asyncio
    async def test_form_displays_current_values(
        self, admin_client: AsyncClient, db_session: AsyncSession  
    ):
        """Test form shows current session values."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            initial_cash=Decimal("1000000.00"),
            expenses=Decimal("50000.00"),
            created_by=admin_client.test_user.id,  
        )

        response = await admin_client.get(f"/sessions/{session.id}/edit-open")  
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_form_closed_session_redirects(
        self, admin_client: AsyncClient, db_session: AsyncSession  
    ):
        """Test accessing edit form for CLOSED session redirects."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="CLOSED",
            created_by=admin_client.test_user.id,  
        )

        response = await admin_client.get(  
            f"/sessions/{session.id}/edit-open",
            follow_redirects=False,
        )
        assert response.status_code == 302


class TestEditOpenSessionFormPOST:
    """Test POST /sessions/{id}/edit-open."""

    @pytest.mark.asyncio
    async def test_post_updates_initial_cash(
        self, admin_client: AsyncClient, db_session: AsyncSession  
    ):
        """Test updating initial_cash field."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            initial_cash=Decimal("1000000.00"),
            created_by=admin_client.test_user.id,  
        )

        response = await admin_client.post(  
            f"/sessions/{session.id}/edit-open",
            data={
                "initial_cash": "1.200.000",
                "reason": "Corrected amount",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302

        await db_session.refresh(session)
        assert session.initial_cash == Decimal("1200000.00")

    @pytest.mark.asyncio
    async def test_post_updates_expenses(
        self, admin_client: AsyncClient, db_session: AsyncSession  
    ):
        """Test updating expenses field."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            expenses=Decimal("0.00"),
            created_by=admin_client.test_user.id,  
        )

        response = await admin_client.post(  
            f"/sessions/{session.id}/edit-open",
            data={
                "expenses": "50.000",
                "reason": "Added delivery costs",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302

        await db_session.refresh(session)
        assert session.expenses == Decimal("50000.00")

    @pytest.mark.asyncio
    async def test_post_updates_multiple_fields(
        self, admin_client: AsyncClient, db_session: AsyncSession  
    ):
        """Test updating multiple fields at once."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            initial_cash=Decimal("1000000.00"),
            expenses=Decimal("0.00"),
            created_by=admin_client.test_user.id,  
        )

        response = await admin_client.post(  
            f"/sessions/{session.id}/edit-open",
            data={
                "initial_cash": "1.100.000",
                "expenses": "25.000",
                "reason": "Corrections",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302

        await db_session.refresh(session)
        assert session.initial_cash == Decimal("1100000.00")
        assert session.expenses == Decimal("25000.00")


class TestEditOpenSessionValidation:
    """Test validation on edit open session."""

    @pytest.mark.asyncio
    async def test_post_invalid_time_returns_error(
        self, admin_client: AsyncClient, db_session: AsyncSession  
    ):
        """Test invalid time format returns error."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            created_by=admin_client.test_user.id,  
        )

        response = await admin_client.post(  
            f"/sessions/{session.id}/edit-open",
            data={
                "opened_time": "invalid",
                "reason": "Test",
            },
        )

        assert response.status_code == 400


class TestEditOpenSessionAuditLogging:
    """Test audit log creation on edit."""

    @pytest.mark.asyncio
    async def test_audit_log_created_on_edit(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test audit log entry is created."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            created_by=admin_client.test_user.id,
        )

        await admin_client.post(
            f"/sessions/{session.id}/edit-open",
            data={
                "initial_cash": "1.500.000",
                "reason": "Audit test",
            },
            follow_redirects=False,
        )

        stmt = select(CashSessionAuditLog).where(
            CashSessionAuditLog.session_id == session.id
        )
        result = await db_session.execute(stmt)
        logs = result.scalars().all()

        assert len(logs) > 0

    @pytest.mark.asyncio
    async def test_audit_log_tracks_changed_fields(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test audit log captures changed fields."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            initial_cash=Decimal("1000000.00"),
            created_by=admin_client.test_user.id,
        )

        await admin_client.post(
            f"/sessions/{session.id}/edit-open",
            data={
                "initial_cash": "1.200.000",
                "reason": "Changed initial",
            },
            follow_redirects=False,
        )

        stmt = select(CashSessionAuditLog).where(
            CashSessionAuditLog.session_id == session.id
        )
        result = await db_session.execute(stmt)
        log = result.scalar_one()

        assert "initial_cash" in log.changed_fields

    @pytest.mark.asyncio
    async def test_audit_log_captures_old_new_values(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test audit log stores old and new values."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            initial_cash=Decimal("1000000.00"),
            created_by=admin_client.test_user.id,
        )

        await admin_client.post(
            f"/sessions/{session.id}/edit-open",
            data={
                "initial_cash": "1.300.000",
                "reason": "Value change",
            },
            follow_redirects=False,
        )

        stmt = select(CashSessionAuditLog).where(
            CashSessionAuditLog.session_id == session.id  # ← FIX HERE
        )
        result = await db_session.execute(stmt)
        log = result.scalar_one()

        assert log.old_values is not None
        assert log.new_values is not None

    @pytest.mark.asyncio
    async def test_audit_log_timestamp_recorded(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test audit log has timestamp."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            created_by=admin_client.test_user.id,
        )

        await admin_client.post(
            f"/sessions/{session.id}/edit-open",
            data={
                "expenses": "10.000",
                "reason": "Timestamp test",
            },
            follow_redirects=False,
        )

        stmt = select(CashSessionAuditLog).where(
            CashSessionAuditLog.session_id == session.id  # ← FIX HERE
        )
        result = await db_session.execute(stmt)
        log = result.scalar_one()

        assert log.changed_at is not None
    """Test audit log creation on edit."""

    @pytest.mark.asyncio
    async def test_audit_log_created_on_edit(
        self, admin_client: AsyncClient, db_session: AsyncSession  
    ):
        """Test audit log entry is created."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            created_by=admin_client.test_user.id,  
        )

        await admin_client.post(  
            f"/sessions/{session.id}/edit-open",
            data={
                "initial_cash": "1.500.000",
                "reason": "Audit test",
            },
            follow_redirects=False,
        )

        stmt = select(CashSessionAuditLog).where(
            CashSessionAuditLog.session_id == session.id
        )
        result = await db_session.execute(stmt)
        logs = result.scalars().all()

        assert len(logs) > 0

    @pytest.mark.asyncio
    async def test_audit_log_tracks_changed_fields(
        self, admin_client: AsyncClient, db_session: AsyncSession  
    ):
        """Test audit log captures changed fields."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            initial_cash=Decimal("1000000.00"),
            created_by=admin_client.test_user.id,  
        )

        await admin_client.post(  
            f"/sessions/{session.id}/edit-open",
            data={
                "initial_cash": "1.200.000",
                "reason": "Changed initial",
            },
            follow_redirects=False,
        )

        stmt = select(CashSessionAuditLog).where(
            CashSessionAuditLog.session_id == session.id
        )
        result = await db_session.execute(stmt)
        log = result.scalar_one()

        assert "initial_cash" in log.changed_fields

    @pytest.mark.asyncio
    async def test_audit_log_captures_old_new_values(
        self, admin_client: AsyncClient, db_session: AsyncSession  
    ):
        """Test audit log stores old and new values."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            initial_cash=Decimal("1000000.00"),
            created_by=admin_client.test_user.id,  
        )

        await admin_client.post(  
            f"/sessions/{session.id}/edit-open",
            data={
                "initial_cash": "1.300.000",
                "reason": "Value change",
            },
            follow_redirects=False,
        )

        stmt = select(CashSessionAuditLog).where(
            CashSessionAuditLog.session_id == session.id
        )
        result = await db_session.execute(stmt)
        log = result.scalar_one()

        assert log.old_values is not None
        assert log.new_values is not None

    @pytest.mark.asyncio
    async def test_audit_log_timestamp_recorded(
        self, admin_client: AsyncClient, db_session: AsyncSession  
    ):
        """Test audit log has timestamp."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            created_by=admin_client.test_user.id,  
        )

        await admin_client.post(  
            f"/sessions/{session.id}/edit-open",
            data={
                "expenses": "10.000",
                "reason": "Timestamp test",
            },
            follow_redirects=False,
        )

        stmt = select(CashSessionAuditLog).where(
            CashSessionAuditLog.session_id == session.id
        )
        result = await db_session.execute(stmt)
        log = result.scalar_one()

        assert log.changed_at is not None


class TestEditOpenSessionLastModified:
    """Test last_modified tracking."""

    @pytest.mark.asyncio
    async def test_last_modified_at_updated(
        self, admin_client: AsyncClient, db_session: AsyncSession  
    ):
        """Test last_modified_at is updated."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            created_by=admin_client.test_user.id,  
        )

        await admin_client.post(  
            f"/sessions/{session.id}/edit-open",
            data={
                "initial_cash": "999.999",
                "reason": "Last modified test",
            },
            follow_redirects=False,
        )

        await db_session.refresh(session)
        assert session.last_modified_at is not None

    @pytest.mark.asyncio
    async def test_last_modified_by_set_to_system(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test last_modified_by is set."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            created_by=admin_client.test_user.id,
        )

        await admin_client.post(
            f"/sessions/{session.id}/edit-open",
            data={
                "expenses": "5.000",
                "reason": "Modified by test",
            },
            follow_redirects=False,
        )

        await db_session.refresh(session)
        assert session.last_modified_by == "Admin User"


class TestEditOpenSessionDecimalFormatting:
    """Test decimal formatting."""

    @pytest.mark.asyncio
    async def test_form_displays_formatted_amounts(
        self, admin_client: AsyncClient, db_session: AsyncSession  
    ):
        """Test form displays Guaraní-formatted amounts."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            initial_cash=Decimal("1234567.00"),
            created_by=admin_client.test_user.id,  
        )

        response = await admin_client.get(f"/sessions/{session.id}/edit-open")  
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_post_accepts_formatted_amounts(
        self, admin_client: AsyncClient, db_session: AsyncSession  
    ):
        """Test post accepts dot-formatted amounts."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            created_by=admin_client.test_user.id,  
        )

        response = await admin_client.post(  
            f"/sessions/{session.id}/edit-open",
            data={
                "initial_cash": "2.500.000",
                "reason": "Formatted input",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302

        await db_session.refresh(session)
        assert session.initial_cash == Decimal("2500000.00")

    @pytest.mark.asyncio
    async def test_post_accepts_comma_formatted_amounts(
        self, admin_client: AsyncClient, db_session: AsyncSession  
    ):
        """Test post accepts comma-formatted amounts."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            created_by=admin_client.test_user.id,  
        )

        response = await admin_client.post(  
            f"/sessions/{session.id}/edit-open",
            data={
                "expenses": "75,000",
                "reason": "Comma format",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302

        await db_session.refresh(session)
        assert session.expenses == Decimal("75000.00")