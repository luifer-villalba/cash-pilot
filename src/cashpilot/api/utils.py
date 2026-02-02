# File: src/cashpilot/api/utils.py
"""Frontend routes - dashboard only. Session/business routes moved to routes/."""

import gettext
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from cashpilot.core.validators import validate_currency
from cashpilot.models import Business, CashSession, User, UserRole
from cashpilot.utils.datetime import now_utc, utc_to_business

TEMPLATES_DIR = Path("/app/templates")


# Define filter BEFORE templates initialization
def format_currency_py(value):
    """Format number as es-PY currency (dots for thousands, no decimals)."""
    if value is None:
        return "0"
    if not isinstance(value, (int, float, Decimal)):
        return "0"
    if value == 0:
        return "0"

    from babel.numbers import format_decimal

    return format_decimal(value, locale="es_PY", group_separator=".")


# Shared Jinja2Templates instance - import this in other modules instead of creating new instances
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
TRANSLATIONS_DIR = Path("/app/translations")

# Register all custom Jinja2 filters in the shared instance
templates.env.filters["format_currency_py"] = format_currency_py


def format_time_business(dt: datetime | None) -> str:
    """Format datetime in business timezone as HH:MM.

    Converts UTC datetime to business timezone and formats as time only.
    Returns empty string if dt is None.
    """
    if dt is None:
        return ""
    if dt.tzinfo is None:
        # If naive, assume UTC
        dt = dt.replace(tzinfo=now_utc().tzinfo)
    business_dt = utc_to_business(dt)
    return business_dt.strftime("%H:%M")


def format_datetime_business(dt: datetime | None, format_str: str = "%d/%m/%Y %H:%M") -> str:
    """Format datetime in business timezone.

    Converts UTC datetime to business timezone and formats it.
    Returns empty string if dt is None.

    Args:
        dt: Timezone-aware datetime in UTC
        format_str: Format string (default: '%d/%m/%Y %H:%M')
    """
    if dt is None:
        return ""
    if dt.tzinfo is None:
        # If naive, assume UTC
        dt = dt.replace(tzinfo=now_utc().tzinfo)
    business_dt = utc_to_business(dt)
    return business_dt.strftime(format_str)


def format_date_business(dt: datetime | None, format_str: str = "%Y-%m-%d") -> str:
    """Format date from datetime in business timezone.

    Converts UTC datetime to business timezone and formats as date only.
    Returns empty string if dt is None.

    Args:
        dt: Timezone-aware datetime in UTC
        format_str: Format string (default: '%Y-%m-%d')
    """
    if dt is None:
        return ""
    if dt.tzinfo is None:
        # If naive, assume UTC
        dt = dt.replace(tzinfo=now_utc().tzinfo)
    business_dt = utc_to_business(dt)
    return business_dt.strftime(format_str)


# Register timezone-related filters in the shared instance
templates.env.filters["format_time_business"] = format_time_business
templates.env.filters["format_datetime_business"] = format_datetime_business
templates.env.filters["format_date_business"] = format_date_business

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
    # Validate input
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    if not value.strip():
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

    # After cleaning, check if valid
    if not value or value == "." or value == "":
        return None

    try:
        return Decimal(value)
    except (ValueError, InvalidOperation):
        return None


async def _build_session_filters(
    from_date: str | None,
    to_date: str | None,
    cashier_name: str | None,
    business_id: str | None,
    status: str | None,
    current_user: User,
    include_deleted: bool = False,
) -> tuple[list, bool]:
    """Build SQLAlchemy filter list from query params.

    Cashier sees only own sessions.
    Admin sees all sessions.

    Returns:
        Tuple of (filters list, include_deleted flag)
    """
    filters = []

    # Role-based filter
    filters.append(_build_role_filter(current_user))

    # Date filters
    if from_date:
        filters.append(_parse_from_date(from_date))
    if to_date:
        filters.append(_parse_to_date(to_date))

    # Text/enum filters
    if cashier_name and cashier_name.strip():
        # Search by cashier user relationship
        filters.append(User.email.ilike(f"%{cashier_name}%"))
    if business_id and business_id.strip():
        filters.append(_parse_business_id(business_id))
    if status and status.strip():
        filters.append(_parse_status(status))

    # Deleted filter (only exclude if not including deleted)
    # Note: This filter will be added in _get_paginated_sessions if needed
    # We return a flag here instead

    return [f for f in filters if f is not None], include_deleted


def _build_role_filter(current_user: User):
    """Build role-based access filter."""
    if current_user.role == UserRole.CASHIER:
        return CashSession.cashier_id == current_user.id
    return None


def _parse_from_date(from_date: str):
    """Parse from_date query param."""
    if from_date is None:
        return None
    if not isinstance(from_date, str):
        return None
    if not from_date.strip():
        return None

    try:
        from_dt = datetime.fromisoformat(from_date).date()
        return CashSession.session_date >= from_dt
    except (ValueError, TypeError, AttributeError):
        return None


def _parse_to_date(to_date: str):
    """Parse to_date query param."""
    if to_date is None:
        return None
    if not isinstance(to_date, str):
        return None
    if not to_date.strip():
        return None

    try:
        to_dt = datetime.fromisoformat(to_date).date()
        return CashSession.session_date <= to_dt
    except (ValueError, TypeError, AttributeError):
        return None


def _parse_business_id(business_id: str):
    """Parse business_id query param."""
    if business_id is None:
        return None
    if not isinstance(business_id, str):
        return None
    if not business_id.strip():
        return None

    try:
        return CashSession.business_id == UUID(business_id)
    except (ValueError, TypeError):
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
    include_deleted: bool = False,
    sort_by: str = "date",
    sort_order: str = "desc",
    group_by_business_for_single_day: bool = False,
) -> tuple[list, int, int]:
    """Fetch paginated sessions with filters. Returns (sessions, total_count, total_pages).

    Args:
        order_clauses.append(
            User.first_name.desc() if sort_order == "desc" else User.first_name.asc()
        )
        order_clauses.append(
            User.last_name.desc() if sort_order == "desc" else User.last_name.asc()
        )
        sort_order: Sort direction ('asc' or 'desc')
    """
    skip = (page - 1) * per_page

    stmt = (
        select(CashSession)
        .join(CashSession.business)
        .options(
            selectinload(CashSession.business),
            selectinload(CashSession.cashier),
        )
    )
    count_stmt = select(func.count(CashSession.id)).join(CashSession.business, isouter=True)

    # Add deleted filter only if not including deleted
    if not include_deleted:
        filters.append(~CashSession.is_deleted)

    # If filtering by cashier_name, join User table
    has_cashier_filter = any(
        hasattr(f, "left")
        and hasattr(f.left, "table")
        and getattr(f.left.table, "name", None) == "users"
        for f in filters
    )
    if has_cashier_filter:
        stmt = stmt.join(CashSession.cashier)
        count_stmt = count_stmt.join(CashSession.cashier, isouter=True)

    for f in filters:
        stmt = stmt.where(f)
        count_stmt = count_stmt.where(f)

    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0
    total_pages = (total + per_page - 1) // per_page

    # Determine sort order
    order_clauses = []
    if group_by_business_for_single_day:
        order_clauses.append(Business.name.desc() if sort_order == "desc" else Business.name.asc())
        order_clauses.extend([CashSession.session_date.asc(), CashSession.opened_time.asc()])
        stmt = stmt.order_by(*order_clauses).offset(skip).limit(per_page)
        result = await db.execute(stmt)
        sessions = result.scalars().all()
        return list(sessions), total, total_pages

    if sort_by == "business":
        order_clauses.append(Business.name.desc() if sort_order == "desc" else Business.name.asc())
        # Secondary sort by date
        order_clauses.extend([CashSession.session_date.desc(), CashSession.opened_time.desc()])
    elif sort_by == "cashier":
        stmt = stmt.join(CashSession.cashier)
        count_stmt = count_stmt.join(CashSession.cashier, isouter=True)
        order_clauses.append(
            User.first_name.desc() if sort_order == "desc" else User.first_name.asc()
        )
        order_clauses.append(
            User.last_name.desc() if sort_order == "desc" else User.last_name.asc()
        )
        order_clauses.extend([CashSession.session_date.desc(), CashSession.opened_time.desc()])
        # Salir aquí para evitar doble append
        stmt = stmt.order_by(*order_clauses).offset(skip).limit(per_page)
        result = await db.execute(stmt)
        sessions = result.scalars().all()
        return list(sessions), total, total_pages
    elif sort_by == "status":
        order_clauses.append(
            CashSession.status.desc() if sort_order == "desc" else CashSession.status.asc()
        )
        order_clauses.extend([CashSession.session_date.desc(), CashSession.opened_time.desc()])
    elif sort_by == "sales":
        # Sort by total_sales calculation (requires case expression)
        sales_expr = (
            (CashSession.final_cash - CashSession.initial_cash)
            + func.coalesce(CashSession.envelope_amount, 0)
            + func.coalesce(CashSession.expenses, 0)
            - func.coalesce(CashSession.credit_payments_collected, 0)
            + func.coalesce(CashSession.card_total, 0)
            + func.coalesce(CashSession.bank_transfer_total, 0)
            + func.coalesce(CashSession.credit_sales_total, 0)
        )
        order_clauses.append(sales_expr.desc() if sort_order == "desc" else sales_expr.asc())
    elif sort_by == "date":
        if sort_order == "asc":
            order_clauses.extend([CashSession.session_date.asc(), CashSession.opened_time.asc()])
        else:
            order_clauses.extend([CashSession.session_date.desc(), CashSession.opened_time.desc()])
    else:
        # fallback: sort by date desc
        order_clauses.extend([CashSession.session_date.desc(), CashSession.opened_time.desc()])

    stmt = stmt.order_by(*order_clauses).offset(skip).limit(per_page)
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    return list(sessions), total, total_pages


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Render login page with i18n support."""
    locale = get_locale(request)
    gettext_func = get_translation_function(locale)

    error = request.query_params.get("error")
    expired = request.query_params.get("expired")

    # Render template with translation function
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "_": gettext_func,
            "error": error,
            "expired": expired,
        },
    )


async def get_session_or_redirect(session_id: str, db: AsyncSession):
    """Fetch session or return None (caller handles redirect)."""
    try:
        session_uuid = UUID(session_id)
    except (ValueError, TypeError):
        return None

    stmt = (
        select(CashSession)
        .options(joinedload(CashSession.business))
        .where(CashSession.id == session_uuid)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _get_session_calculations(session: CashSession) -> dict:
    """Calculate session financials."""
    final_cash = session.final_cash or Decimal("0")
    envelope = session.envelope_amount or Decimal("0")
    bank = session.bank_transfer_total or Decimal("0")
    expenses = session.expenses or Decimal("0")
    credit_payments = session.credit_payments_collected or Decimal("0")
    card_total = session.card_total or Decimal("0")
    credit_sales = session.credit_sales_total or Decimal("0")

    # Align with dashboard stats: cash sales include bank transfers and expenses.
    cash_sales = (final_cash - session.initial_cash) + envelope + expenses - credit_payments + bank
    total_sales = cash_sales + card_total + credit_sales
    return {
        "net_cash_movement": cash_sales,
        "net_earnings": total_sales - expenses,
        "cash_profit": cash_sales - expenses,
        "cash_sales": cash_sales,
        "card_payments_total": card_total,
        "credit_sales_total": credit_sales,
        "total_sales": total_sales,
    }


async def get_active_businesses(db: AsyncSession) -> list:
    """Fetch active businesses sorted by name."""
    stmt = select(Business).where(Business.is_active).order_by(Business.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_assigned_businesses(
    current_user: User,
    db: AsyncSession,
) -> list[Business]:
    """Fetch businesses assigned to the user (AC-01, AC-02).

    For Admins (superadmin): returns all active businesses.
    For Cashiers: returns only assigned businesses via UserBusiness.

    Sorted by business name.
    """
    # Admin sees all active businesses
    if current_user.role == UserRole.ADMIN:
        return await get_active_businesses(db)

    # Cashier sees only assigned businesses
    from cashpilot.models.user_business import UserBusiness

    stmt = (
        select(Business)
        .join(UserBusiness)
        .where((UserBusiness.user_id == current_user.id) & (Business.is_active))
        .order_by(Business.name)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_open_session_fields(
    session: CashSession,
    initial_cash: str | None,
    credit_sales_total: str | None,
    credit_payments_collected: str | None,
    opened_time: str | None,
    notes: str | None,
) -> tuple[list[str], dict, dict]:
    """Track field changes for open session edit."""
    changed_fields = []
    old_values, new_values = {}, {}

    # Currency fields with parse_currency
    currency_fields = {
        "initial_cash": initial_cash,
        "credit_sales_total": credit_sales_total,
        "credit_payments_collected": credit_payments_collected,
    }

    for field_name, form_value in currency_fields.items():
        if form_value:
            parsed_value = parse_currency(form_value) or Decimal("0")
            # Validate that the value doesn't exceed NUMERIC(12, 2) limit
            validate_currency(parsed_value)
            current_value = getattr(session, field_name)
            if parsed_value != current_value:
                old_values[field_name] = str(current_value)
                new_values[field_name] = str(parsed_value)
                setattr(session, field_name, parsed_value)
                changed_fields.append(field_name)

    # Opened time (special handling)
    if opened_time:
        opened_time_val = datetime.strptime(opened_time, "%H:%M").time()
        if opened_time_val != session.opened_time:
            old_values["opened_time"] = session.opened_time.isoformat()
            new_values["opened_time"] = opened_time_val.isoformat()
            session.opened_time = opened_time_val
            changed_fields.append("opened_time")

    # Notes (special handling for empty string)
    if notes is not None and notes != "":
        if notes != session.notes:
            old_values["notes"] = session.notes or ""
            new_values["notes"] = notes
            session.notes = notes
            changed_fields.append("notes")
    elif notes == "" and session.notes:
        old_values["notes"] = session.notes
        new_values["notes"] = ""
        session.notes = ""
        changed_fields.append("notes")

    return changed_fields, old_values, new_values


def _can_edit_closed_session(session: CashSession, current_user: User) -> bool:
    """Check if current user can edit a closed session (32-hour window for cashiers)."""
    if current_user.role == UserRole.ADMIN:
        return True

    if session.status != "CLOSED":
        return False

    if session.cashier_id != current_user.id:
        return False

    # Check if closed_time exists (required for closed sessions)
    if not session.closed_time:
        # Session is closed but has no closed_time (shouldn't happen normally)
        return False

    # Use closed_at property (combines session_date + closed_time with timezone)
    closed_at = session.closed_at
    if not closed_at:
        # closed_at property returned None (timezone issue?),
        # but closed_time exists, so allow editing (session was just closed)
        return True

    time_since_close = now_utc() - closed_at
    return time_since_close <= timedelta(hours=32)


def _update_field(
    session: CashSession,
    field_name: str,
    new_value: Decimal | str | None,
    current_value: Decimal | str | None,
    changed_fields: list[str],
    old_values: dict,
    new_values: dict,
) -> None:
    """Update a single field and track changes."""
    if new_value is None:
        return

    new_val_str = str(new_value) if new_value else None
    current_val_str = str(current_value) if current_value else None

    if new_val_str != current_val_str:
        changed_fields.append(field_name)
        old_values[field_name] = current_val_str
        new_values[field_name] = new_val_str
        setattr(session, field_name, new_value)


async def update_closed_session_fields(
    session: CashSession,
    initial_cash: str | None = None,
    final_cash: str | None = None,
    envelope_amount: str | None = None,
    card_total: str | None = None,
    credit_sales_total: str | None = None,
    credit_payments_collected: str | None = None,
    closing_ticket: str | None = None,
    notes: str | None = None,
) -> tuple[list[str], dict, dict]:
    """Track field changes for closed session edit."""
    changed_fields = []
    old_values = {}
    new_values = {}

    # Parse and validate currency fields
    initial_cash_val = parse_currency(initial_cash) if initial_cash else None
    if initial_cash_val is not None:
        validate_currency(initial_cash_val)

    final_cash_val = parse_currency(final_cash) if final_cash else None
    if final_cash_val is not None:
        validate_currency(final_cash_val)

    envelope_amount_val = parse_currency(envelope_amount) or Decimal("0")
    validate_currency(envelope_amount_val)

    card_total_val = parse_currency(card_total) or Decimal("0")
    validate_currency(card_total_val)

    credit_sales_total_val = parse_currency(credit_sales_total) or Decimal("0")
    validate_currency(credit_sales_total_val)

    credit_payments_collected_val = parse_currency(credit_payments_collected) or Decimal("0")
    validate_currency(credit_payments_collected_val)

    _update_field(
        session,
        "initial_cash",
        initial_cash_val,
        session.initial_cash,
        changed_fields,
        old_values,
        new_values,
    )
    _update_field(
        session,
        "final_cash",
        final_cash_val,
        session.final_cash,
        changed_fields,
        old_values,
        new_values,
    )
    _update_field(
        session,
        "envelope_amount",
        envelope_amount_val,
        session.envelope_amount,
        changed_fields,
        old_values,
        new_values,
    )
    _update_field(
        session,
        "card_total",
        card_total_val,
        session.card_total,
        changed_fields,
        old_values,
        new_values,
    )
    _update_field(
        session,
        "credit_sales_total",
        credit_sales_total_val,
        session.credit_sales_total,
        changed_fields,
        old_values,
        new_values,
    )
    _update_field(
        session,
        "credit_payments_collected",
        credit_payments_collected_val,
        session.credit_payments_collected,
        changed_fields,
        old_values,
        new_values,
    )
    _update_field(
        session,
        "closing_ticket",
        closing_ticket,
        session.closing_ticket,
        changed_fields,
        old_values,
        new_values,
    )
    _update_field(session, "notes", notes, session.notes, changed_fields, old_values, new_values)

    return changed_fields, old_values, new_values
