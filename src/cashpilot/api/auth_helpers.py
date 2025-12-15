# File: src/cashpilot/api/auth_helpers.py
"""Role-based authorization helpers."""

from datetime import datetime, timedelta
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.api.auth import get_current_user
from cashpilot.core.db import get_db
from cashpilot.core.errors import NotFoundError
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
    """Check if user owns the session OR is admin. Cashiers have 12-hour window."""
    stmt = select(CashSession).where(CashSession.id == UUID(session_id))
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise NotFoundError("CashSession", session_id)

    # Admin: can edit any closed session anytime
    if current_user.role == UserRole.ADMIN:
        return session

    # Cashier: can edit only their own, within 12 hours of closing
    if session.cashier_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    if session.status == "CLOSED":
        if datetime.now() - session.closed_time > timedelta(hours=12):
            raise HTTPException(status_code=403, detail="Edit window expired (12 hours)")

    return session
