"""Payment mix regression tests for dashboard stats (CP-QUICK-01)."""

from decimal import Decimal

from cashpilot.api.routes.dashboard import _calculate_payment_mix


class TestDashboardPaymentMix:
    """Ensure payment mix uses mutually exclusive components."""

    def test_payment_mix_does_not_double_count_bank_transfers(self):
        """AC: denominator should not count bank transfers twice."""
        cash_pct, card_pct, bank_pct = _calculate_payment_mix(
            cash_sales_val=Decimal("300"),  # includes bank transfers
            card_total_val=Decimal("50"),
            bank_val=Decimal("100"),
            credit_sales_val=Decimal("50"),
        )

        assert cash_pct == Decimal("50")
        assert card_pct == Decimal("12.5")
        assert bank_pct == Decimal("25")
        # Remaining 12.5% corresponds to credit sales share.
        assert cash_pct + card_pct + bank_pct == Decimal("87.5")

    def test_payment_mix_returns_zero_when_total_income_is_zero(self):
        """AC: avoid division errors on empty aggregates."""
        cash_pct, card_pct, bank_pct = _calculate_payment_mix(
            cash_sales_val=Decimal("0"),
            card_total_val=Decimal("0"),
            bank_val=Decimal("0"),
            credit_sales_val=Decimal("0"),
        )

        assert cash_pct == Decimal("0")
        assert card_pct == Decimal("0")
        assert bank_pct == Decimal("0")

    def test_payment_mix_clamps_negative_cash_component(self):
        """Legacy inconsistent data should not produce negative percentages."""
        cash_pct, card_pct, bank_pct = _calculate_payment_mix(
            cash_sales_val=Decimal("80"),
            card_total_val=Decimal("20"),
            bank_val=Decimal("100"),
            credit_sales_val=Decimal("0"),
        )

        assert cash_pct == Decimal("0")
        assert card_pct == Decimal("16.7")
        assert bank_pct == Decimal("83.3")
