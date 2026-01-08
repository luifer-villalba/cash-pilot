# File: src/cashpilot/api/admin.py
import secrets
import string
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy import and_, case, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cashpilot.api.auth_helpers import require_admin
from cashpilot.api.utils import get_active_businesses, get_locale, get_translation_function
from cashpilot.core.db import get_db
from cashpilot.core.logging import get_logger
from cashpilot.core.security import hash_password
from cashpilot.models.business import Business
from cashpilot.models.cash_session import CashSession
from cashpilot.models.daily_reconciliation import DailyReconciliation
from cashpilot.models.user import User
from cashpilot.models.user_business import UserBusiness
from cashpilot.utils.datetime import today_local

router = APIRouter(prefix="/admin", tags=["admin"])
logger = get_logger(__name__)
templates = Jinja2Templates(directory="/app/templates")

# Variance thresholds for flagging discrepancies
# Uses dual threshold approach (OR logic):
# - Absolute: 20,000 Gs (based on local practice in Paraguay)
# - Percentage: 2% (industry standard)
# Flags "Needs Review" if EITHER threshold is exceeded
ABSOLUTE_THRESHOLD = Decimal("20000.00")  # 20,000 guaraníes
VARIANCE_THRESHOLD = Decimal("2.0")  # 2%


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
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
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
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
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
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Comparison dashboard: manual entries vs system records with variance calculation."""
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
    stmt_businesses = select(Business).where(Business.is_active)
    selected_business_id = None
    if business_id and business_id.strip():
        try:
            selected_business_id = UUID(business_id)
            stmt_businesses = stmt_businesses.where(Business.id == selected_business_id)
        except (ValueError, TypeError):
            selected_business_id = None
    result_businesses = await db.execute(stmt_businesses)
    businesses = result_businesses.scalars().all()

    # Build comparison data for each business
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
            # Card Sales = credit_card + debit_card (only closed sessions)
            func.sum(
                case(
                    (
                        CashSession.status == "CLOSED",
                        func.coalesce(CashSession.credit_card_total, 0)
                        + func.coalesce(CashSession.debit_card_total, 0),
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
                        + func.coalesce(CashSession.credit_card_total, 0)
                        + func.coalesce(CashSession.debit_card_total, 0)
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
        manual_refunds = manual_entry.refunds if manual_entry and manual_entry.refunds else None
        is_closed = manual_entry.is_closed if manual_entry else False

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
                "is_closed": is_closed,
                "manual": {
                    "cash_sales": manual_cash_sales,
                    "card_sales": manual_card_sales,
                    "credit_sales": manual_credit_sales,
                    "total_sales": manual_total_sales,
                    "refunds": manual_refunds,
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
            }
        )

    # Get all businesses for the selector
    all_businesses = await get_active_businesses(db)

    return templates.TemplateResponse(
        request,
        "admin/reconciliation_compare.html",
        {
            "current_user": current_user,
            "comparison_date": comparison_date,
            "selected_business_id": str(selected_business_id) if selected_business_id else None,
            "businesses": all_businesses,
            "comparison_data": comparison_data,
            "locale": locale,
            "_": _,
        },
    )


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
            (session.credit_card_total or Decimal("0")) + (session.debit_card_total or Decimal("0"))
            if session.status == "CLOSED"
            else Decimal("0")
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
        "admin/partials/session_details.html",
        {
            "sessions": session_details,
            "locale": locale,
            "_": _,
        },
    )
