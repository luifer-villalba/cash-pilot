# File: tests/test_session_form_rbac.py
"""Tests for role-aware session creation form."""

from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models.cash_session import CashSession
from cashpilot.models.user import UserRole
from cashpilot.models.user_business import UserBusiness
from cashpilot.utils.datetime import today_local
from tests.factories import BusinessFactory, UserFactory


class TestSessionFormRBAC:
    """Test session creation form with role-based business assignment."""

    @pytest.mark.asyncio
    async def test_admin_sees_all_businesses_dropdown(
            self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test admin sees all businesses in dropdown."""
        await BusinessFactory.create(db_session, name="Business A")
        await BusinessFactory.create(db_session, name="Business B")

        response = await admin_client.get("/sessions/create")

        assert response.status_code == 200
        assert "Business A" in response.text
        assert "Business B" in response.text
        assert 'name="business_id"' in response.text
        # Cashier field is now read-only for everyone (no dropdown)
        assert admin_client.test_user.display_name in response.text

    @pytest.mark.asyncio
    async def test_cashier_with_no_businesses_sees_error(
            self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test cashier with 0 assigned businesses sees error message."""
        response = await client.get("/sessions/create")

        assert response.status_code == 200
        assert "No businesses assigned" in response.text
        assert "Contact an administrator" in response.text
        # Form should be disabled
        assert "disabled" in response.text.lower()

    @pytest.mark.asyncio
    async def test_cashier_with_one_business_sees_prefilled(
            self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test cashier with 1 assigned business sees pre-filled field."""
        business = await BusinessFactory.create(db_session, name="Mi Business")

        # Assign business to cashier using UserBusiness
        assignment = UserBusiness(user_id=client.test_user.id, business_id=business.id)
        db_session.add(assignment)
        await db_session.commit()

        response = await client.get("/sessions/create")

        assert response.status_code == 200
        assert "Mi Business" in response.text
        assert f'value="{business.id}"' in response.text
        assert "disabled" in response.text
        assert client.test_user.display_name in response.text

    @pytest.mark.asyncio
    async def test_cashier_with_multiple_businesses_sees_dropdown(
            self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test cashier with 2+ businesses sees dropdown of assigned only."""
        business1 = await BusinessFactory.create(db_session, name="Business 1")
        business2 = await BusinessFactory.create(db_session, name="Business 2")
        business3 = await BusinessFactory.create(db_session, name="Business 3 (Unassigned)")

        # Assign only business1 and business2 using UserBusiness
        assignment1 = UserBusiness(user_id=client.test_user.id, business_id=business1.id)
        assignment2 = UserBusiness(user_id=client.test_user.id, business_id=business2.id)
        db_session.add(assignment1)
        db_session.add(assignment2)
        await db_session.commit()

        response = await client.get("/sessions/create")

        assert response.status_code == 200
        assert "Business 1" in response.text
        assert "Business 2" in response.text
        assert "Business 3" not in response.text
        assert 'name="business_id"' in response.text
        assert 'select' in response.text.lower()

    @pytest.mark.asyncio
    async def test_cashier_name_readonly_for_cashiers(
            self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test cashier sees own name as read-only."""
        business = await BusinessFactory.create(db_session)

        # Assign business using UserBusiness
        assignment = UserBusiness(user_id=client.test_user.id, business_id=business.id)
        db_session.add(assignment)
        await db_session.commit()

        response = await client.get("/sessions/create")

        assert response.status_code == 200
        assert client.test_user.display_name in response.text
        assert "readonly" in response.text or "disabled" in response.text

    @pytest.mark.asyncio
    async def test_cashier_session_date_is_disabled_with_tooltip(
            self, client: AsyncClient, db_session: AsyncSession
    ):
        """Cashier cannot edit session_date in create form and sees explanation."""
        business = await BusinessFactory.create(db_session)
        assignment = UserBusiness(user_id=client.test_user.id, business_id=business.id)
        db_session.add(assignment)
        await db_session.commit()

        response = await client.get("/sessions/create")

        assert response.status_code == 200
        assert 'name="session_date"' in response.text
        assert "Only administrators can change session date" in response.text
        assert "disabled" in response.text

    @pytest.mark.asyncio
    async def test_cashier_cannot_override_session_date_on_create(
            self, client: AsyncClient, db_session: AsyncSession
    ):
        """Server rejects cashier attempts to override session_date."""
        business = await BusinessFactory.create(db_session)
        assignment = UserBusiness(user_id=client.test_user.id, business_id=business.id)
        db_session.add(assignment)
        await db_session.commit()

        attempted_date = (today_local() - timedelta(days=1)).isoformat()
        response = await client.post(
            "/sessions",
            data={
                "business_id": str(business.id),
                "initial_cash": "500000",
                "session_date": attempted_date,
            },
            follow_redirects=False,
        )

        assert response.status_code == 400
        assert "Only administrators can change session date" in response.text

        stmt = select(CashSession).where(CashSession.cashier_id == client.test_user.id)
        result = await db_session.execute(stmt)
        sessions = result.scalars().all()
        assert len(sessions) == 0

    @pytest.mark.asyncio
    async def test_admin_can_override_session_date_on_create(
            self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Admin can override session_date during session creation."""
        business = await BusinessFactory.create(db_session)
        requested_date = today_local() - timedelta(days=1)

        response = await admin_client.post(
            "/sessions",
            data={
                "business_id": str(business.id),
                "initial_cash": "500000",
                "session_date": requested_date.isoformat(),
            },
            follow_redirects=False,
        )

        assert response.status_code == 302

        stmt = select(CashSession).where(CashSession.cashier_id == admin_client.test_user.id)
        result = await db_session.execute(stmt)
        created_session = result.scalar_one()
        assert created_session.session_date == requested_date

    @pytest.mark.asyncio
    async def test_admin_cannot_create_session_with_future_date(
            self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Admin cannot create a session with a future session_date."""
        business = await BusinessFactory.create(db_session)
        requested_date = today_local() + timedelta(days=1)

        response = await admin_client.post(
            "/sessions",
            data={
                "business_id": str(business.id),
                "initial_cash": "500000",
                "session_date": requested_date.isoformat(),
            },
            follow_redirects=False,
        )

        assert response.status_code == 400
        assert "Session date cannot be in the future" in response.text

        stmt = select(CashSession).where(CashSession.cashier_id == admin_client.test_user.id)
        result = await db_session.execute(stmt)
        sessions = result.scalars().all()
        assert len(sessions) == 0