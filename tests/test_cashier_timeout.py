# File: tests/test_cashier_timeout.py
import asyncio
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone  # timezone is correctly imported

import pytest
from fastapi import HTTPException

from cashpilot.api.auth import get_current_user, ROLE_TIMEOUTS
from cashpilot.models.user import UserRole
from tests.factories import UserFactory
from cashpilot.core.security import hash_password

# Import now_utc_naive for consistency in test setup (optional, but good practice)
from cashpilot.utils.datetime import now_utc_naive


@pytest.mark.asyncio
async def test_cashier_session_not_expired_updates_last_activity(db_session):
    user = await UserFactory.create(
        db_session,
        email="cashier_timeout_ok@example.com",
        first_name="Cashier",
        last_name="User",
        role="CASHIER",
        hashed_password=hash_password("pass1234"),
    )

    cashier_timeout = ROLE_TIMEOUTS[UserRole.CASHIER]
    # Use now_utc_naive() for consistency with the application logic for storing last_activity
    recent_naive = now_utc_naive() - timedelta(seconds=cashier_timeout // 2)

    request = SimpleNamespace(
        session={
            "user_id": str(user.id),
            "user_role": UserRole.CASHIER,
            # Store naive time, matching application behavior
            "last_activity": recent_naive.isoformat(),
        },
        headers={},
    )

    result_user = await get_current_user(request, db=db_session)
    assert result_user.id == user.id
    assert "last_activity" in request.session

    # The application saves a naive datetime. We must load it as naive and convert to aware UTC for comparison.
    refreshed_naive = datetime.fromisoformat(request.session["last_activity"])
    refreshed_aware = refreshed_naive.replace(tzinfo=timezone.utc)

    # Compare aware time (now) with aware time (refreshed_aware)
    assert (datetime.now(timezone.utc) - refreshed_aware) < timedelta(seconds=2)


@pytest.mark.asyncio
async def test_cashier_session_expired_redirects_to_login(db_session):
    user = await UserFactory.create(
        db_session,
        email="cashier_timeout_expired@example.com",
        first_name="Cashier",
        last_name="User",
        role="CASHIER",
        hashed_password=hash_password("pass1234"),
    )

    cashier_timeout = ROLE_TIMEOUTS[UserRole.CASHIER]
    # Use now_utc_naive() for consistency
    old_naive = now_utc_naive() - timedelta(seconds=cashier_timeout + 5)

    session_store = {
        "user_id": str(user.id),
        "user_role": UserRole.CASHIER,
        # Store naive time
        "last_activity": old_naive.isoformat(),
    }
    request = SimpleNamespace(session=session_store, headers={})

    with pytest.raises(HTTPException) as excinfo:
        await get_current_user(request, db=db_session)

    exc = excinfo.value
    assert exc.status_code == 303
    assert exc.headers.get("Location") == "/login?expired=true"
    assert request.session == {}


@pytest.mark.asyncio
async def test_admin_session_not_expired_updates_last_activity(db_session):
    user = await UserFactory.create(
        db_session,
        email="admin_timeout_ok@example.com",
        first_name="Admin",
        last_name="User",
        role="ADMIN",
        hashed_password=hash_password("pass1234"),
    )

    admin_timeout = ROLE_TIMEOUTS[UserRole.ADMIN]
    # Use now_utc_naive() for consistency
    recent_naive = now_utc_naive() - timedelta(seconds=admin_timeout // 2)

    request = SimpleNamespace(
        session={
            "user_id": str(user.id),
            "user_role": UserRole.ADMIN,
            # Store naive time, matching application behavior
            "last_activity": recent_naive.isoformat(),
        },
        headers={},
    )

    result_user = await get_current_user(request, db=db_session)
    assert result_user.id == user.id
    assert "last_activity" in request.session

    # The application saves a naive datetime. We must load it as naive and convert to aware UTC for comparison.
    refreshed_naive = datetime.fromisoformat(request.session["last_activity"])
    refreshed_aware = refreshed_naive.replace(tzinfo=timezone.utc)

    # Compare aware time (now) with aware time (refreshed_aware)
    assert (datetime.now(timezone.utc) - refreshed_aware) < timedelta(seconds=2)


@pytest.mark.asyncio
async def test_admin_session_expired_redirects_to_login(db_session):
    user = await UserFactory.create(
        db_session,
        email="admin_timeout_expired@example.com",
        first_name="Admin",
        last_name="User",
        role="ADMIN",
        hashed_password=hash_password("pass1234"),
    )

    admin_timeout = ROLE_TIMEOUTS[UserRole.ADMIN]
    # Use now_utc_naive() for consistency
    old_naive = now_utc_naive() - timedelta(seconds=admin_timeout + 5)

    session_store = {
        "user_id": str(user.id),
        "user_role": UserRole.ADMIN,
        # Store naive time
        "last_activity": old_naive.isoformat(),
    }
    request = SimpleNamespace(session=session_store, headers={})

    with pytest.raises(HTTPException) as excinfo:
        await get_current_user(request, db=db_session)

    exc = excinfo.value
    assert exc.status_code == 303
    assert exc.headers.get("Location") == "/login?expired=true"
    assert request.session == {}
