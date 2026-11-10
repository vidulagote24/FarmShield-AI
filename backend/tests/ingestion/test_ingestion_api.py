"""API integration and security tests for data ingestion endpoints."""

from datetime import datetime, timezone
import time
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1.endpoints.ingestion import pipeline
from app.core.security import create_access_token, get_password_hash
from app.ingestion.providers.base import ProviderFetchResult
from app.models.farm import Farm, FarmZone
from app.models.observation import Observation
from app.models.user import User
import unittest.mock


@pytest.fixture(autouse=True)
def reset_status_cache():
    """Ensure _STATUS_CACHE is clean before and after each test."""
    from app.api.v1.endpoints.ingestion import _STATUS_CACHE
    _STATUS_CACHE["timestamp"] = 0.0
    _STATUS_CACHE["data"] = None
    yield
    _STATUS_CACHE["timestamp"] = 0.0
    _STATUS_CACHE["data"] = None


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
    try:
        db_session.rollback()
        db_session.query(Observation).delete()
        db_session.query(FarmZone).delete()
        db_session.query(Farm).delete()
        db_session.query(User).filter(User.id.in_([farmer_a.id, farmer_b.id])).delete()
        db_session.commit()
    except Exception:
        db_session.rollback()


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
    assert data1["status"] in ("operational", "degraded")
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
    mock_stac_result = ProviderFetchResult(
        provider_name="Copernicus Sentinel-2 L2A (STAC)",
        endpoint_url=pipeline.satellite_provider.STAC_SEARCH_URL,
        retrieved_at=datetime.now(timezone.utc),
        status_code=200,
        payload={
            "features": [
                {
                    "type": "Feature",
                    "id": "S2A_TEST_SCENE_01",
                    "properties": {
                        "datetime": "2024-10-02T05:30:00Z",
                        "eo:cloud_cover": 5.0,
                        "platform": "Sentinel-2A",
                    },
                    "assets": {
                        "red": {"href": "https://example.com/B04.tif"},
                        "nir": {"href": "https://example.com/B08.tif"},
                    },
                }
            ]
        },
        is_live=False,
    )
    with unittest.mock.patch.object(pipeline.satellite_provider, "search_scenes", return_value=mock_stac_result):
        resp = client.post("/api/v1/ingestion/satellite", json={
            "farm_id": farmer_a_farm_id,
            "bbox": [73.852, 18.522, 73.858, 18.528],
            "start_date": "2024-10-01",
            "end_date": "2024-10-05",
        }, headers=auth_setup["headers_a"])
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"


def test_satellite_ingestion_non_finite_bbox_coordinates(
    client: TestClient,
    auth_setup,
    sample_farm_multipolygon,
):
    """Verify non-finite bbox coordinates (NaN, Inf) are rejected with 400 Bad Request."""
    farm_res = client.post("/api/v1/farms/", json={
        "name": "Non-Finite Test Farm",
        "crop_type": "sugarcane",
        "boundary": sample_farm_multipolygon,
    }, headers=auth_setup["headers_a"])
    assert farm_res.status_code == 201
    farm_id = farm_res.json()["id"]

    # NaN in bbox
    resp_nan = client.post("/api/v1/ingestion/satellite", json={
        "farm_id": farm_id,
        "bbox": ["NaN", 18.522, 73.858, 18.528],
        "start_date": "2024-10-01",
        "end_date": "2024-10-05",
    }, headers=auth_setup["headers_a"])
    assert resp_nan.status_code in (400, 422)

    # Inf in bbox
    resp_inf = client.post("/api/v1/ingestion/satellite", json={
        "farm_id": farm_id,
        "bbox": [73.852, "Infinity", 73.858, 18.528],
        "start_date": "2024-10-01",
        "end_date": "2024-10-05",
    }, headers=auth_setup["headers_a"])
    assert resp_inf.status_code in (400, 422)


def test_satellite_ingestion_crs_reprojection_and_mismatch(
    auth_setup,
):
    """Verify satellite validator reprojects non-4326 farm geometries and rejects invalid SRIDs."""
    from geoalchemy2.shape import from_shape
    import pyproj
    import shapely
    import numpy as np
    from shapely.geometry import box, MultiPolygon
    from fastapi import HTTPException
    from app.api.v1.endpoints.ingestion import validate_satellite_bbox_within_farm

    # Create a farm with boundary in EPSG:3857 (Web Mercator)
    b_4326 = box(73.85, 18.52, 73.86, 18.53)
    transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    def _proj(coords):
        x, y = transformer.transform(coords[:, 0], coords[:, 1])
        return np.column_stack([x, y])
    mp_3857 = shapely.transform(MultiPolygon([b_4326]), _proj)

    farm_3857 = Farm(
        id=uuid.uuid4(),
        owner_id=auth_setup["farmer_a"].id,
        name="Farm EPSG 3857",
        crop_type="sugarcane",
        boundary=from_shape(mp_3857, srid=3857),
        area_hectares=10.0,
        location_name="Pune",
    )

    # In WGS84, bbox inside the reprojected 3857 farm passes validation
    validate_satellite_bbox_within_farm(
        bbox=[73.852, 18.522, 73.858, 18.528],
        farm=farm_3857,
    )

    # In WGS84, bbox outside the reprojected 3857 farm raises 400
    with pytest.raises(HTTPException) as exc_info:
        validate_satellite_bbox_within_farm(
            bbox=[74.00, 19.00, 74.01, 19.01],
            farm=farm_3857,
        )
    assert exc_info.value.status_code == 400
    assert "outside the farm boundary" in exc_info.value.detail

    # Create a farm with unsupported / invalid SRID (999999)
    farm_bad_srid = Farm(
        id=uuid.uuid4(),
        owner_id=auth_setup["farmer_a"].id,
        name="Farm Bad SRID",
        crop_type="sugarcane",
        boundary=from_shape(MultiPolygon([b_4326]), srid=999999),
        area_hectares=10.0,
        location_name="Pune",
    )

    with pytest.raises(HTTPException) as exc_info:
        validate_satellite_bbox_within_farm(
            bbox=[73.852, 18.522, 73.858, 18.528],
            farm=farm_bad_srid,
        )
    assert exc_info.value.status_code == 400
    assert "Unsupported spatial reference system" in exc_info.value.detail or "invalid" in exc_info.value.detail.lower()

    # Create a farm with missing or negative SRID
    farm_bad_srid_neg = Farm(
        id=uuid.uuid4(),
        owner_id=auth_setup["farmer_a"].id,
        name="Farm Neg SRID",
        crop_type="sugarcane",
        boundary=from_shape(MultiPolygon([b_4326]), srid=-1),
        area_hectares=10.0,
        location_name="Pune",
    )

    with pytest.raises(HTTPException) as exc_info:
        validate_satellite_bbox_within_farm(
            bbox=[73.852, 18.522, 73.858, 18.528],
            farm=farm_bad_srid_neg,
        )
    assert exc_info.value.status_code == 400
    assert "missing or invalid SRID" in exc_info.value.detail


def test_status_endpoint_truthful_aggregation_and_exception_handling(
    client: TestClient,
    auth_setup,
):
    """Verify /status reports 'degraded' when a provider is unreachable or raises an exception."""
    from app.api.v1.endpoints.ingestion import pipeline, _STATUS_CACHE
    import unittest.mock as mock

    # Force cache expiry
    _STATUS_CACHE["timestamp"] = 0.0
    _STATUS_CACHE["data"] = None

    # Case 1: All providers reachable -> 'operational'
    with mock.patch.object(pipeline.weather_provider, "health_check", return_value=True):
        with mock.patch.object(pipeline.satellite_provider, "health_check", return_value=True):
            with mock.patch.object(pipeline.soil_provider, "health_check", return_value=True):
                resp = client.get("/api/v1/ingestion/status", headers=auth_setup["headers_a"])
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "operational"
                assert data["providers"]["open_meteo"]["reachable"] is True

    # Case 2: One provider unreachable -> 'degraded'
    _STATUS_CACHE["timestamp"] = 0.0
    _STATUS_CACHE["data"] = None
    with mock.patch.object(pipeline.weather_provider, "health_check", return_value=False):
        with mock.patch.object(pipeline.satellite_provider, "health_check", return_value=True):
            with mock.patch.object(pipeline.soil_provider, "health_check", return_value=True):
                resp = client.get("/api/v1/ingestion/status", headers=auth_setup["headers_a"])
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "degraded"
                assert data["providers"]["open_meteo"]["reachable"] is False

    # Case 3: Provider raises unexpected exception -> 'degraded', endpoint does not crash
    _STATUS_CACHE["timestamp"] = 0.0
    _STATUS_CACHE["data"] = None
    with mock.patch.object(pipeline.satellite_provider, "health_check", side_effect=ConnectionError("STAC API timeout")):
        with mock.patch.object(pipeline.weather_provider, "health_check", return_value=True):
            with mock.patch.object(pipeline.soil_provider, "health_check", return_value=True):
                resp = client.get("/api/v1/ingestion/status", headers=auth_setup["headers_a"])
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "degraded"
                assert data["providers"]["sentinel2_stac"]["reachable"] is False
                assert "STAC API timeout" in data["providers"]["sentinel2_stac"]["error"]


def test_status_cache_concurrency_synchronization(
    client: TestClient,
    auth_setup,
):
    """Verify concurrent requests during cache expiry invoke external provider check only once."""
    import concurrent.futures
    import unittest.mock as mock
    from app.api.v1.endpoints.ingestion import pipeline, _STATUS_CACHE

    _STATUS_CACHE["timestamp"] = 0.0
    _STATUS_CACHE["data"] = None

    probe_counter = mock.MagicMock(return_value=True)

    with mock.patch.object(pipeline.weather_provider, "health_check", probe_counter):
        def _fetch():
            return client.get("/api/v1/ingestion/status", headers=auth_setup["headers_a"])

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(_fetch) for _ in range(5)]
            responses = [f.result() for f in concurrent.futures.as_completed(futures)]

        for r in responses:
            assert r.status_code == 200
            assert r.json()["status"] == "operational"

        # Concurrency lock ensures probe was executed exactly once across all 5 threads
        assert probe_counter.call_count == 1


def test_authorization_rejection_prevents_provider_invocation(
    client: TestClient,
    auth_setup,
    sample_farm_multipolygon,
):
    """Verify unauthorized requests reject before calling external provider methods."""
    from app.api.v1.endpoints.ingestion import pipeline
    import unittest.mock as mock

    # Create Farmer B farm
    farm_b_res = client.post("/api/v1/farms/", json={
        "name": "Target Farm B",
        "crop_type": "sugarcane",
        "boundary": sample_farm_multipolygon,
    }, headers=auth_setup["headers_b"])
    assert farm_b_res.status_code == 201
    farm_b_id = farm_b_res.json()["id"]

    with mock.patch.object(pipeline.weather_provider, "fetch_forecast") as mock_fetch:
        # Farmer A tries to ingest for Farmer B's farm
        resp = client.post("/api/v1/ingestion/weather", json={
            "latitude": 18.52,
            "longitude": 73.85,
            "farm_id": farm_b_id,
            "forecast_days": 1,
        }, headers=auth_setup["headers_a"])
        assert resp.status_code == 403

        # External provider must never be called
        assert mock_fetch.call_count == 0


def test_zone_supplied_without_farm_id_access_control(
    client: TestClient,
    auth_setup,
    sample_farm_multipolygon,
    sample_inside_polygon,
):
    """Verify zone supplied without farm_id verifies parent farm ownership correctly."""
    # Create Farmer A Farm & Zone
    fa_res = client.post("/api/v1/farms/", json={
        "name": "Parent Farm A",
        "crop_type": "sugarcane",
        "boundary": sample_farm_multipolygon,
    }, headers=auth_setup["headers_a"])
    assert fa_res.status_code == 201
    farm_a_id = fa_res.json()["id"]

    za_res = client.post(f"/api/v1/farms/{farm_a_id}/zones", json={
        "zone_name": "Zone A",
        "zone_code": "ZA-PARENT-1",
        "boundary": sample_inside_polygon,
    }, headers=auth_setup["headers_a"])
    assert za_res.status_code == 201
    zone_a_id = za_res.json()["id"]

    # 1. Farmer A passes zone_a_id without farm_id -> resolves parent farm, succeeds (200)
    resp_owner = client.post("/api/v1/ingestion/weather", json={
        "latitude": 18.52,
        "longitude": 73.85,
        "zone_id": zone_a_id,
        "forecast_days": 1,
    }, headers=auth_setup["headers_a"])
    assert resp_owner.status_code == 200
    assert resp_owner.json()["status"] == "success"

    # 2. Farmer B passes zone_a_id without farm_id -> detects lack of ownership on parent farm, rejects with 403
    resp_other = client.post("/api/v1/ingestion/weather", json={
        "latitude": 18.52,
        "longitude": 73.85,
        "zone_id": zone_a_id,
        "forecast_days": 1,
    }, headers=auth_setup["headers_b"])
    assert resp_other.status_code == 403
    assert "permission" in resp_other.json()["detail"].lower()


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
