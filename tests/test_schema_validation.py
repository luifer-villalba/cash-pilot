# File: tests/test_schema_validation.py
"""Tests for Pydantic schema validation."""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from pydantic import ValidationError

from cashpilot.models.user_schemas import UserCreate
from cashpilot.models.business_schemas import BusinessCreate, BusinessUpdate
from cashpilot.models.cash_session_schemas import CashSessionCreate
from uuid import uuid4


class TestUserCreateValidation:
    """Test UserCreate schema validation."""

    def test_valid_user_create(self):
        """Test valid user creation."""
        user = UserCreate(
            email="test@example.com",
            password="SecurePass123",
            first_name="John",
            last_name="Doe",
        )
        assert user.email == "test@example.com"
        assert user.first_name == "John"

    def test_email_normalized_lowercase(self):
        """Test email is converted to lowercase."""
        user = UserCreate(
            email="TEST@EXAMPLE.COM",
            password="SecurePass123",
            first_name="John",
            last_name="Doe",
        )
        assert user.email == "test@example.com"

    def test_invalid_email_fails(self):
        """Test invalid email format is rejected."""
        with pytest.raises(ValidationError) as exc:
            UserCreate(
                email="invalid-email",
                password="SecurePass123",
                first_name="John",
                last_name="Doe",
            )
        assert "Invalid email format" in str(exc.value)

    def test_weak_password_fails(self):
        """Test weak password is rejected."""
        # Too short
        with pytest.raises(ValidationError) as exc:
            UserCreate(
                email="test@example.com",
                password="short",
                first_name="John",
                last_name="Doe",
            )
        assert "at least 8 characters" in str(exc.value)

        # No letter
        with pytest.raises(ValidationError) as exc:
            UserCreate(
                email="test@example.com",
                password="12345678",
                first_name="John",
                last_name="Doe",
            )
        assert "at least one letter" in str(exc.value)

        # No number
        with pytest.raises(ValidationError) as exc:
            UserCreate(
                email="test@example.com",
                password="OnlyLetters",
                first_name="John",
                last_name="Doe",
            )
        assert "at least one number" in str(exc.value)

    def test_invalid_name_characters(self):
        """Test names with invalid characters are rejected."""
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                password="SecurePass123",
                first_name="John123",
                last_name="Doe",
            )


class TestBusinessCreateValidation:
    """Test BusinessCreate schema validation."""

    def test_valid_business_create(self):
        """Test valid business creation."""
        business = BusinessCreate(
            name="Farmacia Central",
            address="Av. España 123",
            phone="+595 21 123456",
            cashiers=["María García", "Juan Pérez"],
        )
        assert business.name == "Farmacia Central"
        assert len(business.cashiers) == 2

    def test_name_sanitized(self):
        """Test business name is validated and trimmed."""
        business = BusinessCreate(
            name="  Farmacia Test  ",
        )
        assert business.name == "Farmacia Test"

    def test_invalid_name_fails(self):
        """Test invalid business name is rejected."""
        with pytest.raises(ValidationError):
            BusinessCreate(name="Test<script>alert('xss')</script>")

    def test_address_sanitized_for_xss(self):
        """Test address is sanitized to prevent XSS."""
        business = BusinessCreate(
            name="Test",
            address="<script>alert('xss')</script>123 Main St",
        )
        assert "<script>" not in business.address

    def test_phone_validated(self):
        """Test phone validation."""
        business = BusinessCreate(
            name="Test",
            phone="+595 21 123456",
        )
        assert business.phone == "+595 21 123456"

        with pytest.raises(ValidationError):
            BusinessCreate(
                name="Test",
                phone="abc",
            )

    def test_cashier_names_validated(self):
        """Test cashier names are validated."""
        business = BusinessCreate(
            name="Test",
            cashiers=["  María  ", "Juan"],
        )
        assert business.cashiers == ["María", "Juan"]

        with pytest.raises(ValidationError):
            BusinessCreate(
                name="Test",
                cashiers=["Valid Name", "A"],
            )


class TestCashSessionCreateValidation:
    """Test CashSessionCreate schema validation."""

    def test_valid_session_create(self):
        """Test valid session creation."""
        session = CashSessionCreate(
            business_id=uuid4(),
            initial_cash=Decimal("500000.00"),
        )
        assert session.initial_cash == Decimal("500000.00")

    def test_future_date_rejected(self):
        """Test future session date is rejected."""
        tomorrow = date.today() + timedelta(days=1)

        with pytest.raises(ValidationError) as exc:
            CashSessionCreate(
                business_id=uuid4(),
                initial_cash=Decimal("100.00"),
                session_date=tomorrow,
            )
        assert "cannot be in the future" in str(exc.value)

    def test_today_and_past_dates_accepted(self):
        """Test today and past dates are accepted."""
        session = CashSessionCreate(
            business_id=uuid4(),
            initial_cash=Decimal("100.00"),
            session_date=date.today(),
        )
        assert session.session_date == date.today()

        yesterday = date.today() - timedelta(days=1)
        session = CashSessionCreate(
            business_id=uuid4(),
            initial_cash=Decimal("100.00"),
            session_date=yesterday,
        )
        assert session.session_date == yesterday
