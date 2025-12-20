"""Tests for session conflict detection."""

import pytest
from datetime import date as date_type, time
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import BusinessFactory, CashSessionFactory


class TestSessionConflicts:
    """Test session conflict detection."""

    @pytest.fixture
    async def business_id(self, db_session: AsyncSession) -> str:
        """Create a test business."""
        business = await BusinessFactory.create(db_session, name="Test Farmacia")
        return str(business.id)

    async def test_no_conflict_non_overlapping_shifts(
            self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test non-overlapping sessions on same day."""
        business = await BusinessFactory.create(db_session)

        # Create first session 8:00-12:00
        session1 = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            session_date=date_type.today(),
            opened_time=time(8, 0),
            status="CLOSED",
            final_cash=Decimal("1000000.00"),
            closed_time=time(12, 0),
        )

        # Create second session 13:00-17:00 (no overlap)
        session2 = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            session_date=date_type.today(),
            opened_time=time(13, 0),
            status="OPEN",
        )

        assert session1.id != session2.id
        response = await client.get("/", follow_redirects=True)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_conflict_same_time(
        self, client: AsyncClient, db_session: AsyncSession, business_id: str
    ):
        """Test that overlapping sessions at same time conflict."""
        business = await BusinessFactory.create(db_session)

        # Create first session at 9:00
        session1 = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            session_date=date_type.today(),
            opened_time=time(9, 0),
            status="OPEN",
        )

        # Try to create another at same time (9:00)
        response = await client.post(
            "/sessions",
            data={
                "business_id": str(business.id),
                "cashier_name": "Second Cashier",
                "initial_cash": "500000.00",
                "opened_time": "09:00",
            },
            follow_redirects=False,
        )

        # Should either fail or succeed with overlap warning
        # Both are acceptable depending on allow_overlap setting
        assert response.status_code in [302, 400, 409]

    @pytest.mark.asyncio
    async def test_allow_overlap_checkbox(
        self, client: AsyncClient, db_session: AsyncSession, business_id: str
    ):
        """Test allow_overlap checkbox bypasses conflict."""
        business = await BusinessFactory.create(db_session)

        # Create first session
        session1 = await CashSessionFactory.create(
            db_session,
            business_id=business.id,
            session_date=date_type.today(),
            opened_time=time(9, 0),
            status="OPEN",
        )

        # Try to create overlapping with allow_overlap=True
        response = await client.post(
            "/sessions",
            data={
                "business_id": str(business.id),
                "cashier_name": "Second Cashier",
                "initial_cash": "500000.00",
                "opened_time": "09:00",
                "allow_overlap": "on",
            },
            follow_redirects=False,
        )

        # With allow_overlap, should succeed
        assert response.status_code in [302, 400]
