"""
Database configuration and session management.

This module provides:
- Async SQLAlchemy engine and session factory
- Declarative Base for models
- FastAPI dependency for database sessions
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

# Read DATABASE_URL from environment
# For now, hardcode for simplicity (we'll improve this later)
DATABASE_URL = "postgresql+asyncpg://cashpilot:dev_password_change_in_prod@db:5432/cashpilot_dev"

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Log SQL queries (useful for development)
    future=True,  # Use SQLAlchemy 2.0 style
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit
)

# Declarative base for models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.

    Usage in endpoints:
        @router.get("/movements")
        async def list_movements(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Movement))
            return result.scalars().all()

    Yields:
        AsyncSession: Database session that auto-closes after request
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
