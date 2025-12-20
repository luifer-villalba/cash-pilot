# File: tests/test_settings.py
"""Tests for user settings endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models.user import User
from cashpilot.core.security import hash_password, verify_password


class TestPasswordChange:
    """Test password change functionality."""

    @pytest.mark.asyncio
    async def test_change_password_success(
            self,
            client: AsyncClient,
            db_session: AsyncSession,
    ) -> None:
        """Test successful password change."""
        # Use the user created by client fixture, not test_user parameter
        test_user = client.test_user

        response = await client.post(
            "/settings/change-password",
            data={
                "current_password": "testpass123",
                "new_password": "newpass456",
                "confirm_password": "newpass456",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "success=password_changed" in response.headers.get("location", "")

        # Query fresh user from DB
        stmt = select(User).where(User.id == test_user.id)
        result = await db_session.execute(stmt)
        updated_user = result.scalar_one()

        assert verify_password("newpass456", updated_user.hashed_password)

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(
            self,
            client: AsyncClient,
    ) -> None:
        """Test password change with wrong current password."""
        response = await client.post(
            "/settings/change-password",
            data={
                "current_password": "wrongpassword",
                "new_password": "newpass456",
                "confirm_password": "newpass456",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "error=invalid_current_password" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_change_password_mismatch(
            self,
            client: AsyncClient,
    ) -> None:
        """Test password change with mismatched confirmation."""
        response = await client.post(
            "/settings/change-password",
            data={
                "current_password": "testpass123",
                "new_password": "newpass456",
                "confirm_password": "different789",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "error=password_mismatch" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_change_password_too_short(
            self,
            client: AsyncClient,
    ) -> None:
        """Test password change with password < 8 chars fails validation."""
        response = await client.post(
            "/settings/change-password",
            data={
                "current_password": "testpass123",
                "new_password": "short",
                "confirm_password": "short",
            },
            follow_redirects=False,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_change_password_requires_auth(
            self,
            unauthenticated_client: AsyncClient,
    ) -> None:
        """Test that unauthenticated users can't change password."""
        response = await unauthenticated_client.post(
            "/settings/change-password",
            data={
                "current_password": "testpass123",
                "new_password": "newpass456",
                "confirm_password": "newpass456",
            },
            follow_redirects=False,
        )

        assert response.status_code == 401
