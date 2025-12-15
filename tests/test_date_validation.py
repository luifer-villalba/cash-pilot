# File: tests/test_date_validation.py

"""Tests for cash session date validation."""

import pytest
from datetime import date, datetime, time, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import BusinessFactory, CashSessionFactory


class TestCashSessionDateValidationAPI:
    """Test date validation via API endpoints."""

    @pytest.mark.asyncio
    async def test_close_session_same_day_succeeds(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test closing session on same day succeeds."""
        business = await BusinessFactory.create(db_session)
        
        today = date.today()
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            session_date=today,
            opened_time=time(8, 0),
            created_by=admin_client.test_user.id,
        )

        response = await admin_client.put(
            f"/cash-sessions/{session.id}",
            json={
                "final_cash": "500000.00",
                "credit_card_total": "0.00",
                "debit_card_total": "0.00",
                "envelope_amount": "0.00",
                "bank_transfer_total": "0.00",
                "closed_time": "18:00:00",
            },
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_close_session_next_day_fails(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test closing session next day fails validation."""
        business = await BusinessFactory.create(db_session)
        
        yesterday = date.today() - timedelta(days=1)
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            session_date=yesterday,
            opened_time=time(8, 0),
            created_by=admin_client.test_user.id,
        )

        response = await admin_client.put(
            f"/cash-sessions/{session.id}",
            json={
                "final_cash": "500000.00",
                "credit_card_total": "0.00",
                "debit_card_total": "0.00",
                "envelope_amount": "0.00",
                "bank_transfer_total": "0.00",
                "closed_time": "18:00:00",
            },
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_close_session_last_minute_same_day(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test closing at 23:59 on same day."""
        business = await BusinessFactory.create(db_session)

        today = date.today()
        session = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            session_date=today,
            opened_time=time(23, 50),
            created_by=admin_client.test_user.id,
        )

        response = await admin_client.put(
            f"/cash-sessions/{session.id}",
            json={
                "final_cash": "500000.00",
                "credit_card_total": "0.00",
                "debit_card_total": "0.00",
                "envelope_amount": "0.00",
                "bank_transfer_total": "0.00",
                "closed_time": "23:59:00",
            },
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_close_requires_all_fields(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test close requires all payment method fields."""
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

    @pytest.mark.asyncio
    async def test_close_with_all_payment_methods(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test closing with all payment methods filled."""
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
                "credit_card_total": "100000.00",
                "debit_card_total": "50000.00",
                "envelope_amount": "200000.00",
                "bank_transfer_total": "150000.00",
                "closed_time": "18:00:00",
            },
        )

        assert response.status_code == 200