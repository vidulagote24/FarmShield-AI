"""Pytest fixtures for FarmShield AI Backend tests."""

import os
import sys
import uuid
from typing import Any, Dict, Generator
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.main import app
from app.db.session import SessionLocal
from app.models.user import User, FarmerProfile
from app.models.farm import Farm, FarmZone
from app.models.observation import Observation
from app.models.recommendation import Recommendation
from app.models.irrigation import IrrigationEvent
from app.core.security import get_password_hash
from app.core.spatial import calculate_geodesic_area_hectares
from app.api.deps import get_current_user, get_current_admin


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    """Create a FastAPI test client fixture."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def db_session():
    """Create a standalone DB session for test setup and teardown."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def test_farmer(db_session) -> Generator[User, None, None]:
    """Create a test farmer user in the database."""
    unique_suffix = uuid.uuid4().hex[:8]
    user = User(
        full_name=f"Ramesh Patil {unique_suffix}",
        email=f"ramesh_{unique_suffix}@farmshield.ai",
        phone="+919876543210",
        hashed_password=get_password_hash("SecretPassword123!"),
        role="farmer",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    yield user

    # Teardown: delete test data and user cleanly
    try:
        db_session.query(Observation).delete()
        db_session.query(Recommendation).delete()
        db_session.query(IrrigationEvent).delete()
        db_session.query(FarmZone).delete()
        db_session.query(Farm).delete()
        db_session.query(FarmerProfile).delete()
        db_session.delete(user)
        db_session.commit()
    except Exception:
        db_session.rollback()


@pytest.fixture(scope="function")
def test_admin(db_session) -> Generator[User, None, None]:
    """Create a test admin user in the database."""
    unique_suffix = uuid.uuid4().hex[:8]
    user = User(
        full_name=f"Admin User {unique_suffix}",
        email=f"admin_{unique_suffix}@farmshield.ai",
        phone="+919876543211",
        hashed_password=get_password_hash("AdminPassword123!"),
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    yield user

    db_session.delete(user)
    db_session.commit()


@pytest.fixture(scope="function")
def auth_client(test_farmer) -> Generator[TestClient, None, None]:
    """TestClient with get_current_user overridden to test_farmer."""
    app.dependency_overrides[get_current_user] = lambda: test_farmer
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(scope="function")
def admin_client(test_admin) -> Generator[TestClient, None, None]:
    """TestClient with get_current_user and get_current_admin overridden to test_admin."""
    app.dependency_overrides[get_current_user] = lambda: test_admin
    app.dependency_overrides[get_current_admin] = lambda: test_admin
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_admin, None)


@pytest.fixture(scope="function")
def unauth_client() -> Generator[TestClient, None, None]:
    """TestClient without any authentication override (fails closed)."""
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_admin, None)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_farm_multipolygon() -> Dict[str, Any]:
    """Sample valid MultiPolygon GeoJSON in Pune, Maharashtra (~116 hectares)."""
    return {
        "type": "MultiPolygon",
        "coordinates": [
            [
                [
                    [73.8500, 18.5200],
                    [73.8600, 18.5200],
                    [73.8600, 18.5300],
                    [73.8500, 18.5300],
                    [73.8500, 18.5200],
                ]
            ]
        ],
    }


@pytest.fixture
def sample_inside_polygon() -> Dict[str, Any]:
    """Sample valid Polygon GeoJSON completely inside sample_farm_multipolygon."""
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [73.8520, 18.5220],
                [73.8550, 18.5220],
                [73.8550, 18.5250],
                [73.8520, 18.5250],
                [73.8520, 18.5220],
            ]
        ],
    }


@pytest.fixture
def sample_outside_polygon() -> Dict[str, Any]:
    """Sample valid Polygon GeoJSON completely outside sample_farm_multipolygon."""
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [74.0000, 19.0000],
                [74.0100, 19.0000],
                [74.0100, 19.0100],
                [74.0000, 19.0100],
                [74.0000, 19.0000],
            ]
        ],
    }
