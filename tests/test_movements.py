"""
Comprehensive tests for Movement CRUD endpoints.
Tests all 5 endpoints with various scenarios.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.main import create_app
from cashpilot.models.enums import MovementType
from cashpilot.models.movement import Movement


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    app = create_app()
    return TestClient(app)


# ==========================================
# POST /api/v1/movements - CREATE
# ==========================================


def test_create_movement_income(client: TestClient) -> None:
    """Test creating an income movement."""
    payload = {
        "occurred_at": "2025-10-20T10:00:00Z",
        "type": "INCOME",
        "amount_gs": 150000,
        "description": "Salary October",
        "category": "Salary",
    }
    
    response = client.post("/api/v1/movements", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "INCOME"
    assert data["amount_gs"] == 150000
    assert data["description"] == "Salary October"
    assert data["category"] == "Salary"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_movement_expense(client: TestClient) -> None:
    """Test creating an expense movement."""
    payload = {
        "occurred_at": "2025-10-20T14:30:00Z",
        "type": "EXPENSE",
        "amount_gs": 50000,
        "description": "Grocery shopping",
        "category": "Groceries",
    }
    
    response = client.post("/api/v1/movements", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "EXPENSE"
    assert data["amount_gs"] == 50000


def test_create_movement_negative_amount_fails(client: TestClient) -> None:
    """Test that negative amounts are rejected."""
    payload = {
        "occurred_at": "2025-10-20T10:00:00Z",
        "type": "INCOME",
        "amount_gs": -1000,
        "description": "Invalid negative amount",
    }
    
    response = client.post("/api/v1/movements", json=payload)
    
    assert response.status_code == 422  # Validation error


def test_create_movement_invalid_type_fails(client: TestClient) -> None:
    """Test that invalid movement types are rejected."""
    payload = {
        "occurred_at": "2025-10-20T10:00:00Z",
        "type": "INVALID_TYPE",
        "amount_gs": 1000,
    }
    
    response = client.post("/api/v1/movements", json=payload)
    
    assert response.status_code == 422


# ==========================================
# GET /api/v1/movements - LIST
# ==========================================


def test_list_movements_empty(client: TestClient) -> None:
    """Test listing movements when database is empty."""
    response = client.get("/api/v1/movements")
    
    assert response.status_code == 200
    assert response.json() == []


def test_list_movements_with_pagination(client: TestClient) -> None:
    """Test pagination with limit and offset."""
    # Create 5 movements
    for i in range(5):
        payload = {
            "occurred_at": f"2025-10-{20+i}T10:00:00Z",
            "type": "INCOME",
            "amount_gs": 10000 * (i + 1),
        }
        client.post("/api/v1/movements", json=payload)
    
    # Get first 3
    response = client.get("/api/v1/movements?limit=3&offset=0")
    assert response.status_code == 200
    assert len(response.json()) == 3
    
    # Get next 2
    response = client.get("/api/v1/movements?limit=3&offset=3")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_movements_filter_by_type(client: TestClient) -> None:
    """Test filtering by movement type."""
    # Create income and expense
    client.post("/api/v1/movements", json={
        "occurred_at": "2025-10-20T10:00:00Z",
        "type": "INCOME",
        "amount_gs": 100000,
    })
    client.post("/api/v1/movements", json={
        "occurred_at": "2025-10-20T11:00:00Z",
        "type": "EXPENSE",
        "amount_gs": 50000,
    })
    
    # Filter by INCOME
    response = client.get("/api/v1/movements?type=INCOME")
    assert response.status_code == 200
    movements = response.json()
    assert len(movements) == 1
    assert movements[0]["type"] == "INCOME"


def test_list_movements_filter_by_category(client: TestClient) -> None:
    """Test filtering by category."""
    # Create movements with different categories
    client.post("/api/v1/movements", json={
        "occurred_at": "2025-10-20T10:00:00Z",
        "type": "INCOME",
        "amount_gs": 100000,
        "category": "Salary",
    })
    client.post("/api/v1/movements", json={
        "occurred_at": "2025-10-20T11:00:00Z",
        "type": "EXPENSE",
        "amount_gs": 50000,
        "category": "Groceries",
    })
    
    # Filter by Salary
    response = client.get("/api/v1/movements?category=Salary")
    assert response.status_code == 200
    movements = response.json()
    assert len(movements) == 1
    assert movements[0]["category"] == "Salary"


# ==========================================
# GET /api/v1/movements/{id} - GET ONE
# ==========================================


def test_get_movement_by_id(client: TestClient) -> None:
    """Test retrieving a single movement by ID."""
    # Create a movement
    create_response = client.post("/api/v1/movements", json={
        "occurred_at": "2025-10-20T10:00:00Z",
        "type": "INCOME",
        "amount_gs": 100000,
        "description": "Test movement",
    })
    movement_id = create_response.json()["id"]
    
    # Get by ID
    response = client.get(f"/api/v1/movements/{movement_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == movement_id
    assert data["description"] == "Test movement"


def test_get_movement_not_found(client: TestClient) -> None:
    """Test 404 when movement doesn't exist."""
    fake_id = str(uuid4())
    response = client.get(f"/api/v1/movements/{fake_id}")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


# ==========================================
# PUT /api/v1/movements/{id} - UPDATE
# ==========================================


def test_update_movement(client: TestClient) -> None:
    """Test updating a movement."""
    # Create a movement
    create_response = client.post("/api/v1/movements", json={
        "occurred_at": "2025-10-20T10:00:00Z",
        "type": "INCOME",
        "amount_gs": 100000,
        "description": "Original description",
    })
    movement_id = create_response.json()["id"]
    
    # Update it
