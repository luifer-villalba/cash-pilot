# File: src/cashpilot/api/reconciliation.py
"""Daily reconciliation API endpoints."""

import re
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.api.auth_helpers import require_admin
from cashpilot.api.utils import (
    get_active_businesses,
    get_locale,
    get_translation_function,
    parse_currency,
    templates,
)
from cashpilot.core.db import get_db
from cashpilot.core.errors import NotFoundError, ValidationError
from cashpilot.core.logging import get_logger
from cashpilot.core.validators import validate_currency
from cashpilot.models import DailyReconciliation, User
from cashpilot.models.daily_reconciliation_audit_log import DailyReconciliationAuditLog
from cashpilot.utils.datetime import now_utc, today_local

logger = get_logger(__name__)

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])


def parse_daily_cost_total(value: str | None) -> int | None:
    """Parse a daily cost total field supporting inline sums like 1000+2000."""
    if value is None or not isinstance(value, str):
        return None
    if not value.strip():
        return None

    if re.search(r"[^\d+\-.,\s]", value):
        raise ValueError("Daily cost total can only contain digits, +, -, commas, dots, and spaces")

    compact = re.sub(r"\s+", "", value)
    if re.search(r"[+\-]{2,}", compact) or re.search(r"[+\-]$", compact):
        raise ValueError("Daily cost total has an invalid operator sequence")

    parts = re.findall(r"[+\-]?\s*[\d.,]+", value)
    total = 0
    has_number = False
    for part in parts:
        cleaned = part.strip()
        if not cleaned:
            continue
        is_negative = cleaned.startswith("-")
        digits = re.sub(r"\D", "", cleaned)
        if digits:
            value_part = int(digits)
            total += -value_part if is_negative else value_part
            has_number = True

    return total if has_number else None


@router.get("/badge", response_class=HTMLResponse)
async def reconciliation_badge(
    request: Request,
    from_date: str | None = Query(None, description="From date in YYYY-MM-DD format"),
    to_date: str | None = Query(None, description="To date in YYYY-MM-DD format"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Return reconciliation badge HTML (HTMX endpoint).

    Handles both single date and date ranges:
    - Single date: Shows badge if reconciliation exists for that date
    - Date range: Shows badge with count of dates that have reconciliation
    """
    from datetime import timedelta

    locale = get_locale(request)
    _ = get_translation_function(locale)

    # Parse dates
    start_date = today_local()
    end_date = today_local()

    if from_date:
        try:
            start_date = datetime.fromisoformat(from_date).date()
        except (ValueError, TypeError):
            # Invalid date format in query param, fall back to today_local()
            pass

    if to_date:
        try:
            end_date = datetime.fromisoformat(to_date).date()
        except (ValueError, TypeError):
            # Invalid date format in query param, fall back to today_local()
            pass

    # Determine if it's a range or single date
    is_range = start_date != end_date

    if is_range:
        # Date range: count how many dates have reconciliation
        date_list = []
        current = start_date
        while current <= end_date:
            date_list.append(current)
            current += timedelta(days=1)

        # Count unique dates that have at least one reconciliation
        stmt_recon = select(func.distinct(DailyReconciliation.date)).where(
            and_(
                DailyReconciliation.date >= start_date,
                DailyReconciliation.date <= end_date,
                DailyReconciliation.deleted_at.is_(None),
            )
        )

        result_recon = await db.execute(stmt_recon)
        reconciled_dates_set = {row[0] for row in result_recon.all()}

        reconciled_dates = len(reconciled_dates_set)
        total_dates = len(date_list)

        if reconciled_dates > 0:
            # Show badge with count
            return templates.TemplateResponse(
                "partials/reconciliation_badge.html",
                {
                    "request": request,
                    "reconciliation_date": None,  # Range, not single date
                    "from_date": start_date.isoformat(),
                    "to_date": end_date.isoformat(),
                    "reconciled_count": reconciled_dates,
                    "total_count": total_dates,
                    "is_range": True,
                    "is_empty": False,
                    "is_partial": False,
                    "locale": locale,
                    "_": _,
                },
            )
        else:
            return templates.TemplateResponse(
                "partials/reconciliation_badge.html",
                {
                    "request": request,
                    "reconciliation_date": None,
                    "from_date": start_date.isoformat(),
                    "to_date": end_date.isoformat(),
                    "reconciled_count": 0,
                    "total_count": total_dates,
                    "is_range": True,
                    "is_empty": True,
                    "is_partial": False,
                    "locale": locale,
                    "_": _,
                },
            )
    else:
        # Single date: detect empty vs started vs reconciled
        check_date = end_date  # Use to_date (or from_date if to_date not set)

        stmt_recon = select(DailyReconciliation).where(
            and_(
                DailyReconciliation.date == check_date,
                DailyReconciliation.deleted_at.is_(None),
            )
        )
        result_recon = await db.execute(stmt_recon)
        reconciliations = result_recon.scalars().all()

        if not reconciliations:
            return templates.TemplateResponse(
                "partials/reconciliation_badge.html",
                {
                    "request": request,
                    "reconciliation_date": check_date.isoformat(),
                    "from_date": None,
                    "to_date": None,
                    "reconciled_count": None,
                    "total_count": None,
                    "is_range": False,
                    "is_empty": True,
                    "is_partial": False,
                    "locale": locale,
                    "_": _,
                },
            )

        active_businesses = await get_active_businesses(db)
        active_business_ids = {b.id for b in active_businesses}
        recon_by_business = {r.business_id: r for r in reconciliations}

        missing_businesses = active_business_ids - recon_by_business.keys()

        def has_sales_data(recon: DailyReconciliation) -> bool:
            return any(
                value is not None
                for value in (
                    recon.cash_sales,
                    recon.credit_sales,
                    recon.card_sales,
                    recon.total_sales,
                )
            )

        is_partial = False
        if missing_businesses:
            is_partial = True
        else:
            for recon in recon_by_business.values():
                if recon.is_closed:
                    continue
                if not has_sales_data(recon):
                    is_partial = True
                    break

        return templates.TemplateResponse(
            "partials/reconciliation_badge.html",
            {
                "request": request,
                "reconciliation_date": check_date.isoformat(),
                "from_date": None,
                "to_date": None,
                "reconciled_count": None,
                "total_count": None,
                "is_range": False,
                "is_empty": False,
                "is_partial": is_partial,
                "locale": locale,
                "_": _,
            },
        )


# Variance thresholds for flagging discrepancies
# Uses dual threshold approach (OR logic):
# - Absolute: 20,000 Gs (based on local practice in Paraguay)
# - Percentage: 2% (industry standard)
# Flags "Needs Review" if EITHER threshold is exceeded
ABSOLUTE_THRESHOLD = Decimal("20000.00")  # 20,000 guaraníes
VARIANCE_THRESHOLD = 2.0  # 2%


# ─────── FORM ENDPOINTS ────────


@router.get("/daily", response_class=HTMLResponse)
async def daily_reconciliation_form(
    request: Request,
    date: str | None = Query(None, description="Pre-fill date"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Form to create/edit daily reconciliation for multiple businesses."""
    locale = get_locale(request)
    _ = get_translation_function(locale)
    businesses = await get_active_businesses(db)

    # Pre-fill date or use today
    if date:
        try:
            selected_date_obj = datetime.fromisoformat(date).date()
            selected_date = selected_date_obj.isoformat()
        except (ValueError, TypeError):
            selected_date_obj = today_local()
            selected_date = selected_date_obj.isoformat()
    else:
        selected_date_obj = today_local()
        selected_date = selected_date_obj.isoformat()

    # Load existing reconciliations for this date
    stmt = select(DailyReconciliation).where(
        and_(
            DailyReconciliation.date == selected_date_obj,
            DailyReconciliation.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    existing_reconciliations = {str(r.business_id): r for r in result.scalars().all()}

    return templates.TemplateResponse(
        request,
        "reconciliation/daily_form.html",
        {
            "current_user": current_user,
            "businesses": businesses,
            "selected_date": selected_date,
            "existing_reconciliations": existing_reconciliations,
            "locale": locale,
            "_": _,
        },
    )


@router.post("/daily", response_class=HTMLResponse)
async def daily_reconciliation_post(
    request: Request,
    date: str = Form(...),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Handle daily reconciliation form submission (bulk create/update)."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    try:

        def has_sales_data(
            cash_sales_value: Decimal | None,
            credit_sales_value: Decimal | None,
            card_sales_value: Decimal | None,
            total_sales_value: Decimal | None,
        ) -> bool:
            return any(
                value is not None
                for value in (
                    cash_sales_value,
                    credit_sales_value,
                    card_sales_value,
                    total_sales_value,
                )
            )

        # Parse date
        try:
            if isinstance(date, str):
                reconciliation_date = datetime.fromisoformat(date).date()
            else:
                reconciliation_date = date
        except (ValueError, TypeError):
            raise ValidationError("Invalid date format")

        # Validate date is not future
        if reconciliation_date > today_local():
            raise ValidationError("Date cannot be in the future")

        # Get all active businesses
        businesses = await get_active_businesses(db)
        {str(b.id) for b in businesses}

        # Process form data for each business
        form_data = await request.form()
        created_count = 0
        updated_count = 0

        for business in businesses:
            business_id_str = str(business.id)
            is_closed_key = f"is_closed_{business_id_str}"
            is_closed = is_closed_key in form_data

            # Check if reconciliation already exists
            stmt = select(DailyReconciliation).where(
                and_(
                    DailyReconciliation.business_id == business.id,
                    DailyReconciliation.date == reconciliation_date,
                    DailyReconciliation.deleted_at.is_(None),
                )
            )
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()

            # Parse sales fields (only if not closed)
            cash_sales = None
            credit_sales = None
            card_sales = None
            total_sales = None
            daily_cost_total = None
            invoice_count = None

            daily_cost_total_val = form_data.get(f"daily_cost_total_{business_id_str}", "")
            daily_cost_total_str = (
                daily_cost_total_val if isinstance(daily_cost_total_val, str) else ""
            )
            daily_cost_total = (
                parse_daily_cost_total(daily_cost_total_str) if daily_cost_total_str else None
            )

            if not is_closed:
                cash_sales_val = form_data.get(f"cash_sales_{business_id_str}", "")
                credit_sales_val = form_data.get(f"credit_sales_{business_id_str}", "")
                card_sales_val = form_data.get(f"card_sales_{business_id_str}", "")
                total_sales_val = form_data.get(f"total_sales_{business_id_str}", "")
                invoice_count_val = form_data.get(f"invoice_count_{business_id_str}", "")

                cash_sales_str = cash_sales_val if isinstance(cash_sales_val, str) else ""
                credit_sales_str = credit_sales_val if isinstance(credit_sales_val, str) else ""
                card_sales_str = card_sales_val if isinstance(card_sales_val, str) else ""
                total_sales_str = total_sales_val if isinstance(total_sales_val, str) else ""
                invoice_count_str = invoice_count_val if isinstance(invoice_count_val, str) else ""

                cash_sales = parse_currency(cash_sales_str) if cash_sales_str else None
                credit_sales = parse_currency(credit_sales_str) if credit_sales_str else None
                card_sales = parse_currency(card_sales_str) if card_sales_str else None
                total_sales = parse_currency(total_sales_str) if total_sales_str else None
                invoice_count = (
                    int(invoice_count_str)
                    if invoice_count_str and invoice_count_str.strip()
                    else None
                )

                # Validate currency values don't exceed database limits
                if cash_sales is not None:
                    validate_currency(cash_sales)
                if credit_sales is not None:
                    validate_currency(credit_sales)
                if card_sales is not None:
                    validate_currency(card_sales)
                if total_sales is not None:
                    validate_currency(total_sales)

            if daily_cost_total is not None:
                validate_currency(Decimal(abs(daily_cost_total)))

            if existing:
                # Update existing reconciliation
                old_values = {
                    "cash_sales": str(existing.cash_sales) if existing.cash_sales else None,
                    "credit_sales": str(existing.credit_sales) if existing.credit_sales else None,
                    "card_sales": str(existing.card_sales) if existing.card_sales else None,
                    "total_sales": str(existing.total_sales) if existing.total_sales else None,
                    "daily_cost_total": (
                        str(existing.daily_cost_total)
                        if existing.daily_cost_total is not None
                        else None
                    ),
                    "invoice_count": existing.invoice_count,
                    "is_closed": existing.is_closed,
                }

                # Preserve existing sales data if not provided in form
                # This allows updating is_closed without re-entering all sales data
                if cash_sales is None:
                    cash_sales = existing.cash_sales
                if credit_sales is None:
                    credit_sales = existing.credit_sales
                if card_sales is None:
                    card_sales = existing.card_sales
                if total_sales is None:
                    total_sales = existing.total_sales
                if daily_cost_total is None:
                    daily_cost_total = existing.daily_cost_total
                if invoice_count is None:
                    invoice_count = existing.invoice_count

                if not is_closed and not has_sales_data(
                    cash_sales, credit_sales, card_sales, total_sales
                ):
                    raise ValidationError("Sales data is required when location is open")

                existing.cash_sales = cash_sales
                existing.credit_sales = credit_sales
                existing.card_sales = card_sales
                existing.total_sales = total_sales
                existing.daily_cost_total = daily_cost_total
                existing.invoice_count = invoice_count
                existing.is_closed = is_closed
                existing.last_modified_at = now_utc()
                existing.last_modified_by = current_user.display_name_email

                new_values = {
                    "cash_sales": str(cash_sales) if cash_sales else None,
                    "credit_sales": str(credit_sales) if credit_sales else None,
                    "card_sales": str(card_sales) if card_sales else None,
                    "total_sales": str(total_sales) if total_sales else None,
                    "daily_cost_total": (
                        str(daily_cost_total) if daily_cost_total is not None else None
                    ),
                    "invoice_count": invoice_count,
                    "is_closed": is_closed,
                }

                # Create audit log
                reason_val = form_data.get("reason", "Bulk update via form")
                reason_str = reason_val if isinstance(reason_val, str) else "Bulk update via form"
                await log_daily_reconciliation_edit(
                    db,
                    existing,
                    current_user.display_name_email,
                    "EDIT",
                    old_values,
                    new_values,
                    reason=reason_str,
                )

                updated_count += 1
            else:
                if not is_closed and not has_sales_data(
                    cash_sales, credit_sales, card_sales, total_sales
                ):
                    raise ValidationError("Sales data is required when location is open")

                # Create new reconciliation
                reconciliation = DailyReconciliation(
                    business_id=business.id,
                    date=reconciliation_date,
                    cash_sales=cash_sales,
                    credit_sales=credit_sales,
                    card_sales=card_sales,
                    total_sales=total_sales,
                    daily_cost_total=daily_cost_total,
                    invoice_count=invoice_count,
                    is_closed=is_closed,
                    admin_id=current_user.id,
                )
                db.add(reconciliation)
                created_count += 1

        await db.commit()

        logger.info(
            "reconciliation.created",
            date=str(reconciliation_date),
            created=created_count,
            updated=updated_count,
            admin_id=str(current_user.id),
        )

        # Redirect to comparison dashboard
        return RedirectResponse(
            url=f"/admin/reconciliation/compare?date={reconciliation_date.isoformat()}",
            status_code=status.HTTP_302_FOUND,
        )

    except ValueError as e:
        await db.rollback()
        # Handle validation errors (like currency format or max value exceeded)
        error_message = str(e)
        if "exceeds maximum" in error_message:
            error_message = "Currency value too large. Maximum allowed: 9,999,999,999.99"
        logger.warning("reconciliation.validation_error", error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_message)
    except ValidationError as e:
        await db.rollback()
        logger.error("reconciliation.validation_error", error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error("reconciliation.error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save daily reconciliation",
        )


# ─────── API ENDPOINTS ────────


@router.get("/compare/", response_model=list[dict])
async def get_reconciliation_compare(
    business_id: UUID | None = Query(None, description="Filter by business ID"),
    date: date | None = Query(None, description="Date in YYYY-MM-DD format"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get reconciliation comparison data with variance calculation.

    Returns JSON with manual entries vs calculated cash sessions totals,
    including variance percentage and status flags.
    """

    from cashpilot.models.business import Business
    from cashpilot.models.cash_session import CashSession

    # Parse date or use today
    if date:
        comparison_date = date
    else:
        comparison_date = today_local()

    # Build query for businesses
    stmt_businesses = select(Business).where(Business.is_active)
    if business_id:
        stmt_businesses = stmt_businesses.where(Business.id == business_id)
    result_businesses = await db.execute(stmt_businesses)
    businesses = result_businesses.scalars().all()

    comparison_results = []

    for business in businesses:
        # Get manual entry (DailyReconciliation)
        stmt_recon = select(DailyReconciliation).where(
            and_(
                DailyReconciliation.business_id == business.id,
                DailyReconciliation.date == comparison_date,
                DailyReconciliation.deleted_at.is_(None),
            )
        )
        result_recon = await db.execute(stmt_recon)
        manual_entry = result_recon.scalar_one_or_none()

        # Calculate system totals from CashSessions (same logic as admin.py)
        stmt_system = select(
            func.sum(
                case(
                    (
                        and_(
                            CashSession.status == "CLOSED",
                            CashSession.final_cash.is_not(None),
                        ),
                        (CashSession.final_cash - CashSession.initial_cash)
                        + func.coalesce(CashSession.envelope_amount, 0)
                        + func.coalesce(CashSession.expenses, 0)
                        - func.coalesce(CashSession.credit_payments_collected, 0)
                        + func.coalesce(CashSession.bank_transfer_total, 0),
                    ),
                    else_=0,
                )
            ).label("cash_sales"),
            func.sum(
                case(
                    (
                        CashSession.status == "CLOSED",
                        func.coalesce(CashSession.card_total, 0),
                    ),
                    else_=0,
                )
            ).label("card_sales"),
            func.sum(
                case(
                    (
                        CashSession.status == "CLOSED",
                        func.coalesce(CashSession.credit_sales_total, 0),
                    ),
                    else_=0,
                )
            ).label("credit_sales"),
            func.sum(
                case(
                    (
                        and_(
                            CashSession.status == "CLOSED",
                            CashSession.final_cash.is_not(None),
                        ),
                        (CashSession.final_cash - CashSession.initial_cash)
                        + func.coalesce(CashSession.envelope_amount, 0)
                        + func.coalesce(CashSession.expenses, 0)
                        - func.coalesce(CashSession.credit_payments_collected, 0)
                        + func.coalesce(CashSession.bank_transfer_total, 0)
                        + func.coalesce(CashSession.card_total, 0)
                        + func.coalesce(CashSession.credit_sales_total, 0),
                    ),
                    else_=0,
                )
            ).label("total_sales"),
            func.count(CashSession.id).label("session_count"),
        ).where(
            and_(
                CashSession.business_id == business.id,
                CashSession.session_date == comparison_date,
                ~CashSession.is_deleted,
            )
        )

        result_system = await db.execute(stmt_system)
        system_data = result_system.one()

        system_cash_sales = (
            system_data.cash_sales if system_data.cash_sales is not None else Decimal("0.00")
        )
        system_card_sales = (
            system_data.card_sales if system_data.card_sales is not None else Decimal("0.00")
        )
        system_credit_sales = (
            system_data.credit_sales if system_data.credit_sales is not None else Decimal("0.00")
        )
        system_total_sales = (
            system_data.total_sales if system_data.total_sales is not None else Decimal("0.00")
        )
        session_count = system_data.session_count if system_data.session_count is not None else 0

        # Manual entry values
        manual_cash_sales = (
            manual_entry.cash_sales
            if manual_entry and manual_entry.cash_sales is not None
            else None
        )
        manual_card_sales = (
            manual_entry.card_sales
            if manual_entry and manual_entry.card_sales is not None
            else None
        )
        manual_credit_sales = (
            manual_entry.credit_sales
            if manual_entry and manual_entry.credit_sales is not None
            else None
        )
        manual_total_sales = (
            manual_entry.total_sales
            if manual_entry and manual_entry.total_sales is not None
            else None
        )
        is_closed = manual_entry.is_closed if manual_entry else False

        # Calculate differences and variance
        def calc_variance(manual: Decimal | None, calculated: Decimal) -> dict:
            """Calculate difference and variance percentage."""
            if manual is None:
                return {
                    "difference": None,
                    "variance_percent": None,
                }
            diff = manual - calculated
            # When both are 0, difference is 0.0 (not None)
            calculated_float = float(calculated)
            manual_float = float(manual)
            if calculated_float == 0.0:
                if manual_float == 0.0:
                    return {
                        "difference": 0.0,
                        "variance_percent": None,
                    }
                else:
                    return {
                        "difference": float(diff),
                        "variance_percent": None,
                    }
            variance_pct = (diff / calculated) * 100
            return {
                "difference": float(diff),
                "variance_percent": float(variance_pct),
            }

        cash_variance = calc_variance(manual_cash_sales, system_cash_sales)
        card_variance = calc_variance(manual_card_sales, system_card_sales)
        credit_variance = calc_variance(manual_credit_sales, system_credit_sales)
        total_variance = calc_variance(manual_total_sales, system_total_sales)

        # Determine status using dual threshold (OR logic):
        # "Needs Review" if absolute difference > 20,000 Gs OR variance % > 2%
        status = "Match"
        if total_variance["difference"] is not None:
            abs_diff = abs(Decimal(str(total_variance["difference"])))
            exceeds_absolute = abs_diff > ABSOLUTE_THRESHOLD
        else:
            exceeds_absolute = False

        if total_variance["variance_percent"] is not None:
            exceeds_percentage = abs(total_variance["variance_percent"]) > VARIANCE_THRESHOLD
        else:
            exceeds_percentage = False

        if exceeds_absolute or exceeds_percentage:
            status = "Needs Review"

        comparison_results.append(
            {
                "business_id": str(business.id),
                "business_name": business.name,
                "date": comparison_date.isoformat(),
                "is_closed": is_closed,
                "manual_entry": {
                    "cash_sales": float(manual_cash_sales) if manual_cash_sales else None,
                    "card_sales": float(manual_card_sales) if manual_card_sales else None,
                    "credit_sales": float(manual_credit_sales) if manual_credit_sales else None,
                    "total_sales": float(manual_total_sales) if manual_total_sales else None,
                },
                "calculated": {
                    "cash_sales": float(system_cash_sales),
                    "card_sales": float(system_card_sales),
                    "credit_sales": float(system_credit_sales),
                    "total_sales": float(system_total_sales),
                    "session_count": session_count,
                },
                "variance": {
                    "cash_sales": cash_variance,
                    "card_sales": card_variance,
                    "credit_sales": credit_variance,
                    "total_sales": total_variance,
                },
                "status": status,
            }
        )

    return comparison_results


@router.get("/daily/", response_model=list[dict])
async def get_daily_reconciliations(
    business_id: UUID | None = Query(None),
    date: date | None = Query(None),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get daily reconciliations with optional filters."""
    stmt = select(DailyReconciliation).where(DailyReconciliation.deleted_at.is_(None))

    if business_id:
        stmt = stmt.where(DailyReconciliation.business_id == business_id)

    if date:
        stmt = stmt.where(DailyReconciliation.date == date)

    result = await db.execute(stmt)
    reconciliations = result.scalars().all()

    return [
        {
            "id": str(r.id),
            "business_id": str(r.business_id),
            "date": r.date.isoformat(),
            "cash_sales": str(r.cash_sales) if r.cash_sales else None,
            "credit_sales": str(r.credit_sales) if r.credit_sales else None,
            "card_sales": str(r.card_sales) if r.card_sales else None,
            "total_sales": str(r.total_sales) if r.total_sales else None,
            "daily_cost_total": r.daily_cost_total,
            "invoice_count": r.invoice_count,
            "is_closed": r.is_closed,
            "admin_id": str(r.admin_id),
            "created_at": r.created_at.isoformat(),
        }
        for r in reconciliations
    ]


@router.put("/daily/{reconciliation_id}", response_model=dict)
async def update_daily_reconciliation(
    reconciliation_id: UUID,
    cash_sales: Decimal | None = Form(None),
    credit_sales: Decimal | None = Form(None),
    card_sales: Decimal | None = Form(None),
    total_sales: Decimal | None = Form(None),
    daily_cost_total: str | None = Form(None),
    invoice_count: int | None = Form(None),
    is_closed: str | None = Form(None),
    reason: str = Form(..., min_length=5),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a daily reconciliation (requires reason for audit trail)."""
    stmt = select(DailyReconciliation).where(
        and_(
            DailyReconciliation.id == reconciliation_id,
            DailyReconciliation.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    reconciliation = result.scalar_one_or_none()

    if not reconciliation:
        raise NotFoundError("DailyReconciliation", str(reconciliation_id))

    # Capture old values for audit
    old_values = {
        "cash_sales": str(reconciliation.cash_sales) if reconciliation.cash_sales else None,
        "credit_sales": str(reconciliation.credit_sales) if reconciliation.credit_sales else None,
        "card_sales": str(reconciliation.card_sales) if reconciliation.card_sales else None,
        "total_sales": str(reconciliation.total_sales) if reconciliation.total_sales else None,
        "daily_cost_total": (
            str(reconciliation.daily_cost_total)
            if reconciliation.daily_cost_total is not None
            else None
        ),
        "invoice_count": reconciliation.invoice_count,
        "is_closed": reconciliation.is_closed,
    }

    # Update fields if provided
    if cash_sales is not None:
        reconciliation.cash_sales = cash_sales
    if credit_sales is not None:
        reconciliation.credit_sales = credit_sales
    if card_sales is not None:
        reconciliation.card_sales = card_sales
    if total_sales is not None:
        reconciliation.total_sales = total_sales
    if daily_cost_total is not None:
        try:
            parsed_daily_cost_total = parse_daily_cost_total(daily_cost_total)
            if parsed_daily_cost_total is not None:
                validate_currency(Decimal(abs(parsed_daily_cost_total)))
            reconciliation.daily_cost_total = parsed_daily_cost_total
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    if invoice_count is not None:
        reconciliation.invoice_count = invoice_count
    # Convert string to bool for is_closed
    if is_closed is not None:
        is_closed_bool = is_closed.lower() in ("true", "1", "yes", "on")
        reconciliation.is_closed = is_closed_bool

    reconciliation.last_modified_at = now_utc()
    reconciliation.last_modified_by = current_user.display_name_email

    new_values = {
        "cash_sales": str(reconciliation.cash_sales) if reconciliation.cash_sales else None,
        "credit_sales": str(reconciliation.credit_sales) if reconciliation.credit_sales else None,
        "card_sales": str(reconciliation.card_sales) if reconciliation.card_sales else None,
        "total_sales": str(reconciliation.total_sales) if reconciliation.total_sales else None,
        "daily_cost_total": (
            str(reconciliation.daily_cost_total)
            if reconciliation.daily_cost_total is not None
            else None
        ),
        "invoice_count": reconciliation.invoice_count,
        "is_closed": reconciliation.is_closed,
    }

    # Create audit log
    await log_daily_reconciliation_edit(
        db,
        reconciliation,
        current_user.display_name_email,
        "EDIT",
        old_values,
        new_values,
        reason=reason,
    )

    await db.commit()

    return {
        "id": str(reconciliation.id),
        "business_id": str(reconciliation.business_id),
        "date": reconciliation.date.isoformat(),
        "cash_sales": str(reconciliation.cash_sales) if reconciliation.cash_sales else None,
        "credit_sales": str(reconciliation.credit_sales) if reconciliation.credit_sales else None,
        "card_sales": str(reconciliation.card_sales) if reconciliation.card_sales else None,
        "total_sales": str(reconciliation.total_sales) if reconciliation.total_sales else None,
        "daily_cost_total": reconciliation.daily_cost_total,
        "invoice_count": reconciliation.invoice_count,
        "is_closed": reconciliation.is_closed,
    }


@router.delete("/daily/{reconciliation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_daily_reconciliation(
    reconciliation_id: UUID,
    reason: str = Form(..., min_length=5),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete a daily reconciliation (requires reason for audit trail)."""
    stmt = select(DailyReconciliation).where(
        and_(
            DailyReconciliation.id == reconciliation_id,
            DailyReconciliation.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    reconciliation = result.scalar_one_or_none()

    if not reconciliation:
        raise NotFoundError("DailyReconciliation", str(reconciliation_id))

    # Capture old values for audit
    old_values = {
        "cash_sales": str(reconciliation.cash_sales) if reconciliation.cash_sales else None,
        "credit_sales": str(reconciliation.credit_sales) if reconciliation.credit_sales else None,
        "card_sales": str(reconciliation.card_sales) if reconciliation.card_sales else None,
        "total_sales": str(reconciliation.total_sales) if reconciliation.total_sales else None,
        "daily_cost_total": (
            str(reconciliation.daily_cost_total)
            if reconciliation.daily_cost_total is not None
            else None
        ),
        "invoice_count": reconciliation.invoice_count,
        "is_closed": reconciliation.is_closed,
    }

    # Soft delete
    reconciliation.deleted_at = now_utc()
    display_name = current_user.display_name
    if not display_name:
        logger.warning(
            "User missing display_name when deleting reconciliation",
            user_id=str(current_user.id),
            reconciliation_id=str(reconciliation.id),
        )
        display_name = f"User-{current_user.id}"
    reconciliation.deleted_by = display_name

    # Create audit log for deletion
    await log_daily_reconciliation_edit(
        db,
        reconciliation,
        current_user.display_name_email,
        "DELETE",
        old_values,
        {},  # No new values for deletion
        reason=reason,
    )

    await db.commit()

    logger.info(
        "reconciliation.deleted",
        reconciliation_id=str(reconciliation.id),
        deleted_by=str(current_user.id),
    )


# ─────── AUDIT LOGGING ────────


async def log_daily_reconciliation_edit(
    db: AsyncSession,
    reconciliation: DailyReconciliation,
    changed_by: str,
    action: str,
    old_values: dict,
    new_values: dict,
    reason: str | None = None,
) -> DailyReconciliationAuditLog | None:
    """Log a DailyReconciliation edit to audit trail."""
    # Only include fields that actually changed
    changed_fields = [k for k in old_values.keys() if old_values[k] != new_values.get(k)]

    if not changed_fields:
        # No changes, skip audit log
        return None

    audit_log = DailyReconciliationAuditLog(
        reconciliation_id=reconciliation.id,
        changed_by=changed_by,
        action=action,
        changed_fields=changed_fields,
        old_values={k: old_values[k] for k in changed_fields},
        new_values={k: new_values.get(k) for k in changed_fields},
        reason=reason,
        changed_at=now_utc(),
    )

    db.add(audit_log)
    return audit_log
