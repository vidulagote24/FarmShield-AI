"""Tests verifying authentication guards fail-closed and succeed with overrides."""

import pytest
from fastapi.testclient import TestClient


def test_unauthenticated_request_fails_closed(unauth_client: TestClient):
    """Verify that protected endpoints reject requests with 401 Unauthorized by default."""
    # Test GET /users/me
    response = unauth_client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert "Authentication credentials were not provided" in response.json()["detail"]

    # Test GET /farms
    response = unauth_client.get("/api/v1/farms")
    assert response.status_code == 401

    # Test POST /farms
    response = unauth_client.post("/api/v1/farms", json={})
    assert response.status_code == 401

    # Test POST /observations
    response = unauth_client.post("/api/v1/observations", json={})
    assert response.status_code == 401

    # Test POST /recommendations
    response = unauth_client.post("/api/v1/recommendations", json={})
    assert response.status_code == 401

    # Test POST /irrigation
    response = unauth_client.post("/api/v1/irrigation", json={})
    assert response.status_code == 401


def test_authenticated_override_succeeds(auth_client: TestClient, test_farmer):
    """Verify that when get_current_user is overridden, protected endpoints succeed."""
    response = auth_client.get("/api/v1/users/me")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_farmer.id)
    assert data["email"] == test_farmer.email
    assert data["role"] == "farmer"
