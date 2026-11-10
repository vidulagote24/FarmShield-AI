"""Full-system end-to-end integration test validating backend, intelligence, and ingestion workflows."""

from datetime import datetime, timezone
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_db
from app.models.farm import Farm, FarmZone
from app.models.irrigation import IrrigationEvent
from app.models.observation import Observation
from app.models.recommendation import Recommendation
from app.models.user import User
from app.intelligence.agronomy.water_balance import (
    SoilWaterCapacities,
    WaterBalanceRainfallMode,
    WaterBalanceResult,
)
from app.intelligence.decision.engine import (
    FarmZoneContext,
    evaluate_zone_decision,
)
from app.intelligence.explanations.explanation_service import (
    ExplanationLanguage,
    build_zone_explanation,
)
from app.intelligence.types import DataQualityStatus


def test_full_system_end_to_end_integration():
    """Verify complete end-to-end workflow from auth to ingestion, intelligence, and data retrieval."""
    client = TestClient(app)
    suffix = uuid.uuid4().hex[:6]
    email = f"e2e_farmer_{suffix}@farmshield.ai"
    password = "E2EPassword123!"

    # 1. Farmer Registration & Login
    reg_resp = client.post("/api/v1/auth/register", json={
        "full_name": f"E2E Farmer {suffix}",
        "email": email,
        "password": password,
        "phone": "+919876543210",
        "role": "farmer",
    })
    assert reg_resp.status_code == 201, f"Registration failed: {reg_resp.text}"
    user_id = reg_resp.json()["id"]

    login_resp = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
    })
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Verify /auth/me
    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["id"] == user_id

    # 3. Create Farm with Polygon geometry
    farm_boundary = {
        "type": "Polygon",
        "coordinates": [[
            [73.850, 18.520],
            [73.860, 18.520],
            [73.860, 18.530],
            [73.850, 18.530],
            [73.850, 18.520]
        ]]
    }
    farm_resp = client.post("/api/v1/farms/", json={
        "name": f"E2E Farm {suffix}",
        "description": "End to end test farm",
        "location_name": "Pune, Maharashtra",
        "crop_type": "sugarcane",
        "crop_variety": "Co 86032",
        "sowing_date": "2024-06-01",
        "boundary": farm_boundary,
    }, headers=headers)
    assert farm_resp.status_code == 201, f"Create farm failed: {farm_resp.text}"
    farm_data = farm_resp.json()
    farm_id = farm_data["id"]
    assert farm_data["area_hectares"] > 0

    # 4. Create Management Zone inside Farm Boundary
    zone_boundary = {
        "type": "Polygon",
        "coordinates": [[
            [73.852, 18.522],
            [73.858, 18.522],
            [73.858, 18.528],
            [73.852, 18.528],
            [73.852, 18.522]
        ]]
    }
    zone_resp = client.post(f"/api/v1/farms/{farm_id}/zones", json={
        "zone_name": "Zone A - Sugarcane Ratoon",
        "zone_code": f"ZA_{suffix}",
        "soil_type": "clay_loam",
        "boundary": zone_boundary,
    }, headers=headers)
    assert zone_resp.status_code == 201, f"Create zone failed: {zone_resp.text}"
    zone_id = zone_resp.json()["id"]

    # 5. Retrieve Farm Boundary and Zones
    boundary_resp = client.get(f"/api/v1/farms/{farm_id}/boundary", headers=headers)
    assert boundary_resp.status_code == 200
    assert boundary_resp.json()["boundary"]["type"] == "MultiPolygon"

    zones_list_resp = client.get(f"/api/v1/farms/{farm_id}/zones", headers=headers)
    assert zones_list_resp.status_code == 200
    assert len(zones_list_resp.json()["items"]) == 1

    # 6. Ingest Weather Observations (Live Open-Meteo or Fallback)
    weather_resp = client.post("/api/v1/ingestion/weather", json={
        "farm_id": farm_id,
        "zone_id": zone_id,
        "latitude": 18.525,
        "longitude": 73.855,
        "forecast_days": 1,
    }, headers=headers)
    assert weather_resp.status_code == 200, f"Weather ingestion failed: {weather_resp.text}"
    assert weather_resp.json()["status"] == "success"
    weather_persisted_count = weather_resp.json()["persisted_observations_count"]
    assert weather_persisted_count > 0

    # 7. Ingest Soil Sensor Reading
    soil_resp = client.post("/api/v1/ingestion/soil", json={
        "farm_id": farm_id,
        "zone_id": zone_id,
        "sensor_id": "PROBE-E2E-01",
        "depth_min_cm": 0.0,
        "depth_max_cm": 30.0,
        "volumetric_water_content_m3_m3": 0.28,
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }, headers=headers)
    assert soil_resp.status_code == 200
    assert soil_resp.json()["status"] == "success"

    # 8. Retrieve Persisted Observations via REST API
    obs_resp = client.get(f"/api/v1/farms/{farm_id}/observations", headers=headers)
    assert obs_resp.status_code == 200
    obs_items = obs_resp.json()["items"]
    assert len(obs_items) >= weather_persisted_count + 1
    obs_types = {o["observation_type"] for o in obs_items}
    assert "weather" in obs_types
    assert "soil_moisture" in obs_types

    # 9. Create Recommendation Grounded in Agronomic Evidence
    rec_resp = client.post(f"/api/v1/farms/{farm_id}/recommendations", json={
        "zone_id": zone_id,
        "recommendation_type": "irrigation",
        "title": "Irrigate Zone A - Sugarcane Ratoon",
        "description": "Apply 29.41 mm gross irrigation depth.",
        "priority": "high",
        "recommended_action": {
            "action": "irrigate",
            "net_irrigation_depth_mm": 25.0,
            "gross_irrigation_depth_mm": 29.41,
            "application_efficiency": 0.85,
        },
        "reasoning": {
            "stress_status": "water_stress_moderate",
            "confidence": 0.91,
            "soil_moisture_depleted": True,
        },
    }, headers=headers)
    assert rec_resp.status_code == 201
    rec_id = rec_resp.json()["id"]

    # 10. Update Recommendation Status Workflow
    patch_rec_resp = client.patch(f"/api/v1/recommendations/{rec_id}/status", json={
        "status": "accepted",
    }, headers=headers)
    assert patch_rec_resp.status_code == 200
    assert patch_rec_resp.json()["status"] == "accepted"

    # 11. Record Irrigation Event
    irr_resp = client.post(f"/api/v1/farms/{farm_id}/irrigation-events", json={
        "zone_id": zone_id,
        "irrigation_date": datetime.now(timezone.utc).isoformat(),
        "water_quantity": 15000.0,
        "water_unit": "liters",
        "irrigation_method": "drip",
        "notes": "Applied according to recommendation",
    }, headers=headers)
    assert irr_resp.status_code == 201

    # 12. Multilingual Intelligence Explanations Verification (EN, MR, HI)
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = WaterBalanceResult(
        rainfall_mode=WaterBalanceRainfallMode.PHYSICAL,
        soil_capacities=SoilWaterCapacities(
            field_capacity_m3_m3=0.30,
            wilting_point_m3_m3=0.15,
            available_water_capacity_m3_m3=0.15,
            effective_rooting_depth_m=0.8,
            depletion_fraction_p=0.5,
            depletion_fraction_p_table=0.5,
            total_available_water_mm=100.0,
            readily_available_water_mm=50.0,
        ),
        final_depletion_mm=55.0,
        total_available_water_mm=100.0,
        readily_available_water_mm=50.0,
        water_stress_coefficient_ks=0.90,
        crop_evapotranspiration_mm=5.0,
        adjusted_crop_evapotranspiration_mm=4.5,
        is_in_stress_zone=True,
        stress_deficit_mm=5.0,
        is_provisional_empirical=False,
        quality_status=DataQualityStatus.GOOD,
    )
    zone_context = FarmZoneContext(
        farm_id=farm_id,
        zone_id=zone_id,
        zone_name="Zone A - Sugarcane Ratoon",
        zone_area_ha=2.0,
        crop_type="sugarcane",
        application_efficiency=0.90,
    )
    decision = evaluate_zone_decision(farm_zone=zone_context, water_balance=wb, as_of_time=now_utc)

    # Test English
    expl_en = build_zone_explanation(
        decision=decision,
        water_balance=wb,
        farm_zone=zone_context,
        language=ExplanationLanguage.EN,
    )
    assert decision.action_type.value == "irrigate"
    assert expl_en.gross_irrigation_depth_mm == 61.11
    assert "61.1 mm gross irrigation" in expl_en.short_summary or "gross" in expl_en.short_summary
    assert "net crop deficit: 55.0 mm" in expl_en.short_summary or "deficit" in expl_en.short_summary

    # Test Marathi
    expl_mr = build_zone_explanation(
        decision=decision,
        water_balance=wb,
        farm_zone=zone_context,
        language=ExplanationLanguage.MR,
    )
    assert "सिंचन आवश्यक आहे" in expl_mr.short_summary
    assert "पुराSubवा" not in expl_mr.why_decision_produced

    # Test Hindi
    expl_hi = build_zone_explanation(
        decision=decision,
        water_balance=wb,
        farm_zone=zone_context,
        language=ExplanationLanguage.HI,
    )
    assert "सिंचाई आवश्यक है" in expl_hi.short_summary

    # 13. Verify Multi-Tenant Access Rejection (Farmer B cannot access Farmer A's farm)
    farmer_b_email = f"farmer_b_{suffix}@farmshield.ai"
    client.post("/api/v1/auth/register", json={
        "full_name": f"Farmer B {suffix}",
        "email": farmer_b_email,
        "password": password,
        "role": "farmer",
    })
    token_b = client.post("/api/v1/auth/login", json={
        "email": farmer_b_email,
        "password": password,
    }).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    forbidden_resp = client.get(f"/api/v1/farms/{farm_id}", headers=headers_b)
    assert forbidden_resp.status_code == 403

    # Clean up test records
    db = next(get_db())
    try:
        db.query(Observation).filter(Observation.farm_id == farm_id).delete()
        db.query(IrrigationEvent).filter(IrrigationEvent.farm_id == farm_id).delete()
        db.query(Recommendation).filter(Recommendation.farm_id == farm_id).delete()
        db.query(FarmZone).filter(FarmZone.farm_id == farm_id).delete()
        db.query(Farm).filter(Farm.id == farm_id).delete()
        db.query(User).filter(User.email.in_([email, farmer_b_email])).delete()
        db.commit()
    finally:
        db.close()
