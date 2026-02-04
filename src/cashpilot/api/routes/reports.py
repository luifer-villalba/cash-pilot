# File: src/cashpilot/api/routes/reports.py
"""Reports routes (HTML endpoints)."""

import secrets
import unicodedata
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.api.auth import get_current_user
from cashpilot.api.auth_helpers import require_admin
from cashpilot.api.utils import (
    get_assigned_businesses,
    get_locale,
    get_translation_function,
    templates,
)
from cashpilot.core.db import get_db
from cashpilot.core.logging import get_logger
from cashpilot.core.report_pdf import get_internal_base_url, render_pdf_from_url
from cashpilot.models import Business, User

logger = get_logger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


def slugify_filename(value: str, max_length: int = 24) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = []
    prev_dash = False
    for char in ascii_text.lower():
        if char.isalnum():
            cleaned.append(char)
            prev_dash = False
        else:
            if not prev_dash:
                cleaned.append("-")
                prev_dash = True
    slug = "".join(cleaned).strip("-")
    if max_length and len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    return slug or "business"


@router.get("", response_class=HTMLResponse)
async def reports_dashboard(
    request: Request,
    current_user: User = Depends(require_admin),
):
    """Reports dashboard landing page. Admin only."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    # Define all 10 reports (placeholder structure)
    reports = [
        {
            "id": "daily-revenue",
            "title": _("Daily Revenue Summary"),
            "description": _("Total sales by payment method, net earnings, and discrepancy counts"),
            "enabled": True,
            "icon": (
                "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"  # noqa: E501
            ),
        },
        {
            "id": "flagged-sessions",
            "title": _("Flagged Cash Sessions"),
            "description": _("Review flagged sessions by business, cashier, and date"),
            "enabled": True,
            "icon": (
                "M12 9v3m0 4h.01M5.07 20h13.86c1.54 0 2.5-1.67 1.73-3"
                "L13.73 4c-.77-1.33-2.69-1.33-3.46 0L3.34 17c-.77 1.33.19 3 "
                "1.73 3z"
            ),
        },
        {
            "id": "weekly-trend",
            "title": _("Weekly Revenue Trend"),
            "description": _(
                "Compare daily revenue across 7-day spans to identify peak/low days "
                "and week-over-week growth patterns"
            ),
            "enabled": True,
            "icon": "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6",
        },
        {
            "id": "monthly-trend",
            "title": _("Monthly Revenue Trend"),
            "description": _(
                "Compare monthly revenue across 30-day spans to identify "
                "peak/low days and month-over-month growth patterns"
            ),
            "enabled": True,
            "icon": (
                "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 "
                "2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 "
                "9 0 11-18 0 9 9 0 0118 0z"
            ),
        },
        {
            "id": "business-stats",
            "title": _("Business Statistics"),
            "description": _("Multi-business statistics dashboard with daily metrics comparison"),
            "enabled": True,
            "icon": (
                "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"  # noqa: E501
            ),
        },
        {
            "id": "business-comparison",
            "title": _("Business Comparison"),
            "description": _("Compare performance across multiple business locations"),
            "enabled": False,
            "icon": (
                "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"  # noqa: E501
            ),
        },
    ]

    return templates.TemplateResponse(
        "reports/dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "reports": reports,
            "locale": locale,
            "_": _,
        },
    )


@router.get("/daily-revenue", response_class=HTMLResponse)
async def daily_revenue_report(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Daily revenue summary report page (AC-01, AC-02).

    Admin sees all businesses.
    Cashier sees only assigned businesses.
    """
    locale = get_locale(request)
    _ = get_translation_function(locale)

    # Filter businesses by user role (AC-01, AC-02)
    businesses = await get_assigned_businesses(current_user, db)

    logger.info(
        f"Daily revenue report accessed by {current_user.display_name}, "
        f"found {len(businesses)} businesses"
    )

    return templates.TemplateResponse(
        "reports/daily-revenue.html",
        {
            "request": request,
            "current_user": current_user,
            "businesses": businesses,
            "locale": locale,
            "_": _,
        },
    )


@router.get("/weekly-trend", response_class=HTMLResponse)
async def weekly_trend_report(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Weekly revenue trend report page (AC-01, AC-02).

    Admin sees all businesses.
    Cashier sees only assigned businesses.
    """
    locale = get_locale(request)
    _ = get_translation_function(locale)

    # Filter businesses by user role (AC-01, AC-02)
    businesses = await get_assigned_businesses(current_user, db)

    logger.info(
        f"Weekly trend report accessed by {current_user.display_name}, "
        f"found {len(businesses)} businesses"
    )

    return templates.TemplateResponse(
        "reports/weekly-trend.html",
        {
            "request": request,
            "current_user": current_user,
            "businesses": businesses,
            "locale": locale,
            "_": _,
        },
    )


@router.get("/weekly-trend/pdf")
async def weekly_trend_report_pdf(
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Generate weekly trend report PDF (admin only)."""
    locale = get_locale(request)
    year_param = request.query_params.get("year")
    week_param = request.query_params.get("week")
    business_id_raw = request.query_params.get("business_id")
    if not year_param or not week_param or not business_id_raw:
        raise HTTPException(status_code=400, detail="year, week, and business_id are required")

    try:
        year = int(year_param)
        week = int(week_param)
        week_start = date.fromisocalendar(year, week, 1)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid year or week") from exc

    try:
        business_id = str(UUID(str(business_id_raw)))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid business_id") from exc

    week_end = date.fromisocalendar(year, week, 7)
    export_hash = secrets.token_hex(3)
    business = await db.execute(select(Business).where(Business.id == business_id))
    business_obj = business.scalar_one_or_none()
    business_slug = slugify_filename(
        business_obj.name if business_obj else "business", max_length=24
    )
    filename = (
        f"{business_slug}-weekly-report_{week_start:%m-%d}_to_{week_end:%m-%d}_"
        f"{export_hash}.pdf"
    )

    base_url = get_internal_base_url(str(request.base_url))
    pdf_url = (
        f"{base_url}/reports/weekly-trend/pdf-view?"
        f"year={year}&week={week}&business_id={business_id}&pdf=1&lang={locale}"
    )
    session_cookie = request.cookies.get("session")
    if locale == "es":
        page_label = "Pagina"
        of_label = "de"
    else:
        page_label = "Page"
        of_label = "of"
    footer_template = (
        '<div style="font-size:10px; width:100%; text-align:right; padding-right:12mm;">'
        f'{page_label} <span class="pageNumber"></span> {of_label} '
        '<span class="totalPages"></span>'
        "</div>"
    )

    logger.info(
        "weekly_trend_pdf_requested",
        user_id=str(current_user.id),
        business_id=business_id,
        year=year,
        week=week,
    )

    pdf_bytes = await render_pdf_from_url(
        url=pdf_url,
        base_url=base_url,
        session_cookie=session_cookie,
        footer_template=footer_template,
        locale="es-ES" if locale == "es" else "en-US",
        wait_selector="#pdfRoot",
        wait_for_flag=(
            "window.reportReady === true && window.reportChartsReady === true && "
            "Array.from(document.querySelectorAll('canvas')).every("
            "c => c.dataset.rendered === 'true' && c.width > 0 && c.height > 0)"
        ),
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/weekly-trend/pdf-view", response_class=HTMLResponse)
async def weekly_trend_report_pdf_view(
    request: Request,
    current_user: User = Depends(require_admin),
):
    """Weekly trend PDF view (layout-only template)."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    return templates.TemplateResponse(
        "reports/weekly-trend-pdf.html",
        {
            "request": request,
            "current_user": current_user,
            "locale": locale,
            "_": _,
        },
    )


@router.get("/monthly-trend", response_class=HTMLResponse)
async def monthly_trend_report(
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Monthly revenue trend report page. Admin only."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    # Get all active businesses
    stmt = select(Business).where(Business.is_active).order_by(Business.name)
    result = await db.execute(stmt)
    businesses = result.scalars().all()

    logger.info(
        f"Monthly trend report accessed by {current_user.display_name}, "
        f"found {len(businesses)} businesses"
    )

    return templates.TemplateResponse(
        "reports/monthly-trend.html",
        {
            "request": request,
            "current_user": current_user,
            "businesses": businesses,
            "locale": locale,
            "_": _,
        },
    )
