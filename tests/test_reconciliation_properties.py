# File: tests/test_reconciliation_properties.py
"""Tests for CashSession reconciliation properties."""
import pytest
from decimal import Decimal
from datetime import datetime
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from cashpilot.models import CashSession
from tests.factories import BusinessFactory, UserFactory
class TestCashSessionProperties:
    """Test reconciliation property calculations."""
    @pytest.mark.asyncio
    async def test_cash_sales_perfect_match(self, db_session):
        """Test cash_sales calculation with perfect match."""
        business = await BusinessFactory.create(db_session)
        cashier = await UserFactory.create(db_session)
        session = CashSession(
            business_id=business.id,
            cashier_id=cashier.id,
            created_by=cashier.id,
            initial_cash=Decimal("500000.00"),
            final_cash=Decimal("1200000.00"),
            envelope_amount=Decimal("300000.00"),
            credit_card_total=Decimal("0.00"),
            bank_transfer_total=Decimal("0.00"),
        )
        # (1,200,000 - 500,000) - 300,000 = 400,000
        assert session.cash_sales == Decimal("400000.00")
    @pytest.mark.asyncio
    async def test_cash_sales_no_envelope(self, db_session):
        """Test cash_sales without envelope."""
        business = await BusinessFactory.create(db_session)
        cashier = await UserFactory.create(db_session)
        session = CashSession(
            business_id=business.id,
            cashier_id=cashier.id,
            created_by=cashier.id,
            initial_cash=Decimal("500000.00"),
            final_cash=Decimal("1500000.00"),
            envelope_amount=Decimal("0.00"),
            credit_card_total=Decimal("0.00"),
            bank_transfer_total=Decimal("0.00"),
        )
        # (1,500,000 - 500,000) - 0 = 1,000,000
        assert session.cash_sales == Decimal("1000000.00")
    @pytest.mark.asyncio
    async def test_cash_sales_when_final_is_none(self, db_session):
        """Test cash_sales returns 0 when session not closed."""
        business = await BusinessFactory.create(db_session)
        cashier = await UserFactory.create(db_session)
        session = CashSession(
            business_id=business.id,
            cashier_id=cashier.id,
            created_by=cashier.id,
            initial_cash=Decimal("500000.00"),
            final_cash=None,  # Session still open
            envelope_amount=Decimal("0.00"),
            credit_card_total=Decimal("0.00"),
            bank_transfer_total=Decimal("0.00"),
        )
        assert session.cash_sales == Decimal("0.00")
    @pytest.mark.asyncio
    async def test_total_sales_all_payment_methods(self, db_session):
        """Test total_sales across all payment methods."""
        business = await BusinessFactory.create(db_session)
        cashier = await UserFactory.create(db_session)
        session = CashSession(
            business_id=business.id,
            cashier_id=cashier.id,
            created_by=cashier.id,
            initial_cash=Decimal("500000.00"),
            final_cash=Decimal("1200000.00"),
            envelope_amount=Decimal("300000.00"),
            credit_card_total=Decimal("800000.00"),
            bank_transfer_total=Decimal("150000.00"),
        )
        # cash_sales = 400,000
        # total_sales = 400,000 + 800,000 + 150,000 = 1,350,000
        assert session.total_sales == Decimal("1350000.00")
    @pytest.mark.asyncio
    async def test_total_sales_cash_only(self, db_session):
        """Test total_sales with only cash payments."""
        business = await BusinessFactory.create(db_session)
        cashier = await UserFactory.create(db_session)
        session = CashSession(
            business_id=business.id,
            cashier_id=cashier.id,
            created_by=cashier.id,
            initial_cash=Decimal("500000.00"),
            final_cash=Decimal("1500000.00"),
            envelope_amount=Decimal("0.00"),
            credit_card_total=Decimal("0.00"),
            bank_transfer_total=Decimal("0.00"),
        )
        # cash_sales = 1,000,000
        # total_sales = 1,000,000 + 0 = 1,000,000
        assert session.total_sales == Decimal("1000000.00")
