"""Tests for authentication endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models.user import User
from cashpilot.core.security import hash_password
from tests.factories import UserFactory


class TestAuthEndpoints:
    """Test authentication endpoints."""

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
        assert "/" in response.headers.get("location", "")
        assert "session" in response.cookies

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
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_login_user_not_found(
        self,
        client: AsyncClient,
    ) -> None:
        """Test login with non-existent email."""
        response = await client.post(
            "/login",
            data={
                "username": "nonexistent@example.com",
                "password": "anypassword",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_login_inactive_user(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test login with inactive user."""
        user = await UserFactory.create(
            db_session,
            email="inactive@example.com",
            hashed_password=hash_password("testpass123"),
            is_active=False,
        )

        response = await client.post(
            "/login",
            data={
                "username": user.email,
                "password": "testpass123",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_logout(
        self,
        client: AsyncClient,
        test_user: User,
    ) -> None:
        """Test logout clears session."""
        # Login first
        await client.post(
            "/login",
            data={
                "username": test_user.email,
                "password": "testpass123",
            },
        )

        # Logout
        response = await client.post("/logout", follow_redirects=False)

        assert response.status_code == 302
        assert "/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_protected_route_requires_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Test protected routes return 401 when not authenticated."""
        # Create a new async client without session to test unauthenticated access
        from fastapi.testclient import TestClient
        from cashpilot.main import create_app

        app = create_app()
        test_client = TestClient(app)

        response = test_client.get("/", follow_redirects=False)
        # Should return 401 (Unauthorized) not 302 (redirect) because of exception handler
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_session_persistence(
        self,
        client: AsyncClient,
        test_user: User,
    ) -> None:
        """Test session persists across requests."""
        # Login
        await client.post(
            "/login",
            data={
                "username": test_user.email,
                "password": "testpass123",
            },
        )

        # Access protected route
        response = await client.get("/")
        assert response.status_code == 200

        # Session should still work on next request
        response = await client.get("/")
        assert response.status_code == 200
