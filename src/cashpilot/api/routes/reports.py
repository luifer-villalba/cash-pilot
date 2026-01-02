# File: src/cashpilot/api/routes/reports.py
"""Reports routes (HTML endpoints)."""

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.api.auth_helpers import require_admin
from cashpilot.api.utils import get_locale, get_translation_function
from cashpilot.core.db import get_db
from cashpilot.models import Business, User

TEMPLATES_DIR = Path("/app/templates")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

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
            "id": "cash-flow",
            "title": _("Cash Flow"),
            "description": _("Track cash inflows and outflows over time"),
            "enabled": False,
            "icon": (
                "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"  # noqa: E501
            ),
        },
        {
            "id": "revenue-analysis",
            "title": _("Revenue Analysis"),
            "description": _("Breakdown of revenue by payment method and category"),
            "enabled": False,
            "icon": (
                "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"  # noqa: E501
            ),
        },
        {
            "id": "expense-tracking",
            "title": _("Expense Tracking"),
            "description": _("Monitor and categorize business expenses"),
            "enabled": False,
            "icon": (
                "M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"  # noqa: E501
            ),
        },
        {
            "id": "session-performance",
            "title": _("Session Performance"),
            "description": _("Analyze cashier and session performance metrics"),
            "enabled": False,
            "icon": "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6",
        },
        {
            "id": "payment-methods",
            "title": _("Payment Methods"),
            "description": _("Distribution of payments by method (cash, card, transfer)"),
            "enabled": False,
            "icon": (
                "M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"  # noqa: E501
            ),
        },
        {
            "id": "discrepancies",
            "title": _("Discrepancies"),
            "description": _("Report on cash discrepancies and flagged sessions"),
            "enabled": False,
            "icon": (
                "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"  # noqa: E501
            ),
        },
        {
            "id": "credit-sales",
            "title": _("Credit Sales"),
            "description": _("Track credit sales and payment collections"),
            "enabled": False,
            "icon": (
                "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"  # noqa: E501
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
        {
            "id": "audit-trail",
            "title": _("Audit Trail"),
            "description": _("Complete history of session changes and edits"),
            "enabled": False,
            "icon": (
                "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"  # noqa: E501
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
    stmt = select(Business).where(Business.is_active is True).order_by(Business.name)
    result = await db.execute(stmt)
    businesses = result.scalars().all()

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
