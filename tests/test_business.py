"""Tests for Business API endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_business(client: AsyncClient):
    """Test creating a new business."""
    payload = {
        "name": "Farmacia Test",
        "address": "Calle Falsa 123",
        "phone": "+595 21 123-4567",
    }
    response = await client.post("/businesses", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Farmacia Test"
    assert data["address"] == "Calle Falsa 123"
    assert data["phone"] == "+595 21 123-4567"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_get_business(client: AsyncClient):
    """Test retrieving a business by ID."""
    # Create business first
    create_response = await client.post(
        "/businesses",
        json={"name": "Farmacia Get Test", "address": "Test Address"},
    )
    business_id = create_response.json()["id"]

    # Get business
    response = await client.get(f"/businesses/{business_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == business_id
    assert data["name"] == "Farmacia Get Test"
    assert data["address"] == "Test Address"


@pytest.mark.asyncio
async def test_get_business_not_found(client: AsyncClient):
    """Test getting non-existent business returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(f"/businesses/{fake_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Business not found"


@pytest.mark.asyncio
async def test_update_business(client: AsyncClient):
    """Test updating a business."""
    # Create business
    create_response = await client.post(
        "/businesses",
        json={"name": "Original Name", "address": "Original Address"},
    )
    business_id = create_response.json()["id"]

    # Update business
    update_payload = {
        "name": "Updated Name",
        "address": "Updated Address",
        "phone": "+595 21 999-8888",
    }
    response = await client.put(f"/businesses/{business_id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == business_id
    assert data["name"] == "Updated Name"
    assert data["address"] == "Updated Address"
    assert data["phone"] == "+595 21 999-8888"


@pytest.mark.asyncio
async def test_update_business_partial(client: AsyncClient):
    """Test partial update (only some fields)."""
    # Create business
    create_response = await client.post(
        "/businesses",
        json={"name": "Partial Test", "address": "Original Address", "phone": "123"},
    )
    business_id = create_response.json()["id"]

    # Update only name
    response = await client.put(f"/businesses/{business_id}", json={"name": "New Name Only"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name Only"
    assert data["address"] == "Original Address"  # Unchanged
    assert data["phone"] == "123"  # Unchanged


@pytest.mark.asyncio
async def test_update_business_not_found(client: AsyncClient):
    """Test updating non-existent business returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.put(f"/businesses/{fake_id}", json={"name": "Test"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Business not found"


@pytest.mark.asyncio
async def test_create_business_validation(client: AsyncClient):
    """Test business creation validates required fields."""
    # Missing name (required)
    response = await client.post("/businesses", json={"address": "Test"})
    assert response.status_code == 422  # Validation error
