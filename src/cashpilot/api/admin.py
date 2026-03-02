# File: src/cashpilot/api/admin.py
import secrets
import string
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import and_, case, delete, func, select
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
from cashpilot.core.security import hash_password
from cashpilot.models.business import Business
from cashpilot.models.cash_session import CashSession
from cashpilot.models.daily_reconciliation import DailyReconciliation
from cashpilot.models.expense_item import ExpenseItem
from cashpilot.models.transfer_item import TransferItem
from cashpilot.models.user import User
from cashpilot.models.user_business import UserBusiness
from cashpilot.utils.datetime import APP_TIMEZONE, now_utc, today_local

router = APIRouter(prefix="/admin", tags=["admin"])
logger = get_logger(__name__)
# Variance thresholds for flagging discrepancies
# Uses dual threshold approach (OR logic):
# - Absolute: 20,000 Gs (based on local practice in Paraguay)
# - Percentage: 2% (industry standard)
# Flags "Needs Review" if EITHER threshold is exceeded
ABSOLUTE_THRESHOLD = Decimal("20000.00")  # 20,000 guaraníes
VARIANCE_THRESHOLD = Decimal("2.0")  # 2%


# ===== HELPER FUNCTIONS =====
async def _build_comparison_data(
    db: AsyncSession,
    comparison_date: datetime,
    businesses: list[Business],
) -> list[dict]:
    """
    Build comparison data for manual vs system reconciliation.

    Shared logic used by both the full dashboard and the partial HTMX endpoint.

    Args:
        db: Database session
        comparison_date: Date to compare
        businesses: List of businesses to process

    Returns:
        List of comparison data dictionaries for each business
    """
    comparison_data = []

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

        # Calculate system totals from CashSessions
        stmt_system = select(
            # Cash Sales = (final_cash - initial_cash) + envelope + expenses
            # - credit_payments_collected + bank_transfer_total
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
            # Card Sales (only closed sessions)
            func.sum(
                case(
                    (
                        CashSession.status == "CLOSED",
                        func.coalesce(CashSession.card_total, 0),
                    ),
                    else_=0,
                )
            ).label("card_sales"),
            # Credit Sales (on-account) - only closed sessions
            func.sum(
                case(
                    (
                        CashSession.status == "CLOSED",
                        func.coalesce(CashSession.credit_sales_total, 0),
                    ),
                    else_=0,
                )
            ).label("credit_sales"),
            # Total Sales = cash + card + credit
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
            # Session count
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

        system_cash_sales = system_data.cash_sales or Decimal("0.00")
        system_card_sales = system_data.card_sales or Decimal("0.00")
        system_credit_sales = system_data.credit_sales or Decimal("0.00")
        system_total_sales = system_data.total_sales or Decimal("0.00")
        session_count = system_data.session_count or 0

        stmt_open_sessions = select(func.count(CashSession.id)).where(
            and_(
                CashSession.business_id == business.id,
                CashSession.session_date == comparison_date,
                CashSession.status == "OPEN",
                ~CashSession.is_deleted,
            )
        )
        result_open_sessions = await db.execute(stmt_open_sessions)
        open_sessions_count = result_open_sessions.scalar() or 0
        has_open_sessions = open_sessions_count > 0

        stmt_notes_count = select(func.count(CashSession.id)).where(
            and_(
                CashSession.business_id == business.id,
                CashSession.session_date == comparison_date,
                ~CashSession.is_deleted,
                CashSession.notes.is_not(None),
                CashSession.notes != "",
            )
        )
        result_notes_count = await db.execute(stmt_notes_count)
        notes_count = result_notes_count.scalar() or 0

        # Get unique cashiers for this business on this date
        stmt_cashiers = (
            select(User.first_name, User.last_name)
            .join(CashSession, CashSession.cashier_id == User.id)
            .where(
                and_(
                    CashSession.business_id == business.id,
                    CashSession.session_date == comparison_date,
                    ~CashSession.is_deleted,
                    User.first_name.is_not(None),
                )
            )
            .distinct()
            .order_by(User.first_name, User.last_name)
        )
        result_cashiers = await db.execute(stmt_cashiers)
        # Format as "FirstName L." (first name + last name initial)
        cashiers = []
        for first_name, last_name in result_cashiers.all():
            if first_name:
                last_initial = f"{last_name[0]}." if last_name else ""
                cashiers.append(f"{first_name} {last_initial}".strip())
        cashiers_str = ", ".join(cashiers) if cashiers else ""

        # Manual entry values
        manual_cash_sales = (
            manual_entry.cash_sales if manual_entry and manual_entry.cash_sales else None
        )
        manual_card_sales = (
            manual_entry.card_sales if manual_entry and manual_entry.card_sales else None
        )
        manual_credit_sales = (
            manual_entry.credit_sales if manual_entry and manual_entry.credit_sales else None
        )
        manual_total_sales = (
            manual_entry.total_sales if manual_entry and manual_entry.total_sales else None
        )
        is_closed = manual_entry.is_closed if manual_entry else False
        has_manual_values = False
        is_partial_entry = False
        if manual_entry:
            sales_values = (
                manual_entry.cash_sales,
                manual_entry.card_sales,
                manual_entry.credit_sales,
                manual_entry.total_sales,
            )

            def is_zero_or_none(value: Decimal | int | None) -> bool:
                if value is None:
                    return True
                return value == 0

            all_sales_present = all(value is not None for value in sales_values)
            any_sales_nonzero = any(not is_zero_or_none(value) for value in sales_values)
            total_sales_nonzero = (
                manual_entry.total_sales is not None and manual_entry.total_sales != 0
            )

            if is_closed:
                has_manual_values = True
            else:
                has_manual_values = total_sales_nonzero or (all_sales_present and any_sales_nonzero)
                is_partial_entry = not has_manual_values

        # Calculate differences and variance
        def calc_variance(manual: Decimal | None, calculated: Decimal) -> dict:
            """Calculate difference and variance percentage."""
            if manual is None:
                return {
                    "difference": None,
                    "variance_percent": None,
                }
            diff = calculated - manual
            # When both are 0, difference is 0.0 (not None)
            calculated_float = float(calculated)
            manual_float = float(manual)
            if calculated_float == 0.0:
                if manual_float == 0.0:
                    return {
                        "difference": Decimal("0.00"),
                        "variance_percent": None,
                    }
                else:
                    return {
                        "difference": diff,
                        "variance_percent": None,
                    }
            variance_pct = (diff / calculated) * 100
            return {
                "difference": diff,
                "variance_percent": variance_pct,
            }

        cash_variance = calc_variance(manual_cash_sales, system_cash_sales)
        card_variance = calc_variance(manual_card_sales, system_card_sales)
        credit_variance = calc_variance(manual_credit_sales, system_credit_sales)
        total_variance = calc_variance(manual_total_sales, system_total_sales)

        # Determine status using dual threshold (OR logic):
        # "Needs Review" if absolute difference > 20,000 Gs OR variance % > 2%
        status = "Match"
        if total_variance["difference"] is not None:
            abs_diff = abs(total_variance["difference"])
            exceeds_absolute = abs_diff > ABSOLUTE_THRESHOLD
        else:
            exceeds_absolute = False

        if total_variance["variance_percent"] is not None:
            exceeds_percentage = abs(total_variance["variance_percent"]) > VARIANCE_THRESHOLD
        else:
            exceeds_percentage = False

        if exceeds_absolute or exceeds_percentage:
            status = "Needs Review"

        comparison_data.append(
            {
                "business": business,
                "cashiers": cashiers_str,
                "manual_entry": manual_entry,
                "has_manual_values": has_manual_values,
                "is_partial_entry": is_partial_entry,
                "is_closed": is_closed,
                "manual": {
                    "cash_sales": manual_cash_sales,
                    "card_sales": manual_card_sales,
                    "credit_sales": manual_credit_sales,
                    "total_sales": manual_total_sales,
                },
                "system": {
                    "cash_sales": system_cash_sales,
                    "card_sales": system_card_sales,
                    "credit_sales": system_credit_sales,
                    "total_sales": system_total_sales,
                    "session_count": session_count,
                },
                "differences": {
                    "cash_sales": cash_variance["difference"],
                    "card_sales": card_variance["difference"],
                    "credit_sales": credit_variance["difference"],
                    "total_sales": total_variance["difference"],
                },
                "variance": {
                    "cash_sales": cash_variance["variance_percent"],
                    "card_sales": card_variance["variance_percent"],
                    "credit_sales": credit_variance["variance_percent"],
                    "total_sales": total_variance["variance_percent"],
                },
                "status": status,
                "has_open_sessions": has_open_sessions,
                "open_sessions_count": open_sessions_count,
                "notes_count": notes_count,
            }
        )

    return comparison_data


async def _fetch_transfer_items_for_reconciliation(
    db: AsyncSession,
    business_id: UUID,
    reconciliation_date: datetime,
) -> list[dict]:
    """
    Fetch all bank transfer items for a business on a given date.

    Returns transfer items from all sessions for that business+date,
    ordered chronologically (earliest first), with cashier names and session IDs.

    Args:
        db: Database session
        business_id: Business ID to filter by
        reconciliation_date: Date to filter by (as date object)

    Returns:
        List of transfer item dictionaries with fields:
        - id: UUID
        - session_id: UUID
        - description: str
        - amount: Decimal
        - created_at: datetime
        - cashier_name: str
        - cashier_id: UUID
    """
    # Convert datetime to date if needed
    if isinstance(reconciliation_date, datetime):
        target_date = reconciliation_date.date()
    else:
        target_date = reconciliation_date

    # Query: transfer items joined with sessions and cashiers
    stmt = (
        select(
            TransferItem.id,
            TransferItem.session_id,
            TransferItem.description,
            TransferItem.amount,
            TransferItem.created_at,
            TransferItem.is_verified,
            User.id.label("cashier_id"),
            User.first_name,
            User.last_name,
            CashSession.session_number,
        )
        .join(CashSession, TransferItem.session_id == CashSession.id)
        .join(User, CashSession.cashier_id == User.id)
        .where(
            and_(
                CashSession.business_id == business_id,
                CashSession.session_date == target_date,
                ~TransferItem.is_deleted,
                ~CashSession.is_deleted,
            )
        )
        .order_by(TransferItem.created_at.asc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    # Format results
    transfer_items = []
    for row in rows:
        # Build cashier name (FirstName L.)
        cashier_name = row.first_name or ""
        if row.last_name:
            cashier_name += f" {row.last_name[0]}."
        cashier_name = cashier_name.strip()

        transfer_items.append(
            {
                "id": row.id,
                "session_id": row.session_id,
                "session_number": row.session_number,
                "description": row.description,
                "amount": row.amount,
                "created_at": row.created_at,
                "cashier_id": row.cashier_id,
                "cashier_name": cashier_name,
                "is_verified": row.is_verified,
            }
        )

    return transfer_items


def _parse_iso_date(value: str | None) -> date | None:
    """Parse YYYY-MM-DD date string safely."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except (ValueError, TypeError):
        return None


def _resolve_transfer_report_range(
    from_date: str | None,
    to_date: str | None,
) -> tuple[date, date]:
    """Resolve date range for transfer report using explicit dates only."""
    today = today_local()

    parsed_from = _parse_iso_date(from_date)
    parsed_to = _parse_iso_date(to_date)

    if parsed_from and parsed_to:
        if parsed_from <= parsed_to:
            return parsed_from, parsed_to
        return parsed_to, parsed_from

    if parsed_from and not parsed_to:
        return parsed_from, parsed_from
    if parsed_to and not parsed_from:
        return parsed_to, parsed_to

    return today, today


async def _fetch_transfer_items_for_date_range(
    db: AsyncSession,
    from_date: date,
    to_date: date,
    selected_business_id: UUID | None = None,
) -> tuple[list[dict], dict[str, str]]:
    """Fetch transfer items across a date range, optionally scoped to one business."""
    stmt = (
        select(
            TransferItem.id,
            TransferItem.session_id,
            TransferItem.description,
            TransferItem.amount,
            TransferItem.created_at,
            TransferItem.is_verified,
            User.id.label("cashier_id"),
            User.first_name,
            User.last_name,
            CashSession.session_number,
            CashSession.business_id,
            CashSession.session_date,
            Business.name.label("business_name"),
        )
        .join(CashSession, TransferItem.session_id == CashSession.id)
        .join(User, CashSession.cashier_id == User.id)
        .join(Business, CashSession.business_id == Business.id)
        .where(
            and_(
                CashSession.session_date >= from_date,
                CashSession.session_date <= to_date,
                ~TransferItem.is_deleted,
                ~CashSession.is_deleted,
                Business.is_active,
            )
        )
        .order_by(TransferItem.created_at.asc())
    )

    if selected_business_id is not None:
        stmt = stmt.where(CashSession.business_id == selected_business_id)

    result = await db.execute(stmt)
    rows = result.all()

    transfer_items = []
    business_names_by_id: dict[str, str] = {}

    for row in rows:
        cashier_name = row.first_name or ""
        if row.last_name:
            cashier_name += f" {row.last_name[0]}."
        cashier_name = cashier_name.strip()

        business_id_str = str(row.business_id)
        business_names_by_id[business_id_str] = row.business_name

        transfer_items.append(
            {
                "id": row.id,
                "session_id": row.session_id,
                "session_number": row.session_number,
                "description": row.description,
                "amount": row.amount,
                "created_at": row.created_at,
                "cashier_id": row.cashier_id,
                "cashier_name": cashier_name,
                "is_verified": row.is_verified,
                "business_id": business_id_str,
                "business_name": row.business_name,
                "session_date": row.session_date,
            }
        )

    return transfer_items, business_names_by_id


async def _apply_transfer_filters(
    items: list[dict],
    filter_business: str | None = None,
    filter_verified: str = "all",
    filter_cashier: str | None = None,
) -> list[dict]:
    """Apply filters to transfer items list (CP-REPORTS-05).

    Args:
        items: List of transfer item dictionaries
        filter_business: Business UUID (as string) to filter by, or None for all
        filter_verified: "all", "verified", or "unverified"
        filter_cashier: Cashier UUID (as string) to filter by, or None for all

    Returns:
        Filtered list of transfer items
    """
    filtered = items

    # Filter by business
    if filter_business:
        filtered = [item for item in filtered if item.get("business_id") == filter_business]

    # Filter by verification status
    if filter_verified == "verified":
        filtered = [item for item in filtered if item.get("is_verified", False)]
    elif filter_verified == "unverified":
        filtered = [item for item in filtered if not item.get("is_verified", False)]

    # Filter by cashier
    if filter_cashier:
        try:
            cashier_uuid = UUID(filter_cashier)
            filtered = [item for item in filtered if item.get("cashier_id") == cashier_uuid]
        except (ValueError, TypeError):
            pass  # Invalid UUID, return unfiltered

    return filtered


async def _apply_transfer_sorting_and_pagination(
    items: list[dict],
    business_names_by_id: dict[str, str],
    sort_by: str = "business,time",
    sort_order: str = "asc",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """Apply sorting and pagination to transfer items (CP-REPORTS-05).

    Args:
        items: List of transfer item dictionaries
        business_names_by_id: Mapping of business IDs to names
        sort_by: Comma-separated sort fields (business, time, amount)
        sort_order: "asc" or "desc"
        page: Page number (1-indexed)
        page_size: Items per page

    Returns:
        Tuple of (paginated_items, total_count)
    """
    total_count = len(items)

    # Parse sort fields
    sort_fields = [f.strip() for f in sort_by.split(",") if f.strip()]
    if not sort_fields:
        sort_fields = ["business", "time"]

    # Build sort key function
    def sort_key(item: dict):
        keys = []
        for field in sort_fields:
            if field == "business":
                # Business name
                business_id = item.get("business_id")
                business_name = business_names_by_id.get(business_id)
                business_sort_key = (
                    business_name.lower() if business_name is not None else str(business_id or "")
                )
                keys.append(business_sort_key)
            elif field == "time":
                # Chronological order
                created_at = item.get("created_at")
                if created_at is None:
                    created_at = datetime.min.replace(tzinfo=ZoneInfo(APP_TIMEZONE))
                keys.append(created_at)
            elif field == "amount":
                # Amount in smallest unit (for proper numeric sorting)
                amount = item.get("amount", 0)
                if isinstance(amount, Decimal):
                    amount = float(amount)
                keys.append(amount)
        return tuple(keys)

    # Apply sorting
    reverse = sort_order.lower() == "desc"
    sorted_items = sorted(items, key=sort_key, reverse=reverse)

    # Apply pagination
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_items = sorted_items[start_idx:end_idx]

    return paginated_items, total_count


# ===== SCHEMAS =====
class PasswordResetRequest(BaseModel):
    new_password: str | None = Field(None, min_length=8, max_length=128)
    generate: bool = False


class PasswordResetResponse(BaseModel):
    user_id: str
    username: str
    new_password: str | None = None
    message: str


class ToggleActiveRequest(BaseModel):
    is_active: bool


class AssignBusinessesRequest(BaseModel):
    business_ids: list[UUID]


# ===== HELPERS =====
def generate_password(length: int = 12) -> str:
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ===== FRONTEND ROUTES =====
@router.get("/users-page", response_class=HTMLResponse)
async def users_management_page(
    request: Request,
    admin_user: User = Depends(require_admin),
):
    """Render user management page."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    return templates.TemplateResponse(
        request,
        "admin/users.html",
        {
            "current_user": admin_user,
            "locale": locale,
            "_": _,
        },
    )


# ===== API ENDPOINTS =====
@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """List all users with their assigned businesses (admin-only)."""
    result = await db.execute(
        select(User).options(selectinload(User.businesses)).order_by(User.created_at.desc())
    )
    users = result.scalars().all()

    return {
        "users": [
            {
                "id": str(user.id),
                "username": user.display_name,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat(),
                "businesses": [
                    {
                        "id": str(business.id),
                        "name": business.name,
                        "is_active": business.is_active,
                    }
                    for business in user.businesses
                ],
            }
            for user in users
        ]
    }


@router.get("/businesses")
async def list_businesses_for_assignment(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """List all active businesses for assignment dropdown (admin-only)."""
    result = await db.execute(
        select(Business).where(Business.is_active == True).order_by(Business.name)  # noqa: E712
    )
    businesses = result.scalars().all()

    return {
        "businesses": [
            {
                "id": str(business.id),
                "name": business.name,
            }
            for business in businesses
        ]
    }


@router.post("/users/{user_id}/businesses")
async def assign_businesses(
    user_id: UUID,
    request: AssignBusinessesRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Assign multiple businesses to a user (admin-only)."""
    # Verify user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify all businesses exist and are active
    if request.business_ids:
        business_result = await db.execute(
            select(Business).where(
                Business.id.in_(request.business_ids),
                Business.is_active == True,  # noqa: E712
            )
        )
        businesses = business_result.scalars().all()
        if len(businesses) != len(request.business_ids):
            raise HTTPException(
                status_code=404,
                detail="One or more businesses not found or inactive",
            )

    # Remove existing assignments not in the new list
    if request.business_ids:
        delete_stmt = delete(UserBusiness).where(
            UserBusiness.user_id == user_id, ~UserBusiness.business_id.in_(request.business_ids)
        )
    else:
        delete_stmt = delete(UserBusiness).where(UserBusiness.user_id == user_id)

    await db.execute(delete_stmt)

    # Add new assignments (skip if already exists)
    for business_id in request.business_ids:
        existing = await db.execute(
            select(UserBusiness).where(
                UserBusiness.user_id == user_id,
                UserBusiness.business_id == business_id,
            )
        )
        if not existing.scalar_one_or_none():
            assignment = UserBusiness(user_id=user_id, business_id=business_id)
            db.add(assignment)

    await db.commit()

    # Refresh and return updated user with businesses
    await db.refresh(user, ["businesses"])

    logger.info(
        "user.businesses.assigned",
        user_id=str(user_id),
        business_ids=[str(bid) for bid in request.business_ids],
        assigned_by=str(admin_user.id),
    )

    return {
        "user_id": str(user.id),
        "username": user.display_name,
        "businesses": [
            {
                "id": str(business.id),
                "name": business.name,
                "is_active": business.is_active,
            }
            for business in user.businesses
        ],
    }


@router.delete("/users/{user_id}/businesses/{business_id}")
async def unassign_business(
    user_id: UUID,
    business_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Remove a business assignment from a user (admin-only)."""
    # Verify user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Delete the specific assignment
    result = await db.execute(
        select(UserBusiness).where(
            UserBusiness.user_id == user_id,
            UserBusiness.business_id == business_id,
        )
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Business assignment not found")

    await db.delete(assignment)
    await db.commit()

    logger.info(
        "user.business.unassigned",
        user_id=str(user_id),
        business_id=str(business_id),
        unassigned_by=str(admin_user.id),
    )

    return {"message": "Business unassigned successfully"}


@router.post("/users/{user_id}/reset-password", response_model=PasswordResetResponse)
async def reset_user_password(
    user_id: str,
    request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Reset a user's password (admin-only). Returns generated password if requested."""
    try:
        user_uuid = UUID(user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Generate or use provided password
    if request.generate:
        new_password = generate_password()
    elif request.new_password:
        new_password = request.new_password
    else:
        raise HTTPException(
            status_code=400,
            detail="Must provide new_password or set generate=true",
        )

    # Update password
    user.hashed_password = hash_password(new_password)
    db.add(user)
    await db.commit()

    logger.info(
        "user.password.reset",
        user_id=user_id,
        reset_by=str(admin_user.id),
        generated=request.generate,
    )

    return PasswordResetResponse(
        user_id=user_id,
        username=user.display_name,
        new_password=new_password if request.generate else None,
        message="Password reset successfully",
    )


@router.post("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: str,
    request: ToggleActiveRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Toggle user active status (admin-only)."""
    try:
        user_uuid = UUID(user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = request.is_active
    db.add(user)
    await db.commit()

    logger.info(
        "user.active.toggled",
        user_id=user_id,
        is_active=request.is_active,
        toggled_by=str(admin_user.id),
    )

    return {
        "user_id": user_id,
        "username": user.display_name,
        "is_active": user.is_active,
    }


@router.get("/reconciliation/compare", response_class=HTMLResponse)
async def reconciliation_compare_dashboard(
    request: Request,
    date: str | None = Query(None, description="Date in YYYY-MM-DD format"),
    business_id: str | None = Query(None, description="Filter by business ID"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=10, le=100, description="Items per page"),
    sort_by: str = Query("business,time", description="Sort fields: business|time|amount"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort order"),
    filter_verified: str = Query(
        "all", pattern="^(all|verified|unverified)$", description="Filter by verification status"
    ),
    filter_business: str | None = Query(None, description="Filter transfer items by business ID"),
    filter_cashier: str | None = Query(None, description="Filter by cashier ID"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Comparison dashboard: manual entries vs system records with variance calculation.
    CP-REPORTS-05: Added pagination, filtering, and sorting support.
    """
    locale = get_locale(request)
    _ = get_translation_function(locale)

    # Parse date or use today
    if date:
        try:
            comparison_date = datetime.fromisoformat(date).date()
        except (ValueError, TypeError):
            comparison_date = today_local()
    else:
        comparison_date = today_local()

    # Get businesses (filtered if business_id provided)
    stmt_businesses = select(Business).where(Business.is_active).order_by(Business.name)
    selected_business_id = None
    if business_id and business_id.strip():
        try:
            selected_business_id = UUID(business_id)
            stmt_businesses = stmt_businesses.where(Business.id == selected_business_id)
        except (ValueError, TypeError):
            selected_business_id = None
    result_businesses = await db.execute(stmt_businesses)
    businesses = result_businesses.scalars().all()

    # Build comparison data using shared helper function
    comparison_data = await _build_comparison_data(db, comparison_date, businesses)

    # Fetch transfer items for each business and consolidate into single sorted list
    all_transfer_items = []
    transfer_items_by_business = {}  # Keep for backwards compatibility
    business_names_by_id = {}  # For template display

    for business in businesses:
        business_names_by_id[str(business.id)] = business.name
        transfer_items = await _fetch_transfer_items_for_reconciliation(
            db, business.id, comparison_date
        )
        transfer_items_by_business[str(business.id)] = transfer_items
        # Add business_id to each transfer for consolidated display
        for item in transfer_items:
            item["business_id"] = str(business.id)
        all_transfer_items.extend(transfer_items)

    # Apply filtering (CP-REPORTS-05)
    filtered_items = await _apply_transfer_filters(
        all_transfer_items,
        filter_business=filter_business,
        filter_verified=filter_verified,
        filter_cashier=filter_cashier,
    )

    total_count = len(filtered_items)
    if total_count == 0:
        total_pages = 0
        clamped_page = 1
        start_index = 0
    else:
        total_pages = (total_count + page_size - 1) // page_size
        clamped_page = min(page, total_pages)
        start_index = (clamped_page - 1) * page_size + 1

    # Apply sorting and pagination (CP-REPORTS-05)
    sorted_items, paginated_total_count = await _apply_transfer_sorting_and_pagination(
        filtered_items,
        business_names_by_id=business_names_by_id,
        sort_by=sort_by,
        sort_order=sort_order,
        page=clamped_page,
        page_size=page_size,
    )

    total_count = paginated_total_count

    # Get all businesses for the selector
    all_businesses = await get_active_businesses(db)

    # Get current time for last_updated display (used by partial template)
    now = datetime.now(ZoneInfo(APP_TIMEZONE))
    last_updated = now.isoformat()
    last_updated_display = now.strftime("%H:%M:%S")

    return templates.TemplateResponse(
        request,
        "admin/reconciliation_compare.html",
        {
            "current_user": current_user,
            "comparison_date": comparison_date,
            "selected_business_id": str(selected_business_id) if selected_business_id else None,
            "businesses": all_businesses,
            "comparison_data": comparison_data,
            "transfer_items_by_business": transfer_items_by_business,
            "all_transfer_items": sorted_items,
            "transfer_items_total_count": total_count,
            "businesses_by_id": business_names_by_id,
            "last_updated": last_updated,
            "last_updated_display": last_updated_display,
            "locale": locale,
            "_": _,
            # Pagination (CP-REPORTS-05)
            "current_page": clamped_page,
            "page_size": page_size,
            "total_pages": total_pages,
            "start_index": start_index,
            # Filter values (for form state)
            "filter_business": filter_business,
            "filter_verified": filter_verified,
            "filter_cashier": filter_cashier,
            "sort_by": sort_by,
            "sort_order": sort_order,
        },
    )


@router.get("/reconciliation/compare-results", response_class=HTMLResponse)
async def reconciliation_compare_results_partial(
    request: Request,
    date: str | None = Query(None, description="Date in YYYY-MM-DD format"),
    business_id: str | None = Query(None, description="Filter by business ID"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Partial endpoint for HTMX polling: returns only the comparison results table."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    # Parse date or use today
    if date:
        try:
            comparison_date = datetime.fromisoformat(date).date()
        except (ValueError, TypeError):
            comparison_date = today_local()
    else:
        comparison_date = today_local()

    # Get businesses (filtered if business_id provided)
    stmt_businesses = select(Business).where(Business.is_active).order_by(Business.name)
    selected_business_id = None
    if business_id and business_id.strip():
        try:
            selected_business_id = UUID(business_id)
            stmt_businesses = stmt_businesses.where(Business.id == selected_business_id)
        except (ValueError, TypeError):
            selected_business_id = None
    result_businesses = await db.execute(stmt_businesses)
    businesses = result_businesses.scalars().all()

    # Build comparison data using shared helper function
    comparison_data = await _build_comparison_data(db, comparison_date, businesses)

    # Get current time for last_updated display
    now = datetime.now(ZoneInfo(APP_TIMEZONE))
    last_updated = now.isoformat()
    last_updated_display = now.strftime("%H:%M:%S")

    return templates.TemplateResponse(
        request,
        "admin/partials/reconciliation_compare_results.html",
        {
            "comparison_date": comparison_date,
            "comparison_data": comparison_data,
            "selected_business_id": str(selected_business_id) if selected_business_id else None,
            "last_updated": last_updated,
            "last_updated_display": last_updated_display,
            "locale": locale,
            "_": _,
        },
    )


@router.get("/transfers/date-range", response_class=HTMLResponse)
async def transfer_date_range_report(
    request: Request,
    single_date: str | None = Query(None, description="Single date (YYYY-MM-DD), maps to from=to"),
    from_date: str | None = Query(None, description="From date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="To date (YYYY-MM-DD)"),
    business_id: str | None = Query(None, description="Filter by single business ID (legacy)"),
    business_ids: list[str] | None = Query(None, description="Filter by one or more business IDs"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=10, le=50, description="Items per page"),
    sort_by: str = Query("time", description="Sort fields: business|time|amount"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    filter_verified: str = Query(
        "all", pattern="^(all|verified|unverified)$", description="Filter by verification status"
    ),
    filter_cashier: str | None = Query(None, description="Filter by cashier ID"),
    filter_description: str | None = Query(
        None,
        description="Case-insensitive substring match on transfer description",
    ),
    origin: str | None = Query(None, description="Navigation origin context"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """CP-REPORTS-06: Bank transfers report with date-range, filters, and pagination."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    normalized_from_date = from_date
    normalized_to_date = to_date

    if single_date and not from_date and not to_date:
        normalized_from_date = single_date
        normalized_to_date = single_date

    selected_from_date, selected_to_date = _resolve_transfer_report_range(
        normalized_from_date, normalized_to_date
    )

    selected_business_ids: list[UUID] = []
    if business_id and business_id.strip():
        try:
            selected_business_ids.append(UUID(business_id))
        except (ValueError, TypeError):
            pass

    for value in business_ids or []:
        if not value or not value.strip():
            continue
        try:
            parsed_business_id = UUID(value)
            if parsed_business_id not in selected_business_ids:
                selected_business_ids.append(parsed_business_id)
        except (ValueError, TypeError):
            continue

    all_businesses = await get_active_businesses(db)

    conditions = [
        CashSession.session_date >= selected_from_date,
        CashSession.session_date <= selected_to_date,
        ~TransferItem.is_deleted,
        ~CashSession.is_deleted,
        Business.is_active,
    ]

    if selected_business_ids:
        conditions.append(CashSession.business_id.in_(selected_business_ids))

    if filter_verified == "verified":
        conditions.append(TransferItem.is_verified)
    elif filter_verified == "unverified":
        conditions.append(~TransferItem.is_verified)

    if filter_cashier and filter_cashier.strip():
        try:
            cashier_uuid = UUID(filter_cashier)
            conditions.append(User.id == cashier_uuid)
        except (ValueError, TypeError):
            filter_cashier = None

    if filter_description and filter_description.strip():
        conditions.append(TransferItem.description.ilike(f"%{filter_description.strip()}%"))

    where_clause = and_(*conditions)

    count_stmt = (
        select(func.count(TransferItem.id))
        .join(CashSession, TransferItem.session_id == CashSession.id)
        .join(User, CashSession.cashier_id == User.id)
        .join(Business, CashSession.business_id == Business.id)
        .where(where_clause)
    )
    count_result = await db.execute(count_stmt)
    filtered_total_count = count_result.scalar() or 0

    total_stmt = (
        select(func.coalesce(func.sum(TransferItem.amount), Decimal("0.00")))
        .join(CashSession, TransferItem.session_id == CashSession.id)
        .join(User, CashSession.cashier_id == User.id)
        .join(Business, CashSession.business_id == Business.id)
        .where(where_clause)
    )
    total_result = await db.execute(total_stmt)
    filtered_total_amount = total_result.scalar() or Decimal("0.00")

    if filtered_total_count == 0:
        total_pages = 0
        clamped_page = 1
        start_index = 0
    else:
        total_pages = (filtered_total_count + page_size - 1) // page_size
        clamped_page = min(page, total_pages)
        start_index = (clamped_page - 1) * page_size + 1

    sort_fields = [field.strip() for field in sort_by.split(",") if field.strip()]
    if not sort_fields:
        sort_fields = ["time"]

    sort_desc = sort_order.lower() == "desc"
    order_clauses = []
    for field in sort_fields:
        if field == "business":
            order_clauses.append(Business.name.desc() if sort_desc else Business.name.asc())
        elif field == "amount":
            order_clauses.append(
                TransferItem.amount.desc() if sort_desc else TransferItem.amount.asc()
            )
        elif field == "time":
            order_clauses.append(
                TransferItem.created_at.desc() if sort_desc else TransferItem.created_at.asc()
            )

    if not order_clauses:
        order_clauses.append(
            TransferItem.created_at.desc() if sort_desc else TransferItem.created_at.asc()
        )
    order_clauses.append(TransferItem.id.desc() if sort_desc else TransferItem.id.asc())

    offset = (clamped_page - 1) * page_size
    data_stmt = (
        select(
            TransferItem.id,
            TransferItem.session_id,
            TransferItem.description,
            TransferItem.amount,
            TransferItem.created_at,
            TransferItem.is_verified,
            User.id.label("cashier_id"),
            User.first_name,
            User.last_name,
            CashSession.session_number,
            CashSession.business_id,
            CashSession.session_date,
            Business.name.label("business_name"),
        )
        .join(CashSession, TransferItem.session_id == CashSession.id)
        .join(User, CashSession.cashier_id == User.id)
        .join(Business, CashSession.business_id == Business.id)
        .where(where_clause)
        .order_by(*order_clauses)
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    paginated_rows = data_result.all()

    paginated_items = []
    business_names_by_id: dict[str, str] = {}
    for row in paginated_rows:
        cashier_name = row.first_name or ""
        if row.last_name:
            cashier_name += f" {row.last_name[0]}."
        cashier_name = cashier_name.strip()

        business_id_str = str(row.business_id)
        business_names_by_id[business_id_str] = row.business_name

        paginated_items.append(
            {
                "id": row.id,
                "session_id": row.session_id,
                "session_number": row.session_number,
                "description": row.description,
                "amount": row.amount,
                "created_at": row.created_at,
                "cashier_id": row.cashier_id,
                "cashier_name": cashier_name,
                "is_verified": row.is_verified,
                "business_id": business_id_str,
                "business_name": row.business_name,
                "session_date": row.session_date,
            }
        )

    page_total_amount = sum((item.get("amount") or Decimal("0")) for item in paginated_items)

    option_conditions = [
        CashSession.session_date >= selected_from_date,
        CashSession.session_date <= selected_to_date,
        ~TransferItem.is_deleted,
        ~CashSession.is_deleted,
        Business.is_active,
    ]
    if selected_business_ids:
        option_conditions.append(CashSession.business_id.in_(selected_business_ids))

    cashier_options_stmt = (
        select(User.id, User.first_name, User.last_name)
        .join(CashSession, CashSession.cashier_id == User.id)
        .join(TransferItem, TransferItem.session_id == CashSession.id)
        .join(Business, CashSession.business_id == Business.id)
        .where(and_(*option_conditions))
        .distinct()
        .order_by(User.first_name, User.last_name)
    )
    cashier_options_result = await db.execute(cashier_options_stmt)

    cashier_options_map: dict[str, str] = {}
    for cashier_id, first_name, last_name in cashier_options_result.all():
        cashier_name = first_name or ""
        if last_name:
            cashier_name += f" {last_name[0]}."
        cashier_name = cashier_name.strip()
        cashier_options_map[str(cashier_id)] = cashier_name

    cashier_options = [
        {"id": cashier_id, "name": cashier_options_map[cashier_id]}
        for cashier_id in sorted(cashier_options_map, key=lambda key: cashier_options_map[key])
    ]

    return templates.TemplateResponse(
        request,
        "admin/transfers_date_range_report.html",
        {
            "current_user": current_user,
            "locale": locale,
            "_": _,
            "from_date": selected_from_date,
            "to_date": selected_to_date,
            "businesses": all_businesses,
            "selected_business_id": str(selected_business_ids[0]) if selected_business_ids else "",
            "selected_business_ids": [
                str(business_uuid) for business_uuid in selected_business_ids
            ],
            "all_transfer_items": paginated_items,
            "transfer_items_total_count": filtered_total_count,
            "filtered_total_amount": filtered_total_amount,
            "page_total_amount": page_total_amount,
            "businesses_by_id": business_names_by_id,
            "cashier_options": cashier_options,
            "current_page": clamped_page,
            "page_size": page_size,
            "total_pages": total_pages,
            "start_index": start_index,
            "filter_verified": filter_verified,
            "filter_cashier": filter_cashier,
            "filter_description": filter_description or "",
            "sort_by": sort_by,
            "sort_order": sort_order,
            "origin": origin or "",
        },
    )


@router.get("/expenses/date-range", response_class=HTMLResponse)
async def expenses_date_range_report(
    request: Request,
    single_date: str | None = Query(None, description="Single date (YYYY-MM-DD), maps to from=to"),
    from_date: str | None = Query(None, description="From date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="To date (YYYY-MM-DD)"),
    preset: str = Query(
        "today",
        pattern="^(today|yesterday|last_2_days|last_3_days|last_7_days|this_month|last_month|custom)$",
        description="Quick date preset",
    ),
    business_id: str | None = Query(None, description="Filter by single business ID (legacy)"),
    business_ids: list[str] | None = Query(None, description="Filter by one or more business IDs"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=10, le=50, description="Items per page"),
    sort_by: str = Query("time", description="Sort fields: business|cashier|time|amount"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    filter_cashier: str | None = Query(None, description="Filter by cashier ID"),
    filter_description: str | None = Query(
        None,
        description="Case-insensitive substring match on expense description",
    ),
    origin: str | None = Query(None, description="Navigation origin context"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """CP-REPORTS-07: Expenses report with date-range, filters, and pagination."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    normalized_from_date = from_date
    normalized_to_date = to_date

    if single_date and not from_date and not to_date:
        normalized_from_date = single_date
        normalized_to_date = single_date

    if not normalized_from_date and not normalized_to_date and preset != "custom":
        today = today_local()
        if preset == "yesterday":
            start, end = (today - timedelta(days=1), today - timedelta(days=1))
        elif preset == "last_2_days":
            start, end = (today - timedelta(days=1), today)
        elif preset == "last_3_days":
            start, end = (today - timedelta(days=2), today)
        elif preset == "last_7_days":
            start, end = (today - timedelta(days=6), today)
        elif preset == "this_month":
            start, end = (today.replace(day=1), today)
        elif preset == "last_month":
            start, end = (today - timedelta(days=29), today)
        else:
            start, end = (today, today)
        normalized_from_date = start.isoformat()
        normalized_to_date = end.isoformat()

    selected_from_date, selected_to_date = _resolve_transfer_report_range(
        normalized_from_date, normalized_to_date
    )

    selected_business_ids: list[UUID] = []
    if business_id and business_id.strip():
        try:
            selected_business_ids.append(UUID(business_id))
        except (ValueError, TypeError):
            pass

    for value in business_ids or []:
        if not value or not value.strip():
            continue
        try:
            parsed_business_id = UUID(value)
            if parsed_business_id not in selected_business_ids:
                selected_business_ids.append(parsed_business_id)
        except (ValueError, TypeError):
            continue

    all_businesses = await get_active_businesses(db)

    conditions = [
        CashSession.session_date >= selected_from_date,
        CashSession.session_date <= selected_to_date,
        ~ExpenseItem.is_deleted,
        ~CashSession.is_deleted,
        Business.is_active,
    ]

    if selected_business_ids:
        conditions.append(CashSession.business_id.in_(selected_business_ids))

    if filter_cashier and filter_cashier.strip():
        try:
            cashier_uuid = UUID(filter_cashier)
            conditions.append(User.id == cashier_uuid)
        except (ValueError, TypeError):
            filter_cashier = None

    if filter_description and filter_description.strip():
        conditions.append(ExpenseItem.description.ilike(f"%{filter_description.strip()}%"))

    where_clause = and_(*conditions)

    count_stmt = (
        select(func.count(ExpenseItem.id))
        .join(CashSession, ExpenseItem.session_id == CashSession.id)
        .join(User, CashSession.cashier_id == User.id)
        .join(Business, CashSession.business_id == Business.id)
        .where(where_clause)
    )
    count_result = await db.execute(count_stmt)
    filtered_total_count = count_result.scalar() or 0

    total_stmt = (
        select(func.coalesce(func.sum(ExpenseItem.amount), Decimal("0.00")))
        .join(CashSession, ExpenseItem.session_id == CashSession.id)
        .join(User, CashSession.cashier_id == User.id)
        .join(Business, CashSession.business_id == Business.id)
        .where(where_clause)
    )
    total_result = await db.execute(total_stmt)
    filtered_total_amount = total_result.scalar() or Decimal("0.00")

    if filtered_total_count == 0:
        total_pages = 0
        clamped_page = 1
        start_index = 0
    else:
        total_pages = (filtered_total_count + page_size - 1) // page_size
        clamped_page = min(page, total_pages)
        start_index = (clamped_page - 1) * page_size + 1

    sort_fields = [field.strip() for field in sort_by.split(",") if field.strip()]
    if not sort_fields:
        sort_fields = ["time"]

    sort_desc = sort_order.lower() == "desc"
    order_clauses = []
    for field in sort_fields:
        if field == "business":
            order_clauses.append(Business.name.desc() if sort_desc else Business.name.asc())
        elif field == "cashier":
            order_clauses.append(User.first_name.desc() if sort_desc else User.first_name.asc())
            order_clauses.append(User.last_name.desc() if sort_desc else User.last_name.asc())
        elif field == "amount":
            order_clauses.append(
                ExpenseItem.amount.desc() if sort_desc else ExpenseItem.amount.asc()
            )
        elif field == "time":
            order_clauses.append(
                ExpenseItem.created_at.desc() if sort_desc else ExpenseItem.created_at.asc()
            )

    if not order_clauses:
        order_clauses.append(
            ExpenseItem.created_at.desc() if sort_desc else ExpenseItem.created_at.asc()
        )
    order_clauses.append(ExpenseItem.id.desc() if sort_desc else ExpenseItem.id.asc())

    offset = (clamped_page - 1) * page_size
    data_stmt = (
        select(
            ExpenseItem.id,
            ExpenseItem.session_id,
            ExpenseItem.description,
            ExpenseItem.amount,
            ExpenseItem.created_at,
            User.id.label("cashier_id"),
            User.first_name,
            User.last_name,
            CashSession.session_number,
            CashSession.business_id,
            CashSession.session_date,
            Business.name.label("business_name"),
        )
        .join(CashSession, ExpenseItem.session_id == CashSession.id)
        .join(User, CashSession.cashier_id == User.id)
        .join(Business, CashSession.business_id == Business.id)
        .where(where_clause)
        .order_by(*order_clauses)
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    paginated_rows = data_result.all()

    paginated_items = []
    business_names_by_id: dict[str, str] = {}
    for row in paginated_rows:
        cashier_name = row.first_name or ""
        if row.last_name:
            cashier_name += f" {row.last_name[0]}."
        cashier_name = cashier_name.strip()

        business_id_str = str(row.business_id)
        business_names_by_id[business_id_str] = row.business_name

        paginated_items.append(
            {
                "id": row.id,
                "session_id": row.session_id,
                "session_number": row.session_number,
                "description": row.description,
                "amount": row.amount,
                "created_at": row.created_at,
                "cashier_id": row.cashier_id,
                "cashier_name": cashier_name,
                "business_id": business_id_str,
                "business_name": row.business_name,
                "session_date": row.session_date,
            }
        )

    page_total_amount = sum((item.get("amount") or Decimal("0")) for item in paginated_items)

    option_conditions = [
        CashSession.session_date >= selected_from_date,
        CashSession.session_date <= selected_to_date,
        ~ExpenseItem.is_deleted,
        ~CashSession.is_deleted,
        Business.is_active,
    ]
    if selected_business_ids:
        option_conditions.append(CashSession.business_id.in_(selected_business_ids))

    cashier_options_stmt = (
        select(User.id, User.first_name, User.last_name)
        .join(CashSession, CashSession.cashier_id == User.id)
        .join(ExpenseItem, ExpenseItem.session_id == CashSession.id)
        .join(Business, CashSession.business_id == Business.id)
        .where(and_(*option_conditions))
        .distinct()
        .order_by(User.first_name, User.last_name)
    )
    cashier_options_result = await db.execute(cashier_options_stmt)

    cashier_options_map: dict[str, str] = {}
    for cashier_id, first_name, last_name in cashier_options_result.all():
        cashier_name = first_name or ""
        if last_name:
            cashier_name += f" {last_name[0]}."
        cashier_name = cashier_name.strip()
        cashier_options_map[str(cashier_id)] = cashier_name

    cashier_options = [
        {"id": cashier_id, "name": cashier_options_map[cashier_id]}
        for cashier_id in sorted(cashier_options_map, key=lambda key: cashier_options_map[key])
    ]

    return templates.TemplateResponse(
        request,
        "admin/expenses_date_range_report.html",
        {
            "current_user": current_user,
            "locale": locale,
            "_": _,
            "from_date": selected_from_date,
            "to_date": selected_to_date,
            "businesses": all_businesses,
            "selected_business_id": str(selected_business_ids[0]) if selected_business_ids else "",
            "selected_business_ids": [
                str(business_uuid) for business_uuid in selected_business_ids
            ],
            "all_expense_items": paginated_items,
            "expense_items_total_count": filtered_total_count,
            "filtered_total_amount": filtered_total_amount,
            "page_total_amount": page_total_amount,
            "businesses_by_id": business_names_by_id,
            "cashier_options": cashier_options,
            "current_page": clamped_page,
            "page_size": page_size,
            "total_pages": total_pages,
            "start_index": start_index,
            "filter_cashier": filter_cashier,
            "filter_description": filter_description or "",
            "sort_by": sort_by,
            "sort_order": sort_order,
            "origin": origin or "",
            "preset": preset,
        },
    )


@router.get("/envelopes/date-range", response_class=HTMLResponse)
async def envelopes_date_range_report(
    request: Request,
    single_date: str | None = Query(None, description="Single date (YYYY-MM-DD), maps to from=to"),
    from_date: str | None = Query(None, description="From date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="To date (YYYY-MM-DD)"),
    preset: str = Query(
        "today",
        pattern="^(today|yesterday|last_2_days|last_3_days|last_7_days|last_month|custom)$",
        description="Quick date preset",
    ),
    business_id: str | None = Query(None, description="Filter by single business ID (legacy)"),
    business_ids: list[str] | None = Query(None, description="Filter by one or more business IDs"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=10, le=50, description="Items per page"),
    sort_by: str = Query("time", description="Sort fields: business|cashier|time|amount"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    filter_cashier: str | None = Query(None, description="Filter by cashier ID"),
    filter_amount_state: str = Query(
        "all",
        pattern="^(all|with_envelope|zero)$",
        description="Filter by envelope amount state",
    ),
    origin: str | None = Query(None, description="Navigation origin context"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """CP-REPORTS-08: Envelope report with date-range, filters, and pagination."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    normalized_from_date = from_date
    normalized_to_date = to_date

    if single_date and not from_date and not to_date:
        normalized_from_date = single_date
        normalized_to_date = single_date

    if not normalized_from_date and not normalized_to_date and preset != "custom":
        today = today_local()
        if preset == "yesterday":
            start, end = (today - timedelta(days=1), today - timedelta(days=1))
        elif preset == "last_2_days":
            start, end = (today - timedelta(days=1), today)
        elif preset == "last_3_days":
            start, end = (today - timedelta(days=2), today)
        elif preset == "last_7_days":
            start, end = (today - timedelta(days=6), today)
        elif preset == "last_month":
            start, end = (today - timedelta(days=29), today)
        else:
            start, end = (today, today)
        normalized_from_date = start.isoformat()
        normalized_to_date = end.isoformat()

    selected_from_date, selected_to_date = _resolve_transfer_report_range(
        normalized_from_date, normalized_to_date
    )

    selected_business_ids: list[UUID] = []
    if business_id and business_id.strip():
        try:
            selected_business_ids.append(UUID(business_id))
        except (ValueError, TypeError):
            pass

    for value in business_ids or []:
        if not value or not value.strip():
            continue
        try:
            parsed_business_id = UUID(value)
            if parsed_business_id not in selected_business_ids:
                selected_business_ids.append(parsed_business_id)
        except (ValueError, TypeError):
            continue

    all_businesses = await get_active_businesses(db)

    conditions = [
        CashSession.session_date >= selected_from_date,
        CashSession.session_date <= selected_to_date,
        ~CashSession.is_deleted,
        Business.is_active,
    ]

    if selected_business_ids:
        conditions.append(CashSession.business_id.in_(selected_business_ids))

    if filter_cashier and filter_cashier.strip():
        try:
            cashier_uuid = UUID(filter_cashier)
            conditions.append(User.id == cashier_uuid)
        except (ValueError, TypeError):
            filter_cashier = None

    if filter_amount_state == "with_envelope":
        conditions.append(CashSession.envelope_amount > Decimal("0.00"))
    elif filter_amount_state == "zero":
        conditions.append(CashSession.envelope_amount == Decimal("0.00"))

    where_clause = and_(*conditions)

    count_stmt = (
        select(func.count(CashSession.id))
        .join(User, CashSession.cashier_id == User.id)
        .join(Business, CashSession.business_id == Business.id)
        .where(where_clause)
    )
    count_result = await db.execute(count_stmt)
    filtered_total_count = count_result.scalar() or 0

    total_stmt = (
        select(func.coalesce(func.sum(CashSession.envelope_amount), Decimal("0.00")))
        .join(User, CashSession.cashier_id == User.id)
        .join(Business, CashSession.business_id == Business.id)
        .where(where_clause)
    )
    total_result = await db.execute(total_stmt)
    filtered_total_amount = total_result.scalar() or Decimal("0.00")

    if filtered_total_count == 0:
        total_pages = 0
        clamped_page = 1
        start_index = 0
    else:
        total_pages = (filtered_total_count + page_size - 1) // page_size
        clamped_page = min(page, total_pages)
        start_index = (clamped_page - 1) * page_size + 1

    sort_fields = [field.strip() for field in sort_by.split(",") if field.strip()]
    if not sort_fields:
        sort_fields = ["time"]

    sort_desc = sort_order.lower() == "desc"
    order_clauses = []
    for field in sort_fields:
        if field == "business":
            order_clauses.append(Business.name.desc() if sort_desc else Business.name.asc())
        elif field == "cashier":
            order_clauses.append(User.first_name.desc() if sort_desc else User.first_name.asc())
            order_clauses.append(User.last_name.desc() if sort_desc else User.last_name.asc())
        elif field == "amount":
            order_clauses.append(
                CashSession.envelope_amount.desc()
                if sort_desc
                else CashSession.envelope_amount.asc()
            )
        elif field == "time":
            order_clauses.append(
                CashSession.session_date.desc() if sort_desc else CashSession.session_date.asc()
            )
            order_clauses.append(
                CashSession.opened_time.desc() if sort_desc else CashSession.opened_time.asc()
            )

    if not order_clauses:
        order_clauses.append(
            CashSession.session_date.desc() if sort_desc else CashSession.session_date.asc()
        )
        order_clauses.append(
            CashSession.opened_time.desc() if sort_desc else CashSession.opened_time.asc()
        )
    order_clauses.append(CashSession.id.desc() if sort_desc else CashSession.id.asc())

    offset = (clamped_page - 1) * page_size
    data_stmt = (
        select(
            CashSession.id,
            CashSession.session_number,
            CashSession.business_id,
            CashSession.session_date,
            CashSession.opened_time,
            CashSession.status,
            CashSession.envelope_amount,
            User.id.label("cashier_id"),
            User.first_name,
            User.last_name,
            Business.name.label("business_name"),
        )
        .join(User, CashSession.cashier_id == User.id)
        .join(Business, CashSession.business_id == Business.id)
        .where(where_clause)
        .order_by(*order_clauses)
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    paginated_rows = data_result.all()

    paginated_sessions = []
    business_names_by_id: dict[str, str] = {}
    for row in paginated_rows:
        cashier_name = row.first_name or ""
        if row.last_name:
            cashier_name += f" {row.last_name[0]}."
        cashier_name = cashier_name.strip()

        business_id_str = str(row.business_id)
        business_names_by_id[business_id_str] = row.business_name

        paginated_sessions.append(
            {
                "session_id": row.id,
                "session_number": row.session_number,
                "amount": row.envelope_amount,
                "session_date": row.session_date,
                "opened_time": row.opened_time,
                "status": row.status,
                "cashier_id": row.cashier_id,
                "cashier_name": cashier_name,
                "business_id": business_id_str,
                "business_name": row.business_name,
            }
        )

    page_total_amount = sum((item.get("amount") or Decimal("0")) for item in paginated_sessions)

    option_conditions = [
        CashSession.session_date >= selected_from_date,
        CashSession.session_date <= selected_to_date,
        ~CashSession.is_deleted,
        Business.is_active,
    ]
    if selected_business_ids:
        option_conditions.append(CashSession.business_id.in_(selected_business_ids))
    if filter_amount_state == "with_envelope":
        option_conditions.append(CashSession.envelope_amount > Decimal("0.00"))
    elif filter_amount_state == "zero":
        option_conditions.append(CashSession.envelope_amount == Decimal("0.00"))

    cashier_options_stmt = (
        select(User.id, User.first_name, User.last_name)
        .join(CashSession, CashSession.cashier_id == User.id)
        .join(Business, CashSession.business_id == Business.id)
        .where(and_(*option_conditions))
        .distinct()
        .order_by(User.first_name, User.last_name)
    )
    cashier_options_result = await db.execute(cashier_options_stmt)

    cashier_options_map: dict[str, str] = {}
    for cashier_id, first_name, last_name in cashier_options_result.all():
        cashier_name = first_name or ""
        if last_name:
            cashier_name += f" {last_name[0]}."
        cashier_name = cashier_name.strip()
        cashier_options_map[str(cashier_id)] = cashier_name

    cashier_options = [
        {"id": cashier_id, "name": cashier_options_map[cashier_id]}
        for cashier_id in sorted(cashier_options_map, key=lambda key: cashier_options_map[key])
    ]

    return templates.TemplateResponse(
        request,
        "admin/envelopes_date_range_report.html",
        {
            "current_user": current_user,
            "locale": locale,
            "_": _,
            "from_date": selected_from_date,
            "to_date": selected_to_date,
            "businesses": all_businesses,
            "selected_business_id": str(selected_business_ids[0]) if selected_business_ids else "",
            "selected_business_ids": [
                str(business_uuid) for business_uuid in selected_business_ids
            ],
            "all_envelope_sessions": paginated_sessions,
            "envelope_sessions_total_count": filtered_total_count,
            "filtered_total_amount": filtered_total_amount,
            "page_total_amount": page_total_amount,
            "businesses_by_id": business_names_by_id,
            "cashier_options": cashier_options,
            "current_page": clamped_page,
            "page_size": page_size,
            "total_pages": total_pages,
            "start_index": start_index,
            "filter_cashier": filter_cashier,
            "filter_amount_state": filter_amount_state,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "origin": origin or "",
            "preset": preset,
        },
    )


@router.post("/transfer-items/{transfer_id}/verify")
async def verify_transfer_item(
    transfer_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Mark a transfer item as verified by the current user."""
    # Get the transfer item
    stmt = select(TransferItem).where(
        and_(TransferItem.id == transfer_id, ~TransferItem.is_deleted)
    )
    result = await db.execute(stmt)
    transfer = result.scalar_one_or_none()

    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer item not found")

    # Update verification fields
    transfer.is_verified = True
    transfer.verified_by = current_user.id
    transfer.verified_at = now_utc()

    await db.commit()
    await db.refresh(transfer)

    return {
        "id": str(transfer.id),
        "is_verified": transfer.is_verified,
        "verified_at": transfer.verified_at.isoformat() if transfer.verified_at else None,
    }


@router.post("/transfer-items/{transfer_id}/unverify")
async def unverify_transfer_item(
    transfer_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Mark a transfer item as unverified."""
    # Get the transfer item
    stmt = select(TransferItem).where(
        and_(TransferItem.id == transfer_id, ~TransferItem.is_deleted)
    )
    result = await db.execute(stmt)
    transfer = result.scalar_one_or_none()

    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer item not found")

    # Update verification fields
    transfer.is_verified = False
    transfer.verified_by = None
    transfer.verified_at = None

    await db.commit()
    await db.refresh(transfer)

    return {
        "id": str(transfer.id),
        "is_verified": transfer.is_verified,
        "verified_at": transfer.verified_at.isoformat() if transfer.verified_at else None,
    }


@router.get("/reconciliation/sessions", response_class=HTMLResponse)
async def get_business_sessions_detail(
    request: Request,
    business_id: str = Query(..., description="Business ID"),
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed session information for a business on a specific date."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    try:
        business_uuid = UUID(business_id)
        session_date = datetime.fromisoformat(date).date()
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid business_id or date format")

    # Get all sessions for this business and date
    stmt = (
        select(CashSession)
        .where(
            and_(
                CashSession.business_id == business_uuid,
                CashSession.session_date == session_date,
                ~CashSession.is_deleted,
            )
        )
        .order_by(CashSession.session_number)
        .options(selectinload(CashSession.cashier))
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    # Calculate totals for each session
    session_details = []
    for session in sessions:
        # Calculate cash sales (same formula as in comparison)
        if session.status == "CLOSED" and session.final_cash is not None:
            cash_sales = (
                (session.final_cash - session.initial_cash)
                + (session.envelope_amount or Decimal("0"))
                + (session.expenses or Decimal("0"))
                - (session.credit_payments_collected or Decimal("0"))
                + (session.bank_transfer_total or Decimal("0"))
            )
        else:
            cash_sales = Decimal("0")

        # Card sales
        card_sales = (
            session.card_total or Decimal("0") if session.status == "CLOSED" else Decimal("0")
        )

        # Credit sales
        credit_sales = (
            session.credit_sales_total or Decimal("0")
            if session.status == "CLOSED"
            else Decimal("0")
        )

        # Total
        total_sales = cash_sales + card_sales + credit_sales

        session_details.append(
            {
                "session": session,
                "cash_sales": cash_sales,
                "card_sales": card_sales,
                "credit_sales": credit_sales,
                "total_sales": total_sales,
            }
        )

    return templates.TemplateResponse(
        request,
        "admin/partials/sessions_summary.html",
        {
            "business_id": business_id,
            "sessions": session_details,
            "locale": locale,
            "_": _,
        },
    )


@router.get("/reconciliation/session-notes", response_class=HTMLResponse)
async def get_business_session_notes(
    request: Request,
    business_id: str = Query(..., description="Business ID"),
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get session notes for a business on a specific date."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    try:
        business_uuid = UUID(business_id)
        session_date = datetime.fromisoformat(date).date()
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid business_id or date format")

    stmt = (
        select(CashSession)
        .where(
            and_(
                CashSession.business_id == business_uuid,
                CashSession.session_date == session_date,
                ~CashSession.is_deleted,
                CashSession.notes.is_not(None),
                CashSession.notes != "",
            )
        )
        .order_by(CashSession.session_number)
        .options(selectinload(CashSession.cashier))
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    return templates.TemplateResponse(
        request,
        "admin/partials/session_notes.html",
        {
            "sessions": sessions,
            "locale": locale,
            "_": _,
        },
    )
