"""Tests for Phase 5 decision engine quantity validation, agronomic isolation, and reproducibility.

Validates:
1. Application efficiency and volumetric conversions (depth mm -> volume m³).
2. Strict volume suppression when zone area is unrecorded.
3. Agronomic non-watering isolation: Vegetation anomalies alone must NEVER trigger irrigation.
4. Soil chemical hazards (salinity, alkalinity, sodicity) must NOT trigger extra watering.
5. Deterministic repeated outputs.
"""

from datetime import datetime, timezone
import pytest

from backend.app.intelligence.agronomy.water_balance import (
    WaterBalanceRainfallMode,
    WaterBalanceResult,
)
from backend.app.intelligence.decision import (
    DecisionAction,
    DecisionConfig,
    DecisionReasonCode,
    FarmZoneContext,
    evaluate_zone_decision,
)
from backend.app.intelligence.stress.assessment import ZoneStressAssessment
from backend.app.intelligence.stress.scoring import (
    DomainStressEvaluation,
    StressReasonCode,
)
from backend.app.intelligence.types import DataQualityStatus, StressStatus


def _make_sample_wb(
    dr: float = 30.0,
    raw: float = 50.0,
    taw: float = 100.0,
    ks: float = 1.0,
) -> WaterBalanceResult:
    return WaterBalanceResult(
        rainfall_mode=WaterBalanceRainfallMode.PHYSICAL,
        initial_depletion_mm=max(0.0, dr - 5.0),
        final_depletion_mm=dr,
        total_available_water_mm=taw,
        readily_available_water_mm=raw,
        crop_evapotranspiration_mm=5.0,
        adjusted_crop_evapotranspiration_mm=5.0 * ks,
        water_stress_coefficient_ks=ks,
        is_in_stress_zone=(dr > raw),
        stress_deficit_mm=max(0.0, dr - raw),
        is_provisional_empirical=False,
        quality_status=DataQualityStatus.GOOD,
        audit_trail=["Synthetic water balance fixture."],
    )


def _make_dummy_stress_assessment(
    zone_id: str,
    veg_status: StressStatus = StressStatus.HEALTHY,
    veg_reasons: list = None,
    soil_status: StressStatus = StressStatus.HEALTHY,
    soil_reasons: list = None,
) -> ZoneStressAssessment:
    """Helper to construct synthetic Phase 4 ZoneStressAssessment."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    v_reasons = veg_reasons or [StressReasonCode.VEGETATION_CANOPY_HEALTHY]
    s_reasons = soil_reasons or [StressReasonCode.SOIL_CONDITIONS_OPTIMAL]

    overall = StressStatus.HEALTHY
    if veg_status == StressStatus.HIGH_STRESS or soil_status == StressStatus.HIGH_STRESS:
        overall = StressStatus.HIGH_STRESS
    elif veg_status == StressStatus.ATTENTION or soil_status == StressStatus.ATTENTION:
        overall = StressStatus.ATTENTION

    w_eval = DomainStressEvaluation(
        domain="water",
        status=StressStatus.HEALTHY,
        stress_detected=False,
        quality_status=DataQualityStatus.GOOD,
        reason_codes=[StressReasonCode.WATER_DEPLETION_NORMAL],
    )
    v_eval = DomainStressEvaluation(
        domain="vegetation",
        status=veg_status,
        stress_detected=(veg_status != StressStatus.HEALTHY),
        quality_status=DataQualityStatus.GOOD,
        reason_codes=v_reasons,
    )
    we_eval = DomainStressEvaluation(
        domain="weather",
        status=StressStatus.HEALTHY,
        stress_detected=False,
        quality_status=DataQualityStatus.GOOD,
        reason_codes=[StressReasonCode.WEATHER_CONDITIONS_FAVORABLE],
    )
    s_eval = DomainStressEvaluation(
        domain="soil",
        status=soil_status,
        stress_detected=(soil_status != StressStatus.HEALTHY),
        quality_status=DataQualityStatus.GOOD,
        reason_codes=s_reasons,
    )

    return ZoneStressAssessment(
        zone_id=zone_id,
        assessed_at=now_utc,
        status=overall,
        data_quality_status=DataQualityStatus.GOOD,
        domain_assessments={
            "water": w_eval,
            "vegetation": v_eval,
            "weather": we_eval,
            "soil": s_eval,
        },
        reason_codes=list(v_reasons) + list(s_reasons),
        evidence_summary={},
        missing_evidence=[],
        stale_evidence=[],
        suspect_evidence=[],
        uncertainty_and_limitations=[],
    )


# ==============================================================================
# 1. APPLICATION EFFICIENCY AND VOLUMETRIC CONVERSIONS
# ==============================================================================

def test_application_efficiency_and_volume_conversion():
    """Verify hand-calculated net refill, gross depth, and volumetric conversions."""
    # Hand calculation:
    # Dr = 45.0 mm >= RAW = 40.0 mm. Net refill = 45.0 mm.
    # Drip system with explicit efficiency eta = 0.90.
    # Expected gross depth = 45.0 / 0.90 = 50.0 mm.
    # Zone area = 3.2 ha.
    # Expected volume = 50.0 mm * 3.2 ha * 10.0 m³/(mm*ha) = 1600.0 m³.
    wb = _make_sample_wb(dr=45.0, raw=40.0, taw=100.0, ks=0.85)
    zone_drip = FarmZoneContext(
        farm_id="farm-vol",
        zone_id="zone-drip",
        zone_area_ha=3.2,
        crop_type="cotton",
        growth_stage="flowering",
        irrigation_system_type="drip",
        application_efficiency=0.90,
    )

    res_drip = evaluate_zone_decision(farm_zone=zone_drip, water_balance=wb)

    assert res_drip.action_type == DecisionAction.IRRIGATE
    assert res_drip.net_irrigation_depth_mm == 45.0
    assert pytest.approx(res_drip.gross_irrigation_depth_mm, abs=1e-2) == 50.0
    assert res_drip.application_efficiency == 0.90
    assert pytest.approx(res_drip.irrigation_volume_m3, abs=0.1) == 1600.0
    assert res_drip.validation_results["quantities"]["volume_consistent"] is True

    # Furrow irrigation test:
    # eta = 0.60. Expected gross = 45.0 / 0.60 = 75.0 mm.
    # Zone area = 2.0 ha. Expected volume = 75.0 * 2.0 * 10 = 1500.0 m³.
    zone_furrow = FarmZoneContext(
        farm_id="farm-vol",
        zone_id="zone-furrow",
        zone_area_ha=2.0,
        irrigation_system_type="furrow",
        application_efficiency=0.60,
    )
    res_furrow = evaluate_zone_decision(farm_zone=zone_furrow, water_balance=wb)
    assert pytest.approx(res_furrow.gross_irrigation_depth_mm, abs=1e-2) == 75.0
    assert pytest.approx(res_furrow.irrigation_volume_m3, abs=0.1) == 1500.0


def test_volume_suppression_when_area_unrecorded():
    """Verify that irrigation volume strictly remains None when zone area is unrecorded."""
    wb = _make_sample_wb(dr=50.0, raw=40.0, taw=100.0)
    zone_no_area = FarmZoneContext(
        farm_id="farm-vol",
        zone_id="zone-no-area",
        zone_area_ha=None,  # Unknown area!
        application_efficiency=0.85,
    )

    res = evaluate_zone_decision(farm_zone=zone_no_area, water_balance=wb)

    assert res.action_type == DecisionAction.IRRIGATE
    assert res.net_irrigation_depth_mm == 50.0
    assert pytest.approx(res.gross_irrigation_depth_mm, abs=0.05) == 58.82
    # Volume MUST be null
    assert res.irrigation_volume_m3 is None
    assert any("Zone area is unrecorded" in lim for lim in res.unresolved_limitations)


# ==============================================================================
# 2. AGRONOMIC NON-WATERING ISOLATION (VEGETATION & SOIL)
# ==============================================================================

def test_vegetation_anomaly_alone_must_never_trigger_irrigation():
    """Verify that a severe vegetation NDVI anomaly alone NEVER triggers irrigation if water balance is healthy."""
    # Root zone has healthy water content: Dr = 15.0 mm < 80% RAW (40.0 mm)
    wb_healthy = _make_sample_wb(dr=15.0, raw=50.0, taw=100.0, ks=1.00)

    # Zone has HIGH_STRESS vegetation assessment due to canopy anomaly (disease/pest/weed)
    stress_veg = _make_dummy_stress_assessment(
        zone_id="zone-veg-anomaly",
        veg_status=StressStatus.HIGH_STRESS,
        veg_reasons=[
            StressReasonCode.VEGETATION_STATISTICAL_ANOMALY,
            StressReasonCode.VEGETATION_MATERIAL_DECLINE,
            StressReasonCode.VEGETATION_ANOMALY_NEGATIVE,
        ],
    )
    zone = FarmZoneContext(farm_id="farm-iso", zone_id="zone-veg-anomaly", zone_area_ha=2.0)

    res = evaluate_zone_decision(
        farm_zone=zone,
        water_balance=wb_healthy,
        stress_assessment=stress_veg,
    )

    # Decision must be NO_ACTION_REQUIRED (root zone is healthy)
    assert res.action_type == DecisionAction.NO_ACTION_REQUIRED
    assert res.net_irrigation_depth_mm is None
    assert res.gross_irrigation_depth_mm is None
    assert res.irrigation_volume_m3 is None

    # Flag is preserved for agronomic inspection, not watering
    assert DecisionReasonCode.AGRONOMIC_FLAG_VEGETATION_ANOMALY_NON_WATERING in res.reason_codes
    assert any("Vegetation canopy spectral anomaly detected" in a for a in res.assumptions)
    assert res.domain_assessments["vegetation"] == "high_stress"


def test_salinity_and_sodicity_must_not_automatically_trigger_extra_watering():
    """Verify that soil salinity and alkalinity hazards do NOT inflate irrigation volume."""
    # Root zone deficit Dr = 50.0 mm >= RAW = 40.0 mm.
    # Refill depth is exactly 50.0 mm (max(0, Dr)).
    wb = _make_sample_wb(dr=50.0, raw=40.0, taw=100.0, ks=0.85)

    # Zone has severe soil salinity hazard
    stress_soil = _make_dummy_stress_assessment(
        zone_id="zone-saline",
        soil_status=StressStatus.HIGH_STRESS,
        soil_reasons=[
            StressReasonCode.SOIL_SALINITY_SEVERE,
            StressReasonCode.SOIL_PH_ALKALINE,
            StressReasonCode.SOIL_SODIC_HAZARD,
        ],
    )
    zone = FarmZoneContext(
        farm_id="farm-iso",
        zone_id="zone-saline",
        zone_area_ha=2.0,
        application_efficiency=0.90,
    )

    res = evaluate_zone_decision(
        farm_zone=zone,
        water_balance=wb,
        stress_assessment=stress_soil,
    )

    # Decision triggers IRRIGATE strictly for root-zone deficit Dr = 50 mm
    assert res.action_type == DecisionAction.IRRIGATE
    assert res.net_irrigation_depth_mm == 50.0
    # Gross depth is exactly 50.0 / 0.90 = 55.56 mm (NOT inflated for leaching)
    assert pytest.approx(res.gross_irrigation_depth_mm, abs=0.02) == 55.56

    # Flags attached without changing quantities
    assert DecisionReasonCode.AGRONOMIC_FLAG_SOIL_SALINITY_NON_WATERING in res.reason_codes
    assert DecisionReasonCode.AGRONOMIC_FLAG_SOIL_ALKALINE_NON_WATERING in res.reason_codes
    assert any("Soil salinity hazard detected" in a for a in res.assumptions)


# ==============================================================================
# 3. DETERMINISTIC REPRODUCIBILITY
# ==============================================================================

def test_deterministic_repeated_outputs():
    """Verify that evaluate_zone_decision returns identical outputs for identical inputs."""
    wb = _make_sample_wb(dr=48.0, raw=40.0, taw=100.0, ks=0.85)
    zone = FarmZoneContext(farm_id="farm-rep", zone_id="zone-rep", zone_area_ha=1.5)
    fixed_time = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)

    res1 = evaluate_zone_decision(farm_zone=zone, water_balance=wb, as_of_time=fixed_time)
    res2 = evaluate_zone_decision(farm_zone=zone, water_balance=wb, as_of_time=fixed_time)

    assert res1.action_type == res2.action_type
    assert res1.priority == res2.priority
    assert res1.net_irrigation_depth_mm == res2.net_irrigation_depth_mm
    assert res1.gross_irrigation_depth_mm == res2.gross_irrigation_depth_mm
    assert res1.irrigation_volume_m3 == res2.irrigation_volume_m3
    assert res1.reason_codes == res2.reason_codes
    assert res1.decision_rules_triggered == res2.decision_rules_triggered
