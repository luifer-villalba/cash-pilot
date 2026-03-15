"""Tests for currency parsing used by form handlers."""

from decimal import Decimal

from cashpilot.api.utils import parse_currency


class TestParseCurrency:
    """Validate supported separator combinations and edge cases."""

    def test_parses_paraguay_grouped_decimal_comma(self):
        """AC: CP-QUICK-03 - parse 1.234,56 format correctly."""
        assert parse_currency("1.234,56") == Decimal("1234.56")

    def test_parses_decimal_comma_without_grouping(self):
        """AC: CP-QUICK-03 - parse 1234,56 format correctly."""
        assert parse_currency("1234,56") == Decimal("1234.56")

    def test_parses_large_grouped_decimal_comma(self):
        """AC: CP-QUICK-03 - parse 1.234.567,89 format correctly."""
        assert parse_currency("1.234.567,89") == Decimal("1234567.89")

    def test_parses_small_decimal_comma(self):
        """AC: CP-QUICK-03 - parse 1,50 format correctly."""
        assert parse_currency("1,50") == Decimal("1.50")

    def test_parses_decimal_dot(self):
        """AC: CP-QUICK-03 - keep dot-decimal compatibility."""
        assert parse_currency("1500.75") == Decimal("1500.75")

    def test_parses_grouped_integer_dot(self):
        """AC: CP-QUICK-03 - keep Guarani grouped integers."""
        assert parse_currency("1.500.000") == Decimal("1500000")

    def test_rejects_malformed_separators(self):
        """Malformed mixed separators should not parse silently."""
        assert parse_currency("1,234,56") is None
        assert parse_currency("1.23.45") is None

    def test_rejects_non_numeric_values(self):
        """Non-numeric strings must return None."""
        assert parse_currency("abc") is None
        assert parse_currency("") is None
        assert parse_currency("   ") is None
        assert parse_currency(None) is None
