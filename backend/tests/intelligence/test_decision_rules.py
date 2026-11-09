"""Tests for Phase 5 deterministic decision rules and action selection.

Validates:
1. IRRIGATE action with valid soil-water deficit (Dr >= RAW).
2. IRRIGATE rejection when water-balance evidence is missing or insufficient.
3. MONITOR action when Dr is approaching RAW (80% RAW <= Dr < RAW).
4. DELAY_AND_REASSESS with significant forecast rainfall (>= 10 mm within 48h).
5. DELAY_AND_REASSESS with recent irrigation redistribution (< 24h elapsed).
6. NO_ACTION_REQUIRED when root zone is healthy (Dr < 80% RAW).
7. Stale evidence rejection.
8. Suspect sensor evidence rejection.
9. Provisional empirical effective rainfall gating (Phase 3.2.4 contract).
10. Traceable reason codes for every rule and outcome.
"""

from datetime import datetime, timedelta, timezone
import pytest

from backend.app.intelligence.agronomy.water_balance import (
    SoilWaterCapacities,
    WaterBalanceRainfallMode,
    WaterBalanceResult,
)
from backend.app.intelligence.decision import (
    DecisionAction,
    DecisionConfig,
    DecisionReasonCode,
    FarmZoneContext,
    IrrigationHistoryContext,
    WeatherForecastContext,
    evaluate_zone_decision,
)
from backend.app.intelligence.types import DataQualityStatus


def _make_sample_wb(
    dr: float = 30.0,
    raw: float = 50.0,
    taw: float = 100.0,
    ks: float = 1.0,
    quality: DataQualityStatus = DataQualityStatus.GOOD,
    is_provisional: bool = False,
) -> WaterBalanceResult:
    """Helper creating synthetic WaterBalanceResult fixture."""
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
        is_provisional_empirical=is_provisional,
        quality_status=quality,
        audit_trail=["Synthetic water balance fixture for rule evaluation."],
    )


def _make_sample_zone(
    zone_id: str = "zone-1",
    crop: str = "wheat",
    stage: str = "vegetative",
    area_ha: float = 2.0,
    eff: float = 0.90,
) -> FarmZoneContext:
    """Helper creating synthetic FarmZoneContext fixture."""
    return FarmZoneContext(
        farm_id="farm-test",
        zone_id=zone_id,
        zone_name=f"Zone {zone_id}",
        zone_area_ha=area_ha,
        crop_type=crop,
        growth_stage=stage,
        irrigation_system_type="drip",
        application_efficiency=eff,
    )


# ==============================================================================
# 1. IRRIGATE WITH VALID DEFICIT (Dr >= RAW)
# ==============================================================================

def test_irrigate_with_valid_soil_water_deficit():
    """Verify IRRIGATE action is triggered when depletion exceeds RAW with valid evidence."""
    # Dr = 60.0 mm >= RAW = 50.0 mm, TAW = 100.0 mm, Ks = 0.80
    wb = _make_sample_wb(dr=60.0, raw=50.0, taw=100.0, ks=0.80)
    zone = _make_sample_zone(zone_id="zone-irrigate", area_ha=2.5, eff=0.90)

    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb)

    assert res.action_type == DecisionAction.IRRIGATE
    assert "RULE_6_WATER_DEFICIT_EXCEEDS_RAW" in res.decision_rules_triggered
    assert DecisionReasonCode.ACTION_IRRIGATE_DEPLETION_EXCEEDS_RAW in res.reason_codes
    assert DecisionReasonCode.ACTION_IRRIGATE_KS_STRESS_ACTIVE in res.reason_codes
    assert res.evidence_quality == DataQualityStatus.GOOD

    # Net depth refills Dr (60 mm); Gross depth = 60 / 0.90 = 66.67 mm
    assert res.net_irrigation_depth_mm == 60.0
    assert pytest.approx(res.gross_irrigation_depth_mm, abs=0.02) == 66.67
    # Volume = 66.67 mm * 2.5 ha * 10 = 1666.75 m³
    assert pytest.approx(res.irrigation_volume_m3, abs=0.5) == 1666.67


# ==============================================================================
# 2. IRRIGATE REJECTION ON INSUFFICIENT EVIDENCE
# ==============================================================================

def test_irrigate_rejection_when_water_balance_insufficient():
    """Verify that IRRIGATE is strictly rejected when water balance evidence is insufficient or missing."""
    zone = _make_sample_zone(zone_id="zone-insufficient")

    # Case A: water balance is None
    res_none = evaluate_zone_decision(farm_zone=zone, water_balance=None)
    assert res_none.action_type == DecisionAction.INSUFFICIENT_DATA
    assert res_none.net_irrigation_depth_mm is None
    assert res_none.gross_irrigation_depth_mm is None
    assert res_none.irrigation_volume_m3 is None
    assert DecisionReasonCode.EVIDENCE_WATER_BALANCE_INSUFFICIENT in res_none.reason_codes
    assert "RULE_1_INSUFFICIENT_EVIDENCE_GATING" in res_none.decision_rules_triggered

    # Case B: quality status is INSUFFICIENT
    wb_inadequate = _make_sample_wb(dr=70.0, quality=DataQualityStatus.INSUFFICIENT)
    res_inad = evaluate_zone_decision(farm_zone=zone, water_balance=wb_inadequate)
    assert res_inad.action_type == DecisionAction.INSUFFICIENT_DATA
    assert res_inad.net_irrigation_depth_mm is None
    assert DecisionReasonCode.EVIDENCE_WATER_BALANCE_INSUFFICIENT in res_inad.reason_codes

    # Case C: missing soil capacity (TAW is 0.0)
    wb_no_soil = _make_sample_wb(dr=50.0, taw=0.0)
    res_no_soil = evaluate_zone_decision(farm_zone=zone, water_balance=wb_no_soil)
    assert res_no_soil.action_type == DecisionAction.INSUFFICIENT_DATA
    assert DecisionReasonCode.EVIDENCE_SOIL_CAPACITY_MISSING in res_no_soil.reason_codes


# ==============================================================================
# 3. MONITOR NEAR RAW (80% RAW <= Dr < RAW)
# ==============================================================================

def test_monitor_when_depletion_approaching_raw():
    """Verify MONITOR action is triggered when depletion is near RAW without stress."""
    # RAW = 50.0 mm. 80% RAW = 40.0 mm.
    # Dr = 42.0 mm (approaching RAW), Ks = 1.0
    wb = _make_sample_wb(dr=42.0, raw=50.0, taw=100.0, ks=1.0)
    zone = _make_sample_zone(zone_id="zone-monitor", stage="vegetative")

    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb)

    assert res.action_type == DecisionAction.MONITOR
    assert "RULE_7_WATER_DEFICIT_APPROACHING_RAW" in res.decision_rules_triggered
    assert DecisionReasonCode.ACTION_MONITOR_APPROACHING_RAW in res.reason_codes
    # No water applied while monitoring
    assert res.net_irrigation_depth_mm is None
    assert res.gross_irrigation_depth_mm is None
    assert res.irrigation_volume_m3 is None


# ==============================================================================
# 4. DELAY_AND_REASSESS WITH WEATHER FORECAST EVIDENCE
# ==============================================================================

def test_delay_and_reassess_with_forecast_rainfall():
    """Verify DELAY_AND_REASSESS action when significant rain is forecast within horizon."""
    # Dr = 55.0 mm >= RAW (would otherwise irrigate)
    wb = _make_sample_wb(dr=55.0, raw=50.0, taw=100.0, ks=0.90)
    zone = _make_sample_zone(zone_id="zone-forecast")

    # Forecast 18 mm rain over next 36 hours from GFS with confirmed effective rain & ETc
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    forecast = WeatherForecastContext(
        forecast_precipitation_mm=18.0,
        forecast_total_precipitation_mm=18.0,
        forecast_effective_rainfall_mm=18.0,
        forecast_etc_mm=4.0,
        forecast_period_hours=36.0,
        forecast_source="Open-Meteo GFS 0.25deg",
        valid_from=now_utc,
        valid_to=now_utc + timedelta(hours=36),
    )

    res = evaluate_zone_decision(
        farm_zone=zone,
        water_balance=wb,
        forecast=forecast,
        as_of_time=now_utc,
    )

    assert res.action_type == DecisionAction.DELAY_AND_REASSESS
    assert "RULE_4_SIGNIFICANT_WEATHER_FORECAST_DELAY" in res.decision_rules_triggered
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN in res.reason_codes
    assert res.forecast_dependency is not None
    assert res.forecast_dependency["forecast_precipitation_mm"] == 18.0
    assert res.net_irrigation_depth_mm is None


# ==============================================================================
# 5. DELAY_AND_REASSESS WITH RECENT IRRIGATION REDISTRIBUTION
# ==============================================================================

def test_delay_and_reassess_with_recent_irrigation():
    """Verify DELAY_AND_REASSESS action when irrigation occurred within redistribution window."""
    wb = _make_sample_wb(dr=52.0, raw=50.0, taw=100.0, ks=0.95)
    zone = _make_sample_zone(zone_id="zone-recent-irr")

    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    # Irrigated 6 hours ago (within 24h redistribution window)
    history = IrrigationHistoryContext(
        last_irrigated_at=now_utc - timedelta(hours=6),
        last_depth_mm=40.0,
        irrigation_method="drip",
        redistribution_hours=24.0,
    )

    res = evaluate_zone_decision(
        farm_zone=zone,
        water_balance=wb,
        history=history,
        as_of_time=now_utc,
    )

    assert res.action_type == DecisionAction.DELAY_AND_REASSESS
    assert "RULE_5_RECENT_IRRIGATION_REDISTRIBUTION_DELAY" in res.decision_rules_triggered
    assert DecisionReasonCode.ACTION_DELAY_RECENT_IRRIGATION in res.reason_codes
    assert res.net_irrigation_depth_mm is None


# ==============================================================================
# 6. NO_ACTION_REQUIRED WITH HEALTHY ROOT ZONE
# ==============================================================================

def test_no_action_required_with_healthy_water_balance():
    """Verify NO_ACTION_REQUIRED when root-zone moisture is well within readily available limits."""
    # RAW = 50.0 mm. 80% RAW = 40.0 mm.
    # Dr = 15.0 mm (well below approach threshold), Ks = 1.00
    wb = _make_sample_wb(dr=15.0, raw=50.0, taw=100.0, ks=1.00)
    zone = _make_sample_zone(zone_id="zone-healthy")

    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb)

    assert res.action_type == DecisionAction.NO_ACTION_REQUIRED
    assert "RULE_8_HEALTHY_ROOT_ZONE_WATER_CONTENT" in res.decision_rules_triggered
    assert DecisionReasonCode.ACTION_NO_ACTION_ROOT_ZONE_HEALTHY in res.reason_codes
    assert res.net_irrigation_depth_mm is None
    assert res.gross_irrigation_depth_mm is None


# ==============================================================================
# 7. STALE EVIDENCE REJECTION
# ==============================================================================

def test_stale_evidence_rejection():
    """Verify that stale water-balance evidence generates INSUFFICIENT_DATA."""
    wb = _make_sample_wb(dr=65.0, quality=DataQualityStatus.STALE)
    zone = _make_sample_zone(zone_id="zone-stale")

    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb)

    assert res.action_type == DecisionAction.INSUFFICIENT_DATA
    assert "RULE_2_STALE_OR_SUSPECT_EVIDENCE_GATING" in res.decision_rules_triggered
    assert DecisionReasonCode.EVIDENCE_WATER_BALANCE_STALE in res.reason_codes
    assert res.net_irrigation_depth_mm is None


# ==============================================================================
# 8. SUSPECT SENSOR EVIDENCE REJECTION
# ==============================================================================

def test_suspect_sensor_evidence_rejection():
    """Verify that suspect sensor evidence generates INSUFFICIENT_DATA."""
    wb = _make_sample_wb(dr=60.0, quality=DataQualityStatus.SUSPECT)
    zone = _make_sample_zone(zone_id="zone-suspect")

    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb)

    assert res.action_type == DecisionAction.INSUFFICIENT_DATA
    assert "RULE_2_STALE_OR_SUSPECT_EVIDENCE_GATING" in res.decision_rules_triggered
    assert DecisionReasonCode.EVIDENCE_WATER_BALANCE_SUSPECT in res.reason_codes
    assert res.net_irrigation_depth_mm is None


# ==============================================================================
# 9. PROVISIONAL RAINFALL RESTRICTIONS
# ==============================================================================

def test_provisional_rainfall_restrictions_and_opt_in():
    """Verify provisional empirical rainfall blocks irrigation unless explicitly approved in research mode."""
    # Water balance uses provisional empirical rainfall (e.g. FAO Dependable)
    wb_prov = _make_sample_wb(dr=60.0, raw=50.0, is_provisional=True)
    zone = _make_sample_zone(zone_id="zone-prov")

    # Case A: Default strict mode (allow_provisional_rainfall = False)
    cfg_strict = DecisionConfig(allow_provisional_rainfall=False)
    res_blocked = evaluate_zone_decision(farm_zone=zone, water_balance=wb_prov, config=cfg_strict)

    assert res_blocked.action_type == DecisionAction.INSUFFICIENT_DATA
    assert "RULE_3_PROVISIONAL_RAINFALL_GATING" in res_blocked.decision_rules_triggered
    assert DecisionReasonCode.EVIDENCE_PROVISIONAL_RAINFALL_BLOCKED in res_blocked.reason_codes
    assert res_blocked.net_irrigation_depth_mm is None

    # Case B: Explicit opt-in (allow_provisional_rainfall = True)
    cfg_opt_in = DecisionConfig(allow_provisional_rainfall=True)
    res_opt = evaluate_zone_decision(farm_zone=zone, water_balance=wb_prov, config=cfg_opt_in)

    assert res_opt.action_type == DecisionAction.IRRIGATE
    assert "RULE_6_WATER_DEFICIT_EXCEEDS_RAW" in res_opt.decision_rules_triggered
    assert res_opt.net_irrigation_depth_mm == 60.0
