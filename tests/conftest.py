"""Pytest configuration and fixtures."""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from cashpilot.core.db import Base, get_db
from cashpilot.main import create_app

# Import all models so they're registered with Base.metadata
from cashpilot.models.business import Business  # noqa: F401
from cashpilot.models.cash_session import CashSession  # noqa: F401

TEST_DATABASE_URL = (
    "postgresql+asyncpg://cashpilot:dev_password_change_in_prod@db:5432/cashpilot_test"
)


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create fresh DB session for each test."""
    # Create engine and session maker
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
    app = create_app()

    # Override get_db dependency
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Use httpx.AsyncClient for async requests
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
