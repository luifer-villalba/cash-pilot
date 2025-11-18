"""Tests for business endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import BusinessFactory


class TestCreateBusiness:
    """Test business creation."""

    @pytest.mark.asyncio
    async def test_create_business_success(self, client: AsyncClient, db_session: AsyncSession):
        """Test creating a business via form (HTML endpoint)."""
        response = await client.post(
            "/businesses",
            data={
                "name": "Farmacia Centro",
                "address": "Avenida Principal 456",
                "phone": "+595971234567",
            },
            follow_redirects=False,
        )

        # Should redirect to /businesses list on success
        assert response.status_code == 302
        assert "/businesses" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_create_business_minimal_data(self, client: AsyncClient, db_session: AsyncSession):
        """Test creating business with only required name field."""
        response = await client.post(
            "/businesses",
            data={"name": "Farmacia Simple"},
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "/businesses" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_create_business_missing_name(self, client: AsyncClient):
        """Test that creation without name fails with validation error."""
        response = await client.post(
            "/businesses",
            data={
                "address": "Some Address",
                "phone": "+595971234567",
            },
            follow_redirects=False,
        )

        # FastAPI returns 422 for validation errors
        assert response.status_code == 422


class TestGetBusiness:
    """Test retrieving business details."""

    @pytest.mark.asyncio
    async def test_get_business_page_exists(self, client: AsyncClient, db_session: AsyncSession):
        """Test that businesses list page exists and is accessible."""
        business = await BusinessFactory.create(db_session)

        response = await client.get("/businesses")

        # Should return the businesses list page
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


class TestUpdateBusiness:
    """Test updating businesses."""

    @pytest.mark.asyncio
    async def test_update_business_not_yet_implemented(
            self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test that edit endpoint now exists (MIZ-XXX completed)."""
        business = await BusinessFactory.create(db_session)

        # Edit endpoint now exists!
        response = await client.get(f"/businesses/{business.id}/edit", follow_redirects=False)

        # Should render the edit form
        assert response.status_code == 200
        html = response.text
        assert "Edit Business" in html

class TestListBusinesses:
    """Test listing businesses."""

    @pytest.mark.asyncio
    async def test_list_businesses_html(self, client: AsyncClient, db_session: AsyncSession):
        """Test listing businesses returns HTML."""
        await BusinessFactory.create(db_session, name="Farmacia 1")
        await BusinessFactory.create(db_session, name="Farmacia 2")

        response = await client.get("/businesses")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        # At least one business name should be in the response
        assert "Farmacia 1" in response.text or "Farmacia 2" in response.text

    @pytest.mark.asyncio
    async def test_list_businesses_empty(self, client: AsyncClient):
        """Test listing when no businesses exist."""
        response = await client.get("/businesses")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_create_form_page(self, client: AsyncClient):
        """Test that create business form page exists."""
        response = await client.get("/businesses/new")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
