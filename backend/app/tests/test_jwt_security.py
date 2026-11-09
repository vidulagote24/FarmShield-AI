"""Tests for JWT token validation, cryptographic signature verification, and expiration."""

import uuid
from datetime import timedelta
import jwt
import pytest
from fastapi.testclient import TestClient
from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User


def test_expired_token_rejected(client: TestClient, test_farmer: User):
    """Verify that an expired JWT token is rejected with 401 Unauthorized."""
    # Create token expired 10 minutes ago
    expired_token = create_access_token(
        subject=test_farmer.id,
        role=test_farmer.role,
        email=test_farmer.email,
        expires_delta=timedelta(minutes=-10),
    )
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


def test_forged_signature_rejected(client: TestClient, test_farmer: User):
    """Verify that a token signed with an invalid secret is rejected."""
    tampered_token = jwt.encode(
        {
            "sub": str(test_farmer.id),
            "role": test_farmer.role,
            "type": "access",
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
            "exp": 9999999999,
            "iat": 1000000000,
            "nbf": 1000000000,
        },
        "wrong-secret-key-forged-signature-attempt-12345",
        algorithm=settings.JWT_ALGORITHM,
    )
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
    assert response.status_code == 401
    assert "signature" in response.json()["detail"].lower()


def test_invalid_issuer_rejected(client: TestClient, test_farmer: User):
    """Verify that a token with an invalid issuer claim is rejected."""
    bad_issuer_token = jwt.encode(
        {
            "sub": str(test_farmer.id),
            "role": test_farmer.role,
            "type": "access",
            "iss": "untrusted-issuer",
            "aud": settings.JWT_AUDIENCE,
            "exp": 9999999999,
            "iat": 1000000000,
            "nbf": 1000000000,
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bad_issuer_token}"})
    assert response.status_code == 401


def test_invalid_audience_rejected(client: TestClient, test_farmer: User):
    """Verify that a token with an invalid audience claim is rejected."""
    bad_aud_token = jwt.encode(
        {
            "sub": str(test_farmer.id),
            "role": test_farmer.role,
            "type": "access",
            "iss": settings.JWT_ISSUER,
            "aud": "rogue-client",
            "exp": 9999999999,
            "iat": 1000000000,
            "nbf": 1000000000,
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bad_aud_token}"})
    assert response.status_code == 401


def test_malformed_token_rejected(client: TestClient):
    """Verify that completely malformed strings are rejected with 401."""
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer this-is-not-a-valid-jwt"})
    assert response.status_code == 401


def test_token_with_nonexistent_user_rejected(client: TestClient):
    """Verify that a token validly signed but referencing a deleted/non-existent user returns 401."""
    random_uuid = uuid.uuid4()
    token = create_access_token(
        subject=random_uuid,
        role="farmer",
        email="ghost@farmshield.ai",
    )
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert "not found" in response.json()["detail"].lower()
