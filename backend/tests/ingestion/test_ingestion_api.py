"""API integration and security tests for data ingestion endpoints."""

from datetime import datetime, timezone
import time
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash
from app.models.farm import Farm, FarmZone
from app.models.observation import Observation
from app.models.user import User


@pytest.fixture
def auth_setup(db_session: Session):
    """Fixture creating Farmer A and Farmer B in the database with authentic JWT tokens."""
    suffix = uuid.uuid4().hex[:6]
    farmer_a = User(
        full_name=f"Farmer A {suffix}",
        email=f"farmer_a_{suffix}@farmshield.ai",
        hashed_password=get_password_hash("FarmerPassA123!"),
        role="farmer",
        is_active=True,
    )
    farmer_b = User(
        full_name=f"Farmer B {suffix}",
        email=f"farmer_b_{suffix}@farmshield.ai",
        hashed_password=get_password_hash("FarmerPassB123!"),
        role="farmer",
        is_active=True,
    )
    db_session.add_all([farmer_a, farmer_b])
    db_session.commit()
    db_session.refresh(farmer_a)
    db_session.refresh(farmer_b)

    token_a = create_access_token(farmer_a.id, farmer_a.role, farmer_a.email)
    token_b = create_access_token(farmer_b.id, farmer_b.role, farmer_b.email)

    yield {
        "farmer_a": farmer_a,
        "farmer_b": farmer_b,
        "headers_a": {"Authorization": f"Bearer {token_a}"},
        "headers_b": {"Authorization": f"Bearer {token_b}"},
    }

    # Clean teardown
    db_session.query(Observation).delete()
    db_session.query(FarmZone).delete()
    db_session.query(Farm).delete()
    db_session.query(User).filter(User.id.in_([farmer_a.id, farmer_b.id])).delete()
    db_session.commit()


def test_ingestion_status_endpoint_auth_and_caching(
    client: TestClient,
    auth_setup,
):
    """Verify /api/v1/ingestion/status requires auth and caches provider checks for 60 seconds."""
    # 1. Unauthenticated request must fail with 401
    unauth_resp = client.get("/api/v1/ingestion/status")
    assert unauth_resp.status_code == 401

    # 2. Authenticated request succeeds
    resp1 = client.get("/api/v1/ingestion/status", headers=auth_setup["headers_a"])
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["status"] == "operational"
    assert "providers" in data1
    assert "open_meteo" in data1["providers"]
    assert "sentinel2_stac" in data1["providers"]
    assert "soil_adapter" in data1["providers"]
    assert "cached_at" in data1

    # 3. Successive call within 60s returns cached data
    resp2 = client.get("/api/v1/ingestion/status", headers=auth_setup["headers_a"])
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["cached_at"] == data1["cached_at"]


def test_ingestion_endpoints_require_authentication(client: TestClient):
    """Verify all protected ingestion endpoints reject unauthenticated requests with 401."""
    # Status
    assert client.get("/api/v1/ingestion/status").status_code == 401

    # Weather
    resp_weather = client.post("/api/v1/ingestion/weather", json={
        "latitude": 18.15,
        "longitude": 74.58,
        "forecast_days": 1,
    })
    assert resp_weather.status_code == 401

    # Satellite
    resp_satellite = client.post("/api/v1/ingestion/satellite", json={
        "farm_id": str(uuid.uuid4()),
        "bbox": [74.5, 18.1, 74.6, 18.2],
        "start_date": "2024-10-01",
        "end_date": "2024-10-05",
    })
    assert resp_satellite.status_code == 401

    # Soil
    resp_soil = client.post("/api/v1/ingestion/soil", json={
        "sensor_id": "TEST-SENSOR-1",
        "volumetric_water_content_m3_m3": 0.25,
    })
    assert resp_soil.status_code == 401


def test_weather_ingestion_farm_and_zone_ownership_validation(
    client: TestClient,
    auth_setup,
    db_session,
    sample_farm_multipolygon,
    sample_inside_polygon,
):
    """Verify 7-step ownership and zone validation sequence for weather ingestion."""
    # 1. Create Farmer A Farm & Zone
    f_res = client.post("/api/v1/farms/", json={
        "name": "Farmer A Farm Weather",
        "crop_type": "sugarcane",
        "boundary": sample_farm_multipolygon,
    }, headers=auth_setup["headers_a"])
    assert f_res.status_code == 201
    farmer_a_farm_id = f_res.json()["id"]

    z_res = client.post(f"/api/v1/farms/{farmer_a_farm_id}/zones", json={
        "zone_name": "Farmer A Zone",
        "zone_code": "FAW-1",
        "boundary": sample_inside_polygon,
    }, headers=auth_setup["headers_a"])
    assert z_res.status_code == 201
    farmer_a_zone_id = z_res.json()["id"]

    # 2. Create Farmer B Farm & Zone
    fb_res = client.post("/api/v1/farms/", json={
        "name": "Farmer B Farm Weather",
        "crop_type": "cotton",
        "boundary": sample_farm_multipolygon,
    }, headers=auth_setup["headers_b"])
    assert fb_res.status_code == 201
    farmer_b_farm_id = fb_res.json()["id"]

    zb_res = client.post(f"/api/v1/farms/{farmer_b_farm_id}/zones", json={
        "zone_name": "Farmer B Zone",
        "zone_code": "FBW-1",
        "boundary": sample_inside_polygon,
    }, headers=auth_setup["headers_b"])
    assert zb_res.status_code == 201
    farmer_b_zone_id = zb_res.json()["id"]

    initial_obs_count = db_session.query(Observation).count()

    # Step 3: Non-existent farm -> 404
    non_existent_farm_id = str(uuid.uuid4())
    resp = client.post("/api/v1/ingestion/weather", json={
        "latitude": 18.52,
        "longitude": 73.85,
        "farm_id": non_existent_farm_id,
        "forecast_days": 1,
    }, headers=auth_setup["headers_a"])
    assert resp.status_code == 404
    assert f"Farm '{non_existent_farm_id}' was not found." in resp.json()["detail"]

    # Step 4: Farmer A accessing Farmer B's farm -> 403 Forbidden
    resp = client.post("/api/v1/ingestion/weather", json={
        "latitude": 18.52,
        "longitude": 73.85,
        "farm_id": farmer_b_farm_id,
        "forecast_days": 1,
    }, headers=auth_setup["headers_a"])
    assert resp.status_code == 403
    assert "permission" in resp.json()["detail"].lower()

    # Step 5: Non-existent zone -> 404
    non_existent_zone_id = str(uuid.uuid4())
    resp = client.post("/api/v1/ingestion/weather", json={
        "latitude": 18.52,
        "longitude": 73.85,
        "farm_id": farmer_a_farm_id,
        "zone_id": non_existent_zone_id,
        "forecast_days": 1,
    }, headers=auth_setup["headers_a"])
    assert resp.status_code == 404
    assert f"Zone '{non_existent_zone_id}' was not found." in resp.json()["detail"]

    # Step 6: Zone belongs to Farmer B's farm, requested under Farmer A's farm -> 400 Bad Request
    resp = client.post("/api/v1/ingestion/weather", json={
        "latitude": 18.52,
        "longitude": 73.85,
        "farm_id": farmer_a_farm_id,
        "zone_id": farmer_b_zone_id,
        "forecast_days": 1,
    }, headers=auth_setup["headers_a"])
    assert resp.status_code == 400
    assert "does not belong to farm" in resp.json()["detail"]

    # Step 7: Verify zero observations created during failed attempts
    assert db_session.query(Observation).count() == initial_obs_count

    # Valid request succeeds
    valid_resp = client.post("/api/v1/ingestion/weather", json={
        "latitude": 18.52,
        "longitude": 73.85,
        "farm_id": farmer_a_farm_id,
        "zone_id": farmer_a_zone_id,
        "forecast_days": 1,
    }, headers=auth_setup["headers_a"])
    assert valid_resp.status_code == 200
    assert valid_resp.json()["status"] == "success"
    assert db_session.query(Observation).count() > initial_obs_count


def test_satellite_ingestion_bbox_and_ownership_validation(
    client: TestClient,
    auth_setup,
    db_session,
    sample_farm_multipolygon,
):
    """Verify satellite bbox coordinate limits, ordering, and complete farm containment."""
    # Create Farmer A Farm
    farm_res = client.post("/api/v1/farms/", json={
        "name": "Satellite Farm A",
        "crop_type": "sugarcane",
        "boundary": sample_farm_multipolygon,
    }, headers=auth_setup["headers_a"])
    assert farm_res.status_code == 201
    farmer_a_farm_id = farm_res.json()["id"]

    # Create Farmer B Farm
    farm_b_res = client.post("/api/v1/farms/", json={
        "name": "Satellite Farm B",
        "crop_type": "wheat",
        "boundary": sample_farm_multipolygon,
    }, headers=auth_setup["headers_b"])
    assert farm_b_res.status_code == 201
    farmer_b_farm_id = farm_b_res.json()["id"]

    initial_obs_count = db_session.query(Observation).count()

    # 1. Missing farm_id -> 422 Unprocessable Entity
    resp = client.post("/api/v1/ingestion/satellite", json={
        "bbox": [73.852, 18.522, 73.858, 18.528],
        "start_date": "2024-10-01",
        "end_date": "2024-10-05",
    }, headers=auth_setup["headers_a"])
    assert resp.status_code == 422

    # 2. Non-existent farm_id -> 404 Not Found
    fake_farm_id = str(uuid.uuid4())
    resp = client.post("/api/v1/ingestion/satellite", json={
        "farm_id": fake_farm_id,
        "bbox": [73.852, 18.522, 73.858, 18.528],
        "start_date": "2024-10-01",
        "end_date": "2024-10-05",
    }, headers=auth_setup["headers_a"])
    assert resp.status_code == 404

    # 3. Farmer A accessing Farmer B's farm_id -> 403 Forbidden
    resp = client.post("/api/v1/ingestion/satellite", json={
        "farm_id": farmer_b_farm_id,
        "bbox": [73.852, 18.522, 73.858, 18.528],
        "start_date": "2024-10-01",
        "end_date": "2024-10-05",
    }, headers=auth_setup["headers_a"])
    assert resp.status_code == 403

    # 4. Inverted coordinates (min_lon >= max_lon) -> 400 Bad Request
    resp = client.post("/api/v1/ingestion/satellite", json={
        "farm_id": farmer_a_farm_id,
        "bbox": [73.858, 18.522, 73.852, 18.528],
        "start_date": "2024-10-01",
        "end_date": "2024-10-05",
    }, headers=auth_setup["headers_a"])
    assert resp.status_code == 400
    assert "Invalid bounding box coordinate ordering" in resp.json()["detail"]

    # 5. Inverted coordinates (min_lat >= max_lat) -> 400 Bad Request
    resp = client.post("/api/v1/ingestion/satellite", json={
        "farm_id": farmer_a_farm_id,
        "bbox": [73.852, 18.528, 73.858, 18.522],
        "start_date": "2024-10-01",
        "end_date": "2024-10-05",
    }, headers=auth_setup["headers_a"])
    assert resp.status_code == 400
    assert "Invalid bounding box coordinate ordering" in resp.json()["detail"]

    # 6. Physical coordinate limits violation -> 400 Bad Request
    resp = client.post("/api/v1/ingestion/satellite", json={
        "farm_id": farmer_a_farm_id,
        "bbox": [-190.0, 18.522, 73.858, 18.528],
        "start_date": "2024-10-01",
        "end_date": "2024-10-05",
    }, headers=auth_setup["headers_a"])
    assert resp.status_code == 400
    assert "out of valid range" in resp.json()["detail"]

    # 7. Bbox completely outside farm boundary -> 400 Bad Request
    resp = client.post("/api/v1/ingestion/satellite", json={
        "farm_id": farmer_a_farm_id,
        "bbox": [74.00, 19.00, 74.01, 19.01],
        "start_date": "2024-10-01",
        "end_date": "2024-10-05",
    }, headers=auth_setup["headers_a"])
    assert resp.status_code == 400
    assert "completely outside the farm boundary" in resp.json()["detail"]

    # 8. Bbox partially outside farm boundary -> 400 Bad Request
    resp = client.post("/api/v1/ingestion/satellite", json={
        "farm_id": farmer_a_farm_id,
        "bbox": [73.855, 18.525, 73.865, 18.535],
        "start_date": "2024-10-01",
        "end_date": "2024-10-05",
    }, headers=auth_setup["headers_a"])
    assert resp.status_code == 400
    assert "extends outside the farm boundary" in resp.json()["detail"]

    # 9. Verify zero observations created during rejected attempts
    assert db_session.query(Observation).count() == initial_obs_count

    # 10. Bbox fully inside farm boundary succeeds
    resp = client.post("/api/v1/ingestion/satellite", json={
        "farm_id": farmer_a_farm_id,
        "bbox": [73.852, 18.522, 73.858, 18.528],
        "start_date": "2024-10-01",
        "end_date": "2024-10-05",
    }, headers=auth_setup["headers_a"])
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


def test_soil_ingestion_ownership_and_zone_mismatch(
    client: TestClient,
    auth_setup,
    db_session,
    sample_farm_multipolygon,
    sample_inside_polygon,
):
    """Verify ownership, non-existent entity, and zone mismatch rejection on soil ingestion."""
    # Create Farmer A Farm & Zone
    f_res = client.post("/api/v1/farms/", json={
        "name": "Soil Security Farm A",
        "crop_type": "sugarcane",
        "boundary": sample_farm_multipolygon,
    }, headers=auth_setup["headers_a"])
    assert f_res.status_code == 201
    farmer_a_farm_id = f_res.json()["id"]

    z_res = client.post(f"/api/v1/farms/{farmer_a_farm_id}/zones", json={
        "zone_name": "Soil Zone A",
        "zone_code": "SZ-SEC-A",
        "boundary": sample_inside_polygon,
    }, headers=auth_setup["headers_a"])
    assert z_res.status_code == 201
    farmer_a_zone_id = z_res.json()["id"]

    # Create Farmer B Farm & Zone
    fb_res = client.post("/api/v1/farms/", json={
        "name": "Soil Security Farm B",
        "crop_type": "sugarcane",
        "boundary": sample_farm_multipolygon,
    }, headers=auth_setup["headers_b"])
    assert fb_res.status_code == 201
    farmer_b_farm_id = fb_res.json()["id"]

    zb_res = client.post(f"/api/v1/farms/{farmer_b_farm_id}/zones", json={
        "zone_name": "Soil Zone B",
        "zone_code": "SZ-SEC-B",
        "boundary": sample_inside_polygon,
    }, headers=auth_setup["headers_b"])
    assert zb_res.status_code == 201
    farmer_b_zone_id = zb_res.json()["id"]

    initial_obs = db_session.query(Observation).count()

    # 1. Non-existent farm_id -> 404
    fake_farm = str(uuid.uuid4())
    resp = client.post("/api/v1/ingestion/soil", json={
        "sensor_id": "TEST-PROBE",
        "volumetric_water_content_m3_m3": 0.28,
        "farm_id": fake_farm,
    }, headers=auth_setup["headers_a"])
    assert resp.status_code == 404
    assert f"Farm '{fake_farm}' was not found." in resp.json()["detail"]

    # 2. Farmer A accessing Farmer B's farm_id -> 403
    resp = client.post("/api/v1/ingestion/soil", json={
        "sensor_id": "TEST-PROBE",
        "volumetric_water_content_m3_m3": 0.28,
        "farm_id": farmer_b_farm_id,
    }, headers=auth_setup["headers_a"])
    assert resp.status_code == 403

    # 3. Zone mismatch -> 400
    resp = client.post("/api/v1/ingestion/soil", json={
        "sensor_id": "TEST-PROBE",
        "volumetric_water_content_m3_m3": 0.28,
        "farm_id": farmer_a_farm_id,
        "zone_id": farmer_b_zone_id,
    }, headers=auth_setup["headers_a"])
    assert resp.status_code == 400
    assert "does not belong to farm" in resp.json()["detail"]

    # 4. Non-existent zone -> 404
    fake_zone = str(uuid.uuid4())
    resp = client.post("/api/v1/ingestion/soil", json={
        "sensor_id": "TEST-PROBE",
        "volumetric_water_content_m3_m3": 0.28,
        "farm_id": farmer_a_farm_id,
        "zone_id": fake_zone,
    }, headers=auth_setup["headers_a"])
    assert resp.status_code == 404

    # 5. Rejected requests do not create DB observations
    assert db_session.query(Observation).count() == initial_obs

    # 6. Valid request succeeds and persists observation
    valid_resp = client.post("/api/v1/ingestion/soil", json={
        "sensor_id": "TDR-PROBE-SEC-1",
        "depth_min_cm": 0.0,
        "depth_max_cm": 30.0,
        "volumetric_water_content_m3_m3": 0.30,
        "farm_id": farmer_a_farm_id,
        "zone_id": farmer_a_zone_id,
    }, headers=auth_setup["headers_a"])
    assert valid_resp.status_code == 200
    assert valid_resp.json()["status"] == "success"
    assert db_session.query(Observation).count() == initial_obs + 1
