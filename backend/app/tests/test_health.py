"""Tests for root service and health endpoints."""

from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient) -> None:
    """Test that the root endpoint returns expected service metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app_name"] == "FarmShield AI Backend"
    assert data["version"] == "1.0.0"
    assert data["status"] == "operational"
    assert data["docs_url"] == "/docs"
    assert data["redoc_url"] == "/redoc"
    assert data["api_prefix"] == "/api/v1"


def test_root_health_endpoint(client: TestClient) -> None:
    """Test GET /health returns expected status and database diagnostics structure."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["app_name"] == "FarmShield AI Backend"
    assert data["version"] == "1.0.0"
    assert "status" in data
    assert "database" in data
    assert "connected" in data["database"]
    assert data["database"]["database"] == "postgresql"


def test_v1_health_endpoint(client: TestClient) -> None:
    """Test GET /api/v1/health returns expected status structure."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["app_name"] == "FarmShield AI Backend"
    assert "database" in data


def test_openapi_schema(client: TestClient) -> None:
    """Test that OpenAPI schema is properly generated."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "FarmShield AI Backend"
    assert data["info"]["version"] == "1.0.0"
    assert "/health" in data["paths"]
    assert "/api/v1/health" in data["paths"]


def test_health_endpoint_fails_when_db_disconnected(client: TestClient) -> None:
    """Test that GET /health returns HTTP 503 when the database is unavailable."""
    from unittest.mock import patch
    fake_diagnostics = {
        "connected": False,
        "database": "postgresql",
        "postgis_installed": False,
        "postgis_version": None,
        "error": "Connection refused",
    }
    with patch("app.api.v1.endpoints.health.check_db_connection", return_value=fake_diagnostics):
        response = client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"]["connected"] is False


def test_health_endpoint_fails_when_postgis_missing(client: TestClient) -> None:
    """Test that GET /health returns HTTP 503 when PostGIS extension is not installed."""
    from unittest.mock import patch
    fake_diagnostics = {
        "connected": True,
        "database": "postgresql",
        "postgis_installed": False,
        "postgis_version": None,
        "error": None,
    }
    with patch("app.api.v1.endpoints.health.check_db_connection", return_value=fake_diagnostics):
        response = client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"]["postgis_installed"] is False
