"""Tests for logging and error handling."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from cashpilot.core.errors import (
    AppError,
    ConflictError,
    ErrorDetail,
    NotFoundError,
    ValidationError,
)
from cashpilot.core.logging import get_request_id, set_request_id
from cashpilot.core.db import get_db
from cashpilot.main import create_app
from tests.conftest import TEST_DATABASE_URL


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """Create test client with database dependency override."""
    from httpx import ASGITransport, AsyncClient
    
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
        ac._engine = engine
        yield ac
    
    # Cleanup
    await engine.dispose()


class TestErrorClasses:
    """Test custom exception classes."""

    def test_validation_error_creates_correct_response(self):
        """Test ValidationError converts to proper response."""
        exc = ValidationError("Invalid email", details={"field": "email"})

        assert exc.code == "VALIDATION_ERROR"
        assert exc.status_code == 422
        assert exc.details == {"field": "email"}

        response = exc.to_response()
        assert isinstance(response, ErrorDetail)
        assert response.code == "VALIDATION_ERROR"

    def test_not_found_error_includes_resource_context(self):
        """Test NotFoundError includes resource details."""
        exc = NotFoundError(resource="Business", resource_id="123")

        assert exc.code == "NOT_FOUND"
        assert exc.status_code == 404
        assert exc.details["resource"] == "Business"
        assert exc.details["resource_id"] == "123"

    def test_conflict_error_creates_correct_response(self):
        """Test ConflictError for duplicate resource."""
        exc = ConflictError("Business already exists", details={"name": "Farmacia XYZ"})

        assert exc.code == "CONFLICT"
        assert exc.status_code == 409
        assert exc.details == {"name": "Farmacia XYZ"}


class TestRequestIDContext:
    """Test request ID injection."""

    def test_set_and_get_request_id(self):
        """Test request ID context var."""
        test_id = "test-request-123"
        set_request_id(test_id)

        assert get_request_id() == test_id

    def test_request_id_default(self):
        """Test default request ID when not set."""
        # Clear by setting default
        set_request_id("no-request-id")
        assert get_request_id() == "no-request-id"


class TestErrorHandling:
    """Test global error handlers."""

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_ok(self, client):
        """Verify health endpoint still works."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        # MIZ-27 enhanced health check with detailed checks
        assert "checks" in data or "status" in data

    @pytest.mark.asyncio
    async def test_request_id_header_in_response(self, client):
        """Test X-Request-ID header is echoed back."""
        test_id = "external-123"
        response = await client.get("/health", headers={"X-Request-ID": test_id})

        assert response.headers.get("X-Request-ID") == test_id

    @pytest.mark.asyncio
    async def test_request_id_propagates_to_response_headers(self, client):
        """Test request ID is propagated through middleware."""
        # Make a request without X-Request-ID header
        response = await client.get("/health")

        # Response should have X-Request-ID header
        assert "X-Request-ID" in response.headers
        # Should be a valid UUID-like string
        assert len(response.headers["X-Request-ID"]) > 0
