"""Pytest configuration and fixtures."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from cashpilot.core.db import Base
from cashpilot.main import create_app

# Import models so Base.metadata knows about them
from cashpilot.models import Business, CashSession


TEST_DATABASE_URL = "postgresql+asyncpg://cashpilot:dev_password_change_in_prod@db:5432/cashpilot_test"


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Create fresh DB session for each test."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        # Clean up tables before each test
        await session.execute(text("DELETE FROM cash_sessions"))
        await session.execute(text("DELETE FROM businesses"))
        await session.commit()

        yield session

        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    """Create async test client."""
    from cashpilot.core.db import get_db

    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
