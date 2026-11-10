"""Global test fixtures re-export for backend integration tests."""

from app.tests.conftest import (
    client,
    db_session,
    test_farmer,
    test_admin,
    auth_client,
    admin_client,
    unauth_client,
    sample_farm_multipolygon,
    sample_inside_polygon,
    sample_outside_polygon,
)

__all__ = [
    "client",
    "db_session",
    "test_farmer",
    "test_admin",
    "auth_client",
    "admin_client",
    "unauth_client",
    "sample_farm_multipolygon",
    "sample_inside_polygon",
    "sample_outside_polygon",
]
