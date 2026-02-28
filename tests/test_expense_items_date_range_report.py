"""Tests for CP-REPORTS-07 — Expenses date-range report."""

from datetime import date, datetime, timedelta
from html import unescape
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models.expense_item import ExpenseItem
from cashpilot.models.user import UserRole


class TestExpenseItemsDateRangeReport:
    """Test CP-REPORTS-07 route behavior."""

    @pytest.mark.asyncio
    async def test_admin_route_renders_date_range_expense_report(
        self, db_session: AsyncSession, factories, admin_client
    ):
        """Admin can open date-range expense report and see expense rows."""
        business = await factories.business(name="Expense Report Business")
        cashier = await factories.user(
            role=UserRole.CASHIER,
            email="cashier-expense-report@test.com",
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
        )

        db_session.add(
            ExpenseItem(
                session_id=session.id,
                description="Date range expense row",
                amount=Decimal("12345.00"),
                created_at=datetime.combine(session_date, datetime.min.time())
                + timedelta(hours=13, minutes=45),
            )
        )
        await db_session.commit()

        response = await admin_client.get(
            "/admin/expenses/date-range",
            params={
                "from_date": session_date.isoformat(),
                "to_date": session_date.isoformat(),
            },
        )

        assert response.status_code == 200
        assert "Expenses by Date Range" in response.text
        assert "Date range expense row" in response.text

    @pytest.mark.asyncio
    async def test_admin_route_accepts_single_date_query(
        self, db_session: AsyncSession, factories, admin_client
    ):
        """single_date maps to one-day range when from/to are not provided."""
        business = await factories.business(name="Expense Single Date Business")
        cashier = await factories.user(
            role=UserRole.CASHIER,
            email="cashier-expense-single-date@test.com",
        )
        await factories.user_business(business=business, user=cashier)

        target_date = date.today() - timedelta(days=1)
        session = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=target_date,
            status="CLOSED",
        )

        db_session.add(
            ExpenseItem(
                session_id=session.id,
                description="Single date expense row",
                amount=Decimal("999.00"),
                created_at=datetime.combine(target_date, datetime.min.time()),
            )
        )
        await db_session.commit()

        response = await admin_client.get(
            "/admin/expenses/date-range",
            params={
                "single_date": target_date.isoformat(),
            },
        )

        assert response.status_code == 200
        assert "Single date expense row" in response.text

    @pytest.mark.asyncio
    async def test_admin_route_filters_with_multiple_business_ids(
        self, db_session: AsyncSession, factories, admin_client
    ):
        """business_ids accepts multiple values and includes rows from selected businesses."""
        business_a = await factories.business(name="Expense Business A")
        business_b = await factories.business(name="Expense Business B")
        business_c = await factories.business(name="Expense Business C")

        cashier = await factories.user(role=UserRole.CASHIER, email="cashier-expense-multi@test.com")
        await factories.user_business(business=business_a, user=cashier)
        await factories.user_business(business=business_b, user=cashier)
        await factories.user_business(business=business_c, user=cashier)

        session_date = date.today() - timedelta(days=1)
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
        session_c = await factories.cash_session(
            business=business_c,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
        )

        db_session.add(
            ExpenseItem(
                session_id=session_a.id,
                description="Business A expense",
                amount=Decimal("1000.00"),
                created_at=datetime.combine(session_date, datetime.min.time()),
            )
        )
        db_session.add(
            ExpenseItem(
                session_id=session_b.id,
                description="Business B expense",
                amount=Decimal("2000.00"),
                created_at=datetime.combine(session_date, datetime.min.time()) + timedelta(minutes=1),
            )
        )
        db_session.add(
            ExpenseItem(
                session_id=session_c.id,
                description="Business C expense",
                amount=Decimal("3000.00"),
                created_at=datetime.combine(session_date, datetime.min.time()) + timedelta(minutes=2),
            )
        )
        await db_session.commit()

        response = await admin_client.get(
            "/admin/expenses/date-range",
            params={
                "from_date": session_date.isoformat(),
                "to_date": session_date.isoformat(),
                "business_ids": [str(business_a.id), str(business_b.id)],
            },
        )

        assert response.status_code == 200
        assert "Business A expense" in response.text
        assert "Business B expense" in response.text
        assert "Business C expense" not in response.text

    @pytest.mark.asyncio
    async def test_admin_route_applies_cashier_filter(
        self, db_session: AsyncSession, factories, admin_client
    ):
        """Cashier filter limits rows to selected cashier."""
        business = await factories.business(name="Expense Cashier Business")
        cashier_a = await factories.user(
            role=UserRole.CASHIER,
            email="cashier-expense-a@test.com",
            first_name="Alice",
            last_name="Doe",
        )
        cashier_b = await factories.user(
            role=UserRole.CASHIER,
            email="cashier-expense-b@test.com",
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
        )
        session_b = await factories.cash_session(
            business=business,
            cashier=cashier_b,
            session_date=session_date,
            status="CLOSED",
        )

        db_session.add(
            ExpenseItem(
                session_id=session_a.id,
                description="Cashier A expense",
                amount=Decimal("1111.00"),
                created_at=datetime.combine(session_date, datetime.min.time()),
            )
        )
        db_session.add(
            ExpenseItem(
                session_id=session_b.id,
                description="Cashier B expense",
                amount=Decimal("2222.00"),
                created_at=datetime.combine(session_date, datetime.min.time()) + timedelta(minutes=1),
            )
        )
        await db_session.commit()

        response = await admin_client.get(
            "/admin/expenses/date-range",
            params={
                "from_date": session_date.isoformat(),
                "to_date": session_date.isoformat(),
                "filter_cashier": str(cashier_a.id),
            },
        )

        assert response.status_code == 200
        assert "Cashier A expense" in response.text
        assert "Cashier B expense" not in response.text

    @pytest.mark.asyncio
    async def test_admin_route_applies_description_filter_case_insensitive(
        self, db_session: AsyncSession, factories, admin_client
    ):
        """Description filter matches substring without case sensitivity."""
        business = await factories.business(name="Expense Description Business")
        cashier = await factories.user(
            role=UserRole.CASHIER,
            email="cashier-expense-description@test.com",
        )
        await factories.user_business(business=business, user=cashier)

        session_date = date.today() - timedelta(days=1)
        session = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
        )

        db_session.add(
            ExpenseItem(
                session_id=session.id,
                description="Cash & Carry Supplies",
                amount=Decimal("1000.00"),
                created_at=datetime.combine(session_date, datetime.min.time()),
            )
        )
        db_session.add(
            ExpenseItem(
                session_id=session.id,
                description="Delivery fuel",
                amount=Decimal("2000.00"),
                created_at=datetime.combine(session_date, datetime.min.time())
                + timedelta(minutes=1),
            )
        )
        await db_session.commit()

        response = await admin_client.get(
            "/admin/expenses/date-range",
            params={
                "from_date": session_date.isoformat(),
                "to_date": session_date.isoformat(),
                "filter_description": "cAsH & CaRrY",
            },
        )

        assert response.status_code == 200
        response_text = unescape(response.text)
        assert "Cash & Carry Supplies" in response_text
        assert "Delivery fuel" not in response_text
