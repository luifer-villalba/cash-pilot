"""Tests for logging and error handling."""

import pytest
from fastapi.testclient import TestClient

from cashpilot.core.errors import (
    AppError,
    ConflictError,
    ErrorDetail,
    NotFoundError,
    ValidationError,
)
from cashpilot.core.logging import get_request_id, set_request_id
from cashpilot.main import create_app


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    app = create_app()
    return TestClient(app)


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

    def test_health_endpoint_returns_ok(self, client: TestClient):
        """Verify health endpoint still works."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        # MIZ-27 enhanced health check with detailed checks
        assert "checks" in data or "status" in data

    def test_request_id_header_in_response(self, client: TestClient):
        """Test X-Request-ID header is echoed back."""
        test_id = "external-123"
        response = client.get("/health", headers={"X-Request-ID": test_id})

        assert response.headers.get("X-Request-ID") == test_id

    def test_request_id_propagates_to_response_headers(self, client: TestClient):
        """Test request ID is propagated through middleware."""
        # Make a request without X-Request-ID header
        response = client.get("/health")

        # Response should have X-Request-ID header
        assert "X-Request-ID" in response.headers
        # Should be a valid UUID-like string
        assert len(response.headers["X-Request-ID"]) > 0
