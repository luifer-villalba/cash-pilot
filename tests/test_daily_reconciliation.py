# File: tests/test_daily_reconciliation.py
"""Tests for daily reconciliation endpoints."""

import pytest
from decimal import Decimal
from datetime import date
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models.daily_reconciliation import DailyReconciliation
from cashpilot.models.daily_reconciliation_audit_log import DailyReconciliationAuditLog
from tests.factories import BusinessFactory, DailyReconciliationFactory, CashSessionFactory


class TestDailyReconciliationAdminAccess:
    """Test admin-only access to daily reconciliation endpoints."""

    @pytest.mark.asyncio
    async def test_get_form_requires_admin(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test non-admin users cannot access the form."""
        response = await client.get("/reconciliation/daily", follow_redirects=False)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_form_allows_admin(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test admin users can access the form."""
        response = await admin_client.get("/reconciliation/daily")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_post_requires_admin(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test non-admin users cannot POST to create reconciliation."""
        response = await client.post(
            "/reconciliation/daily",
            data={"date": "2024-01-01"},
            follow_redirects=False,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_api_requires_admin(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test non-admin users cannot access GET API endpoint."""
        response = await client.get("/reconciliation/daily/", follow_redirects=False)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_put_requires_admin(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test non-admin users cannot PUT to update reconciliation."""
        business = await BusinessFactory.create(db_session)
        reconciliation = await DailyReconciliationFactory.create(
            db_session, business_id=business.id
        )

        response = await client.put(
            f"/reconciliation/daily/{reconciliation.id}",
            data={"reason": "Test reason"},  # type: ignore[arg-type]
            follow_redirects=False,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_requires_admin(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test non-admin users cannot DELETE reconciliation."""
        business = await BusinessFactory.create(db_session)
        reconciliation = await DailyReconciliationFactory.create(
            db_session, business_id=business.id
        )

        response = await client.request(
            "DELETE",
            f"/reconciliation/daily/{reconciliation.id}",
            data={"reason": "Test reason"},
            follow_redirects=False,
        )
        assert response.status_code == 403


class TestDailyReconciliationSchemaValidation:
    """Test schema validation for daily reconciliation."""

    @pytest.mark.asyncio
    async def test_post_validates_date_not_future(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test POST rejects future dates."""
        from datetime import timedelta

        future_date = (date.today() + timedelta(days=1)).isoformat()
        response = await admin_client.post(
            "/reconciliation/daily",
            data={"date": future_date},
            follow_redirects=False,
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_post_validates_date_format(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test POST rejects invalid date format."""
        response = await admin_client.post(
            "/reconciliation/daily",
            data={"date": "invalid-date"},
            follow_redirects=False,
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_put_requires_reason_min_length(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test PUT requires reason with minimum length."""
        business = await BusinessFactory.create(db_session)
        reconciliation = await DailyReconciliationFactory.create(
            db_session, business_id=business.id
        )

        response = await admin_client.put(
            f"/reconciliation/daily/{reconciliation.id}",
            data={"reason": "abc"},  # type: ignore[arg-type]  # Too short
            follow_redirects=False,
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_delete_requires_reason_min_length(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test DELETE requires reason with minimum length."""
        business = await BusinessFactory.create(db_session)
        reconciliation = await DailyReconciliationFactory.create(
            db_session, business_id=business.id
        )

        response = await admin_client.request(
            "DELETE",
            f"/reconciliation/daily/{reconciliation.id}",
            data={"reason": "abc"},  # Too short
            follow_redirects=False,
        )
        assert response.status_code == 422  # Validation error


class TestDailyReconciliationSoftDelete:
    """Test soft delete functionality."""

    @pytest.mark.asyncio
    async def test_delete_sets_deleted_at(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test DELETE sets deleted_at timestamp."""
        business = await BusinessFactory.create(db_session)
        reconciliation = await DailyReconciliationFactory.create(
            db_session, business_id=business.id
        )

        response = await admin_client.request(
            "DELETE",
            f"/reconciliation/daily/{reconciliation.id}",
            data={"reason": "Test deletion reason"},
            follow_redirects=False,
        )
        assert response.status_code == 204

        await db_session.refresh(reconciliation)
        assert reconciliation.deleted_at is not None
        assert reconciliation.deleted_by is not None

    @pytest.mark.asyncio
    async def test_delete_creates_audit_log(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test DELETE creates audit log entry."""
        business = await BusinessFactory.create(db_session)
        reconciliation = await DailyReconciliationFactory.create(
            db_session,
            business_id=business.id,
            cash_sales=Decimal("1000000.00"),
            credit_sales=Decimal("500000.00"),
        )

        response = await admin_client.request(
            "DELETE",
            f"/reconciliation/daily/{reconciliation.id}",
            data={"reason": "Test deletion reason"},
            follow_redirects=False,
        )
        assert response.status_code == 204

        # Check audit log was created
        stmt = select(DailyReconciliationAuditLog).where(
            DailyReconciliationAuditLog.reconciliation_id == reconciliation.id,
            DailyReconciliationAuditLog.action == "DELETE",
        )
        result = await db_session.execute(stmt)
        audit_log = result.scalar_one_or_none()

        assert audit_log is not None
        assert audit_log.reason == "Test deletion reason"
        assert audit_log.action == "DELETE"

    @pytest.mark.asyncio
    async def test_deleted_reconciliation_not_in_get(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test deleted reconciliations are excluded from GET results."""
        business = await BusinessFactory.create(db_session)
        reconciliation = await DailyReconciliationFactory.create(
            db_session, business_id=business.id
        )

        # Delete it
        await admin_client.request(
            "DELETE",
            f"/reconciliation/daily/{reconciliation.id}",
            data={"reason": "Test deletion"},
        )

        # Get all reconciliations
        response = await admin_client.get("/reconciliation/daily/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0 or str(reconciliation.id) not in [r["id"] for r in data]

    @pytest.mark.asyncio
    async def test_cannot_delete_already_deleted(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test cannot delete an already deleted reconciliation."""
        from cashpilot.utils.datetime import now_utc

        business = await BusinessFactory.create(db_session)
        reconciliation = await DailyReconciliationFactory.create(
            db_session, business_id=business.id
        )

        # Manually soft delete it
        reconciliation.deleted_at = now_utc()
        reconciliation.deleted_by = "Test User"
        await db_session.commit()

        # Try to delete again
        response = await admin_client.request(
            "DELETE",
            f"/reconciliation/daily/{reconciliation.id}",
            data={"reason": "Test deletion"},
            follow_redirects=False,
        )
        assert response.status_code == 404


class TestDailyReconciliationIsClosed:
    """Test is_closed flag functionality."""

    @pytest.mark.asyncio
    async def test_is_closed_allows_null_sales_fields(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test when is_closed=true, sales fields can be null."""
        from cashpilot.utils.datetime import today_local

        business = await BusinessFactory.create(db_session)
        business_id = business.id  # Capture ID before async operations
        today = today_local()
        today_str = today.isoformat()

        response = await admin_client.post(
            "/reconciliation/daily",
            data={
                "date": today_str,
                f"is_closed_{business_id}": "on",  # Checkbox checked
            },
            follow_redirects=False,
        )
        assert response.status_code == 302  # Redirect to comparison dashboard

        # Verify reconciliation was created with is_closed=True
        stmt = select(DailyReconciliation).where(
            DailyReconciliation.business_id == business_id,
            DailyReconciliation.date == today,
            DailyReconciliation.deleted_at.is_(None),
        )
        result = await db_session.execute(stmt)
        reconciliation = result.scalar_one_or_none()

        assert reconciliation is not None
        assert reconciliation.is_closed is True
        assert reconciliation.cash_sales is None
        assert reconciliation.card_sales is None

    @pytest.mark.asyncio
    async def test_is_closed_false_requires_sales_data(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test when is_closed=false, sales data is required."""
        from cashpilot.utils.datetime import today_local

        business = await BusinessFactory.create(db_session)
        business_id = business.id  # Capture ID before async operations
        today = today_local()
        today_str = today.isoformat()

        # Create without is_closed (defaults to False) and no sales data
        response = await admin_client.post(
            "/reconciliation/daily",
            data={
                "date": today_str,
                # No is_closed checkbox, no sales data
            },
            follow_redirects=False,
        )
        assert response.status_code == 400  # Should fail validation

        # Verify reconciliation was NOT created due to validation error
        stmt = select(DailyReconciliation).where(
            DailyReconciliation.business_id == business_id,
            DailyReconciliation.date == today,
            DailyReconciliation.deleted_at.is_(None),
        )
        result = await db_session.execute(stmt)
        reconciliation = result.scalar_one_or_none()

        assert reconciliation is None  # Should not be created

    @pytest.mark.asyncio
    async def test_update_is_closed_flag(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test updating is_closed flag via PUT."""
        business = await BusinessFactory.create(db_session)
        reconciliation = await DailyReconciliationFactory.create(
            db_session,
            business_id=business.id,
            is_closed=False,
            cash_sales=Decimal("1000000.00"),
        )

        response = await admin_client.put(
            f"/reconciliation/daily/{reconciliation.id}",
            data={
                "is_closed": "true",
                "reason": "Location was closed that day",
            },
            follow_redirects=False,
        )
        assert response.status_code == 200

        await db_session.refresh(reconciliation)
        assert reconciliation.is_closed is True

    @pytest.mark.asyncio
    async def test_update_is_closed_preserves_sales_data(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test that updating is_closed=True via POST preserves existing sales data."""
        from cashpilot.utils.datetime import today_local

        business = await BusinessFactory.create(db_session)
        business_id = business.id
        today = today_local()
        today_str = today.isoformat()

        # Create reconciliation with sales data
        reconciliation = await DailyReconciliationFactory.create(
            db_session,
            business_id=business_id,
            is_closed=False,
            cash_sales=Decimal("1000000.00"),
            credit_sales=Decimal("500000.00"),
            card_sales=Decimal("200000.00"),
            total_sales=Decimal("1700000.00"),
        )

        # Update via POST with is_closed=True (no sales fields in form)
        response = await admin_client.post(
            "/reconciliation/daily",
            data={
                "date": today_str,
                f"is_closed_{business_id}": "on",  # Checkbox checked
                # No sales fields provided
            },
            follow_redirects=False,
        )
        assert response.status_code == 302  # Should succeed

        # Verify sales data is preserved
        await db_session.refresh(reconciliation)
        assert reconciliation.is_closed is True
        assert reconciliation.cash_sales == Decimal("1000000.00")
        assert reconciliation.credit_sales == Decimal("500000.00")
        assert reconciliation.card_sales == Decimal("200000.00")
        assert reconciliation.total_sales == Decimal("1700000.00")


class TestDailyReconciliationEditAuditTrail:
    """Test audit trail for edits."""

    @pytest.mark.asyncio
    async def test_edit_creates_audit_log(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test editing creates audit log entry."""
        business = await BusinessFactory.create(db_session)
        reconciliation = await DailyReconciliationFactory.create(
            db_session,
            business_id=business.id,
            cash_sales=Decimal("1000000.00"),
        )

        response = await admin_client.put(
            f"/reconciliation/daily/{reconciliation.id}",
            data={
                "cash_sales": "1500000.00",
                "reason": "Corrected cash sales amount",
            },
            follow_redirects=False,
        )
        assert response.status_code == 200

        # Check audit log was created
        stmt = select(DailyReconciliationAuditLog).where(
            DailyReconciliationAuditLog.reconciliation_id == reconciliation.id,
            DailyReconciliationAuditLog.action == "EDIT",
        )
        result = await db_session.execute(stmt)
        audit_log = result.scalar_one_or_none()

        assert audit_log is not None
        assert audit_log.reason == "Corrected cash sales amount"
        assert audit_log.action == "EDIT"
        assert "cash_sales" in audit_log.changed_fields

    @pytest.mark.asyncio
    async def test_edit_tracks_old_and_new_values(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test audit log tracks old and new values."""
        business = await BusinessFactory.create(db_session)
        reconciliation = await DailyReconciliationFactory.create(
            db_session,
            business_id=business.id,
            cash_sales=Decimal("1000000.00"),
        )

        response = await admin_client.put(
            f"/reconciliation/daily/{reconciliation.id}",
            data={
                "cash_sales": "2000000.00",
                "reason": "Updated cash sales",
            },
            follow_redirects=False,
        )
        assert response.status_code == 200

        # Check audit log
        stmt = select(DailyReconciliationAuditLog).where(
            DailyReconciliationAuditLog.reconciliation_id == reconciliation.id
        )
        result = await db_session.execute(stmt)
        audit_log = result.scalar_one_or_none()

        assert audit_log is not None
        assert audit_log.old_values.get("cash_sales") == "1000000.00"
        assert audit_log.new_values.get("cash_sales") == "2000000.00"

    @pytest.mark.asyncio
    async def test_no_audit_log_if_no_changes(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test no audit log created if no fields actually changed."""
        business = await BusinessFactory.create(db_session)
        reconciliation = await DailyReconciliationFactory.create(
            db_session,
            business_id=business.id,
            cash_sales=Decimal("1000000.00"),
        )

        # Update with same value
        response = await admin_client.put(
            f"/reconciliation/daily/{reconciliation.id}",
            data={
                "cash_sales": "1000000.00",  # Same value
                "reason": "No changes made",
            },
            follow_redirects=False,
        )
        assert response.status_code == 200

        # Check no audit log was created (or it was skipped)
        stmt = select(DailyReconciliationAuditLog).where(
            DailyReconciliationAuditLog.reconciliation_id == reconciliation.id
        )
        result = await db_session.execute(stmt)
        audit_logs = result.scalars().all()

        # Should have no audit logs (or the function should skip creating one)
        # The implementation skips if no fields changed, so this is expected
        assert len(audit_logs) == 0


class TestDailyReconciliationGetAPI:
    """Test GET API endpoint."""

    @pytest.mark.asyncio
    async def test_get_all_reconciliations(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test GET returns all reconciliations."""
        business1 = await BusinessFactory.create(db_session, name="Business 1")
        business2 = await BusinessFactory.create(db_session, name="Business 2")

        await DailyReconciliationFactory.create(
            db_session, business_id=business1.id, date=date.today()
        )
        await DailyReconciliationFactory.create(
            db_session, business_id=business2.id, date=date.today()
        )

        response = await admin_client.get("/reconciliation/daily/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

    @pytest.mark.asyncio
    async def test_get_filter_by_business_id(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test GET filters by business_id."""
        business1 = await BusinessFactory.create(db_session)
        business2 = await BusinessFactory.create(db_session)

        await DailyReconciliationFactory.create(
            db_session, business_id=business1.id
        )
        await DailyReconciliationFactory.create(db_session, business_id=business2.id)

        response = await admin_client.get(
            f"/reconciliation/daily/?business_id={business1.id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["business_id"] == str(business1.id)

    @pytest.mark.asyncio
    async def test_get_filter_by_date(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test GET filters by date."""
        from datetime import timedelta

        business = await BusinessFactory.create(db_session)
        today = date.today()
        yesterday = today - timedelta(days=1)

        await DailyReconciliationFactory.create(
            db_session, business_id=business.id, date=today
        )
        await DailyReconciliationFactory.create(
            db_session, business_id=business.id, date=yesterday
        )

        response = await admin_client.get(f"/reconciliation/daily/?date={today.isoformat()}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["date"] == today.isoformat()


class TestReconciliationCompare:
    """Test reconciliation comparison endpoint with variance calculation."""

    @pytest.mark.asyncio
    async def test_compare_variance_calculation(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test variance calculation is correct."""
        from datetime import date

        business = await BusinessFactory.create(db_session)
        today = date.today()

        # Create manual entry
        await DailyReconciliationFactory.create(
            db_session,
            business_id=business.id,
            date=today,
            total_sales=Decimal("1000.00"),
        )

        # Create cash session with calculated total = 1050.00
        # Cash: (1200 - 200) + 0 + 0 - 0 + 0 = 1000
        # Card: 50
        # Total: 1050
        await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            session_date=today,
            status="CLOSED",
            initial_cash=Decimal("200.00"),
            final_cash=Decimal("1200.00"),
            credit_card_total=Decimal("50.00"),
            debit_card_total=Decimal("0.00"),
        )

        response = await admin_client.get(f"/reconciliation/compare/?date={today.isoformat()}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        item = data[0]
        assert item["business_id"] == str(business.id)
        assert item["manual_entry"]["total_sales"] == 1000.0
        assert item["calculated"]["total_sales"] == 1050.0
        assert item["variance"]["total_sales"]["difference"] == -50.0
        # Variance: ((1000 - 1050) / 1050) * 100 = -4.76%
        assert abs(item["variance"]["total_sales"]["variance_percent"] - (-4.76)) < 0.1
        assert item["status"] == "Needs Review"  # > 2% threshold

    @pytest.mark.asyncio
    async def test_compare_multiple_sessions_same_day(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test that multiple sessions on same day are summed correctly."""
        from datetime import date

        business = await BusinessFactory.create(db_session)
        today = date.today()

        # Create manual entry
        await DailyReconciliationFactory.create(
            db_session,
            business_id=business.id,
            date=today,
            total_sales=Decimal("3000.00"),
        )

        # Session 1: Cash 1000, Card 500 = 1500 total
        await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            session_date=today,
            status="CLOSED",
            initial_cash=Decimal("500.00"),
            final_cash=Decimal("1500.00"),  # Cash sales = 1000
            credit_card_total=Decimal("500.00"),
            debit_card_total=Decimal("0.00"),
        )

        # Session 2: Cash 800, Card 700 = 1500 total
        await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            session_date=today,
            status="CLOSED",
            initial_cash=Decimal("200.00"),
            final_cash=Decimal("1000.00"),  # Cash sales = 800
            credit_card_total=Decimal("700.00"),
            debit_card_total=Decimal("0.00"),
        )

        response = await admin_client.get(f"/reconciliation/compare/?date={today.isoformat()}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        item = data[0]
        # Total calculated: (1000 + 500) + (800 + 700) = 3000
        assert item["calculated"]["total_sales"] == 3000.0
        assert item["calculated"]["session_count"] == 2
        assert item["variance"]["total_sales"]["difference"] == 0.0
        assert item["variance"]["total_sales"]["variance_percent"] == 0.0
        assert item["status"] == "Match"

    @pytest.mark.asyncio
    async def test_compare_edge_case_zero_sales(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test edge case with 0 sales."""
        from datetime import date

        business = await BusinessFactory.create(db_session)
        today = date.today()

        # Create manual entry with 0 sales
        await DailyReconciliationFactory.create(
            db_session,
            business_id=business.id,
            date=today,
            total_sales=Decimal("0.00"),
        )

        # Create cash session with 0 sales
        await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            session_date=today,
            status="CLOSED",
            initial_cash=Decimal("500.00"),
            final_cash=Decimal("500.00"),  # No cash sales
            credit_card_total=Decimal("0.00"),
            debit_card_total=Decimal("0.00"),
        )

        response = await admin_client.get(f"/reconciliation/compare/?date={today.isoformat()}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        item = data[0]
        assert item["calculated"]["total_sales"] == 0.0
        assert item["variance"]["total_sales"]["difference"] == 0.0
        # When calculated is 0, variance_percent should be None
        assert item["variance"]["total_sales"]["variance_percent"] is None
        assert item["status"] == "Match"

    @pytest.mark.asyncio
    async def test_compare_no_manual_entry(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test comparison when no manual entry exists."""
        from datetime import date

        business = await BusinessFactory.create(db_session)
        today = date.today()

        # Create cash session but no manual entry
        await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            session_date=today,
            status="CLOSED",
            initial_cash=Decimal("500.00"),
            final_cash=Decimal("1500.00"),
            credit_card_total=Decimal("200.00"),
        )

        response = await admin_client.get(f"/reconciliation/compare/?date={today.isoformat()}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        item = data[0]
        assert item["manual_entry"]["total_sales"] is None
        assert item["calculated"]["total_sales"] == 1200.0  # 1000 cash + 200 card
        assert item["variance"]["total_sales"]["difference"] is None
        assert item["variance"]["total_sales"]["variance_percent"] is None
        assert item["status"] == "Match"

    @pytest.mark.asyncio
    async def test_compare_variance_threshold_match(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test that variance <= 2% shows as Match."""
        from datetime import date

        business = await BusinessFactory.create(db_session)
        today = date.today()

        # Manual: 1000, Calculated: 1015 (1.5% variance)
        await DailyReconciliationFactory.create(
            db_session,
            business_id=business.id,
            date=today,
            total_sales=Decimal("1000.00"),
        )

        # Calculated total should be ~1015 (1.5% difference)
        # Cash: (1215 - 200) = 1015
        await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            session_date=today,
            status="CLOSED",
            initial_cash=Decimal("200.00"),
            final_cash=Decimal("1215.00"),  # Cash sales = 1015
            credit_card_total=Decimal("0.00"),
        )

        response = await admin_client.get(f"/reconciliation/compare/?date={today.isoformat()}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        item = data[0]
        variance_pct = item["variance"]["total_sales"]["variance_percent"]
        # Manual (1000) < Calculated (1015), so variance is negative: -1.48%
        assert abs(variance_pct - (-1.48)) < 0.1  # ~-1.48%
        assert item["status"] == "Match"  # <= 2% threshold and < 20,000 Gs absolute

    @pytest.mark.asyncio
    async def test_compare_absolute_threshold_exceeds_20k(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test that absolute difference > 20,000 Gs flags as Needs Review even if % < 2%."""
        from datetime import date

        business = await BusinessFactory.create(db_session)
        today = date.today()

        # Manual: 1,000,000, Calculated: 1,025,000 (2.5% variance, but 25,000 Gs absolute)
        # This should trigger "Needs Review" because absolute > 20,000 Gs
        await DailyReconciliationFactory.create(
            db_session,
            business_id=business.id,
            date=today,
            total_sales=Decimal("1000000.00"),  # 1M Gs
        )

        # Calculated total: 1,025,000 (25,000 Gs difference, 2.44% variance)
        await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            session_date=today,
            status="CLOSED",
            initial_cash=Decimal("0.00"),
            final_cash=Decimal("1025000.00"),  # Cash sales = 1,025,000
            credit_card_total=Decimal("0.00"),
        )

        response = await admin_client.get(f"/reconciliation/compare/?date={today.isoformat()}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        item = data[0]
        assert item["variance"]["total_sales"]["difference"] == -25000.0  # 25,000 Gs
        variance_pct = item["variance"]["total_sales"]["variance_percent"]
        assert abs(variance_pct - (-2.44)) < 0.1  # ~-2.44%
        # Should be "Needs Review" because absolute difference (25,000) > 20,000 Gs
        assert item["status"] == "Needs Review"

    @pytest.mark.asyncio
    async def test_compare_absolute_threshold_within_20k(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test that absolute difference < 20,000 Gs and % < 2% shows as Match."""
        from datetime import date

        business = await BusinessFactory.create(db_session)
        today = date.today()

        # Manual: 1,000,000, Calculated: 1,015,000 (1.5% variance, 15,000 Gs absolute)
        # This should be "Match" because both thresholds are within limits
        await DailyReconciliationFactory.create(
            db_session,
            business_id=business.id,
            date=today,
            total_sales=Decimal("1000000.00"),  # 1M Gs
        )

        # Calculated total: 1,015,000 (15,000 Gs difference, 1.48% variance)
        await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            session_date=today,
            status="CLOSED",
            initial_cash=Decimal("0.00"),
            final_cash=Decimal("1015000.00"),  # Cash sales = 1,015,000
            credit_card_total=Decimal("0.00"),
        )

        response = await admin_client.get(f"/reconciliation/compare/?date={today.isoformat()}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        item = data[0]
        assert item["variance"]["total_sales"]["difference"] == -15000.0  # 15,000 Gs
        variance_pct = item["variance"]["total_sales"]["variance_percent"]
        assert abs(variance_pct - (-1.48)) < 0.1  # ~-1.48%
        # Should be "Match" because both absolute (15,000) < 20,000 Gs and % (1.48%) < 2%
        assert item["status"] == "Match"

    @pytest.mark.asyncio
    async def test_compare_filter_by_business_id(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Test filtering by business_id."""
        from datetime import date

        business1 = await BusinessFactory.create(db_session)
        business2 = await BusinessFactory.create(db_session)
        today = date.today()

        await DailyReconciliationFactory.create(
            db_session, business_id=business1.id, date=today
        )
        await DailyReconciliationFactory.create(
            db_session, business_id=business2.id, date=today
        )

        response = await admin_client.get(
            f"/reconciliation/compare/?date={today.isoformat()}&business_id={business1.id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["business_id"] == str(business1.id)

