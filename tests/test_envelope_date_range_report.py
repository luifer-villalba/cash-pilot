"""Tests for CP-REPORTS-08 — Envelope date-range report."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models.user import UserRole


class TestEnvelopeDateRangeReport:
    """Test CP-REPORTS-08 route behavior."""

    @pytest.mark.asyncio
    async def test_admin_route_renders_date_range_envelope_report(
        self, db_session: AsyncSession, factories, admin_client
    ):
        """Admin can open date-range envelope report and see envelope rows."""
        business = await factories.business(name="Envelope Report Business")
        cashier = await factories.user(
            role=UserRole.CASHIER,
            email="cashier-envelope-report@test.com",
            first_name="John",
            last_name="Doe",
        )
        await factories.user_business(business=business, user=cashier)

        session_date = date.today() - timedelta(days=1)
        session = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
            envelope_amount=Decimal("12345.00"),
        )
        await db_session.commit()

        response = await admin_client.get(
            "/admin/envelopes/date-range",
            params={
                "from_date": session_date.isoformat(),
                "to_date": session_date.isoformat(),
            },
        )

        assert response.status_code == 200
        assert "Envelopes by Date Range" in response.text
        assert str(session.id) in response.text

    @pytest.mark.asyncio
    async def test_admin_route_accepts_single_date_query(
        self, db_session: AsyncSession, factories, admin_client
    ):
        """single_date maps to one-day range when from/to are not provided."""
        business = await factories.business(name="Envelope Single Date Business")
        cashier = await factories.user(
            role=UserRole.CASHIER,
            email="cashier-envelope-single-date@test.com",
        )
        await factories.user_business(business=business, user=cashier)

        target_date = date.today() - timedelta(days=1)
        session = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=target_date,
            status="CLOSED",
            envelope_amount=Decimal("999.00"),
        )
        await db_session.commit()

        response = await admin_client.get(
            "/admin/envelopes/date-range",
            params={
                "single_date": target_date.isoformat(),
            },
        )

        assert response.status_code == 200
        assert str(session.id) in response.text

    @pytest.mark.asyncio
    async def test_admin_route_filters_with_multiple_business_ids(
        self, db_session: AsyncSession, factories, admin_client
    ):
        """business_ids accepts multiple values and includes rows from selected businesses."""
        business_a = await factories.business(name="Envelope Business A")
        business_b = await factories.business(name="Envelope Business B")
        business_c = await factories.business(name="Envelope Business C")

        cashier = await factories.user(role=UserRole.CASHIER, email="cashier-envelope-multi@test.com")
        await factories.user_business(business=business_a, user=cashier)
        await factories.user_business(business=business_b, user=cashier)
        await factories.user_business(business=business_c, user=cashier)

        session_date = date.today() - timedelta(days=1)
        session_a = await factories.cash_session(
            business=business_a,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
            envelope_amount=Decimal("1000.00"),
        )
        session_b = await factories.cash_session(
            business=business_b,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
            envelope_amount=Decimal("2000.00"),
        )
        session_c = await factories.cash_session(
            business=business_c,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
            envelope_amount=Decimal("3000.00"),
        )
        await db_session.commit()

        response = await admin_client.get(
            "/admin/envelopes/date-range",
            params={
                "from_date": session_date.isoformat(),
                "to_date": session_date.isoformat(),
                "business_ids": [str(business_a.id), str(business_b.id)],
            },
        )

        assert response.status_code == 200
        assert str(session_a.id) in response.text
        assert str(session_b.id) in response.text
        assert str(session_c.id) not in response.text

    @pytest.mark.asyncio
    async def test_admin_route_applies_cashier_filter(
        self, db_session: AsyncSession, factories, admin_client
    ):
        """Cashier filter limits rows to selected cashier."""
        business = await factories.business(name="Envelope Cashier Business")
        cashier_a = await factories.user(
            role=UserRole.CASHIER,
            email="cashier-envelope-a@test.com",
            first_name="Alice",
            last_name="Doe",
        )
        cashier_b = await factories.user(
            role=UserRole.CASHIER,
            email="cashier-envelope-b@test.com",
            first_name="Bob",
            last_name="Doe",
        )

        await factories.user_business(business=business, user=cashier_a)
        await factories.user_business(business=business, user=cashier_b)

        session_date = date.today() - timedelta(days=1)
        session_a = await factories.cash_session(
            business=business,
            cashier=cashier_a,
            session_date=session_date,
            status="CLOSED",
            envelope_amount=Decimal("1111.00"),
        )
        session_b = await factories.cash_session(
            business=business,
            cashier=cashier_b,
            session_date=session_date,
            status="CLOSED",
            envelope_amount=Decimal("2222.00"),
        )
        await db_session.commit()

        response = await admin_client.get(
            "/admin/envelopes/date-range",
            params={
                "from_date": session_date.isoformat(),
                "to_date": session_date.isoformat(),
                "filter_cashier": str(cashier_a.id),
            },
        )

        assert response.status_code == 200
        assert str(session_a.id) in response.text
        assert str(session_b.id) not in response.text

    @pytest.mark.asyncio
    async def test_admin_route_applies_amount_state_filter(
        self, db_session: AsyncSession, factories, admin_client
    ):
        """Amount state filter selects only sessions with envelope amount > 0."""
        business = await factories.business(name="Envelope State Business")
        cashier = await factories.user(role=UserRole.CASHIER, email="cashier-envelope-state@test.com")
        await factories.user_business(business=business, user=cashier)

        session_date = date.today() - timedelta(days=1)
        zero_session = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
            envelope_amount=Decimal("0.00"),
        )
        positive_session = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
            envelope_amount=Decimal("5000.00"),
        )
        await db_session.commit()

        response = await admin_client.get(
            "/admin/envelopes/date-range",
            params={
                "from_date": session_date.isoformat(),
                "to_date": session_date.isoformat(),
                "filter_amount_state": "with_envelope",
            },
        )

        assert response.status_code == 200
        assert str(positive_session.id) in response.text
        assert str(zero_session.id) not in response.text

    @pytest.mark.asyncio
    async def test_admin_route_last_month_preset_sets_date_range(
        self, db_session: AsyncSession, factories, admin_client
    ):
        """last_month preset returns data from the last 30 days window."""
        business = await factories.business(name="Envelope Preset Business")
        cashier = await factories.user(role=UserRole.CASHIER, email="cashier-envelope-preset@test.com")
        await factories.user_business(business=business, user=cashier)

        inside_date = date.today() - timedelta(days=10)
        outside_date = date.today() - timedelta(days=40)

        inside_session = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=inside_date,
            status="CLOSED",
            envelope_amount=Decimal("7000.00"),
        )
        outside_session = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=outside_date,
            status="CLOSED",
            envelope_amount=Decimal("8000.00"),
        )
        await db_session.commit()

        response = await admin_client.get(
            "/admin/envelopes/date-range",
            params={"preset": "last_month"},
        )

        assert response.status_code == 200
        assert str(inside_session.id) in response.text
        assert str(outside_session.id) not in response.text
