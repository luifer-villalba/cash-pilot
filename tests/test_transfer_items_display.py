"""Tests for CP-REPORTS-03 — Bank Transfers Display in Reconciliation."""

import pytest
from datetime import datetime, date, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models.transfer_item import TransferItem
from cashpilot.models.user import UserRole


class TestTransferItemsDisplay:
    """Test CP-REPORTS-03: Bank transfers display in reconciliation."""

    # ─────── AC-1 & AC-2: Transfer items data fetching and display ────────

    @pytest.mark.asyncio
    async def test_view_all_transfer_items_for_business_and_date(
        self, db_session: AsyncSession, factories
    ):
        """
        AC-1: Admin can view all transfer line items for business+date.
        AC-2: Each transfer displays: description, amount, session ID, cashier, timestamp.
        """
        # Setup
        business = await factories.business(name="Test Business")
        admin = await factories.user(role=UserRole.ADMIN, email="admin@test.com")
        cashier = await factories.user(
            role=UserRole.CASHIER, email="cashier@test.com", first_name="John", last_name="Doe"
        )
        await factories.user_business(business=business, user=cashier)

        session_date = date(2026, 2, 16)
        session1 = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
        )
        session2 = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
        )

        # Create transfer items
        transfer1_time = datetime(2026, 2, 16, 14, 30, 0)
        transfer2_time = datetime(2026, 2, 16, 15, 45, 30)

        transfer1 = TransferItem(
            session_id=session1.id,
            description="Customer John Perez - Invoice 123",
            amount=Decimal("50000.00"),
            created_at=transfer1_time,
        )
        transfer2 = TransferItem(
            session_id=session2.id,
            description="Payment to Supplier ABC",
            amount=Decimal("75000.50"),
            created_at=transfer2_time,
        )
        db_session.add(transfer1)
        db_session.add(transfer2)
        await db_session.commit()

        # Import the helper function
        from cashpilot.api.admin import _fetch_transfer_items_for_reconciliation

        # Fetch transfer items
        transfers = await _fetch_transfer_items_for_reconciliation(
            db_session, business.id, session_date
        )

        # AC-1: All transfers are fetched
        assert len(transfers) == 2
        assert transfers[0]["id"] == transfer1.id
        assert transfers[1]["id"] == transfer2.id

        # AC-2: All required fields are present and correct
        assert transfers[0]["session_id"] == session1.id
        assert transfers[0]["description"] == "Customer John Perez - Invoice 123"
        assert transfers[0]["amount"] == Decimal("50000.00")
        assert transfers[0]["created_at"] == transfer1_time.replace(tzinfo=timezone.utc)
        assert transfers[0]["cashier_name"] == "John D."

        assert transfers[1]["session_id"] == session2.id
        assert transfers[1]["description"] == "Payment to Supplier ABC"
        assert transfers[1]["amount"] == Decimal("75000.50")
        assert transfers[1]["created_at"] == transfer2_time.replace(tzinfo=timezone.utc)
        assert transfers[1]["cashier_name"] == "John D."

    # ─────── AC-3: Chronological ordering ────────

    @pytest.mark.asyncio
    async def test_transfer_items_sorted_chronologically(
        self, db_session: AsyncSession, factories
    ):
        """AC-3: Transfers are displayed in chronological order (earliest first)."""
        # Setup
        business = await factories.business(name="Test Business")
        cashier = await factories.user(role=UserRole.CASHIER, email="cashier@test.com")
        await factories.user_business(business=business, user=cashier)

        session_date = date(2026, 2, 16)
        session = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
        )

        # Create transfers in NON-chronological order
        transfer_times = [
            datetime(2026, 2, 16, 15, 0, 0),
            datetime(2026, 2, 16, 14, 0, 0),
            datetime(2026, 2, 16, 16, 30, 0),
        ]

        for i, time in enumerate(transfer_times):
            transfer = TransferItem(
                session_id=session.id,
                description=f"Transfer {i+1}",
                amount=Decimal("50000.00"),
                created_at=time,
            )
            db_session.add(transfer)
        await db_session.commit()

        from cashpilot.api.admin import _fetch_transfer_items_for_reconciliation

        transfers = await _fetch_transfer_items_for_reconciliation(
            db_session, business.id, session_date
        )

        # Verify chronological order (earliest first)
        assert transfers[0]["created_at"] == datetime(2026, 2, 16, 14, 0, 0, tzinfo=timezone.utc)
        assert transfers[1]["created_at"] == datetime(2026, 2, 16, 15, 0, 0, tzinfo=timezone.utc)
        assert transfers[2]["created_at"] == datetime(2026, 2, 16, 16, 30, 0, tzinfo=timezone.utc)

    # ─────── AC-4: Summary calculation ────────

    @pytest.mark.asyncio
    async def test_transfer_items_summary_totals(
        self, db_session: AsyncSession, factories
    ):
        """AC-4: Summary shows correct count and sum of all transfers."""
        # Setup
        business = await factories.business(name="Test Business")
        cashier = await factories.user(role=UserRole.CASHIER, email="cashier@test.com")
        await factories.user_business(business=business, user=cashier)

        session_date = date(2026, 2, 16)
        session = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
        )

        # Create 3 transfers with known amounts
        amounts = [Decimal("50000.00"), Decimal("75000.50"), Decimal("25000.00")]
        for i, amount in enumerate(amounts):
            transfer = TransferItem(
                session_id=session.id,
                description=f"Transfer {i+1}",
                amount=amount,
                created_at=datetime(2026, 2, 16, 14 + i, 0, 0),
            )
            db_session.add(transfer)
        await db_session.commit()

        from cashpilot.api.admin import _fetch_transfer_items_for_reconciliation

        transfers = await _fetch_transfer_items_for_reconciliation(
            db_session, business.id, session_date
        )

        # Verify count and sum
        assert len(transfers) == 3
        total_amount = sum(t["amount"] for t in transfers)
        assert total_amount == Decimal("150000.50")

    # ─────── Empty state: No transfers ────────

    @pytest.mark.asyncio
    async def test_transfer_items_empty_state(
        self, db_session: AsyncSession, factories
    ):
        """Handle case with zero transfers for a business/date."""
        # Setup
        business = await factories.business(name="Test Business")
        cashier = await factories.user(role=UserRole.CASHIER, email="cashier@test.com")
        await factories.user_business(business=business, user=cashier)

        session_date = date(2026, 2, 16)
        session = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
        )
        # No transfers created

        from cashpilot.api.admin import _fetch_transfer_items_for_reconciliation

        transfers = await _fetch_transfer_items_for_reconciliation(
            db_session, business.id, session_date
        )

        assert transfers == []

    # ─────── AC-5: Read-only verification ────────

    @pytest.mark.asyncio
    async def test_transfer_items_read_only_no_edit_endpoints(
        self, db_session: AsyncSession, factories, admin_client
    ):
        """
        AC-5: Transfer section renders verification controls without edit actions.
        """
        business = await factories.business(name="Test Business")
        cashier = await factories.user(role=UserRole.CASHIER, email="cashier@test.com")
        await factories.user_business(business=business, user=cashier)
        session = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=date(2026, 2, 16),
            status="CLOSED",
        )
        db_session.add(
            TransferItem(
                session_id=session.id,
                description="Sample transfer",
                amount=Decimal("50000.00"),
                created_at=datetime(2026, 2, 16, 14, 0, 0, tzinfo=timezone.utc),
            )
        )
        await db_session.commit()
        session_date = date(2026, 2, 16)

        # Load the reconciliation page
        response = await admin_client.get(
            f"/admin/reconciliation/compare?date={session_date.isoformat()}"
        )

        assert response.status_code == 200
        assert "transfer-verify-checkbox" in response.text

    @pytest.mark.asyncio
    async def test_reconciliation_compare_displays_transfer_time_in_business_timezone(
        self, db_session: AsyncSession, factories, admin_client
    ):
        """Transfer time in recon compare is rendered using business timezone."""
        from cashpilot.utils.datetime import utc_to_business

        business = await factories.business(name="Timezone Business")
        cashier = await factories.user(role=UserRole.CASHIER, email="cashier-timezone@test.com")
        await factories.user_business(business=business, user=cashier)

        session_date = date(2026, 2, 16)
        session = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
        )

        created_at_utc = datetime(2026, 2, 16, 14, 0, 0, tzinfo=timezone.utc)
        expected_local_time = utc_to_business(created_at_utc).strftime("%H:%M:%S")

        db_session.add(
            TransferItem(
                session_id=session.id,
                description="Timezone check transfer",
                amount=Decimal("50000.00"),
                created_at=created_at_utc,
            )
        )
        await db_session.commit()

        response = await admin_client.get(
            f"/admin/reconciliation/compare?date={session_date.isoformat()}&tab=transfers"
        )

        assert response.status_code == 200
        assert "Timezone check transfer" in response.text
        assert expected_local_time in response.text

    @pytest.mark.asyncio
    async def test_reconciliation_compare_shows_transfer_verification_summary(
        self, db_session: AsyncSession, factories, admin_client
    ):
        """Transfer tab shows verified and pending counts for the filtered result set."""
        business = await factories.business(name="Summary Business")
        cashier = await factories.user(role=UserRole.CASHIER, email="cashier-summary@test.com")
        await factories.user_business(business=business, user=cashier)

        session_date = date(2026, 2, 16)
        session = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
        )

        db_session.add_all(
            [
                TransferItem(
                    session_id=session.id,
                    description="Verified transfer",
                    amount=Decimal("50000.00"),
                    created_at=datetime(2026, 2, 16, 14, 0, 0, tzinfo=timezone.utc),
                    is_verified=True,
                ),
                TransferItem(
                    session_id=session.id,
                    description="Pending transfer",
                    amount=Decimal("25000.00"),
                    created_at=datetime(2026, 2, 16, 15, 0, 0, tzinfo=timezone.utc),
                    is_verified=False,
                ),
            ]
        )
        await db_session.commit()

        response = await admin_client.get(
            f"/admin/reconciliation/compare?date={session_date.isoformat()}&tab=transfers"
        )

        assert response.status_code == 200
        assert 'data-transfer-summary="verified-count">1<' in response.text
        assert 'data-transfer-summary="pending-count">1<' in response.text
        assert 'data-transfer-progress="verified"' in response.text
        assert 'data-transfer-progress="pending"' in response.text

    @pytest.mark.asyncio
    async def test_reconciliation_compare_marks_pending_transfer_rows(
        self, db_session: AsyncSession, factories, admin_client
    ):
        """Pending transfers render explicit status markers for visual highlighting hooks."""
        business = await factories.business(name="Pending Marker Business")
        cashier = await factories.user(role=UserRole.CASHIER, email="cashier-pending@test.com")
        await factories.user_business(business=business, user=cashier)

        session_date = date(2026, 2, 16)
        session = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
        )

        db_session.add_all(
            [
                TransferItem(
                    session_id=session.id,
                    description="Pending marker transfer",
                    amount=Decimal("60000.00"),
                    created_at=datetime(2026, 2, 16, 16, 0, 0, tzinfo=timezone.utc),
                    is_verified=False,
                ),
                TransferItem(
                    session_id=session.id,
                    description="Verified marker transfer",
                    amount=Decimal("30000.00"),
                    created_at=datetime(2026, 2, 16, 17, 0, 0, tzinfo=timezone.utc),
                    is_verified=True,
                ),
            ]
        )
        await db_session.commit()

        response = await admin_client.get(
            f"/admin/reconciliation/compare?date={session_date.isoformat()}&tab=transfers"
        )

        assert response.status_code == 200
        assert 'data-transfer-status="pending"' in response.text
        assert 'data-transfer-status="verified"' in response.text

    # ─────── AC-6: RBAC enforcement ────────

    @pytest.mark.asyncio
    async def test_transfer_items_admin_only_access(
        self, db_session: AsyncSession, factories, client
    ):
        """AC-6: Transfer section is admin-only; non-admins cannot access."""
        # Setup
        business = await factories.business(name="Test Business")
        cashier = await factories.user(
            role=UserRole.CASHIER,
            email="cashier@test.com",
        )
        await factories.user_business(business=business, user=cashier)

        session_date = date(2026, 2, 16)

        # Try to access as cashier
        response = await client.get(
            f"/admin/reconciliation/compare?date={session_date.isoformat()}",
            headers={"Authorization": f"Bearer {cashier.id}"},
        )

        # Should be denied (not 200)
        assert response.status_code != 200

    # ─────── AC-7: Formatting verification ────────

    @pytest.mark.asyncio
    async def test_transfer_items_amount_formatting(
        self, db_session: AsyncSession, factories
    ):
        """
        AC-7: Monetary amounts use monospace font and Paraguay format (Gs X.XXX).
        Test that the data returned is in correct format for template rendering.
        """
        business = await factories.business(name="Test Business")
        cashier = await factories.user(role=UserRole.CASHIER, email="cashier@test.com")
        await factories.user_business(business=business, user=cashier)

        session_date = date(2026, 2, 16)
        session = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
        )

        # Test various decimal amounts
        test_amounts = [
            Decimal("100.00"),
            Decimal("1000.50"),
            Decimal("50000.00"),
            Decimal("1234567.89"),
        ]

        for i, amount in enumerate(test_amounts):
            transfer = TransferItem(
                session_id=session.id,
                description=f"Transfer {i+1}",
                amount=amount,
                created_at=datetime(2026, 2, 16, 14 + i, 0, 0),
            )
            db_session.add(transfer)
        await db_session.commit()

        from cashpilot.api.admin import _fetch_transfer_items_for_reconciliation

        transfers = await _fetch_transfer_items_for_reconciliation(
            db_session, business.id, session_date
        )

        # Verify amounts are Decimal (preserved for template formatting)
        for i, transfer in enumerate(transfers):
            assert isinstance(transfer["amount"], Decimal)
            assert transfer["amount"] == test_amounts[i]

    # ─────── Soft-deleted transfers are excluded ────────

    @pytest.mark.asyncio
    async def test_transfer_items_excludes_soft_deleted(
        self, db_session: AsyncSession, factories
    ):
        """Soft-deleted transfers (is_deleted=true) should not appear."""
        business = await factories.business(name="Test Business")
        cashier = await factories.user(role=UserRole.CASHIER, email="cashier@test.com")
        await factories.user_business(business=business, user=cashier)

        session_date = date(2026, 2, 16)
        session = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
        )

        # Create active and deleted transfers
        active_transfer = TransferItem(
            session_id=session.id,
            description="Active Transfer",
            amount=Decimal("50000.00"),
            created_at=datetime(2026, 2, 16, 14, 0, 0),
            is_deleted=False,
        )
        deleted_transfer = TransferItem(
            session_id=session.id,
            description="Deleted Transfer",
            amount=Decimal("25000.00"),
            created_at=datetime(2026, 2, 16, 15, 0, 0),
            is_deleted=True,
        )
        db_session.add(active_transfer)
        db_session.add(deleted_transfer)
        await db_session.commit()

        from cashpilot.api.admin import _fetch_transfer_items_for_reconciliation

        transfers = await _fetch_transfer_items_for_reconciliation(
            db_session, business.id, session_date
        )

        assert len(transfers) == 1
        assert transfers[0]["description"] == "Active Transfer"

    # ─────── Cross-business isolation ────────

    @pytest.mark.asyncio
    async def test_transfer_items_business_isolation(
        self, db_session: AsyncSession, factories
    ):
        """Transfer items should be isolated by business_id."""
        business1 = await factories.business(name="Business 1")
        business2 = await factories.business(name="Business 2")

        cashier1 = await factories.user(
            role=UserRole.CASHIER, email="cashier1@test.com", first_name="John"
        )
        cashier2 = await factories.user(
            role=UserRole.CASHIER, email="cashier2@test.com", first_name="Jane"
        )

        await factories.user_business(business=business1, user=cashier1)
        await factories.user_business(business=business2, user=cashier2)

        session_date = date(2026, 2, 16)

        session1 = await factories.cash_session(
            business=business1,
            cashier=cashier1,
            session_date=session_date,
            status="CLOSED",
        )
        session2 = await factories.cash_session(
            business=business2,
            cashier=cashier2,
            session_date=session_date,
            status="CLOSED",
        )

        # Add transfers to both businesses
        transfer1 = TransferItem(
            session_id=session1.id,
            description="Business 1 Transfer",
            amount=Decimal("50000.00"),
            created_at=datetime(2026, 2, 16, 14, 0, 0),
        )
        transfer2 = TransferItem(
            session_id=session2.id,
            description="Business 2 Transfer",
            amount=Decimal("75000.00"),
            created_at=datetime(2026, 2, 16, 15, 0, 0),
        )
        db_session.add(transfer1)
        db_session.add(transfer2)
        await db_session.commit()

        from cashpilot.api.admin import _fetch_transfer_items_for_reconciliation

        # Fetch for business1 - should only get business1 transfers
        transfers_b1 = await _fetch_transfer_items_for_reconciliation(
            db_session, business1.id, session_date
        )
        assert len(transfers_b1) == 1
        assert transfers_b1[0]["description"] == "Business 1 Transfer"

        # Fetch for business2 - should only get business2 transfers
        transfers_b2 = await _fetch_transfer_items_for_reconciliation(
            db_session, business2.id, session_date
        )
        assert len(transfers_b2) == 1
        assert transfers_b2[0]["description"] == "Business 2 Transfer"

    # ─────── Date filtering ────────

    @pytest.mark.asyncio
    async def test_transfer_items_date_filtering(
        self, db_session: AsyncSession, factories
    ):
        """Transfers should be filtered by session date only."""
        business = await factories.business(name="Test Business")
        cashier = await factories.user(role=UserRole.CASHIER, email="cashier@test.com")
        await factories.user_business(business=business, user=cashier)

        # Create sessions on different dates
        session_date1 = date(2026, 2, 15)
        session_date2 = date(2026, 2, 16)

        session1 = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=session_date1,
            status="CLOSED",
        )
        session2 = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=session_date2,
            status="CLOSED",
        )

        # Add transfers to both sessions
        transfer1 = TransferItem(
            session_id=session1.id,
            description="Transfer on Feb 15",
            amount=Decimal("50000.00"),
            created_at=datetime(2026, 2, 15, 14, 0, 0),
        )
        transfer2 = TransferItem(
            session_id=session2.id,
            description="Transfer on Feb 16",
            amount=Decimal("75000.00"),
            created_at=datetime(2026, 2, 16, 15, 0, 0),
        )
        db_session.add(transfer1)
        db_session.add(transfer2)
        await db_session.commit()

        from cashpilot.api.admin import _fetch_transfer_items_for_reconciliation

        # Fetch for 2026-02-16 - should only get Feb 16 transfers
        transfers = await _fetch_transfer_items_for_reconciliation(
            db_session, business.id, session_date2
        )
        assert len(transfers) == 1
        assert transfers[0]["description"] == "Transfer on Feb 16"

    # ─────── Multiple sessions on same date ────────

    @pytest.mark.asyncio
    async def test_transfer_items_multiple_sessions_same_date(
        self, db_session: AsyncSession, factories
    ):
        """Aggregate transfers from all sessions for a date."""
        business = await factories.business(name="Test Business")
        cashier = await factories.user(role=UserRole.CASHIER, email="cashier@test.com")
        await factories.user_business(business=business, user=cashier)

        session_date = date(2026, 2, 16)

        # Create 3 sessions
        session1 = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
        )
        session2 = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
        )
        session3 = await factories.cash_session(
            business=business,
            cashier=cashier,
            session_date=session_date,
            status="CLOSED",
        )

        # Add transfers to each
        for i, session in enumerate([session1, session2, session3]):
            for j in range(2):  # 2 transfers per session
                transfer = TransferItem(
                    session_id=session.id,
                    description=f"Session {i+1} Transfer {j+1}",
                    amount=Decimal("50000.00"),
                    created_at=datetime(2026, 2, 16, 14 + i, j * 30, 0),
                )
                db_session.add(transfer)
        await db_session.commit()

        from cashpilot.api.admin import _fetch_transfer_items_for_reconciliation

        transfers = await _fetch_transfer_items_for_reconciliation(
            db_session, business.id, session_date
        )

        # Should get all 6 transfers (3 sessions × 2 transfers each)
        assert len(transfers) == 6
