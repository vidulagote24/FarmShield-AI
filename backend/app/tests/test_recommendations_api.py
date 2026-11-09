"""Tests for Recommendation CRUD, status transition, and cross-farm zone mismatch validation."""

from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def setup_farms(auth_client: TestClient, sample_farm_multipolygon, sample_inside_polygon):
    """Fixture creating two farms with zones."""
    f1 = auth_client.post("/api/v1/farms/", json={
        "name": "Rec Farm 1",
        "crop_type": "sugarcane",
        "boundary": sample_farm_multipolygon,
    }).json()

    z1 = auth_client.post(f"/api/v1/farms/{f1['id']}/zones", json={
        "zone_name": "F1 Zone 1",
        "zone_code": "REC-Z1",
        "boundary": sample_inside_polygon,
    }).json()

    f2 = auth_client.post("/api/v1/farms/", json={
        "name": "Rec Farm 2",
        "crop_type": "cotton",
        "boundary": sample_farm_multipolygon,
    }).json()

    z2 = auth_client.post(f"/api/v1/farms/{f2['id']}/zones", json={
        "zone_name": "F2 Zone 2",
        "zone_code": "REC-Z2",
        "boundary": sample_inside_polygon,
    }).json()

    return {"farm1": f1, "zone1": z1, "farm2": f2, "zone2": z2}


def test_create_recommendation(auth_client: TestClient, setup_farms):
    """Test creating an agronomic recommendation with rich JSONB reasoning."""
    farm_id = setup_farms["farm1"]["id"]
    zone_id = setup_farms["zone1"]["id"]

    payload = {
        "farm_id": farm_id,
        "zone_id": zone_id,
        "recommendation_type": "irrigation",
        "title": "Irrigate Zone 1 with 25mm water",
        "description": "Soil moisture has dropped below the 35% threshold for sugarcane root zone.",
        "priority": "high",
        "status": "pending",
        "reasoning": {
            "model_version": "v1.2",
            "current_soil_moisture": 28.5,
            "threshold": 35.0,
            "forecast_rain_next_48h": 0.0,
        },
        "recommended_action": {
            "action_type": "irrigate",
            "quantity_mm": 25,
            "recommended_time": "early_morning",
        },
        "valid_until": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
    }
    response = auth_client.post("/api/v1/recommendations", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["priority"] == "high"
    assert data["status"] == "pending"
    assert data["reasoning"]["threshold"] == 35.0
    assert data["recommended_action"]["quantity_mm"] == 25


def test_recommendation_zone_mismatch_rejected(auth_client: TestClient, setup_farms):
    """Verify that referencing a zone from another farm is rejected with 400."""
    farm1_id = setup_farms["farm1"]["id"]
    farm2_zone_id = setup_farms["zone2"]["id"]

    payload = {
        "farm_id": farm1_id,
        "zone_id": farm2_zone_id,
        "recommendation_type": "fertilizer",
        "title": "Apply Urea",
        "description": "Nitrogen deficiency detected",
        "priority": "medium",
    }
    response = auth_client.post("/api/v1/recommendations", json=payload)
    assert response.status_code == 400
    assert "does not belong to farm" in response.json()["detail"]


def test_update_recommendation_status(auth_client: TestClient, setup_farms):
    """Test updating the lifecycle status of a recommendation via PATCH endpoint."""
    farm_id = setup_farms["farm1"]["id"]

    create_res = auth_client.post("/api/v1/recommendations", json={
        "farm_id": farm_id,
        "recommendation_type": "pest_control",
        "title": "Spray Neem Oil",
        "description": "Aphid infestation early signs",
        "priority": "low",
        "status": "pending",
    })
    rec_id = create_res.json()["id"]

    # PATCH status to applied
    patch_res = auth_client.patch(f"/api/v1/recommendations/{rec_id}/status", json={
        "status": "applied",
    })
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "applied"

    # Verify query by status=applied finds it
    list_res = auth_client.get(f"/api/v1/recommendations?farm_id={farm_id}&status=applied")
    assert list_res.status_code == 200
    assert any(r["id"] == rec_id for r in list_res.json()["items"])
