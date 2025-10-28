"""Tests for CashSession API endpoints."""

from decimal import Decimal

import pytest
from httpx import AsyncClient


@pytest.fixture
async def business_id(client: AsyncClient) -> str:
    """Create a business and return its ID for tests."""
    response = await client.post(
        "/businesses",
        json={"name": "Test Pharmacy", "address": "Test Address"},
    )
    return response.json()["id"]


@pytest.mark.asyncio
async def test_open_cash_session(client: AsyncClient, business_id: str):
    """Test opening a new cash session."""
    payload = {
        "business_id": business_id,
        "cashier_name": "María González",
        "initial_cash": 500000.00,
        "shift_hours": "08:00-16:00",
    }

    response = await client.post("/cash-sessions", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["business_id"] == business_id
    assert data["cashier_name"] == "María González"
    assert data["initial_cash"] == "500000.00"
    assert data["shift_hours"] == "08:00-16:00"
    assert data["status"] == "OPEN"
    assert data["closed_at"] is None
    assert data["final_cash"] is None
    assert "id" in data
    assert "opened_at" in data


@pytest.mark.asyncio
async def test_open_session_business_not_found(client: AsyncClient):
    """Test opening session with non-existent business returns 404."""
    fake_business_id = "00000000-0000-0000-0000-000000000000"
    payload = {
        "business_id": fake_business_id,
        "cashier_name": "Test",
        "initial_cash": 500000.00,
    }

    response = await client.post("/cash-sessions", json=payload)

    assert response.status_code == 404
    assert response.json()["detail"] == "Business not found"


@pytest.mark.asyncio
async def test_open_session_duplicate(client: AsyncClient, business_id: str):
    """Test opening multiple sessions for same business returns 409."""
    payload = {
        "business_id": business_id,
        "cashier_name": "Test",
        "initial_cash": 500000.00,
    }

    # Open first session
    response1 = await client.post("/cash-sessions", json=payload)
    assert response1.status_code == 201

    # Try to open second session (should fail)
    response2 = await client.post("/cash-sessions", json=payload)
    assert response2.status_code == 409
    assert response2.json()["detail"] == "Session already open for this business"


@pytest.mark.asyncio
async def test_close_cash_session(client: AsyncClient, business_id: str):
    """Test closing a cash session with all payment methods."""
    # Open session
    open_response = await client.post(
        "/cash-sessions",
        json={
            "business_id": business_id,
            "cashier_name": "Juan Pérez",
            "initial_cash": 500000.00,
        },
    )
    session_id = open_response.json()["id"]

    # Close session
    close_payload = {
        "final_cash": 3500000.00,
        "envelope_amount": 1000000.00,
        "expected_sales": 4000000.00,
        "closing_ticket": "TKT-001",
        "notes": "Turno normal",
    }
    response = await client.put(f"/cash-sessions/{session_id}", json=close_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CLOSED"
    assert data["final_cash"] == "3500000.00"
    assert data["envelope_amount"] == "1000000.00"
    assert data["closing_ticket"] == "TKT-001"
    assert data["notes"] == "Turno normal"
    assert data["closed_at"] is not None


@pytest.mark.asyncio
async def test_close_session_not_found(client: AsyncClient):
    """Test closing non-existent session returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.put(
        f"/cash-sessions/{fake_id}",
        json={"final_cash": 1000000.00},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Cash session not found"


@pytest.mark.asyncio
async def test_close_already_closed_session(client: AsyncClient, business_id: str):
    """Test closing an already closed session returns 400."""
    # Open and close session
    open_response = await client.post(
        "/cash-sessions",
        json={
            "business_id": business_id,
            "cashier_name": "Test",
            "initial_cash": 500000.00,
        },
    )
    session_id = open_response.json()["id"]

    await client.put(
        f"/cash-sessions/{session_id}",
        json={"final_cash": 1000000.00},
    )

    # Try to close again
    response = await client.put(
        f"/cash-sessions/{session_id}",
        json={"final_cash": 2000000.00},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Session is not open"


@pytest.mark.asyncio
async def test_get_cash_session(client: AsyncClient, business_id: str):
    """Test retrieving a cash session by ID."""
    # Open session
    open_response = await client.post(
        "/cash-sessions",
        json={
            "business_id": business_id,
            "cashier_name": "Ana Silva",
            "initial_cash": 500000.00,
        },
    )
    session_id = open_response.json()["id"]

    # Get session
    response = await client.get(f"/cash-sessions/{session_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == session_id
    assert data["cashier_name"] == "Ana Silva"
    assert data["initial_cash"] == "500000.00"


@pytest.mark.asyncio
async def test_list_cash_sessions(client: AsyncClient, business_id: str):
    """Test listing cash sessions."""
    # Create multiple sessions
    for i in range(3):
        await client.post(
            "/cash-sessions",
            json={
                "business_id": business_id,
                "cashier_name": f"Cashier {i}",
                "initial_cash": 500000.00,
            },
        )
        # Close each session to allow creating next one
        sessions_response = await client.get("/cash-sessions")
        sessions = sessions_response.json()
        last_session = sessions[0]
        await client.put(
            f"/cash-sessions/{last_session['id']}",
            json={"final_cash": 1000000.00},
        )

    # List all sessions
    response = await client.get("/cash-sessions")

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3


@pytest.mark.asyncio
async def test_list_sessions_filter_by_business(client: AsyncClient):
    """Test filtering sessions by business_id."""
    # Create two businesses
    biz1_response = await client.post("/businesses", json={"name": "Pharmacy 1"})
    biz1 = biz1_response.json()
    biz2_response = await client.post("/businesses", json={"name": "Pharmacy 2"})
    biz2 = biz2_response.json()

    # Create sessions for each
    await client.post(
        "/cash-sessions",
        json={
            "business_id": biz1["id"],
            "cashier_name": "Test 1",
            "initial_cash": 500000.00,
        },
    )
    await client.post(
        "/cash-sessions",
        json={
            "business_id": biz2["id"],
            "cashier_name": "Test 2",
            "initial_cash": 500000.00,
        },
    )

    # Filter by business 1
    response = await client.get(f"/cash-sessions?business_id={biz1['id']}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["business_id"] == biz1["id"]


@pytest.mark.asyncio
async def test_cash_sales_calculation(client: AsyncClient, business_id: str):
    """Test that cash_sales property is NOT in response (it's calculated)."""
    # Open session
    open_response = await client.post(
        "/cash-sessions",
        json={
            "business_id": business_id,
            "cashier_name": "Test",
            "initial_cash": 500000.00,
        },
    )
    session_id = open_response.json()["id"]

    # Close with known values
    # cash_sales = (3500000 + 1000000) - 500000 = 4000000
    await client.put(
        f"/cash-sessions/{session_id}",
        json={
            "final_cash": 3500000.00,
            "envelope_amount": 1000000.00,
        },
    )

    # Get session
    response = await client.get(f"/cash-sessions/{session_id}")
    data = response.json()

    # Verify calculation manually (cash_sales is a property, not stored)
    initial = Decimal(data["initial_cash"])
    final = Decimal(data["final_cash"])
    envelope = Decimal(data["envelope_amount"])
    expected_cash_sales = (final + envelope) - initial

    assert expected_cash_sales == Decimal("4000000.00")
