# File: tests/test_admin.py
"""Tests for admin endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models.user import User, UserRole
from cashpilot.core.security import hash_password, verify_password
from tests.factories import UserFactory


class TestAdminResetPassword:
    """Test password reset endpoint."""

    @pytest.mark.asyncio
    async def test_reset_password_success(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test successful password reset."""
        target = await UserFactory.create(
            db_session,
            email="target@example.com",
            role="CASHIER",
        )

        response = await admin_client.post(
            f"/admin/reset-password/{target.id}",
            data={"password": "NewPass123"},
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "success=password_reset" in response.headers.get("location", "")
        assert "NewPass123" in response.headers.get("location", "")

        await db_session.refresh(target)
        assert verify_password("NewPass123", target.hashed_password)

    @pytest.mark.asyncio
    async def test_reset_password_auto_generate(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test auto-generated password."""
        target = await UserFactory.create(
            db_session,
            email="target@example.com",
        )

        response = await admin_client.post(
            f"/admin/reset-password/{target.id}",
            data={},
            follow_redirects=False,
        )

        assert response.status_code == 302
        location = response.headers.get("location", "")
        assert "success=password_reset" in location
        assert "password=" in location

    @pytest.mark.asyncio
    async def test_reset_password_not_admin(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test non-admin cannot reset password."""
        target = await UserFactory.create(
            db_session,
            email="target@example.com",
        )

        response = await client.post(
            f"/admin/reset-password/{target.id}",
            data={"password": "NewPass123"},
            follow_redirects=False,
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_reset_password_user_not_found(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test reset for nonexistent user."""
        import uuid
        fake_id = uuid.uuid4()

        response = await admin_client.post(
            f"/admin/reset-password/{fake_id}",
            data={"password": "NewPass123"},
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "error=user_not_found" in response.headers.get("location", "")


class TestAdminDisableUser:
    """Test user disable endpoint."""

    @pytest.mark.asyncio
    async def test_disable_user_success(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test successful user disable."""
        target = await UserFactory.create(
            db_session,
            email="target@example.com",
            is_active=True,
        )

        response = await admin_client.post(
            f"/admin/users/{target.id}/disable",
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "success=user_disabled" in response.headers.get("location", "")

        await db_session.refresh(target)
        assert target.is_active is False

    @pytest.mark.asyncio
    async def test_disable_user_not_admin(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test non-admin cannot disable user."""
        target = await UserFactory.create(
            db_session,
            email="target@example.com",
        )

        response = await client.post(
            f"/admin/users/{target.id}/disable",
            follow_redirects=False,
        )

        assert response.status_code == 403


class TestAdminEnableUser:
    """Test user enable endpoint."""

    @pytest.mark.asyncio
    async def test_enable_user_success(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test successful user enable."""
        target = await UserFactory.create(
            db_session,
            email="target@example.com",
            is_active=False,
        )

        response = await admin_client.post(
            f"/admin/users/{target.id}/enable",
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "success=user_enabled" in response.headers.get("location", "")

        await db_session.refresh(target)
        assert target.is_active is True
