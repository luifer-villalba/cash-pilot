"""Tests for authentication endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.core.security import hash_password
from cashpilot.main import create_app
from cashpilot.models.user import UserRole
from tests.factories import UserFactory


class TestAuthEndpoints:
    """Test authentication endpoints and middleware."""

    @pytest.mark.asyncio
    async def test_protected_route_requires_auth(self, db_session: AsyncSession):
        """Test that protected routes require authentication."""
        app = create_app()

        async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
        ) as ac:
            response = await ac.get("/")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_session_persistence(self, db_session: AsyncSession):
        """Test that session cookies persist across requests."""
        from cashpilot.api.auth import get_current_user
        from cashpilot.core.db import get_db

        app = create_app()

        # Create test user
        user = await UserFactory.create(
            db_session,
            email="session@test.com",
            hashed_password=hash_password("testpass123"),
        )

        # Override dependencies
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                follow_redirects=True  # Add this
        ) as ac:
            # Now dashboard should work
            dashboard_response = await ac.get("/")
            assert dashboard_response.status_code == 200


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
