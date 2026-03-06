# File: src/cashpilot/api/admin.py
import secrets
import string
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from urllib.parse import urlsplit
from uuid import UUID
from zoneinfo import ZoneInfo

from babel.dates import format_date, format_time
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import and_, case, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cashpilot.api.auth_helpers import require_admin
from cashpilot.api.utils import (
    get_active_businesses,
    get_locale,
    get_translation_function,
    parse_currency,
    templates,
)
from cashpilot.core.db import get_db
from cashpilot.core.logging import get_logger
from cashpilot.core.security import hash_password
from cashpilot.core.validators import validate_currency
from cashpilot.models.business import Business
from cashpilot.models.cash_session import CashSession
from cashpilot.models.daily_reconciliation import DailyReconciliation
from cashpilot.models.envelope_deposit_batch import EnvelopeDepositBatch
from cashpilot.models.envelope_deposit_event import EnvelopeDepositEvent
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
DEFAULT_ENVELOPES_REPORT_URL = "/admin/envelopes/date-range"


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
    sort_by: str = Query("business,time", description="Sort fields: business|time|amount"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort order"),
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
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort order"),
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
        pattern="^(today|yesterday|last_2_days|last_3_days|last_7_days|this_month|custom)$",
        description="Quick date preset",
    ),
    business_id: str | None = Query(None, description="Filter by single business ID (legacy)"),
    business_ids: list[str] | None = Query(None, description="Filter by one or more business IDs"),
    page: int = Query(1, ge=1, description="Page number (unused, pagination disabled)"),
    page_size: int = Query(
        20,
        ge=10,
        le=50,
        description="Items per page (unused, pagination disabled)",
    ),
    sort_by: str = Query("time", description="Sort fields: business|cashier|time|amount"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort order"),
    filter_cashier: str | None = Query(None, description="Filter by cashier ID"),
    origin: str | None = Query(None, description="Navigation origin context"),
    start_deposit: bool = Query(False, description="Show guidance to select envelopes"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """CP-REPORTS-08: Envelope report with date-range, filters, and pagination."""
    locale = get_locale(request)
    _ = get_translation_function(locale)
    babel_locale = "es_PY" if locale == "es" else "en"

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
        CashSession.envelope_amount > Decimal("0.00"),
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

    summary_stmt = (
        select(
            CashSession.business_id,
            Business.name.label("business_name"),
            func.count(CashSession.id).label("session_count"),
            func.coalesce(func.sum(CashSession.envelope_amount), Decimal("0.00")).label(
                "envelope_total"
            ),
            func.max(CashSession.session_date).label("last_session_date"),
        )
        .join(User, CashSession.cashier_id == User.id)
        .join(Business, CashSession.business_id == Business.id)
        .where(where_clause)
        .group_by(CashSession.business_id, Business.name)
        .order_by(Business.name.asc())
    )
    summary_result = await db.execute(summary_stmt)
    summary_rows = summary_result.all()

    total_businesses_with_envelopes = len(summary_rows)
    average_envelope_amount = (
        (filtered_total_amount / filtered_total_count)
        if filtered_total_count > 0
        else Decimal("0.00")
    )

    envelopes_by_business = []
    for row in summary_rows:
        business_total = row.envelope_total or Decimal("0.00")
        percentage = (
            (business_total / filtered_total_amount) * Decimal("100")
            if filtered_total_amount > 0
            else Decimal("0.00")
        )
        envelopes_by_business.append(
            {
                "business_id": str(row.business_id),
                "business_name": row.business_name,
                "session_count": row.session_count or 0,
                "total_amount": business_total,
                "percentage": percentage,
                "last_session_date": row.last_session_date,
            }
        )

    if filtered_total_count == 0:
        total_pages = 0
        clamped_page = 1
        start_index = 0
    else:
        total_pages = 1
        clamped_page = 1
        start_index = 1

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

    deposited_totals_subquery = (
        select(
            EnvelopeDepositEvent.session_id.label("session_id"),
            func.coalesce(func.sum(EnvelopeDepositEvent.amount), Decimal("0.00")).label(
                "deposited_total"
            ),
        )
        .where(~EnvelopeDepositEvent.is_deleted)
        .group_by(EnvelopeDepositEvent.session_id)
        .subquery()
    )

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
            func.coalesce(
                deposited_totals_subquery.c.deposited_total,
                Decimal("0.00"),
            ).label("deposited_total"),
        )
        .join(User, CashSession.cashier_id == User.id)
        .join(Business, CashSession.business_id == Business.id)
        .outerjoin(
            deposited_totals_subquery,
            deposited_totals_subquery.c.session_id == CashSession.id,
        )
        .where(where_clause)
        .order_by(*order_clauses)
    )
    data_result = await db.execute(data_stmt)
    paginated_rows = data_result.all()

    paginated_sessions = []
    business_names_by_id: dict[str, str] = {}
    today = today_local()
    yesterday = today - timedelta(days=1)

    def build_session_time_label(session_date: date, opened_time: time | None) -> str:
        weekday_name = session_date.strftime("%A")
        translated_weekday = _(weekday_name)
        date_label = format_date(session_date, format="short", locale=babel_locale)
        time_label = (
            format_time(opened_time, format="HH:mm", locale=babel_locale) if opened_time else "—"
        )

        if session_date == today:
            relative_label = _("Today")
            return f"{relative_label} ({translated_weekday}) · {date_label} · {time_label}"
        if session_date == yesterday:
            relative_label = _("Yesterday")
            return f"{relative_label} ({translated_weekday}) · {date_label} · {time_label}"

        return f"{translated_weekday} · {date_label} · {time_label}"

    for row in paginated_rows:
        cashier_name = row.first_name or ""
        if row.last_name:
            cashier_name += f" {row.last_name[0]}."
        cashier_name = cashier_name.strip()

        envelope_amount = row.envelope_amount or Decimal("0.00")
        deposited_total = row.deposited_total or Decimal("0.00")
        pending_amount = envelope_amount - deposited_total
        if pending_amount < Decimal("0.00"):
            pending_amount = Decimal("0.00")

        if deposited_total <= Decimal("0.00"):
            deposit_status = "PENDING"
        elif pending_amount > Decimal("0.00"):
            deposit_status = "PARTIAL"
        else:
            deposit_status = "DEPOSITED"

        business_id_str = str(row.business_id)
        business_names_by_id[business_id_str] = row.business_name

        paginated_sessions.append(
            {
                "session_id": row.id,
                "session_number": row.session_number,
                "amount": envelope_amount,
                "session_date": row.session_date,
                "opened_time": row.opened_time,
                "session_time_label": build_session_time_label(row.session_date, row.opened_time),
                "status": row.status,
                "cashier_id": row.cashier_id,
                "cashier_name": cashier_name,
                "business_id": business_id_str,
                "business_name": row.business_name,
                "deposited_total": deposited_total,
                "pending_amount": pending_amount,
                "deposit_status": deposit_status,
                "is_depositable": pending_amount > Decimal("0.00"),
            }
        )

    session_ids = [item["session_id"] for item in paginated_sessions]
    deposit_events_by_session: dict[str, list[dict[str, str | int]]] = {
        str(session_id): [] for session_id in session_ids
    }

    if session_ids:
        events_stmt = (
            select(
                EnvelopeDepositEvent.session_id,
                EnvelopeDepositEvent.batch_id,
                EnvelopeDepositEvent.amount,
                EnvelopeDepositEvent.deposit_date,
                EnvelopeDepositEvent.note,
                EnvelopeDepositEvent.deposited_by_name,
                EnvelopeDepositEvent.created_at,
            )
            .where(
                and_(
                    EnvelopeDepositEvent.session_id.in_(session_ids),
                    ~EnvelopeDepositEvent.is_deleted,
                )
            )
            .order_by(
                EnvelopeDepositEvent.deposit_date.desc(),
                EnvelopeDepositEvent.created_at.desc(),
            )
        )
        events_result = await db.execute(events_stmt)

        raw_events = events_result.all()
        batch_ids = {
            event.batch_id for event in raw_events if getattr(event, "batch_id", None) is not None
        }

        batch_summary: dict[str, dict[str, Decimal | list[dict[str, str]]]] = {}
        if batch_ids:
            batch_events_stmt = (
                select(
                    EnvelopeDepositEvent.batch_id,
                    EnvelopeDepositEvent.session_id,
                    EnvelopeDepositEvent.amount,
                    CashSession.session_number,
                )
                .join(CashSession, CashSession.id == EnvelopeDepositEvent.session_id)
                .where(
                    and_(
                        EnvelopeDepositEvent.batch_id.in_(batch_ids),
                        ~EnvelopeDepositEvent.is_deleted,
                    )
                )
            )
            batch_events_result = await db.execute(batch_events_stmt)

            for batch_event in batch_events_result.all():
                if batch_event.batch_id is None:
                    continue

                batch_key = str(batch_event.batch_id)
                if batch_key not in batch_summary:
                    batch_summary[batch_key] = {
                        "total_amount": Decimal("0.00"),
                        "sessions": [],
                    }

                amount_value = batch_event.amount or Decimal("0.00")
                batch_summary[batch_key]["total_amount"] += amount_value

                session_key = str(batch_event.session_id)
                session_label = (
                    f"#{batch_event.session_number}"
                    if batch_event.session_number
                    else f"#{session_key[:8]}"
                )

                existing_sessions = batch_summary[batch_key]["sessions"]
                if not any(item.get("session_id") == session_key for item in existing_sessions):
                    existing_sessions.append(
                        {
                            "session_id": session_key,
                            "session_label": session_label,
                        }
                    )

        for event in raw_events:
            session_key = str(event.session_id)
            if session_key not in deposit_events_by_session:
                deposit_events_by_session[session_key] = []

            batch_key = str(event.batch_id) if event.batch_id else ""
            batch_data = batch_summary.get(batch_key, None) if batch_key else None

            other_session_labels: list[str] = []
            if batch_data:
                for batch_session in batch_data.get("sessions", []):
                    if batch_session.get("session_id") != session_key:
                        other_session_labels.append(batch_session.get("session_label", ""))

            deposit_events_by_session[session_key].append(
                {
                    "amount": f"{event.amount or Decimal('0.00')}",
                    "deposit_date": event.deposit_date.isoformat() if event.deposit_date else "",
                    "note": event.note or "",
                    "deposited_by_name": event.deposited_by_name or "",
                    "created_at": event.created_at.isoformat() if event.created_at else "",
                    "batch_total_amount": (
                        f"{batch_data.get('total_amount', Decimal('0.00'))}"
                        if batch_data
                        else "0.00"
                    ),
                    "batch_session_count": (
                        len(batch_data.get("sessions", [])) if batch_data else 0
                    ),
                    "batch_other_session_labels": [
                        label for label in other_session_labels if label
                    ],
                }
            )

    grouped_sessions_map: dict[str, dict] = {}
    for item in paginated_sessions:
        business_id = item["business_id"]
        if business_id not in grouped_sessions_map:
            grouped_sessions_map[business_id] = {
                "business_id": business_id,
                "business_name": item["business_name"],
                "sessions": [],
                "session_count": 0,
                "total_amount": Decimal("0.00"),
            }

        grouped_sessions_map[business_id]["sessions"].append(item)
        grouped_sessions_map[business_id]["session_count"] += 1
        grouped_sessions_map[business_id]["total_amount"] += item.get("amount") or Decimal("0.00")

    ordered_business_ids = [item["business_id"] for item in envelopes_by_business]
    envelope_sessions_by_business = []

    for business_id in ordered_business_ids:
        if business_id in grouped_sessions_map:
            envelope_sessions_by_business.append(grouped_sessions_map[business_id])

    for business_id, grouped in grouped_sessions_map.items():
        if business_id not in ordered_business_ids:
            envelope_sessions_by_business.append(grouped)

    envelope_sessions_by_business.sort(
        key=lambda grouped: (grouped.get("business_name") or "").casefold()
    )

    page_total_amount = sum((item.get("amount") or Decimal("0")) for item in paginated_sessions)

    option_conditions = [
        CashSession.session_date >= selected_from_date,
        CashSession.session_date <= selected_to_date,
        CashSession.envelope_amount > Decimal("0.00"),
        ~CashSession.is_deleted,
        Business.is_active,
    ]
    if selected_business_ids:
        option_conditions.append(CashSession.business_id.in_(selected_business_ids))

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
            "total_businesses_with_envelopes": total_businesses_with_envelopes,
            "average_envelope_amount": average_envelope_amount,
            "envelopes_by_business": envelopes_by_business,
            "envelope_sessions_by_business": envelope_sessions_by_business,
            "page_total_amount": page_total_amount,
            "businesses_by_id": business_names_by_id,
            "cashier_options": cashier_options,
            "current_page": clamped_page,
            "page_size": page_size,
            "total_pages": total_pages,
            "start_index": start_index,
            "filter_cashier": filter_cashier,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "origin": origin or "",
            "preset": preset,
            "deposit_events_by_session": deposit_events_by_session,
            "show_select_envelopes_hint": start_deposit,
        },
    )


def _resolve_envelopes_return_to(return_to: str | None) -> str:
    """Allow redirects only to the envelopes date-range report."""
    if not return_to:
        return DEFAULT_ENVELOPES_REPORT_URL

    parsed = urlsplit(return_to)
    if parsed.scheme or parsed.netloc:
        return DEFAULT_ENVELOPES_REPORT_URL

    if not return_to.startswith("/") or return_to.startswith("//"):
        return DEFAULT_ENVELOPES_REPORT_URL

    if not return_to.startswith(DEFAULT_ENVELOPES_REPORT_URL):
        return DEFAULT_ENVELOPES_REPORT_URL

    return return_to


async def _load_envelope_selection_rows(
    db: AsyncSession,
    session_ids: list[UUID],
) -> list[dict]:
    """Load selected envelope sessions with deposited/pending calculations."""
    if not session_ids:
        return []

    unique_ids = list(dict.fromkeys(session_ids))

    deposited_totals_subquery = (
        select(
            EnvelopeDepositEvent.session_id.label("session_id"),
            func.coalesce(func.sum(EnvelopeDepositEvent.amount), Decimal("0.00")).label(
                "deposited_total"
            ),
        )
        .where(~EnvelopeDepositEvent.is_deleted)
        .group_by(EnvelopeDepositEvent.session_id)
        .subquery()
    )

    stmt = (
        select(
            CashSession.id,
            CashSession.session_number,
            CashSession.session_date,
            CashSession.opened_time,
            CashSession.envelope_amount,
            User.first_name,
            User.last_name,
            Business.name.label("business_name"),
            func.coalesce(
                deposited_totals_subquery.c.deposited_total,
                Decimal("0.00"),
            ).label("deposited_total"),
        )
        .join(User, CashSession.cashier_id == User.id)
        .join(Business, CashSession.business_id == Business.id)
        .outerjoin(
            deposited_totals_subquery,
            deposited_totals_subquery.c.session_id == CashSession.id,
        )
        .where(
            and_(
                CashSession.id.in_(unique_ids),
                ~CashSession.is_deleted,
                Business.is_active,
                CashSession.envelope_amount > Decimal("0.00"),
            )
        )
        .order_by(
            Business.name.asc(),
            CashSession.session_date.asc(),
            CashSession.opened_time.asc(),
            CashSession.id.asc(),
        )
    )

    result = await db.execute(stmt)
    rows = []

    for item in result.all():
        envelope_amount = item.envelope_amount or Decimal("0.00")
        deposited_total = item.deposited_total or Decimal("0.00")
        pending_amount = envelope_amount - deposited_total
        if pending_amount <= Decimal("0.00"):
            continue

        cashier_name = item.first_name or ""
        if item.last_name:
            cashier_name += f" {item.last_name[0]}."
        cashier_name = cashier_name.strip()

        rows.append(
            {
                "session_id": item.id,
                "session_number": item.session_number,
                "session_date": item.session_date,
                "opened_time": item.opened_time,
                "business_name": item.business_name,
                "cashier_name": cashier_name,
                "envelope_amount": envelope_amount,
                "deposited_total": deposited_total,
                "pending_amount": pending_amount,
            }
        )

    return rows


@router.get("/envelopes/deposits/new", response_class=HTMLResponse)
async def envelopes_new_deposit_screen(
    request: Request,
    session_ids: list[str] | None = Query(None),
    return_to: str | None = Query(None),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Render dedicated envelope batch deposit screen."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    parsed_session_ids: list[UUID] = []
    for raw_session_id in session_ids or []:
        if not raw_session_id or not raw_session_id.strip():
            continue
        try:
            parsed_session_id = UUID(raw_session_id)
        except (ValueError, TypeError):
            continue
        if parsed_session_id not in parsed_session_ids:
            parsed_session_ids.append(parsed_session_id)

    selected_rows = await _load_envelope_selection_rows(db, parsed_session_ids)
    safe_return_to = _resolve_envelopes_return_to(return_to)

    if not parsed_session_ids or not selected_rows:
        return RedirectResponse(
            url=f"{DEFAULT_ENVELOPES_REPORT_URL}?start_deposit=1",
            status_code=303,
        )

    active_users_stmt = select(User).where(User.is_active).order_by(User.first_name, User.last_name)
    active_users_result = await db.execute(active_users_stmt)
    active_users = active_users_result.scalars().all()

    depositor_user_options = [
        {
            "id": str(user.id),
            "label": user.display_name_email,
        }
        for user in active_users
    ]

    return templates.TemplateResponse(
        request,
        "admin/envelopes_new_deposit.html",
        {
            "current_user": current_user,
            "locale": locale,
            "_": _,
            "selected_rows": selected_rows,
            "errors": [],
            "field_errors": {},
            "amount_values": {},
            "note_values": {},
            "depositor_user_options": depositor_user_options,
            "selected_depositor_user_id": str(current_user.id),
            "deposit_date": today_local().isoformat(),
            "return_to": safe_return_to,
            "selected_session_ids": [str(row["session_id"]) for row in selected_rows],
        },
    )


@router.post("/envelopes/deposits/batch")
async def envelopes_batch_deposit_submit(
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Persist one envelope deposit event per selected envelope row."""
    locale = get_locale(request)
    _ = get_translation_function(locale)
    form_data = await request.form()

    selected_session_id_values = form_data.getlist("session_ids")
    return_to = _resolve_envelopes_return_to(form_data.get("return_to"))
    deposit_date_raw = (form_data.get("deposit_date") or "").strip()
    selected_depositor_user_id = (form_data.get("depositor_user_id") or "").strip()

    parsed_session_ids: list[UUID] = []
    invalid_session_ids = False
    for raw_session_id in selected_session_id_values:
        if not raw_session_id or not raw_session_id.strip():
            continue
        try:
            parsed_session_id = UUID(raw_session_id)
        except (ValueError, TypeError):
            invalid_session_ids = True
            continue
        if parsed_session_id not in parsed_session_ids:
            parsed_session_ids.append(parsed_session_id)

    selected_rows = await _load_envelope_selection_rows(db, parsed_session_ids)
    selected_rows_by_id = {str(row["session_id"]): row for row in selected_rows}

    errors: list[str] = []
    field_errors: dict[str, str] = {}
    amount_values: dict[str, str] = {}
    note_values: dict[str, str] = {}

    active_users_stmt = select(User).where(User.is_active).order_by(User.first_name, User.last_name)
    active_users_result = await db.execute(active_users_stmt)
    active_users = active_users_result.scalars().all()
    depositor_user_options = [
        {
            "id": str(user.id),
            "label": user.display_name_email,
        }
        for user in active_users
    ]

    selected_depositor_user = None
    if not selected_depositor_user_id:
        field_errors["depositor_user_id"] = _("Select who deposited this batch.")
    else:
        try:
            selected_depositor_uuid = UUID(selected_depositor_user_id)
            for user in active_users:
                if user.id == selected_depositor_uuid:
                    selected_depositor_user = user
                    break
            if selected_depositor_user is None:
                field_errors["depositor_user_id"] = _("Selected depositor is not valid.")
        except (ValueError, TypeError):
            field_errors["depositor_user_id"] = _("Selected depositor is not valid.")

    if invalid_session_ids:
        errors.append(_("One or more selected envelopes are invalid."))

    if not parsed_session_ids:
        errors.append(_("Select at least one envelope to continue."))

    if parsed_session_ids and len(selected_rows) != len(parsed_session_ids):
        errors.append(_("Some selected envelopes are no longer available for deposit."))

    try:
        deposit_date = datetime.fromisoformat(deposit_date_raw).date()
    except (ValueError, TypeError):
        deposit_date = None
        errors.append(_("Deposit date is required and must be valid."))

    if deposit_date is not None:
        for row in selected_rows:
            if deposit_date < row["session_date"]:
                field_errors["deposit_date"] = _(
                    "Deposit date cannot be earlier than selected session date."
                )
                break

    deposit_rows_payload: dict[str, dict] = {}
    for session_id_str, row in selected_rows_by_id.items():
        amount_field_name = f"amount_{session_id_str}"
        note_field_name = f"note_{session_id_str}"

        raw_amount = (form_data.get(amount_field_name) or "").strip()
        raw_note = (form_data.get(note_field_name) or "").strip()

        amount_values[amount_field_name] = raw_amount
        note_values[note_field_name] = raw_note

        amount_value = parse_currency(raw_amount)

        if amount_value is None:
            field_errors[amount_field_name] = _("Enter a valid amount.")
            continue
        try:
            validate_currency(amount_value)
        except ValueError:
            field_errors[amount_field_name] = _(
                "Currency value too large. Maximum allowed: 9,999,999,999.99"
            )
            continue
        if amount_value <= Decimal("0.00"):
            field_errors[amount_field_name] = _("Amount must be greater than zero.")
            continue
        if amount_value > row["pending_amount"]:
            field_errors[amount_field_name] = _("Amount cannot exceed pending.")
            continue

        pending_after = row["pending_amount"] - amount_value
        if pending_after > Decimal("0.00") and not raw_note:
            field_errors[note_field_name] = _(
                "A note is required when envelope remains pending after this deposit."
            )
            continue

        deposit_rows_payload[session_id_str] = {
            "amount": amount_value,
            "note": raw_note,
        }

    if field_errors:
        errors.append(_("Fix the highlighted amounts and try again."))

    if errors:
        return templates.TemplateResponse(
            request,
            "admin/envelopes_new_deposit.html",
            {
                "current_user": current_user,
                "locale": locale,
                "_": _,
                "selected_rows": selected_rows,
                "errors": errors,
                "field_errors": field_errors,
                "amount_values": amount_values,
                "note_values": note_values,
                "depositor_user_options": depositor_user_options,
                "selected_depositor_user_id": selected_depositor_user_id,
                "deposit_date": deposit_date_raw,
                "return_to": return_to,
                "selected_session_ids": [str(row["session_id"]) for row in selected_rows],
            },
            status_code=400,
        )

    requested_amounts_by_session: dict[UUID, Decimal] = {
        UUID(session_id_str): payload["amount"]
        for session_id_str, payload in deposit_rows_payload.items()
    }
    requested_session_ids = list(requested_amounts_by_session.keys())

    locked_sessions_stmt = (
        select(CashSession.id, CashSession.envelope_amount)
        .where(
            and_(
                CashSession.id.in_(requested_session_ids),
                ~CashSession.is_deleted,
            )
        )
        .with_for_update()
    )
    locked_sessions_result = await db.execute(locked_sessions_stmt)
    locked_sessions = {
        row.id: row.envelope_amount or Decimal("0.00") for row in locked_sessions_result.all()
    }

    if len(locked_sessions) != len(requested_session_ids):
        errors.append(_("Some selected envelopes are no longer available for deposit."))

    if not errors:
        deposited_totals_stmt = (
            select(
                EnvelopeDepositEvent.session_id,
                func.coalesce(func.sum(EnvelopeDepositEvent.amount), Decimal("0.00")).label(
                    "deposited_total"
                ),
            )
            .where(
                and_(
                    EnvelopeDepositEvent.session_id.in_(requested_session_ids),
                    ~EnvelopeDepositEvent.is_deleted,
                )
            )
            .group_by(EnvelopeDepositEvent.session_id)
        )
        deposited_totals_result = await db.execute(deposited_totals_stmt)
        deposited_totals_by_session = {
            row.session_id: row.deposited_total or Decimal("0.00")
            for row in deposited_totals_result.all()
        }

        for session_id, requested_amount in requested_amounts_by_session.items():
            envelope_amount = locked_sessions.get(session_id, Decimal("0.00"))
            deposited_total = deposited_totals_by_session.get(session_id, Decimal("0.00"))
            pending_amount = envelope_amount - deposited_total
            if pending_amount < Decimal("0.00"):
                pending_amount = Decimal("0.00")

            if requested_amount > pending_amount:
                field_errors[f"amount_{session_id}"] = _("Amount cannot exceed pending.")

    if field_errors:
        errors.append(_("Fix the highlighted amounts and try again."))

    if errors:
        refreshed_rows = await _load_envelope_selection_rows(db, parsed_session_ids)
        return templates.TemplateResponse(
            request,
            "admin/envelopes_new_deposit.html",
            {
                "current_user": current_user,
                "locale": locale,
                "_": _,
                "selected_rows": refreshed_rows,
                "errors": errors,
                "field_errors": field_errors,
                "amount_values": amount_values,
                "note_values": note_values,
                "depositor_user_options": depositor_user_options,
                "selected_depositor_user_id": selected_depositor_user_id,
                "deposit_date": deposit_date_raw,
                "return_to": return_to,
                "selected_session_ids": [str(row["session_id"]) for row in refreshed_rows],
            },
            status_code=400,
        )

    deposit_batch = EnvelopeDepositBatch(
        deposit_date=deposit_date,
        deposited_by_user_id=selected_depositor_user.id,
        created_by=current_user.id,
    )
    db.add(deposit_batch)
    await db.flush()

    for session_id_str, payload in deposit_rows_payload.items():
        deposit_event = EnvelopeDepositEvent(
            batch_id=deposit_batch.id,
            session_id=UUID(session_id_str),
            amount=payload["amount"],
            deposit_date=deposit_date,
            note=payload["note"] or None,
            deposited_by_name=selected_depositor_user.display_name,
            created_by=current_user.id,
        )
        db.add(deposit_event)

    await db.commit()

    return RedirectResponse(url=return_to, status_code=303)


@router.get("/envelopes/deposits", response_class=HTMLResponse)
async def envelopes_deposits_list(
    request: Request,
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Render envelope deposits history grouped by deposit batch."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    today = today_local()
    selected_to_date = to_date or today
    selected_from_date = from_date or (selected_to_date - timedelta(days=30))

    if selected_from_date > selected_to_date:
        selected_from_date, selected_to_date = selected_to_date, selected_from_date

    batch_totals_subquery = (
        select(
            EnvelopeDepositEvent.batch_id.label("batch_id"),
            func.count(EnvelopeDepositEvent.id).label("envelopes_count"),
            func.coalesce(func.sum(EnvelopeDepositEvent.amount), Decimal("0.00")).label(
                "total_amount"
            ),
        )
        .where(
            and_(
                EnvelopeDepositEvent.batch_id.isnot(None),
                ~EnvelopeDepositEvent.is_deleted,
            )
        )
        .group_by(EnvelopeDepositEvent.batch_id)
        .subquery()
    )

    batches_stmt = (
        select(
            EnvelopeDepositBatch.id,
            EnvelopeDepositBatch.deposit_date,
            EnvelopeDepositBatch.created_at,
            User.first_name,
            User.last_name,
            User.email,
            func.coalesce(batch_totals_subquery.c.envelopes_count, 0).label("envelopes_count"),
            func.coalesce(batch_totals_subquery.c.total_amount, Decimal("0.00")).label(
                "total_amount"
            ),
        )
        .join(User, User.id == EnvelopeDepositBatch.deposited_by_user_id)
        .outerjoin(
            batch_totals_subquery,
            batch_totals_subquery.c.batch_id == EnvelopeDepositBatch.id,
        )
        .where(
            and_(
                EnvelopeDepositBatch.deposit_date >= selected_from_date,
                EnvelopeDepositBatch.deposit_date <= selected_to_date,
            )
        )
        .order_by(EnvelopeDepositBatch.deposit_date.desc(), EnvelopeDepositBatch.created_at.desc())
    )
    batches_result = await db.execute(batches_stmt)

    batch_rows: list[dict] = []
    batch_ids: list[UUID] = []
    for row in batches_result.all():
        depositor_name = (f"{row.first_name or ''} {row.last_name or ''}").strip()
        if not depositor_name:
            depositor_name = row.email or "—"

        batch_id = row.id
        batch_ids.append(batch_id)
        batch_rows.append(
            {
                "batch_id": str(batch_id),
                "deposit_date": row.deposit_date,
                "created_at": row.created_at,
                "deposited_by": depositor_name,
                "envelopes_count": int(row.envelopes_count or 0),
                "total_amount": row.total_amount or Decimal("0.00"),
                "envelope_rows": [],
            }
        )

    batch_rows_by_id = {item["batch_id"]: item for item in batch_rows}

    if batch_ids:
        items_stmt = (
            select(
                EnvelopeDepositEvent.batch_id,
                EnvelopeDepositEvent.session_id,
                EnvelopeDepositEvent.amount,
                EnvelopeDepositEvent.note,
                CashSession.session_number,
                CashSession.session_date,
                Business.name.label("business_name"),
            )
            .join(CashSession, CashSession.id == EnvelopeDepositEvent.session_id)
            .join(Business, Business.id == CashSession.business_id)
            .where(
                and_(
                    EnvelopeDepositEvent.batch_id.in_(batch_ids),
                    ~EnvelopeDepositEvent.is_deleted,
                )
            )
            .order_by(
                Business.name.asc(),
                CashSession.session_date.asc(),
                CashSession.opened_time.asc(),
            )
        )
        items_result = await db.execute(items_stmt)

        for item in items_result.all():
            if not item.batch_id:
                continue

            batch_key = str(item.batch_id)
            parent = batch_rows_by_id.get(batch_key)
            if not parent:
                continue

            session_id_str = str(item.session_id)
            session_label = (
                f"#{item.session_number}" if item.session_number else f"#{session_id_str[:8]}"
            )
            parent["envelope_rows"].append(
                {
                    "session_id": session_id_str,
                    "session_label": session_label,
                    "session_date": item.session_date,
                    "business_name": item.business_name,
                    "amount": item.amount or Decimal("0.00"),
                    "note": item.note or "",
                }
            )

    total_batches = len(batch_rows)
    grand_total_amount = sum((item["total_amount"] for item in batch_rows), Decimal("0.00"))

    return templates.TemplateResponse(
        request,
        "admin/envelopes_deposits_list.html",
        {
            "current_user": current_user,
            "locale": locale,
            "_": _,
            "from_date": selected_from_date,
            "to_date": selected_to_date,
            "deposit_batches": batch_rows,
            "total_batches": total_batches,
            "grand_total_amount": grand_total_amount,
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
