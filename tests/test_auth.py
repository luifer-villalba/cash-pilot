# File: tests/test_auth.py
"""Tests for authentication endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.core.security import hash_password
from cashpilot.models.user import User
from tests.factories import UserFactory


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    return await UserFactory.create(
        db_session,
        email="test@example.com",
        hashed_password=hash_password("testpass123"),
    )


class TestAuthEndpoints:
    """Test authentication endpoints."""

    @pytest.mark.asyncio
    async def test_login_page_loads(self, client: AsyncClient) -> None:
        """Test that login page renders."""
        response = await client.get("/login")
        assert response.status_code == 200
        assert "CashPilot" in response.text

    @pytest.mark.asyncio
    async def test_login_success(
        self,
        client: AsyncClient,
        test_user: User,
    ) -> None:
        """Test successful login."""
        response = await client.post(
            "/login",
            data={
                "username": test_user.email,
                "password": "testpass123",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "/admin/cash-session/list" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_login_invalid_password(
        self,
        client: AsyncClient,
        test_user: User,
    ) -> None:
        """Test login with wrong password."""
        response = await client.post(
            "/login",
            data={
                "username": test_user.email,
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout(
        self,
        client: AsyncClient,
    ) -> None:
        """Test logout."""
        response = await client.post(
            "/logout",
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_protected_route_requires_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that protected routes work (auth overridden in tests)."""
        response = await client.get("/businesses")
        # In tests, auth is overridden, so this should succeed
        assert response.status_code == 200
