# File: tests/test_username_login.py
"""Tests for username-based login."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.core.security import hash_password
from tests.factories import UserFactory


class TestUsernameLogin:
    """Test username login functionality."""

    @pytest.mark.asyncio
    async def test_login_with_username(
            self,
            unauthenticated_client: AsyncClient,
            db_session: AsyncSession,
    ) -> None:
        """Test login with username works."""
        user = await UserFactory.create(
            db_session,
            email="test_username@example.com",
            username="testuserlogin",
            hashed_password=hash_password("password123"),
        )

        response = await unauthenticated_client.post(
            "/login",
            data={
                "username": "testuserlogin",
                "password": "password123",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert response.headers["location"] == "/"

    @pytest.mark.asyncio
    async def test_login_with_email_still_works(
            self,
            unauthenticated_client: AsyncClient,
            db_session: AsyncSession,
    ) -> None:
        """Test login with email still works."""
        user = await UserFactory.create(
            db_session,
            email="testemail@example.com",
            username="testemailuser",
            hashed_password=hash_password("password123"),
        )

        response = await unauthenticated_client.post(
            "/login",
            data={
                "username": "testemail@example.com",
                "password": "password123",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert response.headers["location"] == "/"

    @pytest.mark.asyncio
    async def test_login_case_insensitive(
            self,
            unauthenticated_client: AsyncClient,
            db_session: AsyncSession,
    ) -> None:
        """Test login is case insensitive for username."""
        await UserFactory.create(
            db_session,
            email="testcase@example.com",
            username="testcaseuser",
            hashed_password=hash_password("password123"),
        )

        response = await unauthenticated_client.post(
            "/login",
            data={
                "username": "TESTCASEUSER",
                "password": "password123",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_username_generated_from_email(
            self,
            db_session: AsyncSession,
    ) -> None:
        """Test username auto-generated from email prefix."""
        user = await UserFactory.create(
            db_session,
            email="john.smith@example.com",
        )

        assert user.username == "john.smith"

    @pytest.mark.asyncio
    async def test_username_truncated_to_50_chars(
            self,
            db_session: AsyncSession,
    ) -> None:
        """Test username respects 50 char limit."""
        long_prefix = "a" * 60

        user = await UserFactory.create(
            db_session,
            email=f"{long_prefix}@example.com",
        )

        assert len(user.username) == 50
        assert user.username == "a" * 50
