"""Role-based authorization helpers."""

from fastapi import Depends, HTTPException, status

from cashpilot.api.auth import get_current_user
from cashpilot.models.user import User, UserRole


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to require ADMIN role."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def require_role(required_role: UserRole):
    """Factory to create a dependency that requires a specific role."""

    async def _check_role(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role.value}' required",
            )
        return current_user

    return _check_role
