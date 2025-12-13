# File: tests/test_cashier_timeout.py
import asyncio
from types import SimpleNamespace
from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException

from cashpilot.api.auth import get_current_user, CASHIER_TIMEOUT
from tests.factories import UserFactory
from cashpilot.core.security import hash_password


@pytest.mark.asyncio
async def test_cashier_session_not_expired_updates_last_activity(db_session):
    # Create a cashier user
    user = await UserFactory.create(
        db_session,
        email="cashier_timeout_ok@example.com",
        first_name="Cashier",
        last_name="User",
        role="CASHIER",
        hashed_password=hash_password("pass1234"),
    )

    # Prepare session with recent activity
    recent = datetime.now() - timedelta(seconds=CASHIER_TIMEOUT // 2)
    request = SimpleNamespace(
        session={
            "user_id": str(user.id),
            "user_role": "CASHIER",
            "last_activity": recent.isoformat(),
        }
    )

    # Should not raise; should return the user and refresh last_activity
    result_user = await get_current_user(request, db=db_session)
    assert result_user.id == user.id
    assert "last_activity" in request.session
    refreshed = datetime.fromisoformat(request.session["last_activity"])
    # refreshed timestamp should be close to now
    assert (datetime.now() - refreshed) < timedelta(seconds=2)


@pytest.mark.asyncio
async def test_cashier_session_expired_redirects_to_login(db_session):
    # Create a cashier user
    user = await UserFactory.create(
        db_session,
        email="cashier_timeout_expired@example.com",
        first_name="Cashier",
        last_name="User",
        role="CASHIER",
        hashed_password=hash_password("pass1234"),
    )

    # Prepare session with old activity beyond timeout
    old = datetime.now() - timedelta(seconds=CASHIER_TIMEOUT + 5)
    session_store = {
        "user_id": str(user.id),
        "user_role": "CASHIER",
        "last_activity": old.isoformat(),
    }
    request = SimpleNamespace(session=session_store)

    # Expect HTTPException with 302 and Location header to /login?expired=1
    with pytest.raises(HTTPException) as excinfo:
        await get_current_user(request, db=db_session)

    exc = excinfo.value
    assert exc.status_code == 302
    assert exc.headers.get("Location") == "/login?expired=1"
    # session should be cleared
    assert request.session == {}
