"""Tests for the health check endpoint."""
import pytest
from fastapi.testclient import TestClient

from cashpilot.main import create_app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    app = create_app()
    return TestClient(app)


def test_health_endpoint_returns_ok(client: TestClient) -> None:
    """Test that /health returns 200 with correct payload."""
    response = client.get("/health")
    
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_endpoint_content_type(client: TestClient) -> None:
    """Test that /health returns JSON content type."""
    response = client.get("/health")
    
    assert "application/json" in response.headers["content-type"]