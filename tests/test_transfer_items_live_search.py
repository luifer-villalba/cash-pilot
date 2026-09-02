"""Wiring of the live amount search on the transfers reconciliation tab.

These render the templates directly (no DB, no HTTP) so the pieces the search
depends on — the htmx attributes, the swap target, and the out-of-band totals —
cannot be dropped by a refactor without a test noticing.
"""

import datetime
import re
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"

BUSINESS_ID = "b1"
BUSINESSES_BY_ID = {BUSINESS_ID: "Farmacia Zulmi - Suc 1"}


def _clear_button_classes(html: str) -> str:
    """The class attribute of the clear (x) button, where `hidden` is toggled."""
    button = html[html.index('id="filter-amount-clear"') :]
    return re.search(r'class="([^"]*)"', button).group(1)


@pytest.fixture
def env():
    environment = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    environment.filters["format_currency_py"] = lambda value: f"{value or 0}"
    environment.filters["format_datetime_business"] = lambda value, fmt=None: str(value)
    environment.globals["_"] = lambda text: text
    return environment


def _context(**overrides):
    context = {
        "all_transfer_items": [
            {
                "id": UUID(int=1),
                "session_id": UUID(int=2),
                "session_number": 2534,
                "business_id": BUSINESS_ID,
                "cashier_name": "Felipa P.",
                "description": "factura 4225 comp.6690",
                "amount": Decimal("52000"),
                "is_verified": False,
                "created_at": datetime.datetime(2026, 9, 1, 15, 25, 43),
            }
        ],
        "transfer_items_total_count": 1,
        "verified_transfer_count": 0,
        "pending_transfer_count": 1,
        "businesses_by_id": BUSINESSES_BY_ID,
        "businesses": [SimpleNamespace(id=BUSINESS_ID, name=BUSINESSES_BY_ID[BUSINESS_ID])],
        "comparison_date": datetime.date(2026, 9, 1),
        "selected_business_id": "",
        "current_page": 1,
        "page_size": 20,
        "total_pages": 1,
        "start_index": 1,
        "filter_business": "",
        "filter_verified": "all",
        "filter_cashier": "",
        "filter_amount": "",
        "sort_by": "business,time",
        "sort_order": "asc",
    }
    context.update(overrides)
    return context


class TestLiveAmountSearchMarkup:
    def test_search_box_filters_while_typing(self, env):
        html = env.get_template("admin/partials/transfer_items_detail.html").render(**_context())

        # Fires on input with a short debounce - never waits for Enter
        assert 'hx-trigger="input changed delay:350ms, search"' in html
        assert "/admin/reconciliation/transfer-items?date=2026-09-01" in html
        assert 'hx-target="#transfer-items-results"' in html
        assert 'hx-include="#filter-business, #filter-verified, #page-size"' in html

    def test_only_the_results_region_is_swapped(self, env):
        """The input has to stay outside the swap or it would lose focus mid-word."""
        html = env.get_template("admin/partials/transfer_items_detail.html").render(**_context())

        results_start = html.index('<div id="transfer-items-results">')
        assert html.index('id="filter-amount"') < results_start

    def test_clear_button_hidden_until_something_is_typed(self, env):
        template = env.get_template("admin/partials/transfer_items_detail.html")

        empty = template.render(**_context(filter_amount=""))
        filled = template.render(**_context(filter_amount="52000"))

        assert "hidden" in _clear_button_classes(empty)
        assert "hidden" not in _clear_button_classes(filled)

    def test_results_partial_refreshes_the_totals_out_of_band(self, env):
        template = env.get_template("admin/partials/transfer_items_results.html")

        live = template.render(**_context(oob=True))
        full_page = template.render(**_context())

        assert 'id="transfer-items-counts"' in live
        assert 'hx-swap-oob="true"' in live
        # In the full page the totals are rendered in the header instead
        assert 'id="transfer-items-counts"' not in full_page

    def test_pagination_links_keep_the_amount_filter(self, env):
        html = env.get_template("admin/partials/transfer_items_results.html").render(
            **_context(filter_amount="52000", total_pages=2, transfer_items_total_count=40)
        )

        assert "filter_amount=52000" in html

    def test_empty_state_offers_a_way_back(self, env):
        html = env.get_template("admin/partials/transfer_items_results.html").render(
            **_context(all_transfer_items=[], filter_amount="99999")
        )

        assert "No transfers found with that amount" in html
        assert "clearTransferAmountFilter()" in html
