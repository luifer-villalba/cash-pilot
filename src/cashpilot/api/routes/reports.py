# File: src/cashpilot/api/routes/reports.py
"""Reports routes (HTML endpoints)."""

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.api.auth_helpers import require_admin
from cashpilot.api.utils import (
    format_datetime_business,
    format_time_business,
    get_locale,
    get_translation_function,
)
from cashpilot.core.db import get_db
from cashpilot.core.logging import get_logger
from cashpilot.models import Business, User

logger = get_logger(__name__)

TEMPLATES_DIR = Path("/app/templates")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.filters["format_time_business"] = format_time_business
templates.env.filters["format_datetime_business"] = format_datetime_business

router = APIRouter(prefix="/reports", tags=["reports"])


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
            "enabled": False,
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
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Daily revenue summary report page. Admin only."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    # Get all active businesses
    stmt = select(Business).where(Business.is_active).order_by(Business.name)
    result = await db.execute(stmt)
    businesses = result.scalars().all()

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
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Weekly revenue trend report page. Admin only."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    # Get all active businesses
    stmt = select(Business).where(Business.is_active).order_by(Business.name)
    result = await db.execute(stmt)
    businesses = result.scalars().all()

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
