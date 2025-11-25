# File: src/cashpilot/api/auth_helpers.py
"""Role-based authorization helpers."""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.api.auth import get_current_user
from cashpilot.core.db import get_db
from cashpilot.core.logging import get_logger
from cashpilot.models.cash_session import CashSession
from cashpilot.models.user import User, UserRole

logger = get_logger(__name__)


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to require ADMIN role."""
    if current_user.role != UserRole.ADMIN:
        logger.warning(
            "auth.permission_denied",
            user_id=str(current_user.id),
            required_role="ADMIN",
            user_role=current_user.role,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource",
        )
    return current_user


async def require_own_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CashSession:
    """Dependency to ensure Cashier can only access their own sessions."""
    stmt = select(CashSession).where(CashSession.id == UUID(session_id))
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Admin can access all, Cashier only their own
    if current_user.role == UserRole.CASHIER and session.created_by != current_user.id:
        logger.warning(
            "auth.session_access_denied",
            user_id=str(current_user.id),
            session_id=session_id,
            created_by=str(session.created_by),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this session",
        )

    return session
