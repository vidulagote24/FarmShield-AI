"""Tests for IrrigationEvent CRUD, filtering, and cross-farm zone mismatch validation."""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def setup_farm_and_zone(auth_client: TestClient, sample_farm_multipolygon, sample_inside_polygon):
    """Fixture creating a farm and a zone."""
    f = auth_client.post("/api/v1/farms/", json={
        "name": "Irrigation Farm",
        "crop_type": "sugarcane",
        "boundary": sample_farm_multipolygon,
    }).json()

    z = auth_client.post(f"/api/v1/farms/{f['id']}/zones", json={
        "zone_name": "Irrigation Zone 1",
        "zone_code": "IRR-Z1",
        "boundary": sample_inside_polygon,
    }).json()

    # Another farm
    f2 = auth_client.post("/api/v1/farms/", json={
        "name": "Irrigation Farm 2",
        "crop_type": "rice",
        "boundary": sample_farm_multipolygon,
    }).json()

    return {"farm": f, "zone": z, "other_farm": f2}


def test_create_and_get_irrigation_event(auth_client: TestClient, setup_farm_and_zone):
    """Test recording an irrigation event."""
    farm_id = setup_farm_and_zone["farm"]["id"]
    zone_id = setup_farm_and_zone["zone"]["id"]

    payload = {
        "farm_id": farm_id,
        "zone_id": zone_id,
        "irrigation_date": datetime.now(timezone.utc).isoformat(),
        "water_quantity": 25000.0,
        "water_unit": "liters",
        "irrigation_method": "drip",
        "notes": "Scheduled 4-hour morning drip cycle",
    }
    response = auth_client.post("/api/v1/irrigation/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["farm_id"] == farm_id
    assert data["zone_id"] == zone_id
    assert data["water_quantity"] == 25000.0
    assert data["water_unit"] == "liters"
    assert data["irrigation_method"] == "drip"


def test_irrigation_zone_mismatch_rejected(auth_client: TestClient, setup_farm_and_zone):
    """Verify that using a zone from another farm is rejected with 400 Bad Request."""
    other_farm_id = setup_farm_and_zone["other_farm"]["id"]
    farm1_zone_id = setup_farm_and_zone["zone"]["id"]

    payload = {
        "farm_id": other_farm_id,
        "zone_id": farm1_zone_id,
        "irrigation_date": datetime.now(timezone.utc).isoformat(),
        "water_quantity": 1000.0,
        "water_unit": "liters",
    }
    response = auth_client.post("/api/v1/irrigation/", json=payload)
    assert response.status_code == 400
    assert "does not belong to farm" in response.json()["detail"]


def test_filter_and_delete_irrigation_events(auth_client: TestClient, setup_farm_and_zone):
    """Test filtering irrigation events by farm_id and deleting an event."""
    farm_id = setup_farm_and_zone["farm"]["id"]

    create_res = auth_client.post("/api/v1/irrigation/", json={
        "farm_id": farm_id,
        "irrigation_date": datetime.now(timezone.utc).isoformat(),
        "water_quantity": 500.0,
        "water_unit": "liters",
        "irrigation_method": "sprinkler",
    })
    event_id = create_res.json()["id"]

    # Filter by farm
    list_res = auth_client.get(f"/api/v1/irrigation/?farm_id={farm_id}")
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # Delete
    del_res = auth_client.delete(f"/api/v1/irrigation/{event_id}")
    assert del_res.status_code == 200

    # Confirm 404
    get_res = auth_client.get(f"/api/v1/irrigation/{event_id}")
    assert get_res.status_code == 404
