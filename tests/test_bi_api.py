# File: tests/test_bi_api.py
"""Tests for the read-only BI integration API (/api/bi/*)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.core.db import get_db
from cashpilot.main import create_app
from tests.factories import BusinessFactory, CashSessionFactory

BI_TOKEN = "test-bi-token"


@pytest.fixture(autouse=True)
def _bi_token_env(monkeypatch):
    monkeypatch.setenv("BI_READONLY_TOKEN", BI_TOKEN)


@pytest.fixture
async def bi_client(db_session: AsyncSession):
    """Async client with the DB dependency overridden, no session cookie (service-token auth)."""
    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


def _auth_headers(token: str = BI_TOKEN) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_bi_endpoints_require_valid_token(bi_client: AsyncClient):
    resp = await bi_client.get("/api/bi/businesses")
    assert resp.status_code == 401

    resp = await bi_client.get("/api/bi/businesses", headers=_auth_headers("wrong-token"))
    assert resp.status_code == 401

    resp = await bi_client.get("/api/bi/businesses", headers=_auth_headers())
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_bi_businesses_lists_active_businesses(
    bi_client: AsyncClient, db_session: AsyncSession
):
    active = await BusinessFactory.create(db_session, name="Sucursal Activa")
    await BusinessFactory.create(db_session, name="Sucursal Inactiva", is_active=False)

    resp = await bi_client.get("/api/bi/businesses", headers=_auth_headers())
    assert resp.status_code == 200
    body = resp.json()
    names = {b["name"] for b in body}
    assert "Sucursal Activa" in names
    assert "Sucursal Inactiva" not in names
    assert any(b["id"] == str(active.id) for b in body)


@pytest.mark.asyncio
async def test_bi_business_stats_aggregates_and_filters_by_business(
    bi_client: AsyncClient, db_session: AsyncSession
):
    business_a = await BusinessFactory.create(db_session, name="Business A")
    business_b = await BusinessFactory.create(db_session, name="Business B")
    today = date.today()

    await CashSessionFactory.create(
        db_session,
        business_id=business_a.id,
        session_date=today,
        status="CLOSED",
        initial_cash=Decimal("100000.00"),
        final_cash=Decimal("150000.00"),
        card_total=Decimal("20000.00"),
    )
    await CashSessionFactory.create(
        db_session,
        business_id=business_b.id,
        session_date=today,
        status="CLOSED",
        initial_cash=Decimal("50000.00"),
        final_cash=Decimal("80000.00"),
    )

    resp = await bi_client.get(
        "/api/bi/business-stats",
        params={"from_date": today.isoformat(), "to_date": today.isoformat()},
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert {b["business_id"] for b in body["businesses"]} == {
        str(business_a.id),
        str(business_b.id),
    }
    assert "totals" in body and "current" in body["totals"]

    resp_filtered = await bi_client.get(
        "/api/bi/business-stats",
        params={
            "from_date": today.isoformat(),
            "to_date": today.isoformat(),
            "business_id": str(business_a.id),
        },
        headers=_auth_headers(),
    )
    assert resp_filtered.status_code == 200
    filtered_body = resp_filtered.json()
    assert len(filtered_body["businesses"]) == 1
    assert filtered_body["businesses"][0]["business_id"] == str(business_a.id)


@pytest.mark.asyncio
async def test_bi_business_stats_rejects_inverted_range(bi_client: AsyncClient):
    today = date.today()
    resp = await bi_client.get(
        "/api/bi/business-stats",
        params={
            "from_date": today.isoformat(),
            "to_date": (today - timedelta(days=1)).isoformat(),
        },
        headers=_auth_headers(),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_bi_flagged_sessions_returns_flagged_detail(
    bi_client: AsyncClient, db_session: AsyncSession
):
    business = await BusinessFactory.create(db_session, name="Flagged Business")
    today = date.today()

    await CashSessionFactory.create(
        db_session,
        business_id=business.id,
        session_date=today,
        status="CLOSED",
        initial_cash=Decimal("100000.00"),
        final_cash=Decimal("90000.00"),
        flagged=True,
        flag_reason="Cash shortage",
    )
    await CashSessionFactory.create(
        db_session,
        business_id=business.id,
        session_date=today,
        status="CLOSED",
        initial_cash=Decimal("100000.00"),
        final_cash=Decimal("100000.00"),
        flagged=False,
    )

    resp = await bi_client.get(
        "/api/bi/flagged-sessions",
        params={"from_date": today.isoformat(), "to_date": today.isoformat()},
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["stats_current"]["total_flagged"] == 1
    assert len(body["flagged_sessions"]) == 1
    assert body["flagged_sessions"][0]["flag_reason"] == "Cash shortage"
    assert body["flagged_sessions"][0]["business_id"] == str(business.id)
