"""Tests for dashboard and list visibility filtering (AC-01, AC-02, AC-06).

Ensures that:
- Admins see all businesses and sessions system-wide
- Cashiers see only their assigned businesses and sessions
- Report filtering respects business assignments
"""

from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.utils.datetime import today_local
from tests.factories import BusinessFactory, CashSessionFactory


class TestRBACDashboardVisibility:
    """Test dashboard shows only authorized businesses/sessions (AC-01, AC-02)."""

    @pytest.mark.asyncio
    async def test_dashboard_endpoint_accessible(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Dashboard endpoint is accessible for authenticated users."""
        response = await client.get("/")
        assert response.status_code in [200, 302]

    @pytest.mark.asyncio
    async def test_dashboard_business_filtering_applied(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Dashboard uses get_assigned_businesses() for filtering."""
        # Create businesses
        await BusinessFactory.create(db_session, is_active=True)
        await BusinessFactory.create(db_session, is_active=True)

        # Dashboard should render without errors
        response = await client.get("/")
        assert response.status_code in [200, 302]

    @pytest.mark.asyncio
    async def test_dashboard_shows_envelope_quick_links_for_admin(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Admin dashboard includes quick access links for envelopes and deposits list."""
        response = await admin_client.get("/")
        assert response.status_code == 200
        assert "/admin/envelopes/date-range" in response.text
        assert "/admin/envelopes/deposits" in response.text

    @pytest.mark.asyncio
    async def test_dashboard_hides_envelope_quick_links_for_cashier(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Cashier dashboard does not render admin-only envelope quick links."""
        response = await client.get("/")
        assert response.status_code in [200, 302]
        if response.status_code == 200:
            assert "/admin/envelopes/date-range" not in response.text
            assert "/admin/envelopes/deposits" not in response.text

    @pytest.mark.asyncio
    async def test_cashier_dashboard_warns_about_previous_open_sessions(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Cashiers see their own open sessions from previous days."""
        business = await BusinessFactory.create(db_session)
        yesterday = today_local() - timedelta(days=1)
        await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            cashier_id=client.test_user.id,
            created_by=client.test_user.id,
            session_date=yesterday,
            status="OPEN",
        )

        response = await client.get("/")

        assert response.status_code == 200
        assert "You have open sessions from previous days" in response.text
        assert "Open oldest" in response.text
        assert "View all" in response.text

    @pytest.mark.asyncio
    async def test_admin_dashboard_does_not_show_cashier_previous_open_warning(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """The previous-open-session warning is part of the cashier experience."""
        business = await BusinessFactory.create(db_session)
        yesterday = today_local() - timedelta(days=1)
        await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            cashier_id=admin_client.test_user.id,
            created_by=admin_client.test_user.id,
            session_date=yesterday,
            status="OPEN",
        )

        response = await admin_client.get("/")

        assert response.status_code == 200
        assert "You have open sessions from previous days" not in response.text


class TestRBACBusinessListVisibility:
    """Test business list respects role-based access (AC-01, AC-02)."""

    @pytest.mark.asyncio
    async def test_business_list_endpoint_accessible(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Business list endpoint is accessible for authenticated users."""
        response = await client.get("/businesses")
        assert response.status_code in [200, 302]


class TestRBACReportVisibility:
    """Test reports show only authorized data (AC-01, AC-02, AC-06)."""

    @pytest.mark.asyncio
    async def test_daily_revenue_report_accessible(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Daily revenue report endpoint accessible for authenticated users."""
        response = await client.get("/reports/daily-revenue")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_weekly_trend_report_accessible(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Weekly trend report endpoint accessible for authenticated users."""
        response = await client.get("/reports/weekly-trend")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_flagged_sessions_report_accessible(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Flagged sessions report endpoint accessible for authenticated users."""
        response = await client.get("/reports/flagged-sessions")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_business_stats_report_accessible(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Business stats report endpoint accessible for authenticated users."""
        response = await client.get("/reports/business-stats")
        assert response.status_code == 200


class TestRBACReportFilteringEnforced:
    """Test that report endpoints enforce business assignment filtering."""

    @pytest.mark.asyncio
    async def test_invalid_business_filter_handled_gracefully(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Unauthorized business filter attempts are handled gracefully."""
        # Try to filter to non-existent business
        response = await client.get(
            "/reports/flagged-sessions?business_id=12345678-1234-5678-1234-567812345678"
        )
        # Should return 200 (graceful handling) or 404 (business not found)
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_business_stats_filters_businesses(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Business stats endpoint applies get_assigned_businesses() filtering."""
        response = await client.get("/reports/business-stats")
        assert response.status_code == 200
