"""
FastAPI application factory and entrypoint.

This module follows the application factory pattern to allow:
- Multiple instances for testing
- Different configurations per environment
- Clean dependency injection
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Lifespan context manager for startup and shutdown events.

    Use this to:
    - Initialize database connections
    - Load ML models
    - Start background tasks
    - Clean up resources on shutdown
    """
    # Startup logic
    print("🚀 CashPilot starting up...")

    # Seed default categories
    from cashpilot.core.db import AsyncSessionLocal
    from cashpilot.core.seed import seed_categories

    async with AsyncSessionLocal() as db:
        await seed_categories(db)

    yield  # Application runs here

    # Shutdown logic
    print("👋 CashPilot shutting down...")
    # TODO: Close database connections
    # TODO: Cleanup background tasks


def create_app() -> FastAPI:
    """Application factory for CashPilot."""
    app = FastAPI(
        title="CashPilot API",
        description="Personal cash flow tracking backend for Guaraníes (Gs)",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Register health endpoint
    from cashpilot.api.categories import router as categories_router
    from cashpilot.api.health import router as health_router
    from cashpilot.api.movements import router as movements_router

    app.include_router(health_router)
    app.include_router(movements_router)
    app.include_router(categories_router)

    return app


def run() -> None:
    """
    Development server entrypoint.

    This function is registered in pyproject.toml [project.scripts].
    Run with: make run
    """
    uvicorn.run(
        "cashpilot.main:create_app",
        factory=True,  # calls create_app() on reload
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
    )
