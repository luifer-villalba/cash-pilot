# File: src/cashpilot/api/utils.py
"""Frontend routes - dashboard only. Session/business routes moved to routes/."""

import gettext
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from cashpilot.models import CashSession

TEMPLATES_DIR = Path("/app/templates")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
TRANSLATIONS_DIR = Path("/app/translations")

router = APIRouter(tags=["frontend"])


def get_locale(request: Request) -> str:
    """Get locale from query param (?lang=es) or Accept-Language header. Default: en."""
    lang = request.query_params.get("lang", "").lower()
    if lang in ["es", "en"]:
        return lang

    accept_lang = request.headers.get("accept-language", "").split(",")[0].split("-")[0].lower()
    if accept_lang == "es":
        return "es"

    return "en"


def get_translation_function(locale: str):
    """Get gettext translation function for locale."""
    if locale == "es":
        try:
            translation = gettext.translation(
                "messages",
                localedir=str(TRANSLATIONS_DIR),
                languages=["es_PY"],
                fallback=True,
            )
            return translation.gettext
        except Exception:
            return lambda x: x
    return lambda x: x


def parse_currency(value: str | None) -> Decimal | None:
    """Parse Paraguay currency format (5.000.000 → 5000000 or 750000.00 → 750000.00)."""
    if not value or not value.strip():
        return None

    value = value.strip()

    # Handle decimal point: split on last dot
    if "." in value:
        parts = value.rsplit(".", 1)
        integer_part = parts[0].replace(".", "").replace(",", "")
        decimal_part = parts[1].replace(",", "")

        # If decimal part is 2 digits, it's a decimal; if 3+ it's thousands sep
        if len(decimal_part) <= 2:
            value = f"{integer_part}.{decimal_part}"
        else:
            # Last dot was thousands separator, remove all dots
            value = value.replace(".", "").replace(",", "")
    else:
        # No dots, just remove commas
        value = value.replace(",", "")

    if not value or value == ".":
        return None

    return Decimal(value)


async def _build_session_filters(
    from_date: str | None,
    to_date: str | None,
    cashier_name: str | None,
    business_id: str | None,
) -> list:
    """Build SQLAlchemy filter list from query params."""
    filters = []

    if from_date:
        try:
            from_dt = datetime.fromisoformat(from_date).date()
            filters.append(CashSession.session_date >= from_dt)
        except ValueError:
            pass

    if to_date:
        try:
            to_dt = datetime.fromisoformat(to_date).date()
            filters.append(CashSession.session_date <= to_dt)
        except ValueError:
            pass

    if cashier_name and cashier_name.strip():
        filters.append(CashSession.cashier_name.ilike(f"%{cashier_name}%"))

    if business_id and business_id.strip():
        try:
            filters.append(CashSession.business_id == UUID(business_id))
        except ValueError:
            pass

    return filters


async def _get_paginated_sessions(
    db: AsyncSession,
    filters: list,
    page: int = 1,
    per_page: int = 10,
) -> tuple[list, int, int]:
    """Fetch paginated sessions with filters. Returns (sessions, total_count, total_pages)."""
    skip = (page - 1) * per_page

    stmt = select(CashSession).options(joinedload(CashSession.business))
    count_stmt = select(func.count(CashSession.id))

    for f in filters:
        stmt = stmt.where(f)
        count_stmt = count_stmt.where(f)

    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0
    total_pages = (total + per_page - 1) // per_page

    stmt = (
        stmt.order_by(CashSession.session_date.desc(), CashSession.opened_time.desc())
        .offset(skip)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    sessions = result.scalars().unique().all()

    return list(sessions), total, total_pages


@router.get("/login", response_class=HTMLResponse)
async def login_page():
    """Render login page (publicly accessible)."""
    template_path = Path("/app/templates/login.html")
    with open(template_path, "r") as f:
        return f.read()
