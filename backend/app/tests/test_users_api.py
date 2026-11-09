"""Tests for Users and FarmerProfile CRUD endpoints."""

import uuid
import pytest
from fastapi.testclient import TestClient


def test_create_farmer_user(client: TestClient):
    """Test user registration with valid data."""
    unique_suffix = uuid.uuid4().hex[:8]
    payload = {
        "email": f"kisan_{unique_suffix}@farmshield.ai",
        "full_name": "Kisanrao Jadhav",
        "phone": "+919123456789",
        "password": "SecurePassword123!",
        "role": "farmer",
    }
    response = client.post("/api/v1/users/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == payload["email"]
    assert data["full_name"] == payload["full_name"]
    assert data["role"] == "farmer"
    assert data["is_active"] is True
    assert "id" in data
    assert "hashed_password" not in data
    assert "password" not in data


def test_create_duplicate_email_rejected(client: TestClient, test_farmer):
    """Test that creating a user with an already registered email returns 409 Conflict."""
    payload = {
        "email": test_farmer.email,
        "full_name": "Another Name",
        "password": "Password123!",
        "role": "farmer",
    }
    response = client.post("/api/v1/users", json=payload)
    assert response.status_code == 409
    assert "already registered" in response.json()["detail"]


def test_get_user_by_id(auth_client: TestClient, test_farmer):
    """Test retrieving user details by ID."""
    response = auth_client.get(f"/api/v1/users/{test_farmer.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_farmer.id)
    assert data["email"] == test_farmer.email


def test_update_user(auth_client: TestClient, test_farmer):
    """Test updating user details."""
    payload = {
        "full_name": "Ramesh S. Patil",
        "phone": "+919999999999",
    }
    response = auth_client.put(f"/api/v1/users/{test_farmer.id}", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Ramesh S. Patil"
    assert data["phone"] == "+919999999999"


def test_create_and_get_farmer_profile(auth_client: TestClient, test_farmer):
    """Test creating and retrieving farmer profile for a user."""
    profile_payload = {
        "preferred_language": "mr",
        "village": "Baramati",
        "district": "Pune",
        "state": "Maharashtra",
        "country": "India",
    }
    response = auth_client.put(f"/api/v1/farmers/{test_farmer.id}/profile", json=profile_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(test_farmer.id)
    assert data["preferred_language"] == "mr"
    assert data["village"] == "Baramati"

    # Retrieve profile
    get_res = auth_client.get(f"/api/v1/farmers/{test_farmer.id}/profile")
    assert get_res.status_code == 200
    assert get_res.json()["village"] == "Baramati"


def test_update_farmer_profile(auth_client: TestClient, test_farmer):
    """Test updating existing farmer profile."""
    # Ensure profile exists
    auth_client.put(f"/api/v1/farmers/{test_farmer.id}/profile", json={
        "preferred_language": "hi",
        "village": "Daund",
        "district": "Pune",
        "state": "Maharashtra",
        "country": "India",
    })

    # Update profile
    update_res = auth_client.put(f"/api/v1/farmers/{test_farmer.id}/profile", json={
        "preferred_language": "mr",
        "village": "Shirur",
        "district": "Pune",
        "state": "Maharashtra",
        "country": "India",
    })
    assert update_res.status_code == 200
    assert update_res.json()["village"] == "Shirur"
    assert update_res.json()["preferred_language"] == "mr"
