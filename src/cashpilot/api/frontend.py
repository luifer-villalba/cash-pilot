# File: src/cashpilot/api/frontend.py
"""Frontend routes - dashboard only. Session/business routes moved to routes/."""

import gettext
from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from cashpilot.core.db import get_db
from cashpilot.models import Business, CashSession
from cashpilot.models.user import User

TEMPLATES_DIR = Path("/app/templates")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
TRANSLATIONS_DIR = Path("/app/translations")

router = APIRouter(tags=["frontend"])


# ========== HELPERS ==========


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


# ========== DASHBOARD ==========


@router.get("/login", response_class=HTMLResponse)
async def login_page():
    """Render login page (public)."""
    template_path = Path("/app/templates/login.html")
    with open(template_path, "r") as f:
        return f.read()


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


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    page: int = Query(1, ge=1),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    cashier_name: str | None = Query(None),
    business_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Dashboard with paginated, filterable session list."""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)

    locale = get_locale(request)
    _ = get_translation_function(locale)

    per_page = 10
    skip = (page - 1) * per_page

    # Build filters
    filters = await _build_session_filters(from_date, to_date, cashier_name, business_id)

    # Count + paginate
    stmt = select(CashSession).options(joinedload(CashSession.business))
    for f in filters:
        stmt = stmt.where(f)

    count_stmt = select(func.count(CashSession.id))
    for f in filters:
        count_stmt = count_stmt.where(f)
    count_result = await db.execute(count_stmt)
    total_sessions = count_result.scalar() or 0
    total_pages = (total_sessions + per_page - 1) // per_page

    stmt = (
        stmt.order_by(CashSession.session_date.desc(), CashSession.opened_time.desc())
        .offset(skip)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    sessions = result.scalars().unique().all()

    # Get stats
    stmt_active = select(func.count(CashSession.id)).where(CashSession.status == "OPEN")
    result_active = await db.execute(stmt_active)
    active_count = result_active.scalar() or 0

    stmt_businesses = select(Business).where(Business.is_active).order_by(Business.name)
    result_businesses = await db.execute(stmt_businesses)
    businesses = result_businesses.scalars().all()
    businesses_count = len(list(businesses))

    today = date_type.today()
    stmt_today = select(
        func.sum(
            CashSession.final_cash
            + CashSession.envelope_amount
            + CashSession.credit_card_total
            + CashSession.debit_card_total
            + CashSession.bank_transfer_total
            - CashSession.initial_cash
        )
    ).where(CashSession.session_date == today, CashSession.status == "CLOSED")
    result_today = await db.execute(stmt_today)
    total_revenue = result_today.scalar() or Decimal("0.00")

    active_filters = {
        k: v
        for k, v in {
            "from_date": from_date,
            "to_date": to_date,
            "cashier_name": cashier_name,
            "business_id": business_id,
        }.items()
        if v
    }

    current_user = None
    user_id = request.session.get("user_id")
    if user_id:
        stmt_user = select(User).where(User.id == UUID(user_id))
        result_user = await db.execute(stmt_user)
        current_user = result_user.scalar_one_or_none()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "current_user": current_user,
            "sessions": sessions,
            "active_sessions_count": active_count,
            "businesses_count": businesses_count,
            "businesses": businesses,
            "page": page,
            "total_pages": total_pages,
            "total_sessions": total_sessions,
            "total_revenue": total_revenue,
            "discrepancies_count": 0,
            "active_filters": active_filters,
            "current_filters": {
                "from_date": from_date,
                "to_date": to_date,
                "cashier_name": cashier_name,
                "business_id": business_id,
            },
            "locale": locale,
            "_": _,
        },
    )
