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
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.api.daily_revenue import get_daily_revenue
from cashpilot.api.monthly_trend import get_monthly_trend
from cashpilot.api.reconciliation import get_daily_reconciliations, get_reconciliation_compare
from cashpilot.api.service_auth import get_service_token
from cashpilot.api.weekly_trend import get_weekly_trend
from cashpilot.core.db import get_db
from cashpilot.models.report_schemas import (
    DailyRevenueSummary,
    MonthlyRevenueTrend,
    WeeklyRevenueTrend,
)

router = APIRouter(
    prefix="/api/bi",
    tags=["bi"],
    dependencies=[Depends(get_service_token)],
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
