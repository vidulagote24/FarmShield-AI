"""Tests for Observation CRUD, filtering, and cross-farm zone mismatch validation."""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def setup_farms_and_zones(auth_client: TestClient, sample_farm_multipolygon, sample_inside_polygon):
    """Fixture creating two distinct farms with zones for cross-farm boundary mismatch tests."""
    # Farm 1
    farm1_res = auth_client.post("/api/v1/farms/", json={
        "name": "Observation Farm 1",
        "crop_type": "wheat",
        "boundary": sample_farm_multipolygon,
    })
    farm1 = farm1_res.json()

    # Zone 1 on Farm 1
    zone1_res = auth_client.post(f"/api/v1/farms/{farm1['id']}/zones", json={
        "zone_name": "Farm 1 Zone A",
        "zone_code": "F1-ZA",
        "boundary": sample_inside_polygon,
    })
    zone1 = zone1_res.json()

    # Farm 2
    farm2_res = auth_client.post("/api/v1/farms/", json={
        "name": "Observation Farm 2",
        "crop_type": "rice",
        "boundary": sample_farm_multipolygon,
    })
    farm2 = farm2_res.json()

    # Zone 2 on Farm 2
    zone2_res = auth_client.post(f"/api/v1/farms/{farm2['id']}/zones", json={
        "zone_name": "Farm 2 Zone B",
        "zone_code": "F2-ZB",
        "boundary": sample_inside_polygon,
    })
    zone2 = zone2_res.json()

    return {
        "farm1": farm1,
        "zone1": zone1,
        "farm2": farm2,
        "zone2": zone2,
    }


def test_create_valid_observation_types(auth_client: TestClient, setup_farms_and_zones):
    """Test creating observations with supported observation types."""
    farm_id = setup_farms_and_zones["farm1"]["id"]
    zone_id = setup_farms_and_zones["zone1"]["id"]

    for obs_type in ["weather", "soil_moisture", "vegetation_index", "temperature", "rainfall", "satellite", "other"]:
        payload = {
            "farm_id": farm_id,
            "zone_id": zone_id,
            "observation_type": obs_type,
            "source": "ground_sensor",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "value": 24.5,
            "unit": "celsius" if obs_type == "temperature" else "units",
            "metadata": {"sensor_id": "SN-001"},
        }
        response = auth_client.post("/api/v1/observations/", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["observation_type"] == obs_type
        assert data["farm_id"] == farm_id
        assert data["zone_id"] == zone_id


def test_invalid_observation_type_rejected(auth_client: TestClient, setup_farms_and_zones):
    """Verify that unsupported observation types are rejected with 422 Unprocessable Entity."""
    farm_id = setup_farms_and_zones["farm1"]["id"]
    payload = {
        "farm_id": farm_id,
        "observation_type": "invalid_magic_type",
        "source": "manual",
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
    response = auth_client.post("/api/v1/observations/", json=payload)
    assert response.status_code == 422


def test_observation_zone_farm_mismatch_rejected(auth_client: TestClient, setup_farms_and_zones):
    """Verify that referencing a zone belonging to a DIFFERENT farm is rejected with 400 Bad Request."""
    farm1_id = setup_farms_and_zones["farm1"]["id"]
    farm2_zone_id = setup_farms_and_zones["zone2"]["id"]  # Belongs to farm2!

    payload = {
        "farm_id": farm1_id,
        "zone_id": farm2_zone_id,
        "observation_type": "soil_moisture",
        "source": "iot_sensor",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "value": 35.2,
        "unit": "percentage",
    }
    response = auth_client.post("/api/v1/observations/", json=payload)
    assert response.status_code == 400
    assert "does not belong to farm" in response.json()["detail"]


def test_query_observations_with_filters(auth_client: TestClient, setup_farms_and_zones):
    """Test filtering observations by farm_id, type, and pagination."""
    farm_id = setup_farms_and_zones["farm1"]["id"]

    # Insert 2 soil_moisture and 1 rainfall
    for i in range(2):
        auth_client.post("/api/v1/observations/", json={
            "farm_id": farm_id,
            "observation_type": "soil_moisture",
            "source": "probe",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "value": 20.0 + i,
        })
    auth_client.post("/api/v1/observations/", json={
        "farm_id": farm_id,
        "observation_type": "rainfall",
        "source": "rain_gauge",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "value": 15.0,
    })

    # Filter by observation_type=soil_moisture
    res = auth_client.get(f"/api/v1/observations/?farm_id={farm_id}&observation_type=soil_moisture")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 2
    assert all(item["observation_type"] == "soil_moisture" for item in data["items"])
