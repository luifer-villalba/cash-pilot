"""Helper functions for cash session creation and management."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.core.errors import NotFoundError
from cashpilot.models import CashSessionCreate, User
from cashpilot.models.user import UserRole


async def _determine_cashier_for_session(
    session: CashSessionCreate,
    current_user: User,
    db: AsyncSession,
) -> tuple[UUID, UUID]:
    """Determine cashier_id and created_by based on user role and RBAC.

    Returns: (cashier_id, created_by)
    """
    if current_user.role == UserRole.ADMIN:
        return await _admin_session_creation(session, current_user, db)
    else:
        return await _cashier_session_creation(session, current_user, db)


async def _admin_session_creation(
    session: CashSessionCreate,
    current_user: User,
    db: AsyncSession,
) -> tuple[UUID, UUID]:
    """Handle admin session creation logic."""
    # Validate inputs
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session data is required",
        )
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User authentication required",
        )
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error",
        )

    cashier_id = session.for_cashier_id if session.for_cashier_id else current_user.id
    created_by = current_user.id

    # Verify cashier exists if different from admin (business logic)
    if cashier_id != current_user.id:
        stmt = select(User).where(User.id == cashier_id)
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            raise NotFoundError("User", str(cashier_id))

    return cashier_id, created_by


async def _cashier_session_creation(
    session: CashSessionCreate,
    current_user: User,
    db: AsyncSession,
) -> tuple[UUID, UUID]:
    """Handle cashier session creation with business assignment validation."""

    if session.for_cashier_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cashiers cannot create sessions for other users",
        )

    # Load cashier's assigned businesses
    stmt = select(User).where(User.id == current_user.id)
    result = await db.execute(stmt)
    user_with_businesses = result.scalar_one_or_none()

    if user_with_businesses is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await db.refresh(user_with_businesses, ["businesses"])

    assigned_business_ids = {b.id for b in (user_with_businesses.businesses or [])}

    # Check if cashier has any assigned businesses
    if not assigned_business_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No businesses assigned. Contact an administrator.",
        )

    # Validate business is assigned
    if session.business_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="business_id is required",
        )
    if session.business_id not in assigned_business_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this business",
        )

    return current_user.id, current_user.id


def _validate_restore_session_inputs(
    session_id: str | None,
    current_user: User | None,
    db: AsyncSession | None,
) -> None:
    """Validate inputs for restore_session endpoint."""
    if session_id is None or not isinstance(session_id, str) or not session_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id is required",
        )
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User authentication required",
        )
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error",
        )
