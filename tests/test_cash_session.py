"""Tests for CashSession API endpoints."""

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


@pytest_asyncio.fixture
async def open_session_id(client: AsyncClient, business_id: str) -> str:
    """Create and open a cash session for testing."""
    session_data = {
        "business_id": business_id,
        "cashier_name": "Carlos",
        "initial_cash": 500.00,
    }
    response = await client.post("/cash-sessions", json=session_data)
    assert response.status_code == 201
    return response.json()["id"]


class TestListCashSessions:
    """Test cash session list endpoint."""

    async def test_list_sessions_empty(self, client: AsyncClient):
        """Test listing sessions when none exist."""
        response = await client.get("/cash-sessions")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_list_sessions_with_filtering(
        self, client: AsyncClient, business_id: str, open_session_id: str
    ):
        """Test listing sessions filtered by business."""
        response = await client.get(f"/cash-sessions?business_id={business_id}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1


class TestOpenCashSession:
    """Test opening a new cash session."""

    async def test_open_session_success(self, client: AsyncClient, business_id: str):
        """Test opening a session returns 201."""
        session_data = {
            "business_id": business_id,
            "cashier_name": "Maria",
            "initial_cash": 1000.00,
        }
        response = await client.post("/cash-sessions", json=session_data)

        assert response.status_code == 201
        data = response.json()
        assert data["cashier_name"] == "Maria"
        assert data["initial_cash"] == "1000.00"
        assert data["status"] == "OPEN"
        assert "id" in data
        assert "opened_at" in data

    async def test_open_session_minimal_data(self, client: AsyncClient, business_id: str):
        """Test opening session with minimal required fields."""
        session_data = {
            "business_id": business_id,
            "cashier_name": "Juan",
            "initial_cash": 250.00,
        }
        response = await client.post("/cash-sessions", json=session_data)

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "OPEN"
        assert "opened_at" in data

    async def test_open_session_business_not_found(self, client: AsyncClient):
        """Test opening session with non-existent business returns 404."""
        session_data = {
            "business_id": "00000000-0000-0000-0000-000000000000",
            "cashier_name": "John",
            "initial_cash": 100.00,
        }
        response = await client.post("/cash-sessions", json=session_data)

        assert response.status_code == 404
        data = response.json()
        assert data["code"] == "NOT_FOUND"

    async def test_open_session_duplicate(self, client: AsyncClient, business_id: str):
        """Test opening duplicate session returns 409."""
        session_data = {
            "business_id": business_id,
            "cashier_name": "John",
            "initial_cash": 100.00,
        }
        # Open first session
        response1 = await client.post("/cash-sessions", json=session_data)
        assert response1.status_code == 201

        # Try to open second (should fail)
        response2 = await client.post("/cash-sessions", json=session_data)
        assert response2.status_code == 409
        data = response2.json()
        assert data["code"] == "CONFLICT"


class TestGetCashSession:
    """Test getting cash session details."""

    async def test_get_session_success(self, client: AsyncClient, open_session_id: str):
        """Test getting existing session returns 200."""
        response = await client.get(f"/cash-sessions/{open_session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == open_session_id
        assert data["status"] == "OPEN"

    async def test_get_session_not_found(self, client: AsyncClient):
        """Test getting non-existent session returns 404."""
        response = await client.get("/cash-sessions/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 404
        data = response.json()
        assert data["code"] == "NOT_FOUND"


class TestCloseCashSession:
    """Test closing a cash session."""

    async def test_close_session_success(self, client: AsyncClient, open_session_id: str):
        """Test closing a session returns 200."""
        close_data = {
            "final_cash": 1500.00,
            "envelope_amount": 200.00,
            "credit_card_total": 700.00,
        }
        response = await client.put(f"/cash-sessions/{open_session_id}", json=close_data)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == open_session_id
        assert data["status"] == "CLOSED"
        assert data["final_cash"] == "1500.00"

    async def test_close_session_partial_data(
        self, client: AsyncClient, open_session_id: str
    ):
        """Test closing with all required fields."""
        close_data = {
            "final_cash": 1200.00,
            "envelope_amount": 100.00,
            "credit_card_total": 500.00,
        }
        response = await client.put(f"/cash-sessions/{open_session_id}", json=close_data)

        assert response.status_code == 200
        data = response.json()
        assert data["final_cash"] == "1200.00"
        assert data["status"] == "CLOSED"

    async def test_close_session_not_found(self, client: AsyncClient):
        """Test closing non-existent session returns 404."""
        response = await client.put(
            "/cash-sessions/00000000-0000-0000-0000-000000000000", json={}
        )

        assert response.status_code == 404
        data = response.json()
        assert data["code"] == "NOT_FOUND"

    async def test_close_already_closed_session(
        self, client: AsyncClient, open_session_id: str
    ):
        """Test closing already-closed session returns 400."""
        # Close it first
        close_data = {
            "final_cash": 1000.00,
            "envelope_amount": 50.00,
            "credit_card_total": 400.00,
        }
        await client.put(f"/cash-sessions/{open_session_id}", json=close_data)

        # Try to close again
        response = await client.put(
            f"/cash-sessions/{open_session_id}", json={"final_cash": 1100.00}
        )

        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "INVALID_STATE"

    async def test_close_without_required_fields(self, client: AsyncClient, business_id: str):
        """Test that closing without required fields fails."""
        # Open session
        resp = await client.post(
            "/cash-sessions",
            json={
                "business_id": business_id,
                "cashier_name": "Test",
                "initial_cash": 500.00,
            },
        )
        session_id = resp.json()["id"]

        # Try to close without required fields
        response = await client.put(
            f"/cash-sessions/{session_id}",
            json={"notes": "Test note"},
        )

        assert response.status_code == 400
        assert response.json()["code"] == "INVALID_STATE"
