"""Tests for Business frontend routes."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from .factories import BusinessFactory


class TestBusinessListPage:
    """Test business list page rendering."""

    async def test_list_page_renders(self, client: AsyncClient):
        """Test GET /businesses renders list page."""
        response = await client.get("/businesses")

        assert response.status_code == 200
        html = response.text
        assert "Businesses" in html
        assert "New Business" in html

    async def test_list_displays_businesses(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test list page displays all businesses."""
        await BusinessFactory.create(db_session, name="Farmacia A")
        await BusinessFactory.create(db_session, name="Farmacia B")

        response = await client.get("/businesses")

        assert response.status_code == 200
        html = response.text
        assert "Farmacia A" in html
        assert "Farmacia B" in html


class TestCreateBusinessPage:
    """Test business creation page."""

    async def test_create_page_renders(self, client: AsyncClient):
        """Test GET /businesses/new renders form."""
        response = await client.get("/businesses/new")

        assert response.status_code == 200
        html = response.text
        assert "Create New Business" in html
        assert 'name="name"' in html

    async def test_create_business_via_form(self, client: AsyncClient):
        """Test POST /businesses creates business."""
        response = await client.post(
            "/businesses",
            data={
                "name": "Farmacia Nueva",
                "address": "Calle Test 123",
                "phone": "+595972000000",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302
        location = response.headers["location"]
        assert "/businesses/" in location
        assert "/edit" in location


class TestEditBusinessPage:
    """Test business edit page."""

    async def test_edit_page_renders(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test GET /businesses/{id}/edit renders form."""
        business = await BusinessFactory.create(db_session, name="Farmacia Test")

        response = await client.get(f"/businesses/{business.id}/edit")

        assert response.status_code == 200
        html = response.text
        assert "Edit Business" in html
        assert "Farmacia Test" in html
        assert "Manage Cashiers" in html

    async def test_update_business_via_form(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test POST updates business."""
        business = await BusinessFactory.create(db_session, name="Old Name")

        response = await client.post(
            f"/businesses/{business.id}",
            data={
                "name": "New Name",
                "address": "New Address",
                "is_active": "on",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert f"/businesses/{business.id}/edit" in response.headers["location"]


class TestCashierManagement:
    """Test cashier add/remove via forms."""

    async def test_add_cashier_via_form(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test adding cashier via form."""
        business = await BusinessFactory.create(db_session, cashiers=[])

        response = await client.post(
            f"/businesses/{business.id}/cashiers/add",
            data={"cashier_name": "María López"},
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert f"/businesses/{business.id}/edit" in response.headers["location"]

    async def test_remove_cashier_via_form(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test removing cashier via form."""
        business = await BusinessFactory.create(
            db_session, cashiers=["María López", "Juan Pérez"]
        )

        response = await client.post(
            f"/businesses/{business.id}/cashiers/remove",
            data={"cashier_name": "María López"},
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert f"/businesses/{business.id}/edit" in response.headers["location"]
