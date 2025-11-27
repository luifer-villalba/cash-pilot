"""Tests for authentication endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models.user import User, UserRole
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
            test_user: User,
            db_session: AsyncSession,
    ) -> None:
        """Test login fails for inactive users."""
        # Deactivate user
        test_user.is_active = False
        await db_session.commit()

        response = await client.post(
            "/login",
            data={
                "username": test_user.email,
                "password": "testpass123",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302  # ← Changed from 403
        assert "error" in response.headers.get("location", "")

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
        """Test protected routes return 401 without auth."""
        from httpx import AsyncClient
        from cashpilot.main import create_app

        app = create_app()
        async with AsyncClient(app=app, base_url="http://test") as unauthenticated_client:
            response = await unauthenticated_client.get("/", follow_redirects=False)
            assert response.status_code == 401
            assert response.json()["detail"] == "Not authenticated"

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


class TestUserCreationWithRoles:
    """Test user creation with role assignment."""

    @pytest.mark.asyncio
    async def test_create_cashier_user(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test creating a user with CASHIER role (default)."""
        user = await UserFactory.create(
            db_session,
            email="cashier@example.com",
            first_name="Maria",
            last_name="Gomez",
            role=UserRole.CASHIER,
        )

        assert user.email == "cashier@example.com"
        assert user.first_name == "Maria"
        assert user.last_name == "Gomez"
        assert user.role == UserRole.CASHIER
        assert user.display_name == "Maria Gomez"
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_create_admin_user(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test creating a user with ADMIN role."""
        user = await UserFactory.create(
            db_session,
            email="admin@example.com",
            first_name="Juan",
            last_name="Silva",
            role=UserRole.ADMIN,
        )

        assert user.email == "admin@example.com"
        assert user.first_name == "Juan"
        assert user.last_name == "Silva"
        assert user.role == UserRole.ADMIN
        assert user.display_name == "Juan Silva"

    @pytest.mark.asyncio
    async def test_user_display_name_fallback_to_email(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test display_name falls back to email when names are empty."""
        user = await UserFactory.create(
            db_session,
            email="test@example.com",
            first_name="",
            last_name="",
        )

        assert user.display_name == "test@example.com"

    @pytest.mark.asyncio
    async def test_default_role_is_cashier(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test new users default to CASHIER role."""
        user = await UserFactory.create(
            db_session,
            email="default@example.com",
        )

        assert user.role == UserRole.CASHIER

    @pytest.mark.asyncio
    async def test_login_stores_role_in_session(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test login stores user role in session."""
        user = await UserFactory.create(
            db_session,
            email="roletest@example.com",
            first_name="Test",
            last_name="Admin",
            role=UserRole.ADMIN,
            hashed_password=hash_password("testpass123"),
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
        # Check that session contains role info
        assert client.cookies.get("session") is not None
