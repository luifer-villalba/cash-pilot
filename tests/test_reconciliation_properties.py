# File: tests/test_reconciliation_properties.py
"""Tests for CashSession reconciliation properties."""

import pytest
from decimal import Decimal
from uuid import uuid4

from cashpilot.models import CashSession


class TestCashSessionProperties:
    """Test reconciliation property calculations."""

    async def test_cash_sales_perfect_match(self):
        """Test cash_sales calculation with perfect match."""
        session = CashSession(
            business_id=uuid4(),
            cashier_id=uuid4(),
            initial_cash=Decimal("500000.00"),
            final_cash=Decimal("1200000.00"),
            envelope_amount=Decimal("300000.00"),
            expenses=Decimal("125000.00"),
            credit_card_total=Decimal("0.00"),
            debit_card_total=Decimal("0.00"),
            bank_transfer_total=Decimal("0.00"),
        )

        # (1,200,000 - 500,000) + 300,000 + 125,000 - 0 = 1,125,000
        assert session.cash_sales == Decimal("1125000.00")

    async def test_cash_sales_no_envelope(self):
        """Test cash_sales without envelope."""
        session = CashSession(
            business_id=uuid4(),
            cashier_id=uuid4(),
            initial_cash=Decimal("500000.00"),
            final_cash=Decimal("1500000.00"),
            envelope_amount=Decimal("0.00"),
            expenses=Decimal("100000.00"),
            credit_card_total=Decimal("0.00"),
            debit_card_total=Decimal("0.00"),
            bank_transfer_total=Decimal("0.00"),
        )

        # (1,500,000 - 500,000) + 0 + 100,000 - 0 = 1,100,000
        assert session.cash_sales == Decimal("1100000.00")

    async def test_cash_sales_no_expenses(self):
        """Test cash_sales without expenses."""
        session = CashSession(
            business_id=uuid4(),
            cashier_id=uuid4(),
            initial_cash=Decimal("500000.00"),
            final_cash=Decimal("1200000.00"),
            envelope_amount=Decimal("300000.00"),
            expenses=Decimal("0.00"),
            credit_card_total=Decimal("0.00"),
            debit_card_total=Decimal("0.00"),
            bank_transfer_total=Decimal("0.00"),
        )

        # (1,200,000 - 500,000) + 300,000 + 0 - 0 = 1,000,000
        assert session.cash_sales == Decimal("1000000.00")

    async def test_cash_sales_when_final_is_none(self):
        """Test cash_sales returns 0 when session not closed."""
        session = CashSession(
            business_id=uuid4(),
            cashier_id=uuid4(),
            initial_cash=Decimal("500000.00"),
            final_cash=None,
            envelope_amount=Decimal("0.00"),
            expenses=Decimal("50000.00"),
            credit_card_total=Decimal("0.00"),
            debit_card_total=Decimal("0.00"),
            bank_transfer_total=Decimal("0.00"),
        )

        assert session.cash_sales == Decimal("0.00")

    async def test_cash_sales_with_credit_payments_collected(self):
        """Test cash_sales calculation subtracting credit_payments_collected."""
        session = CashSession(
            business_id=uuid4(),
            cashier_id=uuid4(),
            initial_cash=Decimal("500000.00"),
            final_cash=Decimal("1200000.00"),
            envelope_amount=Decimal("300000.00"),
            expenses=Decimal("125000.00"),
            credit_payments_collected=Decimal("200000.00"),
            credit_card_total=Decimal("0.00"),
            debit_card_total=Decimal("0.00"),
            bank_transfer_total=Decimal("0.00"),
        )

        # (1,200,000 - 500,000) + 300,000 + 125,000 - 200,000 = 925,000
        assert session.cash_sales == Decimal("925000.00")

    async def test_total_sales_all_payment_methods(self):
        """Test total_sales across all payment methods."""
        session = CashSession(
            business_id=uuid4(),
            cashier_id=uuid4(),
            initial_cash=Decimal("500000.00"),
            final_cash=Decimal("1200000.00"),
            envelope_amount=Decimal("300000.00"),
            expenses=Decimal("125000.00"),
            credit_card_total=Decimal("800000.00"),
            debit_card_total=Decimal("450000.00"),
            bank_transfer_total=Decimal("150000.00"),
        )

        # cash_sales = 1,125,000
        # total_sales = 1,125,000 + 800,000 + 450,000 + 150,000 + 0 = 2,525,000
        assert session.total_sales == Decimal("2525000.00")

    async def test_total_sales_cash_only(self):
        """Test total_sales with only cash payments."""
        session = CashSession(
            business_id=uuid4(),
            cashier_id=uuid4(),
            initial_cash=Decimal("500000.00"),
            final_cash=Decimal("1500000.00"),
            envelope_amount=Decimal("0.00"),
            expenses=Decimal("100000.00"),
            credit_card_total=Decimal("0.00"),
            debit_card_total=Decimal("0.00"),
            bank_transfer_total=Decimal("0.00"),
        )

        # cash_sales = 1,100,000
        # total_sales = 1,100,000 + 0 + 0 + 0 + 0 = 1,100,000
        assert session.total_sales == Decimal("1100000.00")

    async def test_total_sales_with_credit_sales(self):
        """Test total_sales including credit sales."""
        session = CashSession(
            business_id=uuid4(),
            cashier_id=uuid4(),
            initial_cash=Decimal("500000.00"),
            final_cash=Decimal("1200000.00"),
            envelope_amount=Decimal("300000.00"),
            expenses=Decimal("125000.00"),
            credit_card_total=Decimal("800000.00"),
            debit_card_total=Decimal("450000.00"),
            bank_transfer_total=Decimal("150000.00"),
            credit_sales_total=Decimal("500000.00"),
        )

        # cash_sales = 1,125,000
        # total_sales = 1,125,000 + 800,000 + 450,000 + 150,000 + 500,000 = 3,025,000
        assert session.total_sales == Decimal("3025000.00")

    async def test_net_earnings_with_expenses(self):
        """Test net_earnings calculation."""
        session = CashSession(
            business_id=uuid4(),
            cashier_id=uuid4(),
            initial_cash=Decimal("500000.00"),
            final_cash=Decimal("1200000.00"),
            envelope_amount=Decimal("300000.00"),
            expenses=Decimal("125000.00"),
            credit_card_total=Decimal("800000.00"),
            debit_card_total=Decimal("450000.00"),
            bank_transfer_total=Decimal("150000.00"),
        )

        # total_sales = 2,525,000
        # net_earnings = 2,525,000 - 125,000 = 2,400,000
        assert session.net_earnings == Decimal("2400000.00")

    async def test_shortage_surplus_with_expenses(self):
        """Test shortage_surplus calculation with expenses."""
        session = CashSession(
            business_id=uuid4(),
            cashier_id=uuid4(),
            initial_cash=Decimal("500000.00"),
            final_cash=Decimal("1500000.00"),
            envelope_amount=Decimal("200000.00"),
            expenses=Decimal("100000.00"),
            credit_card_total=Decimal("0.00"),
            debit_card_total=Decimal("0.00"),
            bank_transfer_total=Decimal("0.00"),
        )

        # cash_sales = (1,500,000 - 500,000) + 200,000 + 100,000 - 0 = 1,300,000
        # expected_final = 500,000 + 1,300,000 = 1,800,000
        # shortage_surplus = 1,500,000 - 1,800,000 = -300,000 (shortage)
        assert session.shortage_surplus == Decimal("-300000.00")
