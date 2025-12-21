# File: tests/test_validators.py
"""Tests for core validation utilities."""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from cashpilot.utils.datetime import today_local

from cashpilot.core.validators import (
    validate_currency,
    validate_alphanumeric_with_spaces,
    validate_phone,
    validate_no_future_date,
    sanitize_html,
    validate_email,
)


class TestValidateCurrency:
    """Test currency validation."""

    def test_negative_currency_fails(self):
        """Test negative values are rejected."""
        with pytest.raises(ValueError, match="cannot be negative"):
            validate_currency(Decimal("-10.00"))

    def test_exceeds_max_fails(self):
        """Test values exceeding max are rejected."""
        with pytest.raises(ValueError, match="exceeds maximum"):
            validate_currency(Decimal("1000000000.00"))

    def test_invalid_format_fails(self):
        """Test invalid format is rejected."""
        with pytest.raises(ValueError, match="Invalid currency format"):
            validate_currency("invalid")


class TestValidateAlphanumericWithSpaces:
    """Test alphanumeric with spaces validation."""

    def test_valid_text(self):
        """Test valid text passes."""
        assert validate_alphanumeric_with_spaces("John Doe") == "John Doe"
        assert validate_alphanumeric_with_spaces("María García") == "María García"
        assert validate_alphanumeric_with_spaces("Store 123") == "Store 123"

    def test_strips_whitespace(self):
        """Test leading/trailing whitespace is stripped."""
        assert validate_alphanumeric_with_spaces("  John  ") == "John"

    def test_empty_fails(self):
        """Test empty string fails."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_alphanumeric_with_spaces("")

        with pytest.raises(ValueError, match="cannot be empty"):
            validate_alphanumeric_with_spaces("   ")

    def test_min_length_enforced(self):
        """Test minimum length is enforced."""
        with pytest.raises(ValueError, match="must be at least 5 characters"):
            validate_alphanumeric_with_spaces("John", min_length=5)

    def test_max_length_enforced(self):
        """Test maximum length is enforced."""
        with pytest.raises(ValueError, match="cannot exceed 10 characters"):
            validate_alphanumeric_with_spaces("This is too long", max_length=10)

    def test_special_chars_fail_by_default(self):
        """Test special characters are rejected by default."""
        with pytest.raises(ValueError, match="can only contain"):
            validate_alphanumeric_with_spaces("John@Doe")

        with pytest.raises(ValueError, match="can only contain"):
            validate_alphanumeric_with_spaces("Test<script>")

    def test_punctuation_allowed_when_enabled(self):
        """Test basic punctuation is allowed when enabled."""
        result = validate_alphanumeric_with_spaces(
            "Store 1, Main St.",
            allow_punctuation=True
        )
        assert result == "Store 1, Main St."

    def test_xss_patterns_fail(self):
        """Test XSS patterns are rejected."""
        with pytest.raises(ValueError):
            validate_alphanumeric_with_spaces("<script>alert('xss')</script>")

        with pytest.raises(ValueError):
            validate_alphanumeric_with_spaces("John&Doe")


class TestValidatePhone:
    """Test phone validation."""

    def test_valid_phone(self):
        """Test valid phone formats."""
        assert validate_phone("+595 21 123456") == "+595 21 123456"
        assert validate_phone("123-456-7890") == "123-456-7890"
        assert validate_phone("(021) 123456") == "(021) 123456"

    def test_empty_returns_none(self):
        """Test empty/None returns None."""
        assert validate_phone(None) is None
        assert validate_phone("") is None
        assert validate_phone("   ") is None

    def test_minimum_digits_required(self):
        """Test at least 5 digits required."""
        with pytest.raises(ValueError, match="must contain at least 5 digits"):
            validate_phone("123")

    def test_invalid_chars_fail(self):
        """Test invalid characters are rejected."""
        with pytest.raises(ValueError, match="can only contain"):
            validate_phone("123-abc-4567")

        with pytest.raises(ValueError, match="can only contain"):
            validate_phone("phone@example")


class TestValidateNoFutureDate:
    """Test future date validation."""

    def test_today_passes(self):
        """Test today's date passes."""
        today = today_local()
        assert validate_no_future_date(today) == today

    def test_past_date_passes(self):
        """Test past date passes."""
        yesterday = today_local() - timedelta(days=1)
        assert validate_no_future_date(yesterday) == yesterday

    def test_future_date_fails(self):
        """Test future date is rejected."""
        tomorrow = today_local() + timedelta(days=1)
        with pytest.raises(ValueError, match="cannot be in the future"):
            validate_no_future_date(tomorrow)

    def test_custom_field_name(self):
        """Test custom field name in error message."""
        tomorrow = today_local() + timedelta(days=1)
        with pytest.raises(ValueError, match="Session date cannot be in the future"):
            validate_no_future_date(tomorrow, field_name="Session date")


class TestSanitizeHtml:
    """Test HTML sanitization."""

    def test_strips_html_tags(self):
        """Test HTML tags are removed."""
        assert sanitize_html("<p>Hello</p>") == "Hello"
        # Single quotes are also escaped
        assert sanitize_html("<script>alert('xss')</script>") == "alert(&#x27;xss&#x27;)"
        assert sanitize_html("<div>Test<br/>content</div>") == "Testcontent"

    def test_escapes_special_chars(self):
        """Test special characters are escaped."""
        assert sanitize_html("A & B") == "A &amp; B"
        assert sanitize_html("A < B") == "A &lt; B"
        assert sanitize_html("A > B") == "A &gt; B"
        assert sanitize_html('Say "hello"') == "Say &quot;hello&quot;"

    def test_empty_returns_none(self):
        """Test empty input returns None."""
        assert sanitize_html(None) is None
        assert sanitize_html("") is None
        assert sanitize_html("   ") is None

    def test_complex_xss_attack(self):
        """Test complex XSS attempts are neutralized."""
        malicious = '<img src="x" onerror="alert(\'XSS\')">'
        result = sanitize_html(malicious)
        # Pure HTML with no text content returns None (correct behavior)
        assert result is None

        # Test with actual text content mixed with XSS
        malicious_with_text = 'Hello <img src="x" onerror="alert(\'XSS\')"> World'
        result = sanitize_html(malicious_with_text)
        assert result is not None
        assert "Hello" in result
        assert "World" in result
        assert "<img" not in result
        assert "onerror" not in result


class TestValidateEmail:
    """Test email validation."""

    def test_valid_email(self):
        """Test valid email formats."""
        assert validate_email("user@example.com") == "user@example.com"
        assert validate_email("USER@EXAMPLE.COM") == "user@example.com"  # Lowercase
        assert validate_email("test.user+tag@domain.co.uk") == "test.user+tag@domain.co.uk"

    def test_invalid_format_fails(self):
        """Test invalid email formats are rejected."""
        with pytest.raises(ValueError, match="Invalid email format"):
            validate_email("invalid")

        with pytest.raises(ValueError, match="Invalid email format"):
            validate_email("@example.com")

        with pytest.raises(ValueError, match="Invalid email format"):
            validate_email("user@")

        with pytest.raises(ValueError, match="Invalid email format"):
            validate_email("user @example.com")
