"""Pytest configuration and fixtures."""

import asyncio
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from cashpilot.core.db import Base
from cashpilot.main import create_app


# Test database URL (separate from dev)
TEST_DATABASE_URL = "postgresql+asyncpg://cashpilot:dev_password_change_in_prod@db:5432/cashpilot_test"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    """Create fresh DB session for each test."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()  # Rollback any changes


@pytest.fixture
def client(db_session):
    """Create test client with overridden DB dependency."""
    from fastapi.testclient import TestClient
    from cashpilot.core.db import get_db
    
    app = create_app()
    
    # Override DB dependency to use test DB
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    return TestClient(app)