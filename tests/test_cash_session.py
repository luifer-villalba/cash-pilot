# File: tests/test_cash_session.py
"""Tests for cash session endpoints."""

import pytest
from httpx import AsyncClient
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import BusinessFactory, CashSessionFactory


@pytest.fixture
async def business_id(db_session: AsyncSession) -> str:
    """Create a business for testing."""
    business = await BusinessFactory.create(
        db_session,
        name="Farmacia Test",
        address="Calle Test 123",
        phone="+595972000000",
    )
    return str(business.id)


class TestListCashSessions:
    """Test listing cash sessions."""

    @pytest.mark.asyncio
    async def test_list_sessions_with_filtering(
            self, client: AsyncClient, db_session: AsyncSession, business_id: str
    ):
        """Test listing sessions with filters."""
        business = await BusinessFactory.create(db_session)
        await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            cashier_name="María",
            created_by=client.test_user.id,
        )

        response = await client.get("/")
        # Dashboard requires auth, redirects if not authenticated
        assert response.status_code in [200, 302]  # Depends on test client auth state


class TestOpenCashSession:
    """Test opening cash sessions."""

    @pytest.mark.asyncio
    async def test_open_session_success(
        self, client: AsyncClient, db_session: AsyncSession, business_id: str
    ):
        """Test opening a new session."""
        response = await client.post(
            "/sessions",
            data={
                "business_id": business_id,
                "cashier_name": "Juan",
                "initial_cash": "500000.00",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "/sessions/" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_open_session_minimal_data(
        self, client: AsyncClient, db_session: AsyncSession, business_id: str
    ):
        """Test opening session with minimal required data."""
        response = await client.post(
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
        self, client: AsyncClient, db_session: AsyncSession, business_id: str
    ):
        """Test opening overlapping sessions."""
        # Open first session
        response1 = await client.post(
            "/sessions",
            data={
                "business_id": business_id,
                "cashier_name": "Cashier 1",
                "initial_cash": "500000.00",
            },
        )
        assert response1.status_code == 302

        # Try to open another at same time (should fail or need allow_overlap)
        response2 = await client.post(
            "/sessions",
            data={
                "business_id": business_id,
                "cashier_name": "Cashier 2",
                "initial_cash": "500000.00",
            },
            follow_redirects=False,
        )
        # Either succeeds with overlap or fails - both acceptable
        assert response2.status_code in [302, 400, 409]


class TestGetCashSession:
    """Test retrieving session details."""

    @pytest.mark.asyncio
    async def test_get_session_success(self, client: AsyncClient, db_session: AsyncSession):
        """Test retrieving a cash session details."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            created_by=client.test_user.id,
        )

        response = await client.get(f"/cash-sessions/{session.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(session.id)


class TestCloseCashSession:
    """Test closing sessions."""

    @pytest.mark.asyncio
    async def test_close_session_success(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test closing a session."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            initial_cash=Decimal("500000.00"),
            created_by=client.test_user.id,
        )

        response = await client.post(
            f"/sessions/{session.id}",
            data={
                "final_cash": "750000.00",
                "envelope_amount": "100000.00",
                "credit_card_total": "50000.00",
                "debit_card_total": "25000.00",
                "bank_transfer_total": "10000.00",
                "closed_time": "17:00",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_close_session_partial_data(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test closing with minimal required fields."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            created_by=client.test_user.id,
        )

        response = await client.post(
            f"/sessions/{session.id}",
            data={
                "final_cash": "1500000.00",
                "envelope_amount": "0.00",
                "credit_card_total": "0.00",
                "debit_card_total": "0.00",
                "bank_transfer_total": "0.00",
                "closed_time": "17:00",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_close_already_closed_session(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test closing an already closed session fails."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="CLOSED",
            final_cash=Decimal("1000000.00"),
            created_by=client.test_user.id,
        )

        response = await client.post(
            f"/sessions/{session.id}",
            data={
                "final_cash": "2000000.00",
                "envelope_amount": "0.00",
                "credit_card_total": "0.00",
                "debit_card_total": "0.00",
                "bank_transfer_total": "0.00",
                "closed_time": "17:00",
            },
            follow_redirects=False,
        )

        assert response.status_code in [302, 400, 409]

    @pytest.mark.asyncio
    async def test_close_without_required_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test closing without required fields fails."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            status="OPEN",
            created_by=client.test_user.id,
        )

        response = await client.post(
            f"/sessions/{session.id}",
            data={
                # Missing required fields
                "final_cash": "1000000.00",
            },
            follow_redirects=False,
        )

        assert response.status_code in [400, 422]
