# Tests for Flagged Cash Sessions report helpers.

from datetime import date, time
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models import Business, CashSession, User, UserRole


@pytest.mark.asyncio
async def test_resolve_date_ranges_and_previous_period():
    """AC-06: Flagged sessions report correctly resolves date ranges."""
    from cashpilot.api.routes.flagged_sessions import _previous_period, _resolve_date_range

    today = date(2026, 1, 15)

    this_week = _resolve_date_range("this_week", today)
    assert this_week == (date(2026, 1, 12), date(2026, 1, 18))

    last_week = _resolve_date_range("last_week", today)
    assert last_week == (date(2026, 1, 5), date(2026, 1, 11))

    this_month = _resolve_date_range("this_month", today)
    assert this_month == (date(2026, 1, 1), date(2026, 1, 31))

    last_month = _resolve_date_range("last_month", today)
    assert last_month == (date(2025, 12, 1), date(2025, 12, 31))

    prev_from, prev_to = _previous_period(date(2026, 1, 12), date(2026, 1, 18))
    assert (prev_from, prev_to) == (date(2026, 1, 5), date(2026, 1, 11))


@pytest.mark.asyncio
async def test_fetch_flagged_stats_filters(db_session: AsyncSession):
    """AC-06/AC-07: Fetch flagged sessions with proper filtering."""
    from cashpilot.api.routes.flagged_sessions import _fetch_flagged_stats

    business_a = Business(
        id=uuid4(),
        name="Alpha",
        address="Street 1",
        phone="111",
        is_active=True,
    )
    business_b = Business(
        id=uuid4(),
        name="Beta",
        address="Street 2",
        phone="222",
        is_active=True,
    )
    cashier_one = User(
        id=uuid4(),
        email="cashier1@example.com",
        first_name="Cashier",
        last_name="One",
        hashed_password="hashed",
        role=UserRole.CASHIER,
        is_active=True,
    )
    cashier_two = User(
        id=uuid4(),
        email="cashier2@example.com",
        first_name="Cashier",
        last_name="Two",
        hashed_password="hashed",
        role=UserRole.CASHIER,
        is_active=True,
    )
    db_session.add_all([business_a, business_b, cashier_one, cashier_two])
    await db_session.flush()

    def make_session(
        business_id,
        cashier_id,
        session_date,
        flagged,
        session_number,
        is_deleted=False,
    ):
        return CashSession(
            id=uuid4(),
            business_id=business_id,
            cashier_id=cashier_id,
            session_number=session_number,
            status="CLOSED",
            session_date=session_date,
            opened_time=time(9, 0),
            closed_time=time(17, 0),
            initial_cash=Decimal("100.00"),
            final_cash=Decimal("200.00"),
            flagged=flagged,
            flag_reason="Mismatch" if flagged else None,
            is_deleted=is_deleted,
        )

    sessions = [
        make_session(business_a.id, cashier_one.id, date(2026, 1, 12), True, 1),
        make_session(business_a.id, cashier_one.id, date(2026, 1, 13), True, 2),
        make_session(business_a.id, cashier_one.id, date(2026, 1, 14), False, 3),
        make_session(business_a.id, cashier_two.id, date(2026, 1, 15), True, 4),
        make_session(business_b.id, cashier_two.id, date(2026, 1, 16), True, 5),
        make_session(business_a.id, cashier_one.id, date(2026, 1, 17), True, 6, True),
        make_session(business_a.id, cashier_one.id, date(2026, 1, 20), True, 7),
    ]
    db_session.add_all(sessions)
    await db_session.commit()

    stats = await _fetch_flagged_stats(
        db_session,
        date(2026, 1, 12),
        date(2026, 1, 18),
        business_a.id,
        None,
    )

    assert stats["total_sessions"] == 4
    assert stats["total_flagged"] == 3
    assert stats["days_with_flags"] == 3
    assert stats["cashiers_with_flags"] == 2
    assert stats["flag_rate_percent"] == 75.0

    cashier_stats = await _fetch_flagged_stats(
        db_session,
        date(2026, 1, 12),
        date(2026, 1, 18),
        business_a.id,
        "Cashier One",
    )

    assert cashier_stats["total_sessions"] == 3
    assert cashier_stats["total_flagged"] == 2
    assert cashier_stats["days_with_flags"] == 2
    assert cashier_stats["cashiers_with_flags"] == 1
    assert cashier_stats["flag_rate_percent"] == 66.7

    token_stats = await _fetch_flagged_stats(
        db_session,
        date(2026, 1, 12),
        date(2026, 1, 18),
        business_a.id,
        "Cashier  One",
    )

    assert token_stats["total_sessions"] == 3
    assert token_stats["total_flagged"] == 2
