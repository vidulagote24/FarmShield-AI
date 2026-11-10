"""API integration and security tests for data ingestion endpoints."""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.models.observation import Observation


def test_ingestion_status_endpoint(client: TestClient):
    """Verify /api/v1/ingestion/status reports provider availability without auth."""
    resp = client.get("/api/v1/ingestion/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "operational"
    assert "providers" in data
    assert "open_meteo" in data["providers"]
    assert "sentinel2_stac" in data["providers"]
    assert "soil_adapter" in data["providers"]


def test_ingestion_endpoints_require_authentication(unauth_client: TestClient):
    """Verify protected ingestion endpoints reject unauthenticated requests with 401."""
    # Weather
    resp = unauth_client.post("/api/v1/ingestion/weather", json={
        "latitude": 18.15,
        "longitude": 74.58,
        "forecast_days": 1,
    })
    assert resp.status_code == 401

    # Satellite
    resp = unauth_client.post("/api/v1/ingestion/satellite", json={
        "bbox": [74.5, 18.1, 74.6, 18.2],
        "start_date": "2024-10-01",
        "end_date": "2024-10-05",
    })
    assert resp.status_code == 401

    # Soil
    resp = unauth_client.post("/api/v1/ingestion/soil", json={
        "sensor_id": "TEST-SENSOR-1",
        "volumetric_water_content_m3_m3": 0.25,
    })
    assert resp.status_code == 401


def test_ingest_soil_reading_api_flow(auth_client: TestClient, db_session, sample_farm_multipolygon, sample_inside_polygon):
    """Verify in-situ soil reading ingestion endpoint performs validation and persistence."""
    # Create farm & zone
    farm_res = auth_client.post("/api/v1/farms/", json={
        "name": "Soil Ingest Farm",
        "crop_type": "sugarcane",
        "boundary": sample_farm_multipolygon,
    })
    assert farm_res.status_code == 201
    farm_id = farm_res.json()["id"]

    zone_res = auth_client.post(f"/api/v1/farms/{farm_id}/zones", json={
        "zone_name": "Sensor Zone 1",
        "zone_code": "SZ-1",
        "boundary": sample_inside_polygon,
    })
    assert zone_res.status_code == 201
    zone_id = zone_res.json()["id"]

    # Ingest soil reading
    payload = {
        "sensor_id": "TDR-PROBE-99",
        "depth_min_cm": 0.0,
        "depth_max_cm": 30.0,
        "volumetric_water_content_m3_m3": 0.32,
        "farm_id": farm_id,
        "zone_id": zone_id,
    }
    resp = auth_client.post("/api/v1/ingestion/soil", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "success"
    assert data["persisted_observations_count"] == 1
    assert data["soil_summary"]["volumetric_water_content_m3_m3"] == 0.32
    assert data["soil_summary"]["provenance"] == "sensor_measured"

    # Verify DB persistence
    obs = db_session.query(Observation).filter(Observation.farm_id == farm_id).first()
    assert obs is not None
    assert obs.observation_type == "soil_moisture"
    assert obs.value == 0.32
    assert obs.unit == "m³/m³"
