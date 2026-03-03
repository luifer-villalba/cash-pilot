"""Tests for CP-REPORTS-08 — Envelope date-range report."""

from datetime import date, time, timedelta
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
    async def test_admin_route_renders_business_summary_mvp(
        self, db_session: AsyncSession, factories, admin_client
    ):
        """Report renders KPI + business summary block with quick filter action."""
        business_a = await factories.business(name="Envelope Summary A")
        business_b = await factories.business(name="Envelope Summary B")
        cashier = await factories.user(role=UserRole.CASHIER, email="cashier-envelope-summary@test.com")
        await factories.user_business(business=business_a, user=cashier)
        await factories.user_business(business=business_b, user=cashier)

        session_date = date.today() - timedelta(days=1)
        await factories.cash_session(
            business=business_a,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
            envelope_amount=Decimal("1100.00"),
        )
        await factories.cash_session(
            business=business_b,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
            envelope_amount=Decimal("2200.00"),
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
        assert "Summary by business" in response.text
        assert "Businesses with envelopes" in response.text
        assert "View" in response.text

    @pytest.mark.asyncio
    async def test_admin_route_renders_business_groups_in_alphabetical_order(
        self, db_session: AsyncSession, factories, admin_client
    ):
        """Business group sections are shown in alphabetical order by business name."""
        business_z = await factories.business(name="Zeta Pharmacy")
        business_a = await factories.business(name="Alpha Pharmacy")
        cashier = await factories.user(role=UserRole.CASHIER, email="cashier-envelope-alpha-zeta@test.com")
        await factories.user_business(business=business_z, user=cashier)
        await factories.user_business(business=business_a, user=cashier)

        session_date = date.today() - timedelta(days=1)
        await factories.cash_session(
            business=business_z,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
            envelope_amount=Decimal("9000.00"),
        )
        await factories.cash_session(
            business=business_a,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
            envelope_amount=Decimal("1000.00"),
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

        alpha_header = f'business-master-checkbox"\n                            data-business-id="{business_a.id}"'
        zeta_header = f'business-master-checkbox"\n                            data-business-id="{business_z.id}"'

        assert alpha_header in response.text
        assert zeta_header in response.text
        assert response.text.index(alpha_header) < response.text.index(zeta_header)

    @pytest.mark.asyncio
    async def test_admin_route_renders_summary_rows_in_alphabetical_order(
        self, db_session: AsyncSession, factories, admin_client
    ):
        """Summary table rows are ordered alphabetically by business name."""
        business_z = await factories.business(name="Zeta Summary Pharmacy")
        business_a = await factories.business(name="Alpha Summary Pharmacy")
        cashier = await factories.user(
            role=UserRole.CASHIER,
            email="cashier-envelope-summary-order@test.com",
        )
        await factories.user_business(business=business_z, user=cashier)
        await factories.user_business(business=business_a, user=cashier)

        session_date = date.today() - timedelta(days=1)
        await factories.cash_session(
            business=business_z,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
            envelope_amount=Decimal("9000.00"),
        )
        await factories.cash_session(
            business=business_a,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
            envelope_amount=Decimal("1000.00"),
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

        summary_start = response.text.index("Summary by business")
        summary_end = response.text.index("Showing", summary_start)
        summary_block = response.text[summary_start:summary_end]

        assert "Alpha Summary Pharmacy" in summary_block
        assert "Zeta Summary Pharmacy" in summary_block
        assert summary_block.index("Alpha Summary Pharmacy") < summary_block.index("Zeta Summary Pharmacy")

    @pytest.mark.asyncio
    async def test_admin_route_renders_envelopes_in_ascending_datetime_order(
        self, db_session: AsyncSession, factories, admin_client
    ):
        """Envelope rows are ordered by date/time ascending inside business groups."""
        business = await factories.business(name="Envelope Chrono Business")
        cashier = await factories.user(role=UserRole.CASHIER, email="cashier-envelope-chrono@test.com")
        await factories.user_business(business=business, user=cashier)

        oldest_date = date.today() - timedelta(days=3)
        middle_date = date.today() - timedelta(days=2)
        newest_date = date.today() - timedelta(days=1)

        middle_session = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=middle_date,
            opened_time=time(9, 15, 0),
            status="CLOSED",
            envelope_amount=Decimal("1200.00"),
        )
        newest_session = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=newest_date,
            opened_time=time(10, 45, 0),
            status="CLOSED",
            envelope_amount=Decimal("1300.00"),
        )
        oldest_session = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=oldest_date,
            opened_time=time(8, 30, 0),
            status="CLOSED",
            envelope_amount=Decimal("1100.00"),
        )
        await db_session.commit()

        response = await admin_client.get(
            "/admin/envelopes/date-range",
            params={
                "from_date": oldest_date.isoformat(),
                "to_date": newest_date.isoformat(),
            },
        )

        assert response.status_code == 200

        oldest_link = f"/sessions/{oldest_session.id}"
        middle_link = f"/sessions/{middle_session.id}"
        newest_link = f"/sessions/{newest_session.id}"

        assert oldest_link in response.text
        assert middle_link in response.text
        assert newest_link in response.text
        assert response.text.index(oldest_link) < response.text.index(middle_link)
        assert response.text.index(middle_link) < response.text.index(newest_link)

    @pytest.mark.asyncio
    async def test_admin_route_renders_weekday_label_by_locale(
        self, db_session: AsyncSession, factories, admin_client
    ):
        """Session time label includes localized weekday based on selected language."""
        business = await factories.business(name="Envelope Locale Business")
        cashier = await factories.user(role=UserRole.CASHIER, email="cashier-envelope-locale@test.com")
        await factories.user_business(business=business, user=cashier)

        monday_date = date(2026, 2, 23)
        await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=monday_date,
            opened_time=time(14, 30, 0),
            status="CLOSED",
            envelope_amount=Decimal("1500.00"),
        )
        await db_session.commit()

        response_en = await admin_client.get(
            "/admin/envelopes/date-range",
            params={
                "from_date": monday_date.isoformat(),
                "to_date": monday_date.isoformat(),
            },
        )
        response_es = await admin_client.get(
            "/admin/envelopes/date-range",
            params={
                "from_date": monday_date.isoformat(),
                "to_date": monday_date.isoformat(),
                "lang": "es",
            },
        )

        assert response_en.status_code == 200
        assert response_es.status_code == 200
        assert "Monday" in response_en.text
        assert "Lunes" in response_es.text

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
    async def test_admin_route_excludes_zero_envelope_by_default(
        self, db_session: AsyncSession, factories, admin_client
    ):
        """Zero envelope sessions are excluded by default from the report."""
        business = await factories.business(name="Envelope Default Filter Business")
        cashier = await factories.user(role=UserRole.CASHIER, email="cashier-envelope-default@test.com")
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
            envelope_amount=Decimal("500.00"),
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
        assert str(positive_session.id) in response.text
        assert str(zero_session.id) not in response.text

    @pytest.mark.asyncio
    async def test_admin_route_this_month_preset_sets_date_range(
        self, db_session: AsyncSession, factories, admin_client
    ):
        """this_month preset returns data from current month up to today."""
        business = await factories.business(name="Envelope Preset Business")
        cashier = await factories.user(role=UserRole.CASHIER, email="cashier-envelope-preset@test.com")
        await factories.user_business(business=business, user=cashier)

        today = date.today()
        inside_date = today.replace(day=1)
        outside_date = inside_date - timedelta(days=1)

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
            params={"preset": "this_month"},
        )

        assert response.status_code == 200
        assert str(inside_session.id) in response.text
        assert str(outside_session.id) not in response.text
