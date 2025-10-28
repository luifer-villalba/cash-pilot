"""Tests for Business API endpoints."""

import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def business_id(client: AsyncClient) -> str:
    """Create a business for testing."""
    business_data = {
        "name": "Farmacia Test",
        "address": "Calle Test 123",
        "phone": "+595972000000",
    }
    response = await client.post("/businesses", json=business_data)
    assert response.status_code == 201
    return response.json()["id"]


class TestCreateBusiness:
    """Test business creation endpoint."""

    async def test_create_business_success(self, client: AsyncClient):
        """Test creating a business returns 201."""
        business_data = {
            "name": "Farmacia Centro",
            "address": "Avenida Principal 456",
            "phone": "+595971234567",
        }
        response = await client.post("/businesses", json=business_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Farmacia Centro"
        assert "id" in data

    async def test_create_business_minimal_data(self, client: AsyncClient):
        """Test creating business with only required name field."""
        business_data = {"name": "Farmacia Simple"}
        response = await client.post("/businesses", json=business_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Farmacia Simple"


class TestGetBusiness:
    """Test business retrieval endpoint."""

    async def test_get_business_success(self, client: AsyncClient, business_id: str):
        """Test getting existing business returns 200."""
        response = await client.get(f"/businesses/{business_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == business_id

    async def test_get_business_not_found(self, client: AsyncClient):
        """Test getting non-existent business returns 404."""
        response = await client.get("/businesses/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 404
        data = response.json()
        assert data["code"] == "NOT_FOUND"


class TestUpdateBusiness:
    """Test business update endpoint."""

    async def test_update_business_success(self, client: AsyncClient, business_id: str):
        """Test updating business returns 200."""
        update_data = {"name": "Farmacia Actualizada"}
        response = await client.put(f"/businesses/{business_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Farmacia Actualizada"

    async def test_update_business_not_found(self, client: AsyncClient):
        """Test updating non-existent business returns 404."""
        update_data = {"name": "Updated Name"}
        response = await client.put(
            "/businesses/00000000-0000-0000-0000-000000000000", json=update_data
        )

        assert response.status_code == 404
        data = response.json()
        assert data["code"] == "NOT_FOUND"
