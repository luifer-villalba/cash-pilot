# File: src/cashpilot/api/routes/flagged_sessions.py
"""Flagged cash sessions report route (HTML)."""

from calendar import monthrange
from datetime import date, timedelta
from urllib.parse import quote_plus
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cashpilot.api.auth_helpers import require_admin
from cashpilot.api.utils import (
    get_active_businesses,
    get_locale,
    get_translation_function,
    templates,
)
from cashpilot.core.db import get_db
from cashpilot.core.logging import get_logger
from cashpilot.models import Business, CashSession, User
from cashpilot.utils.datetime import today_local

logger = get_logger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


def _this_week_range(today: date) -> tuple[date, date]:
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return start, end


def _last_week_range(today: date) -> tuple[date, date]:
    this_start, _ = _this_week_range(today)
    end = this_start - timedelta(days=1)
    start = end - timedelta(days=6)
    return start, end


def _this_month_range(today: date) -> tuple[date, date]:
    start = date(today.year, today.month, 1)
    end = date(today.year, today.month, monthrange(today.year, today.month)[1])
    return start, end


def _last_month_range(today: date) -> tuple[date, date]:
    year = today.year
    month = today.month - 1
    if month == 0:
        month = 12
        year -= 1
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])
    return start, end


def _resolve_date_range(range_key: str, today: date) -> tuple[date, date]:
    if range_key == "last_week":
        return _last_week_range(today)
    if range_key == "this_month":
        return _this_month_range(today)
    if range_key == "last_month":
        return _last_month_range(today)
    return _this_week_range(today)


def _previous_period(from_date: date, to_date: date) -> tuple[date, date]:
    duration = (to_date - from_date).days
    prev_to = from_date - timedelta(days=1)
    prev_from = prev_to - timedelta(days=duration)
    return prev_from, prev_to


def _format_period_label(from_date: date, to_date: date) -> str:
    return f"{from_date:%d/%m/%Y} - {to_date:%d/%m/%Y}"


def _build_delta(current: float, previous: float, unit: str = "") -> dict:
    delta = current - previous
    if delta > 0:
        direction = "up"
    elif delta < 0:
        direction = "down"
    else:
        direction = "flat"
    value = abs(delta)
    if unit == "pts":
        value = round(value, 1)
    return {
        "value": value,
        "raw": delta,
        "direction": direction,
        "unit": unit,
    }


async def _fetch_flagged_stats(
    db: AsyncSession,
    from_date: date,
    to_date: date,
    business_id: UUID | None,
    cashier_name: str | None,
) -> dict:
    filters = [
        CashSession.session_date >= from_date,
        CashSession.session_date <= to_date,
        ~CashSession.is_deleted,
    ]
    if business_id:
        filters.append(CashSession.business_id == business_id)

    stmt = select(
        func.count(CashSession.id).label("total_sessions"),
        func.sum(case((CashSession.flagged.is_(True), 1), else_=0)).label("flagged_sessions"),
        func.count(
            func.distinct(case((CashSession.flagged.is_(True), CashSession.session_date)))
        ).label("days_with_flags"),
        func.count(
            func.distinct(case((CashSession.flagged.is_(True), CashSession.cashier_id)))
        ).label("cashiers_with_flags"),
    ).select_from(CashSession)

    if cashier_name:
        ilike = f"%{cashier_name}%"
        stmt = stmt.join(CashSession.cashier).where(
            (User.first_name.ilike(ilike))
            | (User.last_name.ilike(ilike))
            | (User.email.ilike(ilike))
        )

    stmt = stmt.where(and_(*filters))

    result = await db.execute(stmt)
    row = result.one()
    total_sessions = int(row.total_sessions or 0)
    flagged_sessions = int(row.flagged_sessions or 0)
    days_with_flags = int(row.days_with_flags or 0)
    cashiers_with_flags = int(row.cashiers_with_flags or 0)
    flag_rate = round((flagged_sessions / total_sessions) * 100, 1) if total_sessions else 0.0

    return {
        "total_sessions": total_sessions,
        "total_flagged": flagged_sessions,
        "days_with_flags": days_with_flags,
        "cashiers_with_flags": cashiers_with_flags,
        "flag_rate_percent": flag_rate,
    }


@router.get("/flagged-sessions", response_class=HTMLResponse)
async def flagged_sessions_report(
    request: Request,
    range_key: str = Query("this_week", alias="range"),
    business_id: str | None = Query(None),
    cashier_name: str | None = Query(None),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Flagged cash sessions report page. Admin only."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    today = today_local()
    date_error = None
    if range_key not in {"this_week", "last_week", "this_month", "last_month"}:
        range_key = "this_week"
        date_error = _("Invalid date range. Please check your dates and try again.")

    from_date, to_date = _resolve_date_range(range_key, today)
    prev_from, prev_to = _previous_period(from_date, to_date)

    selected_business_id = None
    if business_id:
        try:
            selected_business_id = UUID(business_id)
        except (ValueError, TypeError):
            selected_business_id = None
            date_error = _("Invalid business selection.")

    cashier_name_clean = cashier_name.strip() if cashier_name else None

    stats_current = await _fetch_flagged_stats(
        db, from_date, to_date, selected_business_id, cashier_name_clean
    )
    stats_previous = await _fetch_flagged_stats(
        db, prev_from, prev_to, selected_business_id, cashier_name_clean
    )
    stats_delta = {
        "total_flagged": _build_delta(
            stats_current["total_flagged"], stats_previous["total_flagged"]
        ),
        "flag_rate_percent": _build_delta(
            stats_current["flag_rate_percent"], stats_previous["flag_rate_percent"], unit="pts"
        ),
        "days_with_flags": _build_delta(
            stats_current["days_with_flags"], stats_previous["days_with_flags"]
        ),
        "cashiers_with_flags": _build_delta(
            stats_current["cashiers_with_flags"], stats_previous["cashiers_with_flags"]
        ),
        "total_sessions": _build_delta(
            stats_current["total_sessions"], stats_previous["total_sessions"]
        ),
    }

    businesses = await get_active_businesses(db)

    stmt_sessions = (
        select(CashSession)
        .join(CashSession.business)
        .join(CashSession.cashier)
        .options(selectinload(CashSession.business), selectinload(CashSession.cashier))
        .where(
            CashSession.flagged.is_(True),
            CashSession.session_date >= from_date,
            CashSession.session_date <= to_date,
            ~CashSession.is_deleted,
        )
    )
    if selected_business_id:
        stmt_sessions = stmt_sessions.where(CashSession.business_id == selected_business_id)
    if cashier_name_clean:
        ilike = f"%{cashier_name_clean}%"
        stmt_sessions = stmt_sessions.where(
            (User.first_name.ilike(ilike))
            | (User.last_name.ilike(ilike))
            | (User.email.ilike(ilike))
        )

    stmt_sessions = stmt_sessions.order_by(
        Business.name.asc(),
        User.first_name.asc(),
        User.last_name.asc(),
        CashSession.session_date.asc(),
        CashSession.opened_time.asc(),
    )

    result_sessions = await db.execute(stmt_sessions)
    flagged_sessions = list(result_sessions.scalars().all())

    selected_business_id_str = str(selected_business_id) if selected_business_id else ""

    filter_params = []
    if selected_business_id_str:
        filter_params.append(f"business_id={selected_business_id_str}")
    if cashier_name_clean:
        filter_params.append(f"cashier_name={quote_plus(cashier_name_clean)}")
    filter_query = f"&{'&'.join(filter_params)}" if filter_params else ""

    logger.info(
        "flagged_sessions_report_accessed",
        user_id=str(current_user.id),
        range_key=range_key,
        business_id=str(selected_business_id) if selected_business_id else None,
        cashier_name=cashier_name_clean,
        flagged_count=len(flagged_sessions),
    )

    return templates.TemplateResponse(
        "reports/flagged-sessions.html",
        {
            "request": request,
            "current_user": current_user,
            "businesses": businesses,
            "flagged_sessions": flagged_sessions,
            "range_key": range_key,
            "from_date": from_date,
            "to_date": to_date,
            "previous_from_date": prev_from,
            "previous_to_date": prev_to,
            "current_period_label": _format_period_label(from_date, to_date),
            "previous_period_label": _format_period_label(prev_from, prev_to),
            "business_id": selected_business_id_str,
            "cashier_name": cashier_name_clean,
            "filter_query": filter_query,
            "stats_current": stats_current,
            "stats_previous": stats_previous,
            "stats_delta": stats_delta,
            "date_error": date_error,
            "locale": locale,
            "_": _,
        },
    )
