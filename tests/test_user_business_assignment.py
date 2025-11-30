# File: tests/test_user_business_assignment.py
"""Tests for user business assignment endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models.user import UserRole
from tests.factories import BusinessFactory, UserFactory


class TestAssignBusinessesToUser:
    """Test POST /users/{user_id}/assign-businesses endpoint."""

    @pytest.mark.asyncio
    async def test_admin_can_assign_businesses(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test admin can assign businesses to a user."""
        # Create cashier and businesses
        cashier = await UserFactory.create(db_session, role=UserRole.CASHIER)
        business1 = await BusinessFactory.create(db_session, name="Farmacia A")
        business2 = await BusinessFactory.create(db_session, name="Farmacia B")

        response = await admin_client.post(
            f"/users/{cashier.id}/assign-businesses",
            json={"business_ids": [str(business1.id), str(business2.id)]},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["businesses"]) == 2
        business_names = {b["name"] for b in data["businesses"]}
        assert business_names == {"Farmacia A", "Farmacia B"}

    @pytest.mark.asyncio
    async def test_assignment_is_idempotent(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test reassigning replaces previous assignments."""
        cashier = await UserFactory.create(db_session, role=UserRole.CASHIER)
        business1 = await BusinessFactory.create(db_session, name="Farmacia A")
        business2 = await BusinessFactory.create(db_session, name="Farmacia B")
        business3 = await BusinessFactory.create(db_session, name="Farmacia C")

        # First assignment
        await admin_client.post(
            f"/users/{cashier.id}/assign-businesses",
            json={"business_ids": [str(business1.id), str(business2.id)]},
        )

        # Second assignment (replace)
        response = await admin_client.post(
            f"/users/{cashier.id}/assign-businesses",
            json={"business_ids": [str(business3.id)]},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["businesses"]) == 1
        assert data["businesses"][0]["name"] == "Farmacia C"

    @pytest.mark.asyncio
    async def test_nonexistent_business_returns_404(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test assigning nonexistent business returns 404."""
        cashier = await UserFactory.create(db_session, role=UserRole.CASHIER)
        fake_uuid = "12345678-1234-1234-1234-123456789012"

        response = await admin_client.post(
            f"/users/{cashier.id}/assign-businesses",
            json={"business_ids": [fake_uuid]},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_nonexistent_user_returns_404(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test assigning to nonexistent user returns 404."""
        business = await BusinessFactory.create(db_session)
        fake_uuid = "12345678-1234-1234-1234-123456789012"

        response = await admin_client.post(
            f"/users/{fake_uuid}/assign-businesses",
            json={"business_ids": [str(business.id)]},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_cashier_cannot_assign_businesses(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test cashiers cannot assign businesses (admin only)."""
        business = await BusinessFactory.create(db_session)

        response = await client.post(
            f"/users/{client.test_user.id}/assign-businesses",
            json={"business_ids": [str(business.id)]},
        )

        assert response.status_code == 403


class TestSessionCreationRBAC:
    """Test session creation with RBAC business assignment."""

    @pytest.mark.asyncio
    async def test_admin_creates_session_any_business(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test admin can create session for any business without assignment."""
        business = await BusinessFactory.create(db_session, name="Unassigned Farmacia")

        response = await admin_client.post(
            "/cash-sessions",
            json={
                "business_id": str(business.id),
                "initial_cash": "500000.00",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["cashier_id"] == str(admin_client.test_user.id)
        assert data["created_by_user"]["id"] == str(admin_client.test_user.id)

    @pytest.mark.asyncio
    async def test_admin_creates_session_for_another_cashier(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test admin can create session for another cashier using for_cashier_id."""
        cashier = await UserFactory.create(db_session, role=UserRole.CASHIER)
        business = await BusinessFactory.create(db_session)

        response = await admin_client.post(
            "/cash-sessions",
            json={
                "business_id": str(business.id),
                "for_cashier_id": str(cashier.id),
                "initial_cash": "500000.00",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["cashier_id"] == str(cashier.id)
        assert data["created_by_user"]["id"] == str(admin_client.test_user.id)

    @pytest.mark.asyncio
    async def test_cashier_creates_session_assigned_business(
        self, client: AsyncClient, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test cashier can create session for assigned business."""
        # Create cashier and business
        cashier = client.test_user
        business = await BusinessFactory.create(db_session, name="Assigned Farmacia")

        # Assign business (as admin)
        await admin_client.post(
            f"/users/{cashier.id}/assign-businesses",
            json={"business_ids": [str(business.id)]},
        )

        # Cashier creates session
        response = await client.post(
            "/cash-sessions",
            json={
                "business_id": str(business.id),
                "initial_cash": "500000.00",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["cashier_id"] == str(cashier.id)
        assert data["created_by_user"]["id"] == str(cashier.id)

    @pytest.mark.asyncio
    async def test_cashier_cannot_create_for_unassigned_business(
        self, client: AsyncClient, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test cashier cannot create session for unassigned business."""
        cashier = client.test_user
        assigned_business = await BusinessFactory.create(db_session, name="Assigned")
        unassigned_business = await BusinessFactory.create(db_session, name="Unassigned")

        # Assign only one business
        await admin_client.post(
            f"/users/{cashier.id}/assign-businesses",
            json={"business_ids": [str(assigned_business.id)]},
        )

        # Try to create session for unassigned business
        response = await client.post(
            "/cash-sessions",
            json={
                "business_id": str(unassigned_business.id),
                "initial_cash": "500000.00",
            },
        )

        assert response.status_code == 403
        assert "not assigned" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_cashier_with_no_businesses_cannot_create_session(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test cashier with 0 assigned businesses gets proper error."""
        business = await BusinessFactory.create(db_session)

        response = await client.post(
            "/cash-sessions",
            json={
                "business_id": str(business.id),
                "initial_cash": "500000.00",
            },
        )

        assert response.status_code == 403
        assert "No businesses assigned" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_cashier_cannot_use_for_cashier_id(
        self, client: AsyncClient, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test cashier cannot create session for another user."""
        cashier1 = client.test_user
        cashier2 = await UserFactory.create(db_session, role=UserRole.CASHIER)
        business = await BusinessFactory.create(db_session)

        # Assign business to cashier1
        await admin_client.post(
            f"/users/{cashier1.id}/assign-businesses",
            json={"business_ids": [str(business.id)]},
        )

        # Cashier1 tries to create for cashier2
        response = await client.post(
            "/cash-sessions",
            json={
                "business_id": str(business.id),
                "for_cashier_id": str(cashier2.id),
                "initial_cash": "500000.00",
            },
        )

        assert response.status_code == 403
        assert "cannot create sessions for other users" in response.json()["detail"]


class TestListSessionsRBAC:
    """Test list sessions filtering by role."""

    @pytest.mark.asyncio
    async def test_admin_sees_all_sessions(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test admin can see all sessions regardless of cashier."""
        from tests.factories import CashSessionFactory

        cashier1 = await UserFactory.create(
            db_session,
            role=UserRole.CASHIER,
            email="cashier1_admin_test@test.com"
        )
        cashier2 = await UserFactory.create(
            db_session,
            role=UserRole.CASHIER,
            email="cashier2_admin_test@test.com"
        )
        business = await BusinessFactory.create(db_session)

        # Create sessions for different cashiers
        await CashSessionFactory.create(db_session, business_id=business.id, cashier_id=cashier1.id)
        await CashSessionFactory.create(db_session, business_id=business.id, cashier_id=cashier2.id)

        response = await admin_client.get("/cash-sessions")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_cashier_sees_only_own_sessions(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test cashier only sees sessions where they are the cashier."""
        from tests.factories import CashSessionFactory

        cashier1 = client.test_user
        cashier2 = await UserFactory.create(db_session, role=UserRole.CASHIER)
        business = await BusinessFactory.create(db_session)

        # Create sessions for both cashiers
        await CashSessionFactory.create(db_session, business_id=business.id, cashier_id=cashier1.id)
        await CashSessionFactory.create(db_session, business_id=business.id, cashier_id=cashier2.id)

        response = await client.get("/cash-sessions")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["cashier_id"] == str(cashier1.id)
