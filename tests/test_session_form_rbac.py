# File: tests/test_session_form_rbac.py
"""Tests for role-aware session creation form."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models.user import UserRole
from tests.factories import BusinessFactory, UserFactory


class TestSessionFormRBAC:
    """Test session creation form with role-based business assignment."""

    @pytest.mark.asyncio
    async def test_admin_sees_all_businesses_dropdown(
            self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test admin sees all businesses in dropdown."""
        await BusinessFactory.create(db_session, name="Farmacia A")
        await BusinessFactory.create(db_session, name="Farmacia B")

        response = await admin_client.get("/sessions/create")

        assert response.status_code == 200
        assert "Farmacia A" in response.text
        assert "Farmacia B" in response.text
        assert 'name="business_id"' in response.text
        assert 'name="cashier_id"' in response.text  # Admin has cashier dropdown

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
        business = await BusinessFactory.create(db_session, name="Mi Farmacia")

        # Assign business to cashier
        await client.test_user.businesses.append(business)
        await db_session.commit()
        await db_session.refresh(client.test_user, ["businesses"])

        response = await client.get("/sessions/create")

        assert response.status_code == 200
        assert "Mi Farmacia" in response.text
        assert f'value="{business.id}"' in response.text  # Hidden input
        assert "disabled" in response.text  # Business field disabled
        assert client.test_user.display_name in response.text  # Cashier name shown

    @pytest.mark.asyncio
    async def test_cashier_with_multiple_businesses_sees_dropdown(
            self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test cashier with 2+ businesses sees dropdown of assigned only."""
        business1 = await BusinessFactory.create(db_session, name="Farmacia 1")
        business2 = await BusinessFactory.create(db_session, name="Farmacia 2")
        business3 = await BusinessFactory.create(db_session, name="Farmacia 3 (Unassigned)")

        # Assign only business1 and business2
        await client.test_user.businesses.extend([business1, business2])
        await db_session.commit()
        await db_session.refresh(client.test_user, ["businesses"])

        response = await client.get("/sessions/create")

        assert response.status_code == 200
        assert "Farmacia 1" in response.text
        assert "Farmacia 2" in response.text
        assert "Farmacia 3" not in response.text  # Unassigned business not shown
        assert 'name="business_id"' in response.text
        assert 'select' in response.text.lower()

    @pytest.mark.asyncio
    async def test_cashier_name_readonly_for_cashiers(
            self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test cashier sees own name as read-only."""
        business = await BusinessFactory.create(db_session)
        await client.test_user.businesses.append(business)
        await db_session.commit()

        response = await client.get("/sessions/create")

        assert response.status_code == 200
        assert client.test_user.display_name in response.text
        assert "readonly" in response.text or "disabled" in response.text
