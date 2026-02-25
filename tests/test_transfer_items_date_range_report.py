"""Tests for CP-REPORTS-06 — Bank transfers date-range report."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models.transfer_item import TransferItem
from cashpilot.models.user import UserRole


class TestTransferItemsDateRangeReport:
    """Test CP-REPORTS-06 backend helpers and route behavior."""

    @pytest.mark.asyncio
    async def test_resolve_transfer_report_range_last_3_days(self):
        """Preset last_3_days resolves to a 3-day inclusive range."""
        from cashpilot.api.admin import _resolve_transfer_report_range

        from_date, to_date, selected = _resolve_transfer_report_range(
            from_date=None,
            to_date=None,
            preset="last_3_days",
        )

        assert selected == "last_3_days"
        assert (to_date - from_date).days == 2

    @pytest.mark.asyncio
    async def test_fetch_transfer_items_for_date_range_filters_by_dates(
        self, db_session: AsyncSession, factories
    ):
        """Returns only transfer items inside date range."""
        from cashpilot.api.admin import _fetch_transfer_items_for_date_range

        business = await factories.business(name="Range Business")
        cashier = await factories.user(role=UserRole.CASHIER, email="cashier-range@test.com")
        await factories.user_business(business=business, user=cashier)

        in_range_date = date(2026, 2, 20)
        out_of_range_date = date(2026, 2, 15)

        in_range_session = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=in_range_date,
            status="CLOSED",
        )
        out_range_session = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=out_of_range_date,
            status="CLOSED",
        )

        db_session.add(
            TransferItem(
                session_id=in_range_session.id,
                description="Included transfer",
                amount=Decimal("1000.00"),
                created_at=datetime(2026, 2, 20, 10, 0, 0),
            )
        )
        db_session.add(
            TransferItem(
                session_id=out_range_session.id,
                description="Excluded transfer",
                amount=Decimal("2000.00"),
                created_at=datetime(2026, 2, 15, 10, 0, 0),
            )
        )
        await db_session.commit()

        items, _ = await _fetch_transfer_items_for_date_range(
            db_session,
            from_date=date(2026, 2, 18),
            to_date=date(2026, 2, 22),
        )

        assert len(items) == 1
        assert items[0]["description"] == "Included transfer"

    @pytest.mark.asyncio
    async def test_fetch_transfer_items_for_date_range_filters_by_business(
        self, db_session: AsyncSession, factories
    ):
        """Business scoping limits transfer items to selected business."""
        from cashpilot.api.admin import _fetch_transfer_items_for_date_range

        business_a = await factories.business(name="Business A")
        business_b = await factories.business(name="Business B")
        cashier = await factories.user(role=UserRole.CASHIER, email="cashier-biz@test.com")
        await factories.user_business(business=business_a, user=cashier)
        await factories.user_business(business=business_b, user=cashier)

        session_date = date(2026, 2, 20)
        session_a = await factories.cash_session(
            business=business_a,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
        )
        session_b = await factories.cash_session(
            business=business_b,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
        )

        db_session.add(
            TransferItem(
                session_id=session_a.id,
                description="Transfer A",
                amount=Decimal("1000.00"),
                created_at=datetime(2026, 2, 20, 11, 0, 0),
            )
        )
        db_session.add(
            TransferItem(
                session_id=session_b.id,
                description="Transfer B",
                amount=Decimal("2000.00"),
                created_at=datetime(2026, 2, 20, 12, 0, 0),
            )
        )
        await db_session.commit()

        items, _ = await _fetch_transfer_items_for_date_range(
            db_session,
            from_date=session_date,
            to_date=session_date,
            selected_business_id=business_a.id,
        )

        assert len(items) == 1
        assert items[0]["description"] == "Transfer A"

    @pytest.mark.asyncio
    async def test_admin_route_renders_date_range_transfer_report(
        self, db_session: AsyncSession, factories, admin_client
    ):
        """Admin can open date-range transfer report and see transfer rows."""
        business = await factories.business(name="Report Business")
        cashier = await factories.user(
            role=UserRole.CASHIER,
            email="cashier-report@test.com",
            first_name="John",
            last_name="Doe",
        )
        await factories.user_business(business=business, user=cashier)

        session_date = date(2026, 2, 20)
        session = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
        )

        db_session.add(
            TransferItem(
                session_id=session.id,
                description="Date range transfer row",
                amount=Decimal("12345.00"),
                created_at=datetime(2026, 2, 20, 13, 45, 0),
            )
        )
        await db_session.commit()

        response = await admin_client.get(
            "/admin/transfers/date-range",
            params={
                "from_date": session_date.isoformat(),
                "to_date": session_date.isoformat(),
                "preset": "custom",
            },
        )

        assert response.status_code == 200
        assert "Bank Transfers by Date Range" in response.text
        assert "Date range transfer row" in response.text

    @pytest.mark.asyncio
    async def test_admin_route_applies_verified_filter(
        self, db_session: AsyncSession, factories, admin_client
    ):
        """Verified filter limits rows to verified transfers only."""
        business = await factories.business(name="Verified Business")
        cashier = await factories.user(role=UserRole.CASHIER, email="cashier-verified@test.com")
        await factories.user_business(business=business, user=cashier)

        session_date = date.today() - timedelta(days=1)
        session = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
        )

        db_session.add(
            TransferItem(
                session_id=session.id,
                description="Verified row",
                amount=Decimal("1000.00"),
                is_verified=True,
                created_at=datetime.combine(session_date, datetime.min.time()),
            )
        )
        db_session.add(
            TransferItem(
                session_id=session.id,
                description="Unverified row",
                amount=Decimal("2000.00"),
                is_verified=False,
                created_at=datetime.combine(session_date, datetime.min.time()),
            )
        )
        await db_session.commit()

        response = await admin_client.get(
            "/admin/transfers/date-range",
            params={
                "from_date": session_date.isoformat(),
                "to_date": session_date.isoformat(),
                "preset": "custom",
                "filter_verified": "verified",
            },
        )

        assert response.status_code == 200
        assert "Verified row" in response.text
        assert "Unverified row" not in response.text
