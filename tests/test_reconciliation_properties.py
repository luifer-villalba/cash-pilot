"""Tests for CashSession reconciliation properties."""

import pytest
from decimal import Decimal
from datetime import datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models import CashSession


class TestCashSessionProperties:
    """Test reconciliation property calculations."""

    async def test_cash_sales_perfect_match(self):
        """Test cash_sales calculation with perfect match."""
        session = CashSession(
            business_id=uuid4(),
            cashier_name="Test Cashier",
            initial_cash=Decimal("500000.00"),
            final_cash=Decimal("1200000.00"),
            envelope_amount=Decimal("300000.00"),
            credit_card_total=Decimal("0.00"),
            debit_card_total=Decimal("0.00"),
            bank_transfer_total=Decimal("0.00"),
        )

        # (1,200,000 - 500,000) + 300,000 = 1,000,000
        assert session.cash_sales == Decimal("1000000.00")

    async def test_cash_sales_no_envelope(self):
        """Test cash_sales without envelope."""
        session = CashSession(
            business_id=uuid4(),
            cashier_name="Test Cashier",
            initial_cash=Decimal("500000.00"),
            final_cash=Decimal("1500000.00"),
            envelope_amount=Decimal("0.00"),
            credit_card_total=Decimal("0.00"),
            debit_card_total=Decimal("0.00"),
            bank_transfer_total=Decimal("0.00"),
        )

        # (1,500,000 - 500,000) + 0 = 1,000,000
        assert session.cash_sales == Decimal("1000000.00")

    async def test_cash_sales_when_final_is_none(self):
        """Test cash_sales returns 0 when session not closed."""
        session = CashSession(
            business_id=uuid4(),
            cashier_name="Test Cashier",
            initial_cash=Decimal("500000.00"),
            final_cash=None,  # Session still open
            envelope_amount=Decimal("0.00"),
            credit_card_total=Decimal("0.00"),
            debit_card_total=Decimal("0.00"),
            bank_transfer_total=Decimal("0.00"),
        )

        assert session.cash_sales == Decimal("0.00")

    async def test_total_sales_all_payment_methods(self):
        """Test total_sales across all payment methods."""
        session = CashSession(
            business_id=uuid4(),
            cashier_name="Test Cashier",
            initial_cash=Decimal("500000.00"),
            final_cash=Decimal("1200000.00"),
            envelope_amount=Decimal("300000.00"),
            credit_card_total=Decimal("800000.00"),
            debit_card_total=Decimal("450000.00"),
            bank_transfer_total=Decimal("150000.00"),
        )

        # cash_sales = 1,000,000
        # total_sales = 1,000,000 + 800,000 + 450,000 + 150,000 = 2,400,000
        assert session.total_sales == Decimal("2400000.00")

    async def test_total_sales_cash_only(self):
        """Test total_sales with only cash payments."""
        session = CashSession(
            business_id=uuid4(),
            cashier_name="Test Cashier",
            initial_cash=Decimal("500000.00"),
            final_cash=Decimal("1500000.00"),
            envelope_amount=Decimal("0.00"),
            credit_card_total=Decimal("0.00"),
            debit_card_total=Decimal("0.00"),
            bank_transfer_total=Decimal("0.00"),
        )

        # cash_sales = 1,000,000
        # total_sales = 1,000,000 + 0 = 1,000,000
        assert session.total_sales == Decimal("1000000.00")

    async def test_difference_perfect_match(self):
        """Test difference when reconciliation is perfect."""
        session = CashSession(
            business_id=uuid4(),
            cashier_name="Test Cashier",
            initial_cash=Decimal("500000.00"),
            final_cash=Decimal("1200000.00"),
            envelope_amount=Decimal("300000.00"),
            credit_card_total=Decimal("1000000.00"),
            debit_card_total=Decimal("0.00"),
            bank_transfer_total=Decimal("0.00"),
        )

        # cash_sales = 1,000,000
        # total_sales = 1,000,000 + 1,000,000 = 2,000,000
        # difference = 2,000,000 - 1,000,000 = 1,000,000 (all non-cash)
        assert session.difference == Decimal("1000000.00")

    async def test_difference_zero_all_cash(self):
        """Test difference is zero when all sales are cash."""
        session = CashSession(
            business_id=uuid4(),
            cashier_name="Test Cashier",
            initial_cash=Decimal("500000.00"),
            final_cash=Decimal("1500000.00"),
            envelope_amount=Decimal("0.00"),
            credit_card_total=Decimal("0.00"),
            debit_card_total=Decimal("0.00"),
            bank_transfer_total=Decimal("0.00"),
        )

        # cash_sales = 1,000,000
        # total_sales = 1,000,000
        # difference = 0 (perfect match, all cash)
        assert session.difference == Decimal("0.00")

    async def test_difference_shortage(self):
        """Test difference detects shortage."""
        session = CashSession(
            business_id=uuid4(),
            cashier_name="Test Cashier",
            initial_cash=Decimal("500000.00"),
            final_cash=Decimal("900000.00"),  # Lower than expected
            envelope_amount=Decimal("200000.00"),
            credit_card_total=Decimal("1000000.00"),
            debit_card_total=Decimal("0.00"),
            bank_transfer_total=Decimal("0.00"),
        )

        # cash_sales = (900,000 - 500,000) + 200,000 = 600,000
        # total_sales = 600,000 + 1,000,000 = 1,600,000
        # difference = 1,600,000 - 600,000 = 1,000,000 (1M expected in cash but only 600k)
        # Shortage = +400,000
        assert session.cash_sales == Decimal("600000.00")
        assert session.total_sales == Decimal("1600000.00")
        assert session.difference == Decimal("1000000.00")

    async def test_difference_overage(self):
        """Test difference detects overage."""
        session = CashSession(
            business_id=uuid4(),
            cashier_name="Test Cashier",
            initial_cash=Decimal("500000.00"),
            final_cash=Decimal("1600000.00"),  # Higher than expected
            envelope_amount=Decimal("300000.00"),
            credit_card_total=Decimal("1000000.00"),
            debit_card_total=Decimal("0.00"),
            bank_transfer_total=Decimal("0.00"),
        )

        # cash_sales = (1,600,000 - 500,000) + 300,000 = 1,400,000
        # total_sales = 1,400,000 + 1,000,000 = 2,400,000
        # difference = 2,400,000 - 1,400,000 = 1,000,000
        assert session.cash_sales == Decimal("1400000.00")
        assert session.total_sales == Decimal("2400000.00")
        assert session.difference == Decimal("1000000.00")

    async def test_large_numbers_precision(self):
        """Test properties with large numbers maintain precision."""
        session = CashSession(
            business_id=uuid4(),
            cashier_name="Test Cashier",
            initial_cash=Decimal("50000000.00"),  # 50M
            final_cash=Decimal("120000000.00"),   # 120M
            envelope_amount=Decimal("30000000.00"),  # 30M
            credit_card_total=Decimal("80000000.00"),
            debit_card_total=Decimal("45000000.00"),
            bank_transfer_total=Decimal("15000000.00"),
        )

        # cash_sales = (120M - 50M) + 30M = 100M
        assert session.cash_sales == Decimal("100000000.00")
        # total_sales = 100M + 80M + 45M + 15M = 240M
        assert session.total_sales == Decimal("240000000.00")
        # difference = 240M - 100M = 140M
        assert session.difference == Decimal("140000000.00")
