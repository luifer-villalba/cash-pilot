# File: tests/test_numeric_overflow_prevention.py
"""Tests for numeric overflow prevention in cash session operations."""

import pytest
from decimal import Decimal
from cashpilot.core.validators import validate_currency


class TestNumericOverflowPrevention:
    """Test that currency validation prevents database numeric overflow."""

    def test_max_allowed_value_succeeds(self):
        """Test that the maximum allowed value passes validation."""
        max_value = Decimal("9999999999.99")
        result = validate_currency(max_value)
        assert result == max_value

    def test_value_exceeding_max_fails(self):
        """Test that values exceeding NUMERIC(12,2) limit are rejected."""
        # The error that was happening: trying to store 123123213123
        overflow_value = Decimal("123123213123")
        with pytest.raises(ValueError, match="exceeds maximum"):
            validate_currency(overflow_value)

    def test_slightly_over_max_fails(self):
        """Test that values just over the limit fail."""
        over_max = Decimal("10000000000.00")
        with pytest.raises(ValueError, match="exceeds maximum"):
            validate_currency(over_max)

    def test_values_at_boundary_succeed(self):
        """Test boundary values."""
        # Just under the max
        just_under = Decimal("9999999999.98")
        assert validate_currency(just_under) == just_under
        
        # At the max
        at_max = Decimal("9999999999.99")
        assert validate_currency(at_max) == at_max

    def test_custom_max_value_respected(self):
        """Test that custom max_value parameter is respected."""
        custom_max = Decimal("1000.00")
        
        # Should pass
        valid_value = Decimal("999.99")
        assert validate_currency(valid_value, max_value=custom_max) == valid_value
        
        # Should fail
        invalid_value = Decimal("1000.01")
        with pytest.raises(ValueError, match="exceeds maximum"):
            validate_currency(invalid_value, max_value=custom_max)
