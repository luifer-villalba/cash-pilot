"""Tests for category endpoints."""

import pytest
from fastapi.testclient import TestClient

from cashpilot.main import create_app


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    app = create_app()
    return TestClient(app)


def test_list_categories_returns_seeded_data(client: TestClient) -> None:
    """Test that seeded categories are returned."""
    response = client.get("/api/v1/categories")
    
    assert response.status_code == 200
    categories = response.json()
    assert len(categories) == 11
    
    # Check a few expected categories
    names = [c["name"] for c in categories]
    assert "Food" in names
    assert "Salary" in names


def test_filter_categories_by_type(client: TestClient) -> None:
    """Test filtering categories by type."""
    response = client.get("/api/v1/categories?type=INCOME")
    
    assert response.status_code == 200
    categories = response.json()
    
    # All should be INCOME type
    for cat in categories:
        assert cat["type"] in ["INCOME", "BOTH"]


def test_create_duplicate_category_fails(client: TestClient) -> None:
    """Test that duplicate category name+type is rejected."""
    response = client.post(
        "/api/v1/categories",
        params={"name": "Food", "type": "EXPENSE"}
    )
    
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]