"""Tests for Weekly Trend PDF export endpoints."""

from datetime import date
from uuid import uuid4
import re

import pytest

from cashpilot.models import Business


@pytest.mark.asyncio
async def test_weekly_trend_pdf_view_returns_html(admin_client):
    response = await admin_client.get("/reports/weekly-trend/pdf-view?lang=es")
    assert response.status_code == 200
    assert "Reporte semanal" in response.text


@pytest.mark.asyncio
async def test_weekly_trend_pdf_filename_includes_business_and_hash(admin_client, monkeypatch):
    db_session = admin_client.db_session
    business = Business(
        id=uuid4(),
        name="Farmacia Zulmi Suc 2",
        address="Test Address",
        phone="000",
        is_active=True,
    )
    db_session.add(business)
    await db_session.commit()

    async def fake_render_pdf_from_url(**kwargs):
        return b"%PDF-1.4"

    monkeypatch.setattr(
        "cashpilot.api.routes.reports.render_pdf_from_url",
        fake_render_pdf_from_url,
    )

    response = await admin_client.get(
        "/reports/weekly-trend/pdf",
        params={
            "year": 2026,
            "week": 4,
            "business_id": str(business.id),
            "lang": "es",
        },
    )
    assert response.status_code == 200
    disposition = response.headers.get("Content-Disposition", "")
    assert "attachment;" in disposition

    match = re.search(r'filename="([^"]+)"', disposition)
    assert match
    filename = match.group(1)

    week_start = date.fromisocalendar(2026, 4, 1)
    week_end = date.fromisocalendar(2026, 4, 7)
    expected_prefix = (
        f"farmacia-zulmi-suc-2-weekly-report_{week_start:%m-%d}_to_{week_end:%m-%d}_"
    )
    assert filename.startswith(expected_prefix)
    assert filename.endswith(".pdf")

    hash_part = filename.rsplit("_", 1)[-1].replace(".pdf", "")
    assert re.fullmatch(r"[0-9a-f]{6}", hash_part)
