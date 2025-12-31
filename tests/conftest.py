# File: tests/conftest.py
"""Pytest configuration and fixtures."""

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from cashpilot.core.db import Base, get_db
from cashpilot.core.security import hash_password
from cashpilot.main import create_app

# Import all models
from cashpilot.models.business import Business  # noqa: F401
from cashpilot.models.cash_session import CashSession  # noqa: F401
from cashpilot.models.user import User  # noqa: F401
from tests.factories import UserFactory

TEST_DATABASE_URL = (
    "postgresql+asyncpg://cashpilot:dev_password_change_in_prod@db:5432/cashpilot_test"
)

DB_HOST = "db"
DB_PORT = 5432
DB_USER = "cashpilot"
DB_PASSWORD = "dev_password_change_in_prod"
DB_NAME = "cashpilot_test"


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_test_database():
    """Create test database using raw asyncpg connection."""
    try:
        # Connect to postgres database (always exists)
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database="postgres",
        )

        # Create database if it doesn't exist
        try:
            await conn.execute(f'CREATE DATABASE {DB_NAME}')
        except asyncpg.DuplicateDatabaseError:
            pass  # Database already exists

        await conn.close()
    except Exception as e:
        print(f"Warning: Could not create test database: {e}")

    yield


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create fresh DB session for each test."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Provide session
    async with async_session_maker() as session:
        yield session
        await session.rollback()

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    """Create async test client with overridden DB dependency."""
    from cashpilot.api.auth import get_current_user

    app = create_app()

    # Create a test user (CASHIER by default)
    test_user = await UserFactory.create(
        db_session,
        email="testclient@example.com",
        first_name="Test",
        last_name="Client",
        hashed_password=hash_password("testpass123"),
    )

    # Override dependencies
    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    # Create client
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        # Attach test_user to client for test access
        ac.test_user = test_user
        ac.db_session = db_session
        yield ac


@pytest.fixture
async def test_user(db_session: AsyncSession, request) -> User:
    """Create a test user with proper password hashing."""
    # Generate unique email per test
    test_name = request.node.name
    email = f"testuser_{test_name}@example.com"

    user = await UserFactory.create(
        db_session,
        email=email,
        first_name="Test",
        last_name="User",
        hashed_password=hash_password("testpass123"),
        is_active=True,
    )
    return user


@pytest.fixture
async def unauthenticated_client(
        db_session: AsyncSession,
) -> AsyncClient:
    """AsyncClient without authentication overrides (for testing auth failures)."""
    app = create_app()

    async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
    ) as ac:
        ac.db_session = db_session
        yield ac


@pytest_asyncio.fixture
async def client_for_health_checks(db_session: AsyncSession):
    """
    Create a test client for health check endpoints with proper database session management.

    Creates a new engine and session factory to ensure fresh sessions per request,
    which is required for health check endpoints that need to test database connectivity.
    """
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    app = create_app()

    # Create a new engine using the same database URL
    # Tables are already created by db_session fixture, so we just need the engine
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Override get_db dependency to create a new session for each request
    async def override_get_db():
        async with async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        # Store engine reference to prevent garbage collection
        ac.test_engine = engine
        yield ac

    # Cleanup
    await engine.dispose()

@pytest_asyncio.fixture
async def admin_client(db_session):
    """Create async test client with admin user."""
    from cashpilot.api.auth import get_current_user
    from cashpilot.models.user import UserRole

    app = create_app()

    # Create admin user
    admin_user = await UserFactory.create(
        db_session,
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        role=UserRole.ADMIN,
        hashed_password=hash_password("adminpass123"),
    )

    # Override dependencies
    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return admin_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    # Create client
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        ac.test_user = admin_user
        ac.db_session = db_session
        yield ac
