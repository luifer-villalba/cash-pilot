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

from cashpilot.models import Business, CashSession

TEMPLATES_DIR = Path("/app/templates")


# Define filter BEFORE templates initialization
def format_currency_py(value):
    """Format number as es-PY currency (dots for thousands, no decimals)."""
    if value is None or value == 0:
        return "0"

    from babel.numbers import format_decimal

    return format_decimal(value, locale="es_PY", group_separator=".")


templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
TRANSLATIONS_DIR = Path("/app/translations")

# Register custom Jinja2 filter
templates.env.filters["format_currency_py"] = format_currency_py

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
    status: str | None,
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

    if status and status.strip():
        if status in ("OPEN", "CLOSED"):  # Validate enum values
            filters.append(CashSession.status == status)

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

    # Add deleted filter
    filters.append(~CashSession.is_deleted)

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
async def login_page(request: Request):
    """Render login page with i18n support."""
    locale = get_locale(request)
    gettext_func = get_translation_function(locale)

    error = request.query_params.get("error")

    # Render template with translation function
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "_": gettext_func,
            "error": error,
        },
    )


async def get_session_or_redirect(session_id: str, db: AsyncSession):
    """Fetch session or return None (caller handles redirect)."""
    stmt = (
        select(CashSession)
        .options(joinedload(CashSession.business))
        .where(CashSession.id == UUID(session_id))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _get_session_calculations(session: CashSession) -> dict:
    """Calculate session financials."""
    final_cash = session.final_cash or Decimal("0")
    envelope = session.envelope_amount or Decimal("0")
    bank = session.bank_transfer_total or Decimal("0")
    expenses = session.expenses or Decimal("0")
    return {
        "net_cash_movement": final_cash - session.initial_cash + envelope + bank,
        "net_earnings": (final_cash - session.initial_cash + envelope + bank) - expenses,
        "cash_profit": (final_cash - session.initial_cash + envelope) - expenses,
    }


async def get_active_businesses(db: AsyncSession) -> list:
    """Fetch active businesses sorted by name."""
    stmt = select(Business).where(Business.is_active).order_by(Business.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# File: src/cashpilot/api/utils.py (add this function)


async def update_open_session_fields(
    session: CashSession,
    cashier_name: str | None,
    initial_cash: str | None,
    opened_time: str | None,
    expenses: str | None,
) -> tuple[list[str], dict, dict]:
    from datetime import datetime
    from decimal import Decimal

    changed_fields = []
    old_values, new_values = {}, {}

    if cashier_name and cashier_name.strip() != session.cashier_name:
        old_values["cashier_name"] = session.cashier_name
        new_values["cashier_name"] = cashier_name.strip()
        session.cashier_name = cashier_name.strip()
        changed_fields.append("cashier_name")

    if initial_cash:
        initial_cash_val = parse_currency(initial_cash)
        if initial_cash_val != session.initial_cash:
            old_values["initial_cash"] = str(session.initial_cash)
            new_values["initial_cash"] = str(initial_cash_val)
            session.initial_cash = initial_cash_val
            changed_fields.append("initial_cash")

    if opened_time:
        opened_time_val = datetime.strptime(opened_time, "%H:%M").time()
        if opened_time_val != session.opened_time:
            old_values["opened_time"] = session.opened_time.isoformat()
            new_values["opened_time"] = opened_time_val.isoformat()
            session.opened_time = opened_time_val
            changed_fields.append("opened_time")

    if expenses is not None:
        expenses_val = parse_currency(expenses) if expenses else Decimal("0")
        if expenses_val != (session.expenses or Decimal("0")):
            old_values["expenses"] = str(session.expenses or "0")
            new_values["expenses"] = str(expenses_val)
            session.expenses = expenses_val
            changed_fields.append("expenses")

    return changed_fields, old_values, new_values
