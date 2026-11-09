"""Tests for FarmZone spatial containment validation and CRUD APIs."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_farm_instance(auth_client: TestClient, sample_farm_multipolygon):
    """Fixture providing a persisted Farm instance for zone testing."""
    res = auth_client.post("/api/v1/farms/", json={
        "name": "Zone Testing Farm",
        "crop_type": "sugarcane",
        "boundary": sample_farm_multipolygon,
    })
    assert res.status_code == 201
    return res.json()


def test_create_zone_inside_farm_boundary_accepted(
    auth_client: TestClient, test_farm_instance, sample_inside_polygon
):
    """Verify that a zone with boundary completely inside the farm is accepted."""
    farm_id = test_farm_instance["id"]
    payload = {
        "zone_name": "North Field Block 1",
        "zone_code": "Z-01",
        "boundary": sample_inside_polygon,
        "metadata": {"soil_type": "black_clay", "irrigation_type": "drip"},
    }
    response = auth_client.post(f"/api/v1/farms/{farm_id}/zones", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["zone_code"] == "Z-01"
    assert data["zone_name"] == "North Field Block 1"
    assert data["farm_id"] == farm_id
    assert data["area_hectares"] > 0
    # Zone area must be smaller than parent farm area
    assert data["area_hectares"] < test_farm_instance["area_hectares"]
    assert data["metadata"]["soil_type"] == "black_clay"


def test_create_zone_outside_farm_boundary_rejected(
    auth_client: TestClient, test_farm_instance, sample_outside_polygon
):
    """Verify that a zone with boundary outside the farm is rejected with 400 Bad Request."""
    farm_id = test_farm_instance["id"]
    payload = {
        "zone_name": "Distant Field Block",
        "zone_code": "Z-99",
        "boundary": sample_outside_polygon,
    }
    response = auth_client.post(f"/api/v1/farms/{farm_id}/zones", json=payload)
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "Zone boundary must be completely contained within the farm boundary" in detail


def test_duplicate_zone_code_rejected(
    auth_client: TestClient, test_farm_instance, sample_inside_polygon
):
    """Verify that duplicate zone_code in the same farm is rejected with 409 Conflict."""
    farm_id = test_farm_instance["id"]
    payload = {
        "zone_name": "Block A",
        "zone_code": "BLK-A",
        "boundary": sample_inside_polygon,
    }
    res1 = auth_client.post(f"/api/v1/farms/{farm_id}/zones", json=payload)
    assert res1.status_code == 201

    # Duplicate zone_code
    res2 = auth_client.post(f"/api/v1/farms/{farm_id}/zones", json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


def test_list_and_delete_zones(
    auth_client: TestClient, test_farm_instance, sample_inside_polygon
):
    """Test listing zones for a farm and deleting a zone."""
    farm_id = test_farm_instance["id"]
    create_res = auth_client.post(f"/api/v1/farms/{farm_id}/zones", json={
        "zone_name": "Temporary Block",
        "zone_code": "TEMP-01",
        "boundary": sample_inside_polygon,
    })
    zone_id = create_res.json()["id"]

    # List
    list_res = auth_client.get(f"/api/v1/farms/{farm_id}/zones")
    assert list_res.status_code == 200
    assert any(z["id"] == zone_id for z in list_res.json()["items"])

    # Delete
    del_res = auth_client.delete(f"/api/v1/farms/{farm_id}/zones/{zone_id}")
    assert del_res.status_code == 200

    # Confirm gone
    get_res = auth_client.get(f"/api/v1/farms/{farm_id}/zones/{zone_id}")
    assert get_res.status_code == 404
