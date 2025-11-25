"""Tests for date validation in cash sessions."""

import pytest
from datetime import date as date_type, datetime, timedelta
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import BusinessFactory, CashSessionFactory


class TestCashSessionDateValidationAPI:
    """Test date validation for cash sessions."""

    @pytest.fixture
    async def business_id(self, db_session: AsyncSession) -> str:
        """Create a test business."""
        business = await BusinessFactory.create(db_session, name="Test Farmacia")
        return str(business.id)

    @pytest.mark.asyncio
    async def test_close_session_same_day_succeeds(
        self, client: AsyncClient, db_session: AsyncSession, business_id: str
    ):
        """Test closing a session on the same day succeeds."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            session_date=date_type.today(),
            status="OPEN",
            created_by=client.test_user.id,
        )

        response = await client.post(
            f"/sessions/{session.id}",
            data={
                "final_cash": "1000000.00",
                "envelope_amount": "0.00",
                "credit_card_total": "0.00",
                "debit_card_total": "0.00",
                "bank_transfer_total": "0.00",
                "closed_time": "17:00",
            },
        )

        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_close_session_next_day_fails(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test closing a session on a different day fails."""
        business = await BusinessFactory.create(db_session)
        yesterday = date_type.today() - timedelta(days=1)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            session_date=yesterday,
            status="OPEN",
            created_by=client.test_user.id,
        )

        response = await client.post(
            f"/sessions/{session.id}",
            data={
                "final_cash": "1000000.00",
                "envelope_amount": "0.00",
                "credit_card_total": "0.00",
                "debit_card_total": "0.00",
                "bank_transfer_total": "0.00",
                "closed_time": "17:00",
            },
            follow_redirects=False,
        )

        # Should fail - session date doesn't match
        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_close_session_last_minute_same_day(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test closing at 23:59 on the same day."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            session_date=date_type.today(),
            status="OPEN",
            created_by=client.test_user.id,
        )

        response = await client.post(
            f"/sessions/{session.id}",
            data={
                "final_cash": "1000000.00",
                "envelope_amount": "0.00",
                "credit_card_total": "0.00",
                "debit_card_total": "0.00",
                "bank_transfer_total": "0.00",
                "closed_time": "23:59",
            },
        )

        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_close_requires_all_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test closing requires all payment method fields."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            session_date=date_type.today(),
            status="OPEN",
            created_by=client.test_user.id,
        )

        response = await client.post(
            f"/sessions/{session.id}",
            data={
                "final_cash": "1000000.00",
                # Missing other required fields
            },
            follow_redirects=False,
        )

        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_close_with_all_payment_methods(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test closing with all payment methods specified."""
        business = await BusinessFactory.create(db_session)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            session_date=date_type.today(),
            status="OPEN",
            initial_cash=Decimal("500000.00"),
            created_by=client.test_user.id,
        )

        response = await client.post(
            f"/sessions/{session.id}",
            data={
                "final_cash": "750000.00",
                "envelope_amount": "100000.00",
                "credit_card_total": "500000.00",
                "debit_card_total": "250000.00",
                "bank_transfer_total": "100000.00",
                "expenses": "0.00",
                "closed_time": "17:00",
            },
        )

        assert response.status_code == 302
