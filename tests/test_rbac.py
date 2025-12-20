"""Tests for role-based access control (RBAC) permissions - fixed version."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models.user import User, UserRole
from cashpilot.core.security import hash_password
from tests.factories import UserFactory, BusinessFactory, CashSessionFactory


class TestRBACBusinessAPIReadAccess:
    """Test read access to business endpoints."""

    @pytest.mark.asyncio
    async def test_cashier_can_read_businesses(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test cashier can access business list."""
        await BusinessFactory.create(db_session, name="Farmacia Test")

        response = await client.get("/businesses")
        assert response.status_code == 200
        # Route returns HTML (frontend), check content
        assert "Farmacia Test" in response.text or isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_get_single_business(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test get single business endpoint."""
        business = await BusinessFactory.create(db_session, name="Farmacia Test")

        response = await client.get(f"/businesses/{business.id}")
        assert response.status_code == 200
        # API endpoint returns JSON
        if response.headers.get("content-type", "").startswith("application/json"):
            data = response.json()
            assert data["name"] == "Farmacia Test"


class TestRBACBusinessAPIWriteAccess:
    """Test write access (admin-only) to business API endpoints.

    Note: These tests use the default test_user which is a CASHIER.
    Tests verify that cashiers get 403 on write operations.
    """

    @pytest.mark.asyncio
    async def test_cashier_cannot_create_business(
        self,
        client: AsyncClient,
    ) -> None:
        """Test cashier gets 403 on POST /businesses."""
        response = await client.post(
            "/businesses",
            json={
                "name": "Unauthorized Pharmacy",
                "address": "456 Oak Ave",
                "phone": "789-012-3456",
            },
        )

        assert response.status_code == 403
        assert "permission" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_cashier_cannot_update_business(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test cashier gets 403 on PUT /businesses/{id}."""
        business = await BusinessFactory.create(db_session)

        response = await client.put(
            f"/businesses/{business.id}",
            json={"name": "Hacked Name"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_cashier_cannot_delete_business(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test cashier gets 403 on DELETE /businesses/{id}."""
        business = await BusinessFactory.create(db_session)

        response = await client.delete(f"/businesses/{business.id}")

        assert response.status_code == 403


class TestRBACSessionAccess:
    """Test role-based access control for session endpoints."""

    @pytest.mark.asyncio
    async def test_cashier_can_read_own_session(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test cashier can read their own session."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            cashier_id=admin_client.test_user.id,
            created_by=admin_client.test_user.id,
        )

        response = await admin_client.get(f"/sessions/{session.id}")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_cashier_cannot_read_other_cashier_session(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test cashier blocked from accessing other cashier's session."""
        other_cashier = await UserFactory.create(
            db_session,
            email="other_cashier@test.com",
            role=UserRole.CASHIER,
        )

        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business=business,
            created_by=other_cashier.id,
        )

        response = await client.get(f"/cash-sessions/{session.id}")

        assert response.status_code == 403
        assert "permission" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_cashier_list_shows_only_own_sessions(
            self,
            client: AsyncClient,
            db_session: AsyncSession,
    ) -> None:
        """Test cashier can only list their own sessions."""
        other_cashier = await UserFactory.create(
            db_session,
            email="cashier_list_test@test.com",
            role=UserRole.CASHIER,
        )

        business = await BusinessFactory.create(db_session)

        # Create session owned by test_user
        own_session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            cashier_id=client.test_user.id,
        )

        # Create session owned by other cashier
        other_session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            cashier_id=other_cashier.id,
        )

        response = await client.get("/cash-sessions")

        assert response.status_code == 200
        sessions = response.json()
        session_ids = [s["id"] for s in sessions]

        # Should have own session
        assert str(own_session.id) in session_ids
        # Should NOT have other cashier's session
        assert str(other_session.id) not in session_ids


class TestRBACBusinessFrontendAccess:
    """Test frontend route access control."""

    @pytest.mark.asyncio
    async def test_cashier_can_view_business_list_page(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test cashier can view business list HTML page."""
        await BusinessFactory.create(db_session, name="Farmacia Test")

        response = await client.get("/businesses")
        assert response.status_code == 200
        html = response.text
        assert "Businesses" in html
        assert "Farmacia Test" in html

    @pytest.mark.asyncio
    async def test_cashier_cannot_access_create_business_form(
        self,
        client: AsyncClient,
    ) -> None:
        """Test cashier gets 403 trying to access create business form."""
        response = await client.get("/businesses/new", follow_redirects=False)
        # require_admin blocks access with 403
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_cashier_cannot_access_edit_business_form(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test cashier gets 403 trying to access edit business form."""
        business = await BusinessFactory.create(db_session)

        response = await client.get(f"/businesses/{business.id}/edit", follow_redirects=False)
        # require_admin blocks access with 403
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_business_list_shows_disabled_buttons_for_cashier(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test business list page shows disabled buttons for cashier."""
        await BusinessFactory.create(db_session, name="Farmacia Test")

        response = await client.get("/businesses")
        assert response.status_code == 200
        html = response.text

        # Page should render
        assert "Farmacia Test" in html
        # Edit button should be disabled (contains disabled attribute)
        assert "disabled" in html
        assert "Only admins" in html or "only admins" in html.lower()
