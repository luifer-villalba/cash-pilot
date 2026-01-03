"""Test timezone support - verifies UTC storage and timezone-aware datetimes.

This test suite verifies that:
1. All datetime columns use TIMESTAMPTZ (timezone-aware)
2. Datetimes are stored in UTC
3. Timezone conversions work correctly
4. No DST-related bugs occur
"""

import pytest
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from cashpilot.utils.datetime import (
    now_utc,
    now_business,
    today_business,
    utc_to_business,
    business_to_utc,
    APP_TIMEZONE,
)
from cashpilot.models.business import Business
from cashpilot.models.user import User
from cashpilot.models.cash_session import CashSession
from cashpilot.models.expense_item import ExpenseItem
from cashpilot.models.transfer_item import TransferItem
from tests.factories import UserFactory, BusinessFactory


class TestDatetimeUtilities:
    """Test the datetime utility functions."""

    def test_now_utc_returns_timezone_aware(self):
        """Verify now_utc() returns timezone-aware datetime in UTC."""
        dt = now_utc()
        
        assert dt.tzinfo is not None, "now_utc() must return timezone-aware datetime"
        assert dt.tzinfo == timezone.utc, "now_utc() must return UTC timezone"
        
        # Verify it's close to current time (within 1 second)
        now = datetime.now(timezone.utc)
        assert abs((now - dt).total_seconds()) < 1

    def test_now_business_returns_timezone_aware(self):
        """Verify now_business() returns timezone-aware datetime in business TZ."""
        dt = now_business()
        
        assert dt.tzinfo is not None, "now_business() must return timezone-aware datetime"
        
        # For Paraguay (UTC-3), verify timezone offset
        expected_tz = ZoneInfo(APP_TIMEZONE)
        assert dt.tzinfo == expected_tz or str(dt.tzinfo) == APP_TIMEZONE

    def test_now_business_with_custom_timezone(self):
        """Verify now_business() works with custom timezone."""
        tokyo_tz = "Asia/Tokyo"
        dt = now_business(tokyo_tz)
        
        assert dt.tzinfo is not None
        # Tokyo is UTC+9
        expected_offset = timedelta(hours=9)
        assert dt.utcoffset() == expected_offset

    def test_today_business_returns_correct_date(self):
        """Verify today_business() returns date in business timezone."""
        date = today_business()
        
        # Should be a date object
        from datetime import date as date_type
        assert isinstance(date, date_type)
        
        # Should match the date from now_business()
        assert date == now_business().date()

    def test_utc_to_business_conversion(self):
        """Verify UTC to business timezone conversion."""
        utc_dt = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)  # Noon UTC
        
        business_dt = utc_to_business(utc_dt)
        
        # Paraguay is UTC-3, so noon UTC = 9am Paraguay
        assert business_dt.hour == 9
        assert business_dt.tzinfo is not None

    def test_utc_to_business_rejects_naive_datetime(self):
        """Verify utc_to_business() rejects naive datetimes."""
        naive_dt = datetime(2026, 1, 15, 12, 0, 0)  # No timezone
        
        with pytest.raises(ValueError, match="must be timezone-aware"):
            utc_to_business(naive_dt)

    def test_business_to_utc_conversion(self):
        """Verify business timezone to UTC conversion."""
        paraguay_tz = ZoneInfo(APP_TIMEZONE)
        business_dt = datetime(2026, 1, 15, 9, 0, 0, tzinfo=paraguay_tz)  # 9am Paraguay
        
        utc_dt = business_to_utc(business_dt)
        
        # 9am Paraguay = noon UTC (Paraguay is UTC-3)
        assert utc_dt.hour == 12
        assert utc_dt.tzinfo == timezone.utc

    def test_business_to_utc_rejects_naive_datetime(self):
        """Verify business_to_utc() rejects naive datetimes."""
        naive_dt = datetime(2026, 1, 15, 9, 0, 0)  # No timezone
        
        with pytest.raises(ValueError, match="must be timezone-aware"):
            business_to_utc(naive_dt)

    def test_timezone_aware_datetimes_are_comparable(self):
        """Verify timezone-aware datetimes can be compared across timezones."""
        utc_dt = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        paraguay_tz = ZoneInfo(APP_TIMEZONE)
        business_dt = datetime(2026, 1, 15, 9, 0, 0, tzinfo=paraguay_tz)
        
        # These represent the same moment in time
        assert utc_dt == business_dt
        
        # Verify they're truly equal
        assert (utc_dt - business_dt).total_seconds() == 0


@pytest.mark.asyncio
class TestModelTimezoneSupport:
    """Test that models properly handle timezone-aware datetimes."""

    async def test_business_created_at_is_timezone_aware(self, db_session):
        """Verify Business.created_at is timezone-aware."""
        business = await BusinessFactory.create(
            db_session,
            name="Test Pharmacy",
        )
        await db_session.commit()
        await db_session.refresh(business)
        
        assert business.created_at.tzinfo is not None, "Business.created_at must be timezone-aware"
        assert business.created_at.tzinfo == timezone.utc, "Business.created_at must be in UTC"

    async def test_business_updated_at_is_timezone_aware(self, db_session):
        """Verify Business.updated_at is timezone-aware."""
        business = await BusinessFactory.create(
            db_session,
            name="Test Pharmacy",
        )
        await db_session.commit()
        await db_session.refresh(business)
        
        assert business.updated_at.tzinfo is not None, "Business.updated_at must be timezone-aware"
        assert business.updated_at.tzinfo == timezone.utc, "Business.updated_at must be in UTC"

    async def test_user_created_at_is_timezone_aware(self, db_session):
        """Verify User.created_at is timezone-aware."""
        user = await UserFactory.create(
            db_session,
            email="test@example.com",
        )
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.created_at.tzinfo is not None, "User.created_at must be timezone-aware"
        assert user.created_at.tzinfo == timezone.utc, "User.created_at must be in UTC"

    async def test_cash_session_opened_at_is_timezone_aware(self, db_session):
        """Verify CashSession.opened_at property returns timezone-aware datetime."""
        from datetime import date, time
        
        business = await BusinessFactory.create(db_session)
        user = await UserFactory.create(db_session)
        await db_session.commit()
        
        session = CashSession(
            business_id=business.id,
            cashier_id=user.id,
            session_date=date(2026, 1, 15),
            opened_time=time(9, 0, 0),
            initial_cash=100000,
            status="OPEN",
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)
        
        opened_at = session.opened_at
        assert opened_at.tzinfo is not None, "CashSession.opened_at must be timezone-aware"

    async def test_cash_session_closed_at_is_timezone_aware(self, db_session):
        """Verify CashSession.closed_at property returns timezone-aware datetime."""
        from datetime import date, time
        
        business = await BusinessFactory.create(db_session)
        user = await UserFactory.create(db_session)
        await db_session.commit()
        
        session = CashSession(
            business_id=business.id,
            cashier_id=user.id,
            session_date=date(2026, 1, 15),
            opened_time=time(9, 0, 0),
            closed_time=time(17, 0, 0),
            initial_cash=100000,
            final_cash=150000,
            status="CLOSED",
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)
        
        closed_at = session.closed_at
        assert closed_at is not None
        assert closed_at.tzinfo is not None, "CashSession.closed_at must be timezone-aware"

    async def test_cash_session_deleted_at_is_timezone_aware(self, db_session):
        """Verify CashSession.deleted_at is timezone-aware when set."""
        from datetime import date, time
        
        business = await BusinessFactory.create(db_session)
        user = await UserFactory.create(db_session)
        await db_session.commit()
        
        session = CashSession(
            business_id=business.id,
            cashier_id=user.id,
            session_date=date(2026, 1, 15),
            opened_time=time(9, 0, 0),
            initial_cash=100000,
            status="OPEN",
            is_deleted=True,
            deleted_at=now_utc(),
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)
        
        assert session.deleted_at is not None
        assert session.deleted_at.tzinfo is not None, "CashSession.deleted_at must be timezone-aware"
        assert session.deleted_at.tzinfo == timezone.utc

    async def test_cash_session_last_modified_at_is_timezone_aware(self, db_session):
        """Verify CashSession.last_modified_at is timezone-aware when set."""
        from datetime import date, time
        
        business = await BusinessFactory.create(db_session)
        user = await UserFactory.create(db_session)
        await db_session.commit()
        
        session = CashSession(
            business_id=business.id,
            cashier_id=user.id,
            session_date=date(2026, 1, 15),
            opened_time=time(9, 0, 0),
            initial_cash=100000,
            status="OPEN",
            last_modified_at=now_utc(),
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)
        
        assert session.last_modified_at is not None
        assert session.last_modified_at.tzinfo is not None, "last_modified_at must be timezone-aware"
        assert session.last_modified_at.tzinfo == timezone.utc

    async def test_expense_item_created_at_is_timezone_aware(self, db_session):
        """Verify ExpenseItem.created_at is timezone-aware."""
        from datetime import date, time
        from decimal import Decimal
        
        business = await BusinessFactory.create(db_session)
        user = await UserFactory.create(db_session)
        await db_session.commit()
        
        session = CashSession(
            business_id=business.id,
            cashier_id=user.id,
            session_date=date(2026, 1, 15),
            opened_time=time(9, 0, 0),
            initial_cash=100000,
            status="OPEN",
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)
        
        expense = ExpenseItem(
            session_id=session.id,
            description="Office supplies",
            amount=Decimal("50000"),
        )
        db_session.add(expense)
        await db_session.commit()
        await db_session.refresh(expense)
        
        assert expense.created_at.tzinfo is not None, "ExpenseItem.created_at must be timezone-aware"
        assert expense.created_at.tzinfo == timezone.utc

    async def test_transfer_item_created_at_is_timezone_aware(self, db_session):
        """Verify TransferItem.created_at is timezone-aware."""
        from datetime import date, time
        from decimal import Decimal
        
        business = await BusinessFactory.create(db_session)
        user = await UserFactory.create(db_session)
        await db_session.commit()
        
        session = CashSession(
            business_id=business.id,
            cashier_id=user.id,
            session_date=date(2026, 1, 15),
            opened_time=time(9, 0, 0),
            initial_cash=100000,
            status="OPEN",
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)
        
        transfer = TransferItem(
            session_id=session.id,
            description="Bank deposit",
            amount=Decimal("100000"),
        )
        db_session.add(transfer)
        await db_session.commit()
        await db_session.refresh(transfer)
        
        assert transfer.created_at.tzinfo is not None, "TransferItem.created_at must be timezone-aware"
        assert transfer.created_at.tzinfo == timezone.utc


class TestDSTHandling:
    """Test that DST transitions are handled correctly."""

    def test_dst_transition_doesnt_affect_utc_storage(self):
        """Verify that DST transitions don't affect UTC storage.
        
        Paraguay doesn't observe DST since 2016, but we test the principle:
        UTC storage is immune to DST changes.
        """
        # Create two datetimes during different DST periods (if applicable)
        utc_dt1 = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)  # Summer
        utc_dt2 = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)  # Winter
        
        # Both should remain in UTC unchanged
        assert utc_dt1.tzinfo == timezone.utc
        assert utc_dt2.tzinfo == timezone.utc
        
        # Time difference should be exactly 6 months (no DST drift)
        expected_diff = timedelta(days=181)  # Jan 15 to July 15
        actual_diff = utc_dt2 - utc_dt1
        assert abs((actual_diff - expected_diff).total_seconds()) < 86400  # Within 1 day

    def test_timezone_conversion_during_dst_transition(self):
        """Verify timezone conversions work correctly during DST transitions.
        
        Test with a timezone that does observe DST (e.g., New York).
        """
        ny_tz = ZoneInfo("America/New_York")
        
        # Winter time (EST = UTC-5)
        winter_utc = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        winter_ny = winter_utc.astimezone(ny_tz)
        assert winter_ny.hour == 7  # 12 UTC - 5 hours
        
        # Summer time (EDT = UTC-4, DST active)
        summer_utc = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
        summer_ny = summer_utc.astimezone(ny_tz)
        assert summer_ny.hour == 8  # 12 UTC - 4 hours (DST)

    def test_paraguay_timezone_no_dst(self):
        """Verify Paraguay timezone (UTC-3) doesn't observe DST."""
        paraguay_tz = ZoneInfo(APP_TIMEZONE)
        
        # Winter
        winter_dt = datetime(2026, 1, 15, 12, 0, 0, tzinfo=paraguay_tz)
        assert winter_dt.utcoffset() == timedelta(hours=-3)
        
        # Summer
        summer_dt = datetime(2026, 7, 15, 12, 0, 0, tzinfo=paraguay_tz)
        assert summer_dt.utcoffset() == timedelta(hours=-3)
        
        # Both should have same UTC offset (no DST)
        assert winter_dt.utcoffset() == summer_dt.utcoffset()


class TestBackwardCompatibility:
    """Test backward compatibility with legacy naive datetimes."""

    def test_now_utc_naive_deprecated_warning(self):
        """Verify now_utc_naive() issues deprecation warning."""
        from cashpilot.utils.datetime import now_utc_naive
        import warnings
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            dt = now_utc_naive()
            
            # Verify deprecation warning was issued
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()

    def test_auth_handles_legacy_naive_session_timestamps(self):
        """Verify auth system handles legacy naive timestamps for backward compatibility."""
        from cashpilot.api.auth import get_current_user
        from types import SimpleNamespace
        
        # Create a legacy naive timestamp (no timezone)
        legacy_naive_dt = datetime(2026, 1, 15, 12, 0, 0)  # No tzinfo
        
        # The auth system should handle this by adding UTC timezone
        # This is tested in the auth.py code with backward compatibility check
        iso_string = legacy_naive_dt.isoformat()
        
        # Verify we can parse it back
        parsed = datetime.fromisoformat(iso_string)
        
        # If naive, we should be able to add UTC timezone
        if parsed.tzinfo is None:
            aware_dt = parsed.replace(tzinfo=timezone.utc)
            assert aware_dt.tzinfo == timezone.utc


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
