"""Validation tests for close session HTML form endpoint."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import BusinessFactory, CashSessionFactory


@pytest.mark.asyncio
async def test_close_session_overflow_returns_400_not_500(
    admin_client: AsyncClient, db_session: AsyncSession
):
    """Overflow values should return validation response instead of server error."""
    business = await BusinessFactory.create(db_session)
    session = await CashSessionFactory.create(
        db_session,
        business_id=business.id,
        created_by=admin_client.test_user.id,
        status="OPEN",
    )

    response = await admin_client.post(
        f"/sessions/{session.id}",
        data={
            "final_cash": "500000",
            "envelope_amount": "0",
            "card_total": "0",
            "credit_sales_total": "10000000000.00",
            "credit_payments_collected": "0",
            "closed_time": "18:00",
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert "Close Cash Session" in response.text
    assert "Currency value too large" in response.text

    await db_session.refresh(session)
    assert session.status == "OPEN"
