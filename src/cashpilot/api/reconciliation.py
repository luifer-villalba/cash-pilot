# File: src/cashpilot/api/reconciliation.py
"""Daily reconciliation API endpoints."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.api.auth import get_current_user
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
from cashpilot.models import Business, DailyReconciliation, User
from cashpilot.models.daily_reconciliation_audit_log import DailyReconciliationAuditLog
from cashpilot.utils.datetime import now_utc, today_local

logger = get_logger(__name__)

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])


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
        business_ids = {str(b.id) for b in businesses}

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
            refunds = None
            total_sales = None

            if not is_closed:
                cash_sales_val = form_data.get(f"cash_sales_{business_id_str}", "")
                credit_sales_val = form_data.get(f"credit_sales_{business_id_str}", "")
                card_sales_val = form_data.get(f"card_sales_{business_id_str}", "")
                refunds_val = form_data.get(f"refunds_{business_id_str}", "")
                total_sales_val = form_data.get(f"total_sales_{business_id_str}", "")

                cash_sales_str = cash_sales_val if isinstance(cash_sales_val, str) else ""
                credit_sales_str = credit_sales_val if isinstance(credit_sales_val, str) else ""
                card_sales_str = card_sales_val if isinstance(card_sales_val, str) else ""
                refunds_str = refunds_val if isinstance(refunds_val, str) else ""
                total_sales_str = total_sales_val if isinstance(total_sales_val, str) else ""

                cash_sales = parse_currency(cash_sales_str) if cash_sales_str else None
                credit_sales = parse_currency(credit_sales_str) if credit_sales_str else None
                card_sales = parse_currency(card_sales_str) if card_sales_str else None
                refunds = parse_currency(refunds_str) if refunds_str else None
                total_sales = parse_currency(total_sales_str) if total_sales_str else None

            if existing:
                # Update existing reconciliation
                old_values = {
                    "cash_sales": str(existing.cash_sales) if existing.cash_sales else None,
                    "credit_sales": str(existing.credit_sales) if existing.credit_sales else None,
                    "card_sales": str(existing.card_sales) if existing.card_sales else None,
                    "refunds": str(existing.refunds) if existing.refunds else None,
                    "total_sales": str(existing.total_sales) if existing.total_sales else None,
                    "is_closed": existing.is_closed,
                }

                existing.cash_sales = cash_sales
                existing.credit_sales = credit_sales
                existing.card_sales = card_sales
                existing.refunds = refunds
                existing.total_sales = total_sales
                existing.is_closed = is_closed

                new_values = {
                    "cash_sales": str(cash_sales) if cash_sales else None,
                    "credit_sales": str(credit_sales) if credit_sales else None,
                    "card_sales": str(card_sales) if card_sales else None,
                    "refunds": str(refunds) if refunds else None,
                    "total_sales": str(total_sales) if total_sales else None,
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
                # Create new reconciliation
                reconciliation = DailyReconciliation(
                    business_id=business.id,
                    date=reconciliation_date,
                    cash_sales=cash_sales,
                    credit_sales=credit_sales,
                    card_sales=card_sales,
                    refunds=refunds,
                    total_sales=total_sales,
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
            "refunds": str(r.refunds) if r.refunds else None,
            "total_sales": str(r.total_sales) if r.total_sales else None,
            "is_closed": r.is_closed,
            "admin_id": str(r.admin_id),
            "created_at": r.created_at.isoformat(),
        }
        for r in reconciliations
    ]


@router.put("/daily/{reconciliation_id}", response_model=dict)
async def update_daily_reconciliation(
    reconciliation_id: UUID,
    cash_sales: Decimal | None = None,
    credit_sales: Decimal | None = None,
    card_sales: Decimal | None = None,
    refunds: Decimal | None = None,
    total_sales: Decimal | None = None,
    is_closed: bool | None = None,
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
        "refunds": str(reconciliation.refunds) if reconciliation.refunds else None,
        "total_sales": str(reconciliation.total_sales) if reconciliation.total_sales else None,
        "is_closed": reconciliation.is_closed,
    }

    # Update fields if provided
    if cash_sales is not None:
        reconciliation.cash_sales = cash_sales
    if credit_sales is not None:
        reconciliation.credit_sales = credit_sales
    if card_sales is not None:
        reconciliation.card_sales = card_sales
    if refunds is not None:
        reconciliation.refunds = refunds
    if total_sales is not None:
        reconciliation.total_sales = total_sales
    if is_closed is not None:
        reconciliation.is_closed = is_closed

    new_values = {
        "cash_sales": str(reconciliation.cash_sales) if reconciliation.cash_sales else None,
        "credit_sales": str(reconciliation.credit_sales) if reconciliation.credit_sales else None,
        "card_sales": str(reconciliation.card_sales) if reconciliation.card_sales else None,
        "refunds": str(reconciliation.refunds) if reconciliation.refunds else None,
        "total_sales": str(reconciliation.total_sales) if reconciliation.total_sales else None,
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
        "refunds": str(reconciliation.refunds) if reconciliation.refunds else None,
        "total_sales": str(reconciliation.total_sales) if reconciliation.total_sales else None,
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
        "refunds": str(reconciliation.refunds) if reconciliation.refunds else None,
        "total_sales": str(reconciliation.total_sales) if reconciliation.total_sales else None,
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

