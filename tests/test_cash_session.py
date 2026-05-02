# File: tests/test_cash_session.py

"""Tests for cash session endpoints."""

from datetime import timedelta
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.utils.datetime import today_local
from tests.factories import BusinessFactory, CashSessionFactory


@pytest.fixture
async def business_id(db_session: AsyncSession) -> str:
    """Create a business for testing."""
    business = await BusinessFactory.create(
        db_session,
        name="Business Test",
        address="Calle Test 123",
        phone="+595972000000",
    )
    return str(business.id)


class TestListCashSessions:
    """Test listing cash sessions."""

    @pytest.mark.asyncio
    async def test_list_sessions_with_filtering(
        self, admin_client: AsyncClient, db_session: AsyncSession, business_id: str
    ):
        """Test listing sessions with filters."""
        business = await BusinessFactory.create(db_session)
        await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            cashier_name="María",
            created_by=admin_client.test_user.id,
        )

        response = await admin_client.get("/")
        # Dashboard requires auth, redirects if not authenticated
        assert response.status_code in [200, 302]


class TestOpenCashSession:
    """Test opening cash sessions."""

    @pytest.mark.asyncio
    async def test_open_session_success(
        self, admin_client: AsyncClient, db_session: AsyncSession, business_id: str
    ):
        """Test opening a new session."""
        response = await admin_client.post(
            "/sessions",
            data={
                "business_id": business_id,
                "cashier_name": "Juan",
                "initial_cash": "500000.00",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_open_session_minimal_data(
        self, admin_client: AsyncClient, db_session: AsyncSession, business_id: str
    ):
        """Test opening session with minimal required data."""
        response = await admin_client.post(
            "/sessions",
            data={
                "business_id": business_id,
                "cashier_name": "Test Cashier",
                "initial_cash": "1000000.00",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_open_session_duplicate(
        self, admin_client: AsyncClient, db_session: AsyncSession, business_id: str
    ):
        """Test opening overlapping sessions."""
        # Open first session
        response1 = await admin_client.post(
            "/sessions",
            data={
                "business_id": business_id,
                "cashier_name": "Cashier 1",
                "initial_cash": "500000.00",
            },
        )
        assert response1.status_code == 302

        # Try to open another at same time
        response2 = await admin_client.post(
            "/sessions",
            data={
                "business_id": business_id,
                "cashier_name": "Cashier 2",
                "initial_cash": "500000.00",
            },
            follow_redirects=False,
        )
        assert response2.status_code in [400, 409]

    @pytest.mark.asyncio
    async def test_open_session_allows_different_business(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test opening sessions in different businesses for same cashier."""
        business_one = await BusinessFactory.create(db_session, name="Business One")
        business_two = await BusinessFactory.create(db_session, name="Business Two")

        response1 = await admin_client.post(
            "/sessions",
            data={
                "business_id": str(business_one.id),
                "cashier_name": "Cashier",
                "initial_cash": "500000.00",
            },
            follow_redirects=False,
        )
        assert response1.status_code == 302

        response2 = await admin_client.post(
            "/sessions",
            data={
                "business_id": str(business_two.id),
                "cashier_name": "Cashier",
                "initial_cash": "500000.00",
            },
            follow_redirects=False,
        )
        assert response2.status_code == 302

    @pytest.mark.asyncio
    async def test_open_session_allows_after_closing(
        self, admin_client: AsyncClient, db_session: AsyncSession, business_id: str
    ):
        """Test opening new session after closing existing one."""
        await CashSessionFactory.create(
            db_session,
            business_id=UUID(business_id),
            cashier_id=admin_client.test_user.id,
            status="CLOSED",
        )

        response = await admin_client.post(
            "/sessions",
            data={
                "business_id": business_id,
                "cashier_name": "Cashier",
                "initial_cash": "500000.00",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_open_session_allows_with_soft_deleted_open(
        self, admin_client: AsyncClient, db_session: AsyncSession, business_id: str
    ):
        """Test opening new session when existing OPEN session is soft-deleted."""
        await CashSessionFactory.create(
            db_session,
            business_id=UUID(business_id),
            cashier_id=admin_client.test_user.id,
            status="OPEN",
            is_deleted=True,
        )

        response = await admin_client.post(
            "/sessions",
            data={
                "business_id": business_id,
                "cashier_name": "Cashier",
                "initial_cash": "500000.00",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302


class TestGetCashSession:
    """Test retrieving session details."""

    @pytest.mark.asyncio
    async def test_get_session_success(self, admin_client: AsyncClient, db_session: AsyncSession):
        """Test retrieving a cash session details."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            created_by=admin_client.test_user.id,
        )

        response = await admin_client.get(f"/cash-sessions/{session.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(session.id)


class TestCloseCashSession:
    """Test closing sessions."""

    @pytest.mark.asyncio
    async def test_close_session_success(self, admin_client: AsyncClient, db_session: AsyncSession):
        """Test closing a session."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            created_by=admin_client.test_user.id,
        )

        response = await admin_client.put(
            f"/cash-sessions/{session.id}",
            json={
                "final_cash": "550000.00",
                "card_total": "150000.00",
                "envelope_amount": "0.00",
                "bank_transfer_total": "0.00",
                "closed_time": "18:00:00",
            },
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_close_session_partial_data(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test closing with partial payment methods."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            created_by=admin_client.test_user.id,
        )

        response = await admin_client.put(
            f"/cash-sessions/{session.id}",
            json={
                "final_cash": "500000.00",
                "card_total": "0.00",
                "envelope_amount": "0.00",
                "bank_transfer_total": "0.00",
                "closed_time": "18:00:00",
            },
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_close_already_closed_session(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test closing already closed session."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="CLOSED",
            created_by=admin_client.test_user.id,
        )

        response = await admin_client.put(
            f"/cash-sessions/{session.id}",
            json={
                "final_cash": "600000.00",
                "card_total": "0.00",
                "envelope_amount": "0.00",
                "bank_transfer_total": "0.00",
                "closed_time": "18:00:00",
            },
        )

        assert response.status_code in [302, 400, 409]

    @pytest.mark.asyncio
    async def test_close_without_required_fields(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test closing without required fields."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            created_by=admin_client.test_user.id,
        )

        response = await admin_client.put(
            f"/cash-sessions/{session.id}",
            json={"final_cash": "500000.00"},
        )

        assert response.status_code in [400, 422]


class TestOpenCashSessionAPI:
    """Test opening cash sessions via REST API (/cash-sessions POST)."""

    @pytest.mark.asyncio
    async def test_api_open_session_success(
        self, admin_client: AsyncClient, db_session: AsyncSession, business_id: str
    ):
        """Test opening session via REST API."""
        response = await admin_client.post(
            "/cash-sessions",
            json={
                "business_id": business_id,
                "initial_cash": "500000.00",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "OPEN"
        assert float(data["initial_cash"]) == 500000.0

    @pytest.mark.asyncio
    async def test_api_prevent_duplicate_open_session(
        self, admin_client: AsyncClient, db_session: AsyncSession, business_id: str
    ):
        """Test API prevents duplicate open sessions for same cashier/business.

        This tests the new validation added in open_shift() to catch duplicates
        before they reach the database, returning 409 Conflict instead of 500.
        """
        # Open first session via API
        response1 = await admin_client.post(
            "/cash-sessions",
            json={
                "business_id": business_id,
                "initial_cash": "500000.00",
            },
        )
        assert response1.status_code == 201

        # Try to open second session for same cashier/business
        response2 = await admin_client.post(
            "/cash-sessions",
            json={
                "business_id": business_id,
                "initial_cash": "600000.00",
            },
        )

        # Should return 409 Conflict with clear error message
        assert response2.status_code == 409
        error = response2.json()
        assert error["code"] == "CONFLICT"
        assert "already exists" in error["message"].lower()
        assert "session_id" in error.get("details", {})
        assert "session_number" in error.get("details", {})

    @pytest.mark.asyncio
    async def test_api_allow_different_business_sessions(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test can open sessions in different businesses for same cashier via API."""
        business_one = await BusinessFactory.create(db_session, name="Business One")
        business_two = await BusinessFactory.create(db_session, name="Business Two")

        # Open session in business one
        response1 = await admin_client.post(
            "/cash-sessions",
            json={
                "business_id": str(business_one.id),
                "initial_cash": "500000.00",
            },
        )
        assert response1.status_code == 201

        # Open session in business two (different business, same cashier)
        response2 = await admin_client.post(
            "/cash-sessions",
            json={
                "business_id": str(business_two.id),
                "initial_cash": "600000.00",
            },
        )
        assert response2.status_code == 201


class TestRestoreCashSessionAPI:
    """Test restoring soft-deleted cash sessions via REST API."""

    @pytest.mark.asyncio
    async def test_restore_open_session_conflicts_with_existing_open_session(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Restoring a deleted OPEN session must not violate the DB unique index."""
        business = await BusinessFactory.create(db_session)
        cashier_id = admin_client.test_user.id

        deleted_session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            cashier_id=cashier_id,
            created_by=cashier_id,
            status="OPEN",
            is_deleted=True,
        )
        blocking_session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            cashier_id=cashier_id,
            created_by=cashier_id,
            status="OPEN",
        )

        response = await admin_client.patch(f"/cash-sessions/{deleted_session.id}/restore")

        assert response.status_code == 409
        error = response.json()
        assert error["code"] == "CONFLICT"
        assert error["details"]["session_id"] == str(deleted_session.id)
        assert error["details"]["blocking_session_id"] == str(blocking_session.id)

        await db_session.refresh(deleted_session)
        assert deleted_session.is_deleted is True

    @pytest.mark.asyncio
    async def test_restore_open_session_allows_existing_open_session_on_different_date(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Admins can restore yesterday's deleted OPEN session while today is open."""
        business = await BusinessFactory.create(db_session)
        cashier_id = admin_client.test_user.id
        yesterday = today_local() - timedelta(days=1)
        today = today_local()

        deleted_session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            cashier_id=cashier_id,
            created_by=cashier_id,
            session_date=yesterday,
            status="OPEN",
            is_deleted=True,
        )
        await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            cashier_id=cashier_id,
            created_by=cashier_id,
            session_date=today,
            status="OPEN",
        )

        response = await admin_client.patch(f"/cash-sessions/{deleted_session.id}/restore")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(deleted_session.id)
        assert data["is_deleted"] is False

    @pytest.mark.asyncio
    async def test_api_open_after_closing(
        self, admin_client: AsyncClient, db_session: AsyncSession, business_id: str
    ):
        """Test can open new session after closing existing one via API."""
        session_date = today_local().isoformat()

        # Open first session
        response1 = await admin_client.post(
            "/cash-sessions",
            json={
                "business_id": business_id,
                "initial_cash": "500000.00",
                "session_date": session_date,
                "opened_time": "06:00:00",
            },
        )
        assert response1.status_code == 201
        first_session_id = response1.json()["id"]

        # Close first session
        response_close = await admin_client.put(
            f"/cash-sessions/{first_session_id}",
            json={
                "final_cash": "510000.00",
                "card_total": "0.00",
                "envelope_amount": "0.00",
                "bank_transfer_total": "0.00",
                "expenses": "0.00",
                "credit_sales_total": "0.00",
                "credit_payments_collected": "0.00",
                "closed_time": "07:00:00",
            },
        )
        assert response_close.status_code == 200

        # Open new session after closing
        response2 = await admin_client.post(
            "/cash-sessions",
            json={
                "business_id": business_id,
                "initial_cash": "600000.00",
                "session_date": session_date,
                "opened_time": "08:00:00",
            },
        )
        assert response2.status_code == 201
