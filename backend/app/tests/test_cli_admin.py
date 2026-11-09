"""Tests for Administrative CLI provisioning tool."""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.cli import create_admin_user
from app.models.user import User


def test_cli_create_admin_success(client: TestClient, db_session: Session):
    """Test provisioning an admin user through the CLI logic."""
    suffix = uuid.uuid4().hex[:8]
    email = f"cli_admin_{suffix}@farmshield.ai"
    password = "AdminSuperSecret123!"

    # Provision admin via CLI function
    create_admin_user(
        email=email,
        name="CLI Admin User",
        password=password,
        phone="+919988776655",
    )

    # Verify user exists in database with admin role and Argon2id hash
    admin_user = db_session.query(User).filter(User.email == email).first()
    assert admin_user is not None
    assert admin_user.role == "admin"
    assert admin_user.is_active is True
    assert admin_user.hashed_password.startswith("$argon2id$")

    # Verify the provisioned admin can authenticate via /auth/login
    login_res = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # Verify admin privileges on /api/v1/users/me
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["role"] == "admin"

    # Teardown
    db_session.delete(admin_user)
    db_session.commit()
