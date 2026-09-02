"""Tests for CP-REPORTS-05 — Transfer List Review UX (pagination + filters + sorting)."""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class TestTransferItemsPagination:
    """Test CP-REPORTS-05: Pagination, filtering, and sorting of transfer items."""

    # ─────── Pagination Tests ────────

    @pytest.mark.asyncio
    async def test_pagination_default_page_size_is_20(
        self, db_session: AsyncSession, factories
    ):
        """AC-1: Default page size is 20 items."""
        from cashpilot.api.admin import _apply_transfer_sorting_and_pagination

        business = await factories.business(name="Test Business")
        
        # Create 50 transfers
        transfers = []
        for i in range(50):
            transfer = {
                "id": UUID(int=i),
                "session_id": UUID(int=0),
                "session_number": i + 1,
                "description": f"Transfer {i+1}",
                "amount": Decimal("1000.00"),
                "created_at": datetime(2026, 2, 16, 10, 0, 0, tzinfo=timezone.utc),
                "cashier_id": UUID(int=0),
                "cashier_name": "John D.",
                "is_verified": False,
                "business_id": str(business.id),
            }
            transfers.append(transfer)
        
        # Get first page with default size
        paginated, total = await _apply_transfer_sorting_and_pagination(
            transfers,
            business_names_by_id={str(business.id): business.name},
            page=1,
            page_size=20,
        )
        
        assert len(paginated) == 20
        assert total == 50

    @pytest.mark.asyncio
    async def test_pagination_with_custom_page_size_50(
        self, db_session: AsyncSession, factories
    ):
        """AC-1: Can select 50 items per page."""
        from cashpilot.api.admin import _apply_transfer_sorting_and_pagination

        business = await factories.business(name="Test Business")
        
        # Create 75 transfers
        transfers = []
        for i in range(75):
            transfer = {
                "id": UUID(int=i),
                "session_id": UUID(int=0),
                "session_number": i + 1,
                "description": f"Transfer {i+1}",
                "amount": Decimal("1000.00"),
                "created_at": datetime(2026, 2, 16, 10, 0, 0, tzinfo=timezone.utc),
                "cashier_id": UUID(int=0),
                "cashier_name": "John D.",
                "is_verified": False,
                "business_id": str(business.id),
            }
            transfers.append(transfer)
        
        # First page with page_size=50
        paginated, total = await _apply_transfer_sorting_and_pagination(
            transfers,
            business_names_by_id={str(business.id): business.name},
            page=1,
            page_size=50,
        )
        
        assert len(paginated) == 50
        assert total == 75
        
        # Second page
        paginated, total = await _apply_transfer_sorting_and_pagination(
            transfers,
            business_names_by_id={str(business.id): business.name},
            page=2,
            page_size=50,
        )
        
        assert len(paginated) == 25

    @pytest.mark.asyncio
    async def test_pagination_calculates_correct_pages(
        self, db_session: AsyncSession, factories
    ):
        """AC-1: Pagination correctly calculates total pages."""
        from cashpilot.api.admin import _apply_transfer_sorting_and_pagination

        business = await factories.business(name="Test Business")
        
        # Create 63 transfers
        transfers = []
        for i in range(63):
            transfer = {
                "id": UUID(int=i),
                "session_id": UUID(int=0),
                "session_number": i + 1,
                "description": f"Transfer {i+1}",
                "amount": Decimal("1000.00"),
                "created_at": datetime(2026, 2, 16, 10, 0, 0, tzinfo=timezone.utc),
                "cashier_id": UUID(int=0),
                "cashier_name": "John D.",
                "is_verified": False,
                "business_id": str(business.id),
            }
            transfers.append(transfer)
        
        _, total = await _apply_transfer_sorting_and_pagination(
            transfers,
            business_names_by_id={str(business.id): business.name},
            page=1,
            page_size=20,
        )
        
        # 63 / 20 = 3 full pages + 1 partial = 4 total pages
        total_pages = (total + 20 - 1) // 20
        assert total_pages == 4

    # ─────── Filter Tests ────────

    @pytest.mark.asyncio
    async def test_filter_by_verification_status_unverified_only(
        self, db_session: AsyncSession, factories
    ):
        """AC-2: Filter for unverified transfers only."""
        from cashpilot.api.admin import _apply_transfer_filters

        business = await factories.business(name="Test Business")
        
        transfers = [
            {
                "id": UUID(int=1),
                "is_verified": False,
                "business_id": str(business.id),
                "amount": Decimal("1000.00"),
                "cashier_id": UUID(int=0),
                "cashier_name": "John D.",
            },
            {
                "id": UUID(int=2),
                "is_verified": True,
                "business_id": str(business.id),
                "amount": Decimal("2000.00"),
                "cashier_id": UUID(int=0),
                "cashier_name": "John D.",
            },
            {
                "id": UUID(int=3),
                "is_verified": False,
                "business_id": str(business.id),
                "amount": Decimal("3000.00"),
                "cashier_id": UUID(int=0),
                "cashier_name": "John D.",
            },
        ]
        
        filtered = await _apply_transfer_filters(
            transfers,
            filter_verified="unverified",
        )
        
        assert len(filtered) == 2
        assert all(not item["is_verified"] for item in filtered)
        assert filtered[0]["id"] == UUID(int=1)
        assert filtered[1]["id"] == UUID(int=3)

    @pytest.mark.asyncio
    async def test_filter_by_verification_status_verified_only(
        self, db_session: AsyncSession, factories
    ):
        """AC-2: Filter for verified transfers only."""
        from cashpilot.api.admin import _apply_transfer_filters

        business = await factories.business(name="Test Business")
        
        transfers = [
            {
                "id": UUID(int=1),
                "is_verified": False,
                "business_id": str(business.id),
                "amount": Decimal("1000.00"),
                "cashier_id": UUID(int=0),
                "cashier_name": "John D.",
            },
            {
                "id": UUID(int=2),
                "is_verified": True,
                "business_id": str(business.id),
                "amount": Decimal("2000.00"),
                "cashier_id": UUID(int=0),
                "cashier_name": "John D.",
            },
            {
                "id": UUID(int=3),
                "is_verified": False,
                "business_id": str(business.id),
                "amount": Decimal("3000.00"),
                "cashier_id": UUID(int=0),
                "cashier_name": "John D.",
            },
        ]
        
        filtered = await _apply_transfer_filters(
            transfers,
            filter_verified="verified",
        )
        
        assert len(filtered) == 1
        assert all(item["is_verified"] for item in filtered)
        assert filtered[0]["id"] == UUID(int=2)

    @pytest.mark.asyncio
    async def test_filter_by_business(
        self, db_session: AsyncSession, factories
    ):
        """AC-2: Filter transfers by business."""
        from cashpilot.api.admin import _apply_transfer_filters

        business1 = await factories.business(name="Business 1")
        business2 = await factories.business(name="Business 2")
        
        transfers = [
            {
                "id": UUID(int=1),
                "business_id": str(business1.id),
                "is_verified": False,
                "cashier_id": UUID(int=0),
            },
            {
                "id": UUID(int=2),
                "business_id": str(business2.id),
                "is_verified": False,
                "cashier_id": UUID(int=0),
            },
            {
                "id": UUID(int=3),
                "business_id": str(business1.id),
                "is_verified": False,
                "cashier_id": UUID(int=0),
            },
        ]
        
        filtered = await _apply_transfer_filters(
            transfers,
            filter_business=str(business1.id),
        )
        
        assert len(filtered) == 2
        assert all(item["business_id"] == str(business1.id) for item in filtered)

    @pytest.mark.asyncio
    async def test_filter_by_cashier(
        self, db_session: AsyncSession, factories
    ):
        """AC-2: Filter transfers by cashier."""
        from cashpilot.api.admin import _apply_transfer_filters

        cashier1_id = UUID(int=1)
        cashier2_id = UUID(int=2)
        
        transfers = [
            {
                "id": UUID(int=1),
                "cashier_id": cashier1_id,
                "is_verified": False,
                "business_id": "bus-1",
            },
            {
                "id": UUID(int=2),
                "cashier_id": cashier2_id,
                "is_verified": False,
                "business_id": "bus-1",
            },
            {
                "id": UUID(int=3),
                "cashier_id": cashier1_id,
                "is_verified": False,
                "business_id": "bus-1",
            },
        ]
        
        filtered = await _apply_transfer_filters(
            transfers,
            filter_cashier=str(cashier1_id),
        )
        
        assert len(filtered) == 2
        assert all(item["cashier_id"] == cashier1_id for item in filtered)

    @pytest.mark.asyncio
    async def test_multiple_filters_combined(
        self, db_session: AsyncSession, factories
    ):
        """AC-2: Apply multiple filters together."""
        from cashpilot.api.admin import _apply_transfer_filters

        business1 = await factories.business(name="Business 1")
        cashier1_id = UUID(int=1)
        
        transfers = [
            {
                "id": UUID(int=1),
                "business_id": str(business1.id),
                "cashier_id": cashier1_id,
                "is_verified": False,
            },
            {
                "id": UUID(int=2),
                "business_id": str(business1.id),
                "cashier_id": UUID(int=2),
                "is_verified": True,
            },
            {
                "id": UUID(int=3),
                "business_id": str(UUID(int=999)),
                "cashier_id": cashier1_id,
                "is_verified": False,
            },
            {
                "id": UUID(int=4),
                "business_id": str(business1.id),
                "cashier_id": cashier1_id,
                "is_verified": True,
            },
        ]
        
        # Filter: business1, unverified, cashier1
        filtered = await _apply_transfer_filters(
            transfers,
            filter_business=str(business1.id),
            filter_verified="unverified",
            filter_cashier=str(cashier1_id),
        )
        
        assert len(filtered) == 1
        assert filtered[0]["id"] == UUID(int=1)

    # ─────── Sorting Tests ────────

    @pytest.mark.asyncio
    async def test_sort_by_time_ascending(
        self, db_session: AsyncSession, factories
    ):
        """AC-3: Sort by time in ascending order (default)."""
        from cashpilot.api.admin import _apply_transfer_sorting_and_pagination

        business = await factories.business(name="Test Business")
        
        transfers = [
            {
                "id": UUID(int=3),
                "created_at": datetime(2026, 2, 16, 15, 0, 0, tzinfo=timezone.utc),
                "business_id": str(business.id),
                "amount": Decimal("1000.00"),
                "cashier_id": UUID(int=0),
            },
            {
                "id": UUID(int=1),
                "created_at": datetime(2026, 2, 16, 10, 0, 0, tzinfo=timezone.utc),
                "business_id": str(business.id),
                "amount": Decimal("1000.00"),
                "cashier_id": UUID(int=0),
            },
            {
                "id": UUID(int=2),
                "created_at": datetime(2026, 2, 16, 12, 0, 0, tzinfo=timezone.utc),
                "business_id": str(business.id),
                "amount": Decimal("1000.00"),
                "cashier_id": UUID(int=0),
            },
        ]
        
        sorted_items, _ = await _apply_transfer_sorting_and_pagination(
            transfers,
            business_names_by_id={str(business.id): business.name},
            sort_by="time",
            sort_order="asc",
            page=1,
            page_size=20,
        )
        
        assert [item["id"] for item in sorted_items] == [UUID(int=1), UUID(int=2), UUID(int=3)]

    @pytest.mark.asyncio
    async def test_sort_by_amount_descending(
        self, db_session: AsyncSession, factories
    ):
        """AC-3: Sort by amount in descending order."""
        from cashpilot.api.admin import _apply_transfer_sorting_and_pagination

        business = await factories.business(name="Test Business")
        
        transfers = [
            {
                "id": UUID(int=1),
                "amount": Decimal("1000.00"),
                "created_at": datetime(2026, 2, 16, 10, 0, 0, tzinfo=timezone.utc),
                "business_id": str(business.id),
                "cashier_id": UUID(int=0),
            },
            {
                "id": UUID(int=2),
                "amount": Decimal("3000.00"),
                "created_at": datetime(2026, 2, 16, 10, 0, 0, tzinfo=timezone.utc),
                "business_id": str(business.id),
                "cashier_id": UUID(int=0),
            },
            {
                "id": UUID(int=3),
                "amount": Decimal("2000.00"),
                "created_at": datetime(2026, 2, 16, 10, 0, 0, tzinfo=timezone.utc),
                "business_id": str(business.id),
                "cashier_id": UUID(int=0),
            },
        ]
        
        sorted_items, _ = await _apply_transfer_sorting_and_pagination(
            transfers,
            business_names_by_id={str(business.id): business.name},
            sort_by="amount",
            sort_order="desc",
            page=1,
            page_size=20,
        )
        
        assert [item["id"] for item in sorted_items] == [UUID(int=2), UUID(int=3), UUID(int=1)]

    @pytest.mark.asyncio
    async def test_sort_by_business_then_time(
        self, db_session: AsyncSession, factories
    ):
        """AC-3: Sort by business first, then time (stable sort)."""
        from cashpilot.api.admin import _apply_transfer_sorting_and_pagination

        business1 = await factories.business(name="Alpha Business")
        business2 = await factories.business(name="Beta Business")
        
        transfers = [
            {
                "id": UUID(int=1),
                "business_id": str(business2.id),
                "created_at": datetime(2026, 2, 16, 10, 0, 0, tzinfo=timezone.utc),
                "amount": Decimal("1000.00"),
                "cashier_id": UUID(int=0),
            },
            {
                "id": UUID(int=2),
                "business_id": str(business1.id),
                "created_at": datetime(2026, 2, 16, 15, 0, 0, tzinfo=timezone.utc),
                "amount": Decimal("1000.00"),
                "cashier_id": UUID(int=0),
            },
            {
                "id": UUID(int=3),
                "business_id": str(business1.id),
                "created_at": datetime(2026, 2, 16, 10, 0, 0, tzinfo=timezone.utc),
                "amount": Decimal("1000.00"),
                "cashier_id": UUID(int=0),
            },
            {
                "id": UUID(int=4),
                "business_id": str(business2.id),
                "created_at": datetime(2026, 2, 16, 12, 0, 0, tzinfo=timezone.utc),
                "amount": Decimal("1000.00"),
                "cashier_id": UUID(int=0),
            },
        ]
        
        business_names = {
            str(business1.id): "Alpha Business",
            str(business2.id): "Beta Business",
        }
        
        sorted_items, _ = await _apply_transfer_sorting_and_pagination(
            transfers,
            business_names_by_id=business_names,
            sort_by="business,time",
            sort_order="asc",
            page=1,
            page_size=20,
        )
        
        # Expected: business1 first (Alpha) sorted by time, then business2 (Beta) sorted by time
        assert [item["id"] for item in sorted_items] == [UUID(int=3), UUID(int=2), UUID(int=1), UUID(int=4)]

    # ─────── Integration Tests ────────

    @pytest.mark.asyncio
    async def test_default_view_shows_only_unverified_focus(
        self, db_session: AsyncSession, factories
    ):
        """AC-4: Default view can focus on unverified transfers."""
        from cashpilot.api.admin import _apply_transfer_filters, _apply_transfer_sorting_and_pagination

        business = await factories.business(name="Test Business")
        
        transfers = [
            {
                "id": UUID(int=1),
                "is_verified": False,
                "business_id": str(business.id),
                "amount": Decimal("1000.00"),
                "created_at": datetime(2026, 2, 16, 10, 0, 0, tzinfo=timezone.utc),
                "cashier_id": UUID(int=0),
            },
            {
                "id": UUID(int=2),
                "is_verified": True,
                "business_id": str(business.id),
                "amount": Decimal("1000.00"),
                "created_at": datetime(2026, 2, 16, 10, 0, 0, tzinfo=timezone.utc),
                "cashier_id": UUID(int=0),
            },
            {
                "id": UUID(int=3),
                "is_verified": False,
                "business_id": str(business.id),
                "amount": Decimal("1000.00"),
                "created_at": datetime(2026, 2, 16, 10, 0, 0, tzinfo=timezone.utc),
                "cashier_id": UUID(int=0),
            },
        ]
        
        # Filter for unverified only
        filtered = await _apply_transfer_filters(
            transfers,
            filter_verified="unverified",
        )
        
        # Paginate with default settings
        paginated, total = await _apply_transfer_sorting_and_pagination(
            filtered,
            business_names_by_id={str(business.id): business.name},
            sort_by="business,time",
            sort_order="asc",
            page=1,
            page_size=20,
        )
        
        assert total == 2
        assert len(paginated) == 2
        assert all(not item["is_verified"] for item in paginated)

    @pytest.mark.asyncio
    async def test_pagination_with_filters_and_sorting(
        self, db_session: AsyncSession, factories
    ):
        """AC-5: Pagination works correctly with filters and sorting applied."""
        from cashpilot.api.admin import _apply_transfer_filters, _apply_transfer_sorting_and_pagination

        business = await factories.business(name="Test Business")
        
        # Create 30 unverified transfers with different amounts
        transfers = []
        for i in range(30):
            transfer = {
                "id": UUID(int=i),
                "is_verified": i % 2 == 0,  # Half verified, half not
                "business_id": str(business.id),
                "amount": Decimal(f"{1000 + (i * 100)}.00"),
                "created_at": datetime(2026, 2, 16, 10 + (i % 8), 0, 0, tzinfo=timezone.utc),
                "cashier_id": UUID(int=0),
            }
            transfers.append(transfer)
        
        # Filter for unverified only
        filtered = await _apply_transfer_filters(
            transfers,
            filter_verified="unverified",
        )
        
        assert len(filtered) == 15
        
        # Get first page with page_size=10
        paginated, total = await _apply_transfer_sorting_and_pagination(
            filtered,
            business_names_by_id={str(business.id): business.name},
            sort_by="amount",
            sort_order="asc",
            page=1,
            page_size=10,
        )
        
        assert total == 15
        assert len(paginated) == 10
        
        # Get second page
        paginated_page2, _ = await _apply_transfer_sorting_and_pagination(
            filtered,
            business_names_by_id={str(business.id): business.name},
            sort_by="amount",
            sort_order="asc",
            page=2,
            page_size=10,
        )
        
        assert len(paginated_page2) == 5


class TestTransferAmountSearch:
    """Amount search box: users type the amount as they read it on screen."""

    @staticmethod
    def _transfers():
        return [
            {"id": UUID(int=1), "amount": Decimal("52000.00"), "is_verified": False},
            {"id": UUID(int=2), "amount": Decimal("52500.00"), "is_verified": False},
            {"id": UUID(int=3), "amount": Decimal("520000.00"), "is_verified": True},
            {"id": UUID(int=4), "amount": Decimal("38500.00"), "is_verified": False},
        ]

    def test_normalize_amount_query_strips_separators(self):
        from cashpilot.api.admin import _normalize_amount_query

        assert _normalize_amount_query("52.000") == "52000"
        assert _normalize_amount_query("Gs 52.000") == "52000"
        assert _normalize_amount_query(" 52 000 ") == "52000"
        assert _normalize_amount_query("abc") == ""
        assert _normalize_amount_query(None) == ""

    @pytest.mark.asyncio
    async def test_search_exact_amount_without_dots(self):
        from cashpilot.api.admin import _apply_transfer_filters

        filtered = await _apply_transfer_filters(self._transfers(), filter_amount="52000")

        assert [item["id"] for item in filtered] == [UUID(int=1)]

    @pytest.mark.asyncio
    async def test_search_accepts_formatted_amount(self):
        from cashpilot.api.admin import _apply_transfer_filters

        filtered = await _apply_transfer_filters(self._transfers(), filter_amount="Gs 52.000")

        assert [item["id"] for item in filtered] == [UUID(int=1)]

    @pytest.mark.asyncio
    async def test_search_matches_by_leading_digits_when_no_exact_match(self):
        from cashpilot.api.admin import _apply_transfer_filters

        filtered = await _apply_transfer_filters(self._transfers(), filter_amount="52")

        assert [item["id"] for item in filtered] == [UUID(int=1), UUID(int=2), UUID(int=3)]

    @pytest.mark.asyncio
    async def test_exact_amount_wins_over_longer_amounts(self):
        """Typing 52000 must not bury Gs 52.000 among Gs 520.000."""
        from cashpilot.api.admin import _apply_transfer_filters

        filtered = await _apply_transfer_filters(self._transfers(), filter_amount="52000")

        assert [item["id"] for item in filtered] == [UUID(int=1)]

    @pytest.mark.asyncio
    async def test_empty_search_returns_everything(self):
        from cashpilot.api.admin import _apply_transfer_filters

        assert len(await _apply_transfer_filters(self._transfers(), filter_amount="")) == 4
        assert len(await _apply_transfer_filters(self._transfers(), filter_amount=None)) == 4
        assert len(await _apply_transfer_filters(self._transfers(), filter_amount="Gs")) == 4

    @pytest.mark.asyncio
    async def test_amount_search_combines_with_status_filter(self):
        from cashpilot.api.admin import _apply_transfer_filters

        filtered = await _apply_transfer_filters(
            self._transfers(),
            filter_verified="unverified",
            filter_amount="52",
        )

        assert [item["id"] for item in filtered] == [UUID(int=1), UUID(int=2)]

    @pytest.mark.asyncio
    async def test_search_matches_the_rounded_amount_shown_on_screen(self):
        """Gs 1.234,75 is displayed as Gs 1.235, so 1235 has to find it."""
        from cashpilot.api.admin import _apply_transfer_filters

        transfers = [
            {"id": UUID(int=10), "amount": Decimal("1234.75")},
            {"id": UUID(int=11), "amount": Decimal("1234.50")},
        ]

        found = await _apply_transfer_filters(transfers, filter_amount="1235")
        assert [item["id"] for item in found] == [UUID(int=10)]

        # 1234.50 displays as Gs 1.234 (half-even), so that is what finds it
        found = await _apply_transfer_filters(transfers, filter_amount="1234")
        assert [item["id"] for item in found] == [UUID(int=11)]

    @pytest.mark.asyncio
    async def test_no_match_returns_empty(self):
        from cashpilot.api.admin import _apply_transfer_filters

        assert await _apply_transfer_filters(self._transfers(), filter_amount="99999") == []
