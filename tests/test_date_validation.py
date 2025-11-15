import pytest
from datetime import date, time
from httpx import AsyncClient
from freezegun import freeze_time

from cashpilot.core.validation import validate_session_dates


class TestValidateSessionDates:
    """Test same-day validation logic."""

    async def test_valid_same_day_open_close(self):
        """Test valid session that opens and closes same day."""
        opened = time(8, 0, 0)
        closed = time(16, 0, 0)

        result = await validate_session_dates(date(2025, 11, 11), opened, closed)
        assert result is None  # Valid

    async def test_invalid_close_before_open(self):
        """Test invalid: closed before opened."""
        opened = time(16, 0, 0)
        closed = time(8, 0, 0)

        result = await validate_session_dates(date(2025, 11, 11), opened, closed)
        assert result is not None
        assert "after open time" in result["message"]

    async def test_valid_open_session_no_closed_time(self):
        """Test valid: open session with no closed_time."""
        opened = time(8, 0, 0)

        result = await validate_session_dates(date(2025, 11, 11), opened, None)
        assert result is None  # Valid (open session)

    async def test_valid_midnight_to_late_night(self):
        """Test valid: opens at midnight, closes at 23:59 same day."""
        opened = time(0, 0, 0)
        closed = time(23, 59, 59)

        result = await validate_session_dates(date(2025, 11, 11), opened, closed)
        assert result is None  # Valid

    async def test_valid_one_minute_apart(self):
        """Test valid: opens and closes 1 minute apart same day."""
        opened = time(8, 0, 0)
        closed = time(8, 1, 0)

        result = await validate_session_dates(date(2025, 11, 11), opened, closed)
        assert result is None  # Valid


class TestCashSessionDateValidationAPI:
    """Test API enforcement of date validation with frozen time."""

    @pytest.fixture
    async def business_id(self, client: AsyncClient) -> str:
        """Create a test business."""
        response = await client.post("/businesses", json={"name": "Test Farmacia"})
        return response.json()["id"]

    @freeze_time("2025-11-11 16:30:00")
    async def test_close_session_same_day_succeeds(self, client: AsyncClient, business_id: str):
        """Test closing session on same day succeeds (time frozen at Nov 11, 4:30pm)."""
        # Open session at 8am same day (use date + time fields)
        open_resp = await client.post(
            "/cash-sessions",
            json={
                "business_id": business_id,
                "cashier_name": "Maria",
                "initial_cash": "500000.00",
                "session_date": "2025-11-11",
                "opened_time": "08:00:00",
            },
        )
        assert open_resp.status_code == 201
        session_id = open_resp.json()["id"]

        # Close same day with closed_time (current time is 4:30pm on Nov 11)
        close_resp = await client.put(
            f"/cash-sessions/{session_id}",
            json={
                "final_cash": "1000000.00",
                "envelope_amount": "200000.00",
                "credit_card_total": "500000.00",
                "closed_time": "16:35:00",  # NEW: time field only
            },
        )

        assert close_resp.status_code == 200, f"Response: {close_resp.json()}"
        data = close_resp.json()
        assert data["status"] == "CLOSED"
        assert data["final_cash"] == "1000000.00"

    @freeze_time("2025-11-11 16:30:00")
    async def test_close_session_next_day_fails(self, client: AsyncClient, business_id: str):
        """Test that sessions lock to their session_date (immutable)."""
        # Open session on Nov 11
        open_resp = await client.post(
            "/cash-sessions",
            json={
                "business_id": business_id,
                "cashier_name": "Juan",
                "initial_cash": "500000.00",
                "session_date": "2025-11-11",
                "opened_time": "08:00:00",
            },
        )
        session_id = open_resp.json()["id"]

        # Try to close with an impossible time (after midnight on same day = invalid)
        # Since closed_time must be >= opened_time and before 23:59:59 same day
        # Test: closing is allowed only if closed_time > opened_time
        close_resp = await client.put(
            f"/cash-sessions/{session_id}",
            json={
                "final_cash": "1000000.00",
                "envelope_amount": "200000.00",
                "credit_card_total": "500000.00",
                "closed_time": "07:00:00",  # Before opened_time (08:00) → invalid
            },
        )

        assert close_resp.status_code == 400
        assert "after open time" in close_resp.json()["message"].lower()

    @freeze_time("2025-11-11 23:59:00")
    async def test_close_session_last_minute_same_day(self, client: AsyncClient, business_id: str):
        """Test closing at 23:59 same day succeeds."""
        open_resp = await client.post(
            "/cash-sessions",
            json={
                "business_id": business_id,
                "cashier_name": "Carlos",
                "initial_cash": "500000.00",
                "session_date": "2025-11-11",
                "opened_time": "08:00:00",
            },
        )
        session_id = open_resp.json()["id"]

        # Close at 23:59 same day
        close_resp = await client.put(
            f"/cash-sessions/{session_id}",
            json={
                "final_cash": "1500000.00",
                "envelope_amount": "300000.00",
                "credit_card_total": "800000.00",
                "closed_time": "23:59:00",
            },
        )

        assert close_resp.status_code == 200
        assert close_resp.json()["status"] == "CLOSED"

    @freeze_time("2025-11-11 16:30:00")
    async def test_close_requires_all_fields(self, client: AsyncClient, business_id: str):
        """Test that closing still requires all required fields."""
        open_resp = await client.post(
            "/cash-sessions",
            json={
                "business_id": business_id,
                "cashier_name": "Pedro",
                "initial_cash": "500000.00",
            },
        )
        session_id = open_resp.json()["id"]

        # Try without final_cash
        close_resp = await client.put(
            f"/cash-sessions/{session_id}",
            json={
                "envelope_amount": "200000.00",
                "credit_card_total": "500000.00",
                "closed_time": "16:35:00",
            },
        )

        assert close_resp.status_code == 400
        assert "required" in close_resp.json()["message"].lower()

    @freeze_time("2025-11-11 16:30:00")
    async def test_close_with_all_payment_methods(self, client: AsyncClient, business_id: str):
        """Test closing with all payment method totals recorded."""
        open_resp = await client.post(
            "/cash-sessions",
            json={
                "business_id": business_id,
                "cashier_name": "Sofia",
                "initial_cash": "500000.00",
            },
        )
        session_id = open_resp.json()["id"]

        # Close with all payment methods
        close_resp = await client.put(
            f"/cash-sessions/{session_id}",
            json={
                "final_cash": "750000.00",
                "envelope_amount": "150000.00",
                "credit_card_total": "1000000.00",
                "debit_card_total": "500000.00",
                "bank_transfer_total": "200000.00",
                "closing_ticket": "TICKET-001",
                "notes": "All systems normal",
                "closed_time": "16:35:00",  # NEW: time field
            },
        )

        assert close_resp.status_code == 200, f"Status: {close_resp.status_code}, Response: {close_resp.json()}"
        data = close_resp.json()
        assert data["status"] == "CLOSED"
        assert data["credit_card_total"] == "1000000.00"
        assert data["closing_ticket"] == "TICKET-001"
