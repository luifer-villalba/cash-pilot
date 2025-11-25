"""Tests for Business CRUD operations - updated for RBAC."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import BusinessFactory


class TestListBusinesses:
    """Test listing businesses."""

    @pytest.mark.asyncio
    async def test_list_businesses_returns_list(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test GET /businesses returns list of businesses."""
        await BusinessFactory.create(db_session, name="Farmacia A")
        await BusinessFactory.create(db_session, name="Farmacia B")

        response = await client.get("/businesses")

        assert response.status_code == 200
        # Route returns HTML frontend, check for content
        assert "Farmacia A" in response.text or "Farmacia B" in response.text

    @pytest.mark.asyncio
    async def test_list_businesses_empty(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test list when no businesses exist."""
        response = await client.get("/businesses")

        assert response.status_code == 200
        # Should still render page even if empty
        html = response.text
        assert "Businesses" in html or "businesses" in html.lower()

    @pytest.mark.asyncio
    async def test_create_form_page_blocked_for_cashier(self, client: AsyncClient):
        """Test cashier gets 403 on /businesses/new form page."""
        response = await client.get("/businesses/new", follow_redirects=False)

        # Cashier (default test_user) is blocked by require_admin
        assert response.status_code == 403


class TestCreateBusiness:
    """Test business creation - admin only."""

    @pytest.mark.asyncio
    async def test_cashier_cannot_create_business(self, client: AsyncClient):
        """Test cashier gets 403 on POST to create business."""
        response = await client.post(
            "/businesses",
            data={
                "name": "Test Business",
                "address": "123 Main St",
                "phone": "123-456-7890",
            },
            follow_redirects=False,
        )

        # Cashier blocked by require_admin
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_cashier_cannot_create_with_minimal_data(self, client: AsyncClient):
        """Test cashier gets 403 with minimal data."""
        response = await client.post(
            "/businesses",
            data={"name": "Minimal Business"},
            follow_redirects=False,
        )

        # Still 403, same reason
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_cashier_cannot_create_missing_required_field(
        self, client: AsyncClient
    ):
        """Test cashier gets 403 even with missing fields."""
        # Don't include name (required field)
        response = await client.post(
            "/businesses",
            data={"address": "No Name St"},
            follow_redirects=False,
        )

        # Still 403 due to RBAC, not validation
        assert response.status_code == 403


class TestUpdateBusiness:
    """Test business update - admin only."""

    @pytest.mark.asyncio
    async def test_cashier_cannot_edit_business_form(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test cashier gets 403 on edit form."""
        business = await BusinessFactory.create(db_session, name="Original")

        response = await client.get(
            f"/businesses/{business.id}/edit", follow_redirects=False
        )

        # Blocked by require_admin
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_cashier_cannot_update_business(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test cashier gets 403 on PUT business."""
        business = await BusinessFactory.create(db_session, name="Original")

        response = await client.put(
            f"/businesses/{business.id}",
            json={"name": "Updated"},
        )

        assert response.status_code == 403


class TestGetBusiness:
    """Test getting a single business."""

    @pytest.mark.asyncio
    async def test_get_business_success(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test GET /businesses/{id} returns business."""
        business = await BusinessFactory.create(
            db_session, name="Test Business", address="123 Main St"
        )

        response = await client.get(f"/businesses/{business.id}")

        assert response.status_code == 200
        # Check if JSON or HTML response
        try:
            data = response.json()
            assert data["name"] == "Test Business"
        except ValueError:
            # HTML response, check content
            assert "Test Business" in response.text or "123 Main St" in response.text

    @pytest.mark.asyncio
    async def test_get_business_not_found(self, client: AsyncClient):
        """Test GET non-existent business."""
        response = await client.get("/businesses/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 404
