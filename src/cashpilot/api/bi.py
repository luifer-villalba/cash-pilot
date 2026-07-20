"""Read-only BI integration API.

Reuses the existing report endpoints' logic (weekly/monthly/daily revenue trend,
reconciliation) under a separate `/api/bi` prefix, gated by a service bearer
token (see `service_auth.py`) instead of the human session cookie. Intended for
a single trusted internal consumer (e.g. a BI assistant), not a public API.

None of the underlying report functions use `current_user` for filtering or
scoping — it's only used as an auth gate on the human-facing routes — so it's
safe to call them here with `current_user=None`.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cashpilot.api.daily_revenue import get_daily_revenue
from cashpilot.api.monthly_trend import get_monthly_trend
from cashpilot.api.reconciliation import get_daily_reconciliations, get_reconciliation_compare
from cashpilot.api.routes.business_stats import (
    METRIC_KEYS,
    aggregate_business_metrics,
    build_business_metrics,
    derive_margin_and_mix,
)
from cashpilot.api.routes.flagged_sessions import cashier_name_filters, fetch_flagged_stats
from cashpilot.api.service_auth import get_service_token
from cashpilot.api.utils import get_active_businesses
from cashpilot.api.weekly_trend import get_weekly_trend
from cashpilot.core.db import get_db
from cashpilot.models import CashSession
from cashpilot.models.report_schemas import (
    DailyRevenueSummary,
    MonthlyRevenueTrend,
    WeeklyRevenueTrend,
)
from cashpilot.services.report_utils import calculate_delta, calculate_previous_period

router = APIRouter(
    prefix="/api/bi",
    tags=["bi"],
    dependencies=[Depends(get_service_token)],
)

# BI callers pass explicit from/to dates rather than named views, so a single sanity
# check on range size replaces the "view" based validation used by the human reports.
MAX_BI_RANGE_DAYS = 366


def _validate_date_range(from_date: date, to_date: date) -> None:
    if from_date > to_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="from_date must be before or equal to to_date",
        )
    if (to_date - from_date).days > MAX_BI_RANGE_DAYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Date range cannot exceed {MAX_BI_RANGE_DAYS} days",
        )


@router.get("/weekly-trend", response_model=WeeklyRevenueTrend)
async def bi_weekly_trend(
    year: int = Query(..., ge=2020, le=2100),
    week: int = Query(..., ge=1, le=53),
    business_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> WeeklyRevenueTrend:
    return await get_weekly_trend(
        year=year, week=week, business_id=business_id, current_user=None, db=db
    )


@router.get("/monthly-trend", response_model=MonthlyRevenueTrend)
async def bi_monthly_trend(
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
    business_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> MonthlyRevenueTrend:
    return await get_monthly_trend(
        year=year, month=month, business_id=business_id, current_user=None, db=db
    )


@router.get("/daily-revenue", response_model=DailyRevenueSummary)
async def bi_daily_revenue(
    business_id: str = Query(...),
    date_param: date | None = Query(None, alias="date"),
    db: AsyncSession = Depends(get_db),
) -> DailyRevenueSummary:
    return await get_daily_revenue(
        date_param=date_param, business_id=business_id, current_user=None, db=db
    )


@router.get("/reconciliation/compare", response_model=list[dict])
async def bi_reconciliation_compare(
    business_id: UUID | None = Query(None),
    date_param: date | None = Query(None, alias="date"),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    return await get_reconciliation_compare(
        business_id=business_id, date=date_param, current_user=None, db=db
    )


@router.get("/reconciliation/daily", response_model=list[dict])
async def bi_reconciliation_daily(
    business_id: UUID | None = Query(None),
    date_param: date | None = Query(None, alias="date"),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    return await get_daily_reconciliations(
        business_id=business_id, date=date_param, current_user=None, db=db
    )


@router.get("/businesses", response_model=list[dict])
async def bi_businesses(db: AsyncSession = Depends(get_db)) -> list[dict]:
    """List active business locations, so a BI consumer can enumerate business_id values.

    There is no human-facing JSON equivalent of this endpoint — the admin UI only
    renders an HTML business list — so this is BI-only.
    """
    businesses = await get_active_businesses(db)
    return [
        {
            "id": str(b.id),
            "name": b.name,
            "address": b.address,
            "phone": b.phone,
            "is_active": b.is_active,
        }
        for b in businesses
    ]


@router.get("/business-stats", response_model=dict)
async def bi_business_stats(
    from_date: date = Query(...),
    to_date: date = Query(...),
    business_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Aggregated per-business financial stats for a date range.

    Cash profit, gross margin, payment-method mix, and session counts (open/closed/
    needs-review), each compared against the immediately preceding period of equal
    length. This is the richest cross-business report in the app and previously only
    existed as an admin-only HTML dashboard (`/reports/business-stats`).
    """
    _validate_date_range(from_date, to_date)
    prev_from, prev_to = calculate_previous_period(from_date, to_date)

    # Sequential, not gathered: both calls share this request-scoped AsyncSession,
    # and SQLAlchemy async sessions don't support concurrent operations on one
    # connection (asyncpg raises "another operation is in progress").
    current_metrics = await aggregate_business_metrics(db, from_date, to_date)
    previous_metrics = await aggregate_business_metrics(db, prev_from, prev_to)

    businesses = await get_active_businesses(db)
    if business_id:
        businesses = [b for b in businesses if b.id == business_id]

    results = []
    totals_current = {key: Decimal("0") for key in METRIC_KEYS}
    totals_previous = {key: Decimal("0") for key in METRIC_KEYS}

    for business in businesses:
        bid = str(business.id)
        current, previous, deltas = build_business_metrics(
            current_metrics.get(bid, {}), previous_metrics.get(bid, {})
        )
        results.append(
            {
                "business_id": bid,
                "business_name": business.name,
                "current": current,
                "previous": previous,
                "deltas": deltas,
            }
        )
        for key in METRIC_KEYS:
            if key.startswith("sessions_") or key == "invoice_count":
                totals_current[key] = Decimal(str(int(totals_current[key]) + int(current[key])))
                totals_previous[key] = Decimal(str(int(totals_previous[key]) + int(previous[key])))
            else:
                totals_current[key] += current[key]
                totals_previous[key] += previous[key]

    results.sort(key=lambda r: r["current"]["total_sales"], reverse=True)

    derive_margin_and_mix(totals_current)
    derive_margin_and_mix(totals_previous)
    totals_deltas = {
        key: calculate_delta(totals_current[key], totals_previous[key])
        for key in METRIC_KEYS
        if key != "payment_method_mix"
    }

    return {
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "previous_from_date": prev_from.isoformat(),
        "previous_to_date": prev_to.isoformat(),
        "businesses": results,
        "totals": {
            "current": totals_current,
            "previous": totals_previous,
            "deltas": totals_deltas,
        },
    }


@router.get("/flagged-sessions", response_model=dict)
async def bi_flagged_sessions(
    from_date: date = Query(...),
    to_date: date = Query(...),
    business_id: UUID | None = Query(None),
    cashier_name: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Flagged (discrepancy) cash sessions for a date range.

    Returns aggregate stats (flag rate, days/cashiers with flags) compared against the
    immediately preceding period, plus the individual flagged sessions with business,
    cashier, and discrepancy detail. Previously only existed as an admin-only HTML
    report (`/reports/flagged-sessions`).
    """
    _validate_date_range(from_date, to_date)
    prev_from, prev_to = calculate_previous_period(from_date, to_date)
    authorized_ids = [business_id] if business_id else None

    # Sequential, not gathered: see the comment in bi_business_stats above.
    stats_current = await fetch_flagged_stats(
        db, from_date, to_date, business_id, cashier_name, authorized_ids
    )
    stats_previous = await fetch_flagged_stats(
        db, prev_from, prev_to, business_id, cashier_name, authorized_ids
    )

    stmt = (
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
    if business_id:
        stmt = stmt.where(CashSession.business_id == business_id)
    if cashier_name:
        name_filter = cashier_name_filters(cashier_name)
        if name_filter is not None:
            stmt = stmt.where(name_filter)

    stmt = stmt.order_by(CashSession.session_date.asc())
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    flagged_items = []
    for s in sessions:
        discrepancy = None
        if s.final_cash is not None:
            discrepancy = float(s.final_cash - s.initial_cash - s.cash_sales)
        flagged_items.append(
            {
                "session_id": str(s.id),
                "business_id": str(s.business_id),
                "business_name": s.business.name,
                "cashier_name": s.cashier.display_name,
                "session_date": s.session_date.isoformat(),
                "status": s.status,
                "initial_cash": float(s.initial_cash),
                "final_cash": float(s.final_cash) if s.final_cash is not None else None,
                "discrepancy": discrepancy,
                "flag_reason": s.flag_reason,
                "flagged_by": s.flagged_by,
            }
        )

    return {
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "previous_from_date": prev_from.isoformat(),
        "previous_to_date": prev_to.isoformat(),
        "stats_current": stats_current,
        "stats_previous": stats_previous,
        "flagged_sessions": flagged_items,
    }
