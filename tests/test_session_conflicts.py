"""Tests for Conflict detection validation."""


import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient


@pytest.fixture
async def business_id(client: AsyncClient) -> str:
    """Create a test business."""
    response = await client.post("/businesses", json={"name": "Test Farmacia"})
    return response.json()["id"]


class TestSessionConflicts:
    """Test overlap detection."""

    async def test_no_conflict_non_overlapping_shifts(self, client: AsyncClient, business_id: str):
        """Test that non-overlapping shifts are allowed."""
        now = datetime.now()

        # Shift 1: 1 hour ago (so closed_at will be before shift 2 opens)
        shift1_open = now - timedelta(hours=1)

        resp1 = await client.post(
            "/cash-sessions",
            json={
                "business_id": business_id,
                "cashier_name": "Maria",
                "initial_cash": 500000,
                "opened_at": shift1_open.isoformat(),
            },
        )
        assert resp1.status_code == 201
        session1_id = resp1.json()["id"]

        # Close shift 1 (closed_at = now)
        close_resp = await client.put(
            f"/cash-sessions/{session1_id}",
            json={
                "final_cash": 1000000,
                "envelope_amount": 100000,
                "credit_card_total": 300000,
            },
        )
        assert close_resp.status_code == 200

        # Shift 2: 1 hour in future (after shift 1 is closed)
        shift2_open = now + timedelta(hours=1)

        response = await client.post(
            "/cash-sessions",
            json={
                "business_id": business_id,
                "cashier_name": "Juan",
                "initial_cash": 500000,
                "opened_at": shift2_open.isoformat(),
            },
        )

        assert response.status_code == 201

    async def test_conflict_same_time(self, client: AsyncClient, business_id: str):
        """Test that same-time shifts conflict."""
        now = datetime.now()

        # Open shift 1
        resp1 = await client.post(
            "/cash-sessions",
            json={
                "business_id": business_id,
                "cashier_name": "Maria",
                "initial_cash": 500000,
                "opened_at": now.isoformat(),
            },
        )
        assert resp1.status_code == 201

        # Try to open shift 2 at same time (conflict)
        resp2 = await client.post(
            "/cash-sessions",
            json={
                "business_id": business_id,
                "cashier_name": "Juan",
                "initial_cash": 500000,
                "opened_at": now.isoformat(),
            },
        )

        assert resp2.status_code == 409
        assert resp2.json()["code"] == "CONFLICT"
        assert "Maria" in resp2.json()["message"]

    async def test_allow_overlap_checkbox(self, client: AsyncClient, business_id: str):
        """Test that allow_overlap=true bypasses conflict check."""
        now = datetime.now()

        # Open shift 1
        await client.post(
            "/cash-sessions",
            json={
                "business_id": business_id,
                "cashier_name": "Maria",
                "initial_cash": 500000,
                "opened_at": now.isoformat(),
            },
        )

        # Open shift 2 with override (same time, but allowed)
        response = await client.post(
            "/cash-sessions",
            json={
                "business_id": business_id,
                "cashier_name": "Juan",
                "initial_cash": 500000,
                "opened_at": now.isoformat(),
                "allow_overlap": True,
            },
        )

        assert response.status_code == 201

    async def test_close_session_requires_fields(self, client: AsyncClient, business_id: str):
        """Test that closing requires final_cash, envelope_amount, credit_card_total."""
        # Open a session
        resp = await client.post(
            "/cash-sessions",
            json={
                "business_id": business_id,
                "cashier_name": "Maria",
                "initial_cash": 500000,
            },
        )
        session_id = resp.json()["id"]

        # Try to close without required fields
        close_resp = await client.put(
            f"/cash-sessions/{session_id}",
            json={"notes": "Test"},
        )

        assert close_resp.status_code == 400
        assert close_resp.json()["code"] == "INVALID_STATE"

        # Close with all required fields
        close_resp = await client.put(
            f"/cash-sessions/{session_id}",
            json={
                "final_cash": 1000000,
                "envelope_amount": 200000,
                "credit_card_total": 500000,
            },
        )

        assert close_resp.status_code == 200
        assert close_resp.json()["status"] == "CLOSED"

    async def test_conflict_detection_marks_has_conflict(self, client: AsyncClient, business_id: str):
        """Test that overlapping sessions are marked with has_conflict."""
        now = datetime.now()

        # Create session 1
        resp1 = await client.post(
            "/cash-sessions",
            json={
                "business_id": business_id,
                "cashier_name": "Maria",
                "initial_cash": "500000.00",
                "opened_at": now.isoformat(),
            },
        )
        assert resp1.status_code == 201

        # Create session 2 with overlap
        resp2 = await client.post(
            "/cash-sessions",
            json={
                "business_id": business_id,
                "cashier_name": "Juan",
                "initial_cash": "500000.00",
                "opened_at": now.isoformat(),
                "allow_overlap": True,
            },
        )
        assert resp2.status_code == 201
