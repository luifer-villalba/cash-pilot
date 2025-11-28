"""Frontend routes - dashboard only. Session/business routes moved to routes/."""

import gettext
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import selectinload
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from typing import Sequence

from cashpilot.models import Business, CashSession, User, UserRole

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
        cashier_name: str | None,  # Still accept this param
        business_id: str | None,
        status: str | None,
        current_user: User,
) -> list:
    """Build SQLAlchemy filters for session queries."""
    from cashpilot.models.user import User, UserRole

    filters = [~CashSession.is_deleted]

    # Role-based filtering
    if current_user.role == UserRole.CASHIER:
        filters.append(CashSession.cashier_id == current_user.id)

    # Date filters
    if from_date:
        filters.append(CashSession.session_date >= from_date)
    if to_date:
        filters.append(CashSession.session_date <= to_date)

    # Cashier name filter (now joins User table)
    if cashier_name:
        filters.append(
            or_(
                User.first_name.ilike(f"%{cashier_name}%"),
                User.last_name.ilike(f"%{cashier_name}%"),
                User.email.ilike(f"%{cashier_name}%"),
            )
        )

    # Business filter
    if business_id:
        filters.append(CashSession.business_id == UUID(business_id))

    # Status filter
    if status:
        filters.append(CashSession.status == status)

    return filters


def _build_role_filter(current_user: User):
    """Build role-based access filter."""
    if current_user.role == UserRole.CASHIER:
        return CashSession.created_by == current_user.id
    return None


def _parse_from_date(from_date: str):
    """Parse from_date query param."""
    try:
        from_dt = datetime.fromisoformat(from_date).date()
        return CashSession.session_date >= from_dt
    except ValueError:
        return None


def _parse_to_date(to_date: str):
    """Parse to_date query param."""
    try:
        to_dt = datetime.fromisoformat(to_date).date()
        return CashSession.session_date <= to_dt
    except ValueError:
        return None


def _parse_business_id(business_id: str):
    """Parse business_id query param."""
    try:
        return CashSession.business_id == UUID(business_id)
    except ValueError:
        return None


def _parse_status(status: str):
    """Parse status query param."""
    if status in ("OPEN", "CLOSED"):
        return CashSession.status == status
    return None


async def _get_paginated_sessions(
        db: AsyncSession,
        filters: list,
        page: int = 1,
        per_page: int = 10,
) -> tuple[list[CashSession], int, int]:
    """Get paginated sessions with filters."""
    from cashpilot.models.user import User

    # Count total matching sessions
    count_stmt = select(func.count(CashSession.id))

    # If filtering by cashier name, need to join User
    has_user_filter = any(
        hasattr(f, 'left') and hasattr(f.left, 'table') and
        getattr(f.left.table, 'name', None) == 'users'
        for f in filters
    )

    if has_user_filter:
        count_stmt = count_stmt.join(User, CashSession.cashier_id == User.id)

    count_stmt = count_stmt.where(and_(*filters))
    result = await db.execute(count_stmt)
    total_sessions = result.scalar() or 0

    # Calculate pagination
    total_pages = (total_sessions + per_page - 1) // per_page
    offset = (page - 1) * per_page

    # Fetch paginated sessions with eager loading of cashier
    stmt = (
        select(CashSession)
        .options(selectinload(CashSession.cashier))  # Eager load cashier
        .options(selectinload(CashSession.business))  # Eager load business
    )

    if has_user_filter:
        stmt = stmt.join(User, CashSession.cashier_id == User.id)

    stmt = stmt.where(and_(*filters))
    stmt = stmt.order_by(CashSession.session_date.desc(), CashSession.opened_time.desc())
    stmt = stmt.offset(offset).limit(per_page)

    result = await db.execute(stmt)
    sessions = list(result.scalars().all())

    return sessions, total_sessions, total_pages


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


async def update_open_session_fields(
        session: CashSession,
        initial_cash: str | None,
        opened_time: str | None,
        notes: str | None,  # Changed from expenses
) -> tuple[list[str], dict, dict]:
    """Update OPEN session fields and track changes for audit."""
    changed_fields = []
    old_values = {}
    new_values = {}

    # Helper to track changes
    def _update_field(field_name, new_value, old_value):
        if new_value is not None and new_value != old_value:
            changed_fields.append(field_name)
            old_values[field_name] = str(old_value) if old_value is not None else None
            new_values[field_name] = str(new_value)
            setattr(session, field_name, new_value)

    # REMOVED: cashier_name (immutable)

    if initial_cash:
        _update_field("initial_cash", parse_currency(initial_cash), session.initial_cash)

    if opened_time:
        from datetime import time as time_type
        parsed_time = time_type.fromisoformat(opened_time)
        _update_field("opened_time", parsed_time, session.opened_time)

    if notes is not None:
        _update_field("notes", notes, session.notes)

    return changed_fields, old_values, new_values
