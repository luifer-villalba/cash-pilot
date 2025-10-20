"""Database configuration and session management."""

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

# Read from environment, fallback to dev DB
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://cashpilot:dev_password_change_in_prod@db:5432/cashpilot_dev"
)

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    future=True,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Declarative base
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()