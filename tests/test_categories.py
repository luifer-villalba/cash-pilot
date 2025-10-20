"""Tests for category endpoints."""

import pytest
# Remove the old @pytest.fixture here

# Tests use the client fixture from conftest.py automatically
def test_list_categories_returns_seeded_data(client) -> None:
    """Test that seeded categories are returned."""
    response = client.get("/api/v1/categories")
    
    assert response.status_code == 200
    categories = response.json()
    assert len(categories) >= 4  # Assuming at least 4 seeded categories
    
    names = [c["name"] for c in categories]
    assert "Food" in names
    assert "Salary" in names


def test_filter_categories_by_type(client) -> None:
    """Test filtering categories by type."""
    response = client.get("/api/v1/categories?type=INCOME")
    
    assert response.status_code == 200
    categories = response.json()
    
    for cat in categories:
        assert cat["type"] in ["INCOME", "BOTH"]


def test_create_duplicate_category_fails(client) -> None:
    """Test that duplicate category name+type is rejected."""
    # First create one
    client.post("/api/v1/categories", params={"name": "TestCat", "type": "EXPENSE"})
    
    response = client.post(
        "/api/v1/categories",
        params={"name": "TestCat", "type": "EXPENSE"}
    )
    
    assert response.status_code == 409