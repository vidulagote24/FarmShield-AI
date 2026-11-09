"""Tests for Authentication API: Registration, Login, Token Issuance, and Backward Compatibility."""

import hashlib
import os
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import create_access_token, decode_access_token, get_password_hash
from app.models.user import FarmerProfile, User


def _make_legacy_pbkdf2_hash(password: str) -> str:
    """Generate a legacy PBKDF2 hash to test backward-compatible verification and rehashing."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"pbkdf2_sha256$100000${salt.hex()}${key.hex()}"


def test_register_farmer_success(client: TestClient, db_session: Session):
    """Test successful public farmer registration."""
    unique_suffix = uuid.uuid4().hex[:8]
    payload = {
        "full_name": "Suresh Deshmukh",
        "email": f"suresh_{unique_suffix}@farmshield.ai",
        "password": "StrongPassword123!",
        "phone": "+919811122233",
        "preferred_language": "mr",
        "village": "Manchar",
        "district": "Pune",
        "state": "Maharashtra",
        "country": "India",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == payload["email"].lower()
    assert data["full_name"] == payload["full_name"]
    assert data["role"] == "farmer"
    assert data["is_active"] is True
    assert "id" in data
    assert "hashed_password" not in data
    assert "password" not in data

    # Verify user in database has Argon2id hash
    user_in_db = db_session.query(User).filter(User.email == payload["email"].lower()).first()
    assert user_in_db is not None
    assert user_in_db.hashed_password.startswith("$argon2id$")
    assert user_in_db.role == "farmer"

    # Verify profile created
    profile = db_session.query(FarmerProfile).filter(FarmerProfile.user_id == user_in_db.id).first()
    assert profile is not None
    assert profile.preferred_language == "mr"
    assert profile.village == "Manchar"

    # Cleanup
    db_session.delete(profile)
    db_session.delete(user_in_db)
    db_session.commit()


def test_register_prevents_privilege_escalation(client: TestClient, db_session: Session):
    """Verify that public registration rejects or ignores role escalation to admin."""
    unique_suffix = uuid.uuid4().hex[:8]
    payload = {
        "full_name": "Hacker Attempt",
        "email": f"hacker_{unique_suffix}@farmshield.ai",
        "password": "StrongPassword123!",
        "role": "admin",  # Client attempts to pass admin
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "farmer"  # Must ALWAYS be farmer

    user_in_db = db_session.query(User).filter(User.email == payload["email"].lower()).first()
    assert user_in_db.role == "farmer"

    db_session.delete(user_in_db)
    db_session.commit()


def test_register_duplicate_email_conflict(client: TestClient, test_farmer: User):
    """Verify duplicate email registration returns 409 Conflict."""
    payload = {
        "full_name": "Duplicate Farmer",
        "email": test_farmer.email,
        "password": "Password123!",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    assert "already registered" in response.json()["detail"]


def test_register_password_complexity_rejected(client: TestClient):
    """Verify weak passwords are rejected during registration."""
    unique_suffix = uuid.uuid4().hex[:8]

    # Too short (< 8 chars)
    res = client.post("/api/v1/auth/register", json={
        "full_name": "Weak Pass User",
        "email": f"weak1_{unique_suffix}@farmshield.ai",
        "password": "short",
    })
    assert res.status_code == 422

    # Letters only (no numbers or symbols)
    res2 = client.post("/api/v1/auth/register", json={
        "full_name": "Weak Pass User",
        "email": f"weak2_{unique_suffix}@farmshield.ai",
        "password": "allcharactersonly",
    })
    assert res2.status_code == 422


def test_login_json_success(client: TestClient, db_session: Session):
    """Test login via JSON payload returns JWT and public user info."""
    unique_suffix = uuid.uuid4().hex[:8]
    raw_password = "SecretFarmerPassword123!"
    user = User(
        full_name="Login Test Farmer",
        email=f"login_test_{unique_suffix}@farmshield.ai",
        hashed_password=get_password_hash(raw_password),
        role="farmer",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    login_res = client.post("/api/v1/auth/login", json={
        "email": user.email,
        "password": raw_password,
    })
    assert login_res.status_code == 200
    data = login_res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0
    assert data["user"]["id"] == str(user.id)
    assert data["user"]["email"] == user.email
    assert data["user"]["role"] == "farmer"

    # Verify token payload
    decoded = decode_access_token(data["access_token"])
    assert decoded["sub"] == str(user.id)
    assert decoded["role"] == "farmer"
    assert decoded["iss"] == "farmshield-ai"
    assert decoded["aud"] == "farmshield-app"

    db_session.delete(user)
    db_session.commit()


def test_login_oauth2_form_success(client: TestClient, db_session: Session):
    """Test login via OAuth2 form data (for Swagger UI interactive authorization)."""
    unique_suffix = uuid.uuid4().hex[:8]
    raw_password = "SwaggerPassword123!"
    user = User(
        full_name="Swagger User",
        email=f"swagger_{unique_suffix}@farmshield.ai",
        hashed_password=get_password_hash(raw_password),
        role="farmer",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    form_res = client.post(
        "/api/v1/auth/login",
        data={"username": user.email, "password": raw_password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert form_res.status_code == 200
    assert "access_token" in form_res.json()

    db_session.delete(user)
    db_session.commit()


def test_login_invalid_password(client: TestClient, test_farmer: User):
    """Test login with incorrect password fails with 401 Unauthorized."""
    response = client.post("/api/v1/auth/login", json={
        "email": test_farmer.email,
        "password": "WrongPassword123!",
    })
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_login_nonexistent_email(client: TestClient):
    """Test login with non-existent email fails with 401."""
    response = client.post("/api/v1/auth/login", json={
        "email": "doesnotexist@farmshield.ai",
        "password": "AnyPassword123!",
    })
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_login_inactive_user_rejected(client: TestClient, db_session: Session):
    """Test login with inactive user account returns 403 Forbidden."""
    unique_suffix = uuid.uuid4().hex[:8]
    raw_password = "InactivePass123!"
    user = User(
        full_name="Inactive Farmer",
        email=f"inactive_{unique_suffix}@farmshield.ai",
        hashed_password=get_password_hash(raw_password),
        role="farmer",
        is_active=False,  # Deactivated
    )
    db_session.add(user)
    db_session.commit()

    response = client.post("/api/v1/auth/login", json={
        "email": user.email,
        "password": raw_password,
    })
    assert response.status_code == 403
    assert "inactive" in response.json()["detail"].lower()

    db_session.delete(user)
    db_session.commit()


def test_login_legacy_pbkdf2_transparent_rehash(client: TestClient, db_session: Session):
    """Test backward-compatible verification of legacy PBKDF2 hash and transparent rehash to Argon2id."""
    unique_suffix = uuid.uuid4().hex[:8]
    raw_password = "LegacyPassword123!"
    legacy_hash = _make_legacy_pbkdf2_hash(raw_password)

    user = User(
        full_name="Legacy User",
        email=f"legacy_{unique_suffix}@farmshield.ai",
        hashed_password=legacy_hash,
        role="farmer",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.hashed_password.startswith("pbkdf2_sha256$")

    # Login should succeed
    login_res = client.post("/api/v1/auth/login", json={
        "email": user.email,
        "password": raw_password,
    })
    assert login_res.status_code == 200

    # User in database should now be transparently rehashed to Argon2id!
    db_session.expire_all()
    user_after = db_session.query(User).filter(User.id == user.id).first()
    assert user_after.hashed_password.startswith("$argon2id$")

    # Subsequent login works with newly stored Argon2id hash
    login_res2 = client.post("/api/v1/auth/login", json={
        "email": user.email,
        "password": raw_password,
    })
    assert login_res2.status_code == 200

    db_session.delete(user_after)
    db_session.commit()


def test_auth_me_endpoint(client: TestClient, test_farmer: User):
    """Test GET /api/v1/auth/me with Bearer token."""
    token = create_access_token(subject=test_farmer.id, role=test_farmer.role, email=test_farmer.email)
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_farmer.id)
    assert data["email"] == test_farmer.email
    assert data["role"] == test_farmer.role


def test_auth_me_unauthenticated_fails(client: TestClient):
    """Test GET /api/v1/auth/me fails without token."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_logout_endpoint(client: TestClient):
    """Test POST /api/v1/auth/logout returns 200 confirmation."""
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert "logged out" in response.json()["message"].lower()
