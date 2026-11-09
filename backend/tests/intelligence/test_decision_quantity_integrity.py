"""Phase 5.2: Final Decision and Quantity Integrity Tests.

Validates:
1. Distinction between forecast_total_precipitation_mm and forecast_effective_rainfall_mm.
2. Forecast effective rainfall compared against projected root-zone deficit (Dr) and RAW.
3. Forecast effective rainfall smaller than deficit relief requirement denies deferral and triggers IRRIGATE.
4. Forecast effective rainfall relieving deficit (Dr - Peff < RAW) approves DELAY_AND_REASSESS.
5. Missing infiltration/runoff evidence preserves clearly marked provisional forecast-deferral policy without data fabrication.
6. Unified quantity validation: Emergency IRRIGATE and Standard IRRIGATE share the exact same pipeline.
7. Emergency with unknown efficiency strictly withholds gross depth and volume while reporting net refill depth.
8. Emergency with missing zone area strictly withholds volume and suppresses farm-wide volume sum.
9. FarmDecisionSummary volume calculation status: COMPLETE_MEASURED vs COMPLETE_PROVISIONAL vs SUPPRESSED_MISSING_AREA vs SUPPRESSED_UNKNOWN_EFFICIENCY vs ZERO_IRRIGATION.
10. Mixed measured and assumed efficiency tracking across multi-zone farm decisions.
11. Split-application arithmetic: exact remainder assignment to final event, zero accumulation error, total mass conservation.
12. Configurable maximum event-depth operational policy (100.0 mm default) without universal physics claims.
"""

from datetime import date, datetime, timedelta, timezone
import pytest

from backend.app.intelligence.agronomy.water_balance import (
    WaterBalanceRainfallMode,
    WaterBalanceResult,
)
from backend.app.intelligence.decision import (
    DecisionAction,
    DecisionConfig,
    DecisionPriority,
    DecisionReasonCode,
    EfficiencyProvenance,
    EfficiencyVerificationRecord,
    FarmDecisionSummary,
    FarmZoneContext,
    VolumeCalculationStatus,
    WeatherForecastContext,
    calculate_split_application_depths,
    evaluate_farm_decisions,
    evaluate_zone_decision,
)
from backend.app.intelligence.types import DataQualityStatus


def _make_test_wb(
    dr: float = 30.0,
    raw: float = 50.0,
    taw: float = 100.0,
    ks: float = 1.0,
    quality: DataQualityStatus = DataQualityStatus.GOOD,
) -> WaterBalanceResult:
    """Helper constructing synthetic WaterBalanceResult fixture."""
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
        quality_status=quality,
        audit_trail=["Synthetic water balance fixture for Phase 5.2 integrity tests."],
    )


# ==============================================================================
# 1. FORECAST RAINFALL EFFECTIVENESS & DEFICIT COMPARISON
# ==============================================================================

def test_forecast_raw_versus_estimated_effective_rainfall():
    """Verify distinction between raw NWP forecast precipitation and estimated effective rainfall."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    zone = FarmZoneContext(farm_id="farm-f52", zone_id="z-eff-rain", irrigation_system_type="drip")
    wb = _make_test_wb(dr=60.0, raw=50.0, taw=100.0, ks=0.85)

    # Raw forecast precipitation is 25.0 mm, but expected effective infiltration is 18.0 mm
    fc = WeatherForecastContext(
        forecast_precipitation_mm=25.0,
        forecast_total_precipitation_mm=25.0,
        forecast_effective_rainfall_mm=18.0,
        forecast_etc_mm=4.0,
        effective_rainfall_method="validated_soil_water_retention",
        effective_rainfall_provenance="in_situ_tension_infiltrometer",
        forecast_period_hours=36.0,
        forecast_probability=0.80,
        forecast_source="ECMWF IFS 0.1deg",
        issue_time=now_utc - timedelta(hours=2),
    )

    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc, as_of_time=now_utc)

    # 18 mm effective rain on 60 mm deficit brings remaining deficit to 42 mm (< RAW 50 mm)
    assert res.action_type == DecisionAction.DELAY_AND_REASSESS
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN in res.reason_codes
    assert DecisionReasonCode.FORECAST_EFFECTIVE_RAINFALL_EVALUATED in res.reason_codes
    assert res.forecast_dependency is not None
    assert res.forecast_dependency["forecast_total_precipitation_mm"] == 25.0
    assert res.forecast_dependency["forecast_effective_rainfall_mm"] == 18.0
    assert res.forecast_dependency["forecast_etc_mm"] == 4.0
    assert res.forecast_dependency["effective_rainfall_method"] == "validated_soil_water_retention"


def test_forecast_effective_smaller_than_projected_deficit():
    """Verify that when forecast effective rain is too small to relieve stress, deferral is denied."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    zone = FarmZoneContext(farm_id="farm-f52", zone_id="z-small-relief", irrigation_system_type="drip")
    # Substantial root-zone deficit: Dr = 60 mm, RAW = 50 mm
    wb = _make_test_wb(dr=60.0, raw=50.0, taw=100.0, ks=0.85)

    # Total rain is 12 mm (> 10 mm raw threshold), BUT expected effective rain is only 6.0 mm!
    # With projected ETc = 4 mm, remaining deficit = 60 + 4 - 6 = 58 mm (> RAW 50 mm). Crop will remain stressed!
    fc_small_relief = WeatherForecastContext(
        forecast_precipitation_mm=12.0,
        forecast_total_precipitation_mm=12.0,
        forecast_effective_rainfall_mm=6.0,
        forecast_etc_mm=4.0,
        effective_rainfall_method="runoff_curve_number",
        forecast_period_hours=24.0,
        forecast_probability=0.85,
        forecast_source="GFS 0.25deg",
        issue_time=now_utc - timedelta(hours=2),
    )
    cfg = DecisionConfig(
        forecast_rain_delay_threshold_mm=10.0,
        forecast_min_deficit_coverage_fraction=0.50,  # Requires 50% coverage (30 mm)
    )

    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc_small_relief, config=cfg, as_of_time=now_utc)

    # Deferral denied! Remains IRRIGATE to protect crop
    assert res.action_type == DecisionAction.IRRIGATE
    assert DecisionReasonCode.FORECAST_INSUFFICIENT_DEFICIT_RELIEF in res.reason_codes
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN not in res.reason_codes
    assert res.net_irrigation_depth_mm == 60.0


def test_forecast_effective_relieving_projected_deficit():
    """Verify that when forecast effective rain restores moisture below RAW, deferral is granted."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    zone = FarmZoneContext(farm_id="farm-f52", zone_id="z-good-relief", irrigation_system_type="drip")
    wb = _make_test_wb(dr=60.0, raw=50.0, taw=100.0, ks=0.85)

    # Effective rain is 20.0 mm -> Remaining deficit = 60 + 4 - 20 = 44 mm (< RAW 50 mm)
    fc_adequate = WeatherForecastContext(
        forecast_precipitation_mm=25.0,
        forecast_total_precipitation_mm=25.0,
        forecast_effective_rainfall_mm=20.0,
        forecast_etc_mm=4.0,
        effective_rainfall_method="soil_water_retention",
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        forecast_source="GFS 0.25deg",
        issue_time=now_utc - timedelta(hours=1),
    )

    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc_adequate, as_of_time=now_utc)

    assert res.action_type == DecisionAction.DELAY_AND_REASSESS
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN in res.reason_codes
    assert DecisionReasonCode.FORECAST_EFFECTIVE_RAINFALL_EVALUATED in res.reason_codes


def test_missing_infiltration_runoff_evidence_retains_provisional_policy():
    """Verify missing infiltration evidence retains marked provisional deferral policy when Dr < RAW and opted in."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    zone = FarmZoneContext(farm_id="farm-f52", zone_id="z-no-infilt", irrigation_system_type="drip")
    wb = _make_test_wb(dr=42.0, raw=50.0, taw=100.0, ks=1.0)  # Dr < RAW (approaching RAW)

    # Infiltration/runoff evidence is NOT available (forecast_effective_rainfall_mm is None)
    # Valid ETc provided: Dr=42, RAW=50, ETc=4.0 over 36h keeps Dr strictly < RAW
    fc_raw_only = WeatherForecastContext(
        forecast_precipitation_mm=16.0,
        forecast_effective_rainfall_mm=None,  # Unknown effective rain!
        forecast_etc_mm=4.0,
        forecast_period_hours=36.0,
        forecast_probability=0.75,
        forecast_source="Open-Meteo GFS",
        issue_time=now_utc - timedelta(hours=2),
    )
    cfg = DecisionConfig(allow_provisional_forecast_deferral=True)

    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc_raw_only, config=cfg, as_of_time=now_utc)

    # Deferral triggered via clearly marked provisional policy
    assert res.action_type == DecisionAction.DELAY_AND_REASSESS
    assert DecisionReasonCode.FORECAST_DEFERRAL_PROVISIONAL_POLICY in res.reason_codes
    assert res.forecast_dependency is not None
    assert res.forecast_dependency["is_provisional_deferral"] is True
    assert any("Provisional forecast-deferral policy applied" in a for a in res.assumptions)


# ==============================================================================
# 2. UNIFIED QUANTITY-VALIDATION PIPELINE (EMERGENCY & STANDARD)
# ==============================================================================

def test_emergency_with_unknown_efficiency_strictly_withholds_quantities():
    """Verify emergency wilting condition strictly withholds gross depth and volume when efficiency is unknown."""
    # Emergency wilting: Dr = 100 mm >= TAW = 100 mm, Ks = 0.05
    wb_emergency = _make_test_wb(dr=100.0, raw=50.0, taw=100.0, ks=0.05)
    # Zone has area (2.5 ha) but NO application efficiency and NO irrigation system type
    zone_no_eff = FarmZoneContext(
        farm_id="farm-emrg-pipe",
        zone_id="z-emrg-no-eff",
        zone_area_ha=2.5,
        irrigation_system_type=None,
        application_efficiency=None,
    )

    res = evaluate_zone_decision(farm_zone=zone_no_eff, water_balance=wb_emergency)

    # Urgency does NOT bypass quantity validation!
    assert res.action_type == DecisionAction.IRRIGATE
    assert res.priority == DecisionPriority.CRITICAL
    assert res.net_irrigation_depth_mm == 100.0  # Net refill depth reported independently
    assert res.gross_irrigation_depth_mm is None  # Strictly withheld!
    assert res.irrigation_volume_m3 is None       # Strictly withheld!
    assert res.application_efficiency is None
    assert res.application_efficiency_provenance == EfficiencyProvenance.UNKNOWN
    assert DecisionReasonCode.EFFICIENCY_UNKNOWN_WITHHELD in res.reason_codes


def test_emergency_with_missing_zone_area_suppresses_volume():
    """Verify emergency wilting condition with missing area reports depth but strictly suppresses volume."""
    wb_emergency = _make_test_wb(dr=100.0, raw=50.0, taw=100.0, ks=0.05)
    # Efficiency is known (drip = 0.90), but area is missing (None)
    zone_no_area = FarmZoneContext(
        farm_id="farm-emrg-pipe",
        zone_id="z-emrg-no-area",
        zone_area_ha=None,
        irrigation_system_type="drip",
        application_efficiency=0.90,
    )

    res = evaluate_zone_decision(farm_zone=zone_no_area, water_balance=wb_emergency)

    assert res.action_type == DecisionAction.IRRIGATE
    assert res.priority == DecisionPriority.CRITICAL
    assert res.net_irrigation_depth_mm == 100.0
    assert pytest.approx(res.gross_irrigation_depth_mm, abs=0.02) == 111.11
    assert res.irrigation_volume_m3 is None  # Strictly null without area!
    assert any("Zone area is unrecorded" in lim for lim in res.unresolved_limitations)


# ==============================================================================
# 3. SPLIT-APPLICATION ARITHMETIC & MASS CONSERVATION
# ==============================================================================

def test_split_application_exact_arithmetic_and_remainder_conservation():
    """Verify split application assigns remainder to final event and strictly conserves total water."""
    # Deficit Dr = 90.03 mm, efficiency eta = 0.60
    # Gross depth = 90.03 / 0.60 = 150.05 mm > 100.0 mm max single event limit
    wb = _make_test_wb(dr=90.03, raw=70.0, taw=150.0, ks=0.70)
    zone = FarmZoneContext(
        farm_id="farm-split",
        zone_id="z-split-math",
        zone_area_ha=2.0,
        irrigation_system_type="furrow",
        application_efficiency=0.60,
    )
    cfg = DecisionConfig(max_allowable_gross_depth_mm=100.0)

    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, config=cfg)

    assert res.action_type == DecisionAction.IRRIGATE
    assert res.split_application_required is True
    assert res.split_event_count == 2
    assert res.total_gross_irrigation_depth_mm == 150.05

    # Event 1 = 75.02 mm, Event 2 = 75.03 mm (remainder assigned to final event!)
    assert res.split_event_depths_mm == [75.02, 75.03]
    # Sum of events must equal 150.05 mm exactly within float tolerance
    assert pytest.approx(sum(res.split_event_depths_mm), abs=1e-4) == 150.05
    # Every event must remain strictly <= 100.0 mm
    assert all(d <= 100.0 for d in res.split_event_depths_mm)

    # Three-event test case: Gross = 250.01 mm, max = 100.0 mm
    # 200.01 / 0.80 = 250.0125 -> Gross = 250.01 mm
    # 250.01 / 3 = 83.3366... Base = 83.33, remainder = 2 cents evenly distributed -> Events = [83.33, 83.34, 83.34]
    wb3 = _make_test_wb(dr=200.01, raw=100.0, taw=300.0, ks=0.60)
    zone3 = FarmZoneContext(farm_id="farm-split", zone_id="z3", zone_area_ha=1.0, application_efficiency=0.80)
    res3 = evaluate_zone_decision(farm_zone=zone3, water_balance=wb3, config=cfg)
    assert res3.split_event_count == 3
    assert res3.total_gross_irrigation_depth_mm == 250.01
    assert res3.split_event_depths_mm == [83.33, 83.34, 83.34]
    assert pytest.approx(sum(res3.split_event_depths_mm), abs=1e-4) == 250.01


# ==============================================================================
# 4. FARM-WIDE VOLUME METADATA & RELIABILITY CLASSIFICATION
# ==============================================================================

def test_farm_summary_complete_measured_vs_provisional():
    """Verify FarmDecisionSummary distinguishes measured-input totals from assumed-efficiency totals."""
    farm_id = "farm-meta-test"
    wb = _make_test_wb(dr=50.0, raw=40.0)

    # Farm 1: 100% measured application efficiency
    z_m1 = FarmZoneContext(farm_id=farm_id, zone_id="zm1", zone_area_ha=2.0, application_efficiency=0.90, application_efficiency_provenance=EfficiencyProvenance.MEASURED)
    z_m2 = FarmZoneContext(farm_id=farm_id, zone_id="zm2", zone_area_ha=1.0, application_efficiency=0.85, application_efficiency_provenance=EfficiencyProvenance.MEASURED)

    summ_measured = evaluate_farm_decisions(
        farm_id=farm_id,
        zone_contexts=[z_m1, z_m2],
        water_balances={"zm1": wb, "zm2": wb},
    )
    assert summ_measured.volume_calculation_complete is True
    assert summ_measured.has_provisional_efficiency is False
    assert summ_measured.provisional_zone_ids == []
    assert summ_measured.volume_calculation_status == VolumeCalculationStatus.COMPLETE_MEASURED
    assert summ_measured.total_estimated_irrigation_volume_m3 is not None

    # Farm 2: Assumed default efficiency (provisional)
    z_p1 = FarmZoneContext(farm_id=farm_id, zone_id="zp1", zone_area_ha=2.0, irrigation_system_type="drip")  # default 0.90 assumed
    summ_prov = evaluate_farm_decisions(
        farm_id=farm_id,
        zone_contexts=[z_p1],
        water_balances={"zp1": wb},
    )
    assert summ_prov.volume_calculation_complete is True
    assert summ_prov.has_provisional_efficiency is True
    assert summ_prov.provisional_zone_ids == ["zp1"]
    assert summ_prov.volume_calculation_status == VolumeCalculationStatus.COMPLETE_PROVISIONAL
    assert summ_prov.total_estimated_irrigation_volume_m3 is not None


def test_mixed_measured_and_assumed_zone_efficiencies():
    """Verify mixed farm with 1 measured zone and 1 assumed zone is marked COMPLETE_PROVISIONAL."""
    farm_id = "farm-mixed"
    wb = _make_test_wb(dr=50.0, raw=40.0)

    z1 = FarmZoneContext(farm_id=farm_id, zone_id="Z1_meas", zone_area_ha=2.0, application_efficiency=0.90, application_efficiency_provenance=EfficiencyProvenance.MEASURED)
    z2 = FarmZoneContext(farm_id=farm_id, zone_id="Z2_assum", zone_area_ha=1.5, irrigation_system_type="sprinkler")  # assumed 0.75

    summary = evaluate_farm_decisions(
        farm_id=farm_id,
        zone_contexts=[z1, z2],
        water_balances={"Z1_meas": wb, "Z2_assum": wb},
    )

    assert summary.volume_calculation_complete is True
    assert summary.has_provisional_efficiency is True
    assert summary.provisional_zone_ids == ["Z2_assum"]
    assert summary.volume_calculation_status == VolumeCalculationStatus.COMPLETE_PROVISIONAL
    assert summary.total_estimated_irrigation_volume_m3 is not None


def test_complete_vs_provisional_vs_incomplete_farm_volume_lifecycle():
    """Verify all 5 lifecycle statuses of VolumeCalculationStatus."""
    farm_id = "farm-lifecycle"
    wb_wet = _make_test_wb(dr=10.0, raw=50.0)  # Healthy (no action)
    wb_dry = _make_test_wb(dr=60.0, raw=50.0)  # Irrigated

    # 1. ZERO_IRRIGATION
    z_healthy = FarmZoneContext(farm_id=farm_id, zone_id="zh", zone_area_ha=2.0)
    s_zero = evaluate_farm_decisions(farm_id=farm_id, zone_contexts=[z_healthy], water_balances={"zh": wb_wet})
    assert s_zero.volume_calculation_status == VolumeCalculationStatus.ZERO_IRRIGATION
    assert s_zero.total_estimated_irrigation_volume_m3 == 0.0

    # 2. SUPPRESSED_MISSING_AREA
    z_no_area = FarmZoneContext(farm_id=farm_id, zone_id="zna", zone_area_ha=None, application_efficiency=0.90)
    s_area = evaluate_farm_decisions(farm_id=farm_id, zone_contexts=[z_no_area], water_balances={"zna": wb_dry})
    assert s_area.volume_calculation_status == VolumeCalculationStatus.SUPPRESSED_MISSING_AREA
    assert s_area.total_estimated_irrigation_volume_m3 is None

    # 3. SUPPRESSED_UNKNOWN_EFFICIENCY
    z_no_eff = FarmZoneContext(farm_id=farm_id, zone_id="zne", zone_area_ha=2.0, irrigation_system_type=None, application_efficiency=None)
    s_eff = evaluate_farm_decisions(farm_id=farm_id, zone_contexts=[z_no_eff], water_balances={"zne": wb_dry})
    assert s_eff.volume_calculation_status == VolumeCalculationStatus.SUPPRESSED_UNKNOWN_EFFICIENCY
    assert s_eff.total_estimated_irrigation_volume_m3 is None


# ==============================================================================
# 5. PHASE 5.2.1: SPLIT-APPLICATION ARITHMETIC EDGE CASES & MASS CONSERVATION
# ==============================================================================

def test_split_application_critical_edge_cases():
    """Verify split application algorithm across critical edge cases:
    - 100.01 mm
    - 199.99 mm
    - 200.01 mm
    - 999.99 mm (violates max event in buggy floor-and-remainder method)
    - Very large gross depth
    - Non-two-decimal input
    - Strict sum conservation
    - Maximum event depth invariant (every event <= max_event_depth)
    """
    from backend.app.intelligence.decision.engine import calculate_split_application_depths

    max_limit = 100.0

    # 1. 100.01 mm -> 2 events
    d1, tot1, n1 = calculate_split_application_depths(100.01, max_limit)
    assert n1 == 2
    assert d1 == [50.00, 50.01]
    assert pytest.approx(sum(d1), abs=1e-5) == 100.01
    assert all(d <= max_limit for d in d1)

    # 2. 199.99 mm -> 2 events
    d2, tot2, n2 = calculate_split_application_depths(199.99, max_limit)
    assert n2 == 2
    assert d2 == [99.99, 100.00]
    assert pytest.approx(sum(d2), abs=1e-5) == 199.99
    assert all(d <= max_limit for d in d2)

    # 3. 200.01 mm -> 3 events
    d3, tot3, n3 = calculate_split_application_depths(200.01, max_limit)
    assert n3 == 3
    assert d3 == [66.67, 66.67, 66.67]
    assert pytest.approx(sum(d3), abs=1e-5) == 200.01
    assert all(d <= max_limit for d in d3)

    # 4. 999.99 mm -> 10 events (Critical failure case of floor-and-terminal-remainder!)
    d4, tot4, n4 = calculate_split_application_depths(999.99, max_limit)
    assert n4 == 10
    # In buggy algorithm, final event was 100.08 mm!
    # In our corrected algorithm, 1 event of 99.99 and 9 events of 100.00:
    assert d4 == [99.99] + [100.00] * 9
    assert pytest.approx(sum(d4), abs=1e-5) == 999.99
    assert all(d <= max_limit for d in d4), f"Violation: events {[d for d in d4 if d > max_limit]} exceed {max_limit} mm!"

    # 5. Very large gross depth: 5432.10 mm -> 55 events
    d5, tot5, n5 = calculate_split_application_depths(5432.10, max_limit)
    assert n5 == 55
    assert pytest.approx(sum(d5), abs=1e-4) == 5432.10
    assert all(d <= max_limit for d in d5)
    assert max(d5) - min(d5) <= 0.01  # Perfectly even distribution within 1 cent

    # 6. Non-two-decimal input: 100.005 mm
    d6, tot6, n6 = calculate_split_application_depths(100.005, max_limit, precision=2)
    assert n6 == 2
    assert tot6 == 100.01
    assert pytest.approx(sum(d6), abs=1e-5) == 100.01
    assert all(d <= max_limit for d in d6)


# ==============================================================================
# 6. PHASE 5.2.1: FORECAST HORIZON WATER-BALANCE PROJECTION & TIMING
# ==============================================================================

def test_forecast_effective_rainfall_with_etc_24h_and_48h():
    """Verify forecast water-balance projection incorporates ETc over 24h and 48h horizons."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=40.0, raw=50.0, taw=100.0, ks=1.0)
    zone = FarmZoneContext(farm_id="farm-fc-proj", zone_id="z-etc-24", irrigation_system_type="drip")

    # 24h horizon: Dr = 40 mm, RAW = 50 mm.
    # ETc = 8.0 mm over 24h. Without rain, Dr would reach 48.0 mm.
    # Effective rain = 15.0 mm. Projected Dr = max(0, 40 + 8 - 15) = 33.0 mm <= RAW (50 mm).
    fc_24 = WeatherForecastContext(
        forecast_precipitation_mm=20.0,
        forecast_effective_rainfall_mm=15.0,
        forecast_etc_mm=8.0,
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        forecast_source="ECMWF IFS",
        issue_time=now_utc - timedelta(hours=1),
    )
    res_24 = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc_24, as_of_time=now_utc)
    assert res_24.action_type == DecisionAction.DELAY_AND_REASSESS
    assert DecisionReasonCode.FORECAST_ETC_EVALUATED in res_24.reason_codes
    assert DecisionReasonCode.FORECAST_PREVENTS_STRESS in res_24.reason_codes
    assert res_24.forecast_dependency["projected_depletion_mm"] == 33.0

    # 48h horizon: Dr = 40 mm, RAW = 50 mm.
    # ETc = 18.0 mm over 48h. Pre-rain Dr = 58.0 mm > RAW (stress would occur!).
    # Effective rain = 25.0 mm. Projected Dr = max(0, 40 + 18 - 25) = 33.0 mm <= RAW.
    fc_48 = WeatherForecastContext(
        forecast_precipitation_mm=30.0,
        forecast_effective_rainfall_mm=25.0,
        forecast_etc_mm=18.0,
        forecast_period_hours=48.0,
        forecast_probability=0.85,
        forecast_source="ECMWF IFS",
        issue_time=now_utc - timedelta(hours=1),
    )
    res_48 = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc_48, as_of_time=now_utc)
    assert res_48.action_type == DecisionAction.DELAY_AND_REASSESS
    assert res_48.forecast_dependency["projected_depletion_mm"] == 33.0
    assert res_48.forecast_dependency["pre_rain_depletion_mm"] == 58.0


def test_forecast_rainfall_timing_after_versus_before_stress():
    """Verify rainfall timing: rain delayed past stress onset blocks deferral."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    # Zone is approaching RAW: Dr = 46.0 mm, RAW = 50.0 mm.
    wb = _make_test_wb(dr=46.0, raw=50.0, taw=100.0, ks=1.0)
    zone = FarmZoneContext(farm_id="farm-timing", zone_id="z-time", irrigation_system_type="drip")

    # Case A: Rain arrives BEFORE stress onset (Rain onset in 4 hours; Dr reaches 46 + (12/24 * 4) = 48 < 50)
    fc_before = WeatherForecastContext(
        forecast_precipitation_mm=20.0,
        forecast_effective_rainfall_mm=15.0,
        forecast_etc_mm=12.0,
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        forecast_source="GFS 0.25deg",
        expected_rainfall_start=now_utc + timedelta(hours=4),
        issue_time=now_utc - timedelta(hours=1),
    )
    res_before = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc_before, as_of_time=now_utc)
    assert res_before.action_type == DecisionAction.DELAY_AND_REASSESS
    assert DecisionReasonCode.FORECAST_RAINFALL_AFTER_STRESS not in res_before.reason_codes

    # Case B: Rain arrives AFTER stress onset (Stress reached at hour 8; rain arrives in 20 hours!)
    # Crop would suffer 12 hours of unmitigated moisture stress before rain arrives!
    fc_after = WeatherForecastContext(
        forecast_precipitation_mm=20.0,
        forecast_effective_rainfall_mm=15.0,
        forecast_etc_mm=12.0,
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        forecast_source="GFS 0.25deg",
        expected_rainfall_start=now_utc + timedelta(hours=20),
        issue_time=now_utc - timedelta(hours=1),
    )
    res_after = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc_after, as_of_time=now_utc)
    # Delay is denied! Action proceeds to MONITOR (approaching RAW) or IRRIGATE
    assert res_after.action_type != DecisionAction.DELAY_AND_REASSESS
    assert res_after.forecast_dependency["rainfall_after_stress"] is True
    assert DecisionReasonCode.FORECAST_RAINFALL_AFTER_STRESS in res_after.reason_codes


def test_forecast_unable_to_bring_depletion_below_raw():
    """Verify forecast is rejected for deferral when effective rain leaves projected Dr > RAW."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    # Zone has active deficit: Dr = 65.0 mm, RAW = 50.0 mm
    wb = _make_test_wb(dr=65.0, raw=50.0, taw=100.0, ks=0.85)
    zone = FarmZoneContext(farm_id="farm-fail-relieve", zone_id="z-fail", irrigation_system_type="drip")

    # ETc = 6.0 mm, Eff Rain = 8.0 mm. Projected Dr = 65 + 6 - 8 = 63.0 mm > RAW (50.0 mm)
    fc_inadequate = WeatherForecastContext(
        forecast_precipitation_mm=12.0,
        forecast_effective_rainfall_mm=8.0,
        forecast_etc_mm=6.0,
        forecast_period_hours=24.0,
        forecast_probability=0.75,
        issue_time=now_utc - timedelta(hours=1),
    )
    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc_inadequate, as_of_time=now_utc)
    assert res.action_type == DecisionAction.IRRIGATE
    assert DecisionReasonCode.FORECAST_INSUFFICIENT_DEFICIT_RELIEF in res.reason_codes


def test_forecast_prevents_expected_raw_exceedance():
    """Verify forecast prevents expected RAW exceedance when approaching RAW."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    # Dr = 45.0 mm, RAW = 50.0 mm (approaching RAW at 90%).
    # ETc = 10.0 mm over 24h -> would reach 55.0 mm > RAW.
    # Eff Rain = 16.0 mm -> projected Dr = 45 + 10 - 16 = 39.0 mm <= RAW.
    wb = _make_test_wb(dr=45.0, raw=50.0, taw=100.0, ks=1.0)
    zone = FarmZoneContext(farm_id="farm-prevent", zone_id="z-prev", irrigation_system_type="drip")

    fc_prevent = WeatherForecastContext(
        forecast_precipitation_mm=22.0,
        forecast_effective_rainfall_mm=16.0,
        forecast_etc_mm=10.0,
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        issue_time=now_utc - timedelta(hours=1),
    )
    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc_prevent, as_of_time=now_utc)
    assert res.action_type == DecisionAction.DELAY_AND_REASSESS
    assert DecisionReasonCode.FORECAST_PREVENTS_STRESS in res.reason_codes


def test_missing_forecast_etc_evaluates_with_fallback_note():
    """Verify that when forecast ETc is missing:
    - Missing forecast ETc remains None (never 0.0).
    - Projected depletion and timing projections are marked unavailable (None).
    - Confirmed safe deferral cannot be claimed (FORECAST_PREVENTS_STRESS withheld).
    - Preserves FORECAST_ETC_MISSING in reasons.
    - Continues ordinary decision evaluation using current water balance (Dr=55 >= RAW=50 -> IRRIGATE).
    """
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=55.0, raw=50.0, taw=100.0, ks=0.90)
    zone = FarmZoneContext(farm_id="farm-no-etc", zone_id="z-no-etc", irrigation_system_type="drip")

    # forecast_etc_mm is None
    fc_no_etc = WeatherForecastContext(
        forecast_precipitation_mm=20.0,
        forecast_effective_rainfall_mm=15.0,
        forecast_etc_mm=None,
        forecast_period_hours=24.0,
        forecast_probability=0.75,
        issue_time=now_utc - timedelta(hours=1),
    )
    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc_no_etc, as_of_time=now_utc)
    assert res.action_type == DecisionAction.IRRIGATE
    assert DecisionReasonCode.FORECAST_ETC_MISSING in res.reason_codes
    assert DecisionReasonCode.FORECAST_PREVENTS_STRESS not in res.reason_codes
    assert res.forecast_dependency["forecast_etc_mm"] is None
    assert res.forecast_dependency["projected_depletion_mm"] is None
    assert res.forecast_dependency["stress_onset_hours"] is None


def test_provisional_forecast_deferral_with_reassessment_metadata():
    """Verify provisional forecast deferral populates reassessment timestamp and interval when Dr < RAW and opted in."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=42.0, raw=50.0, taw=100.0, ks=1.0)  # Dr < RAW
    zone = FarmZoneContext(farm_id="farm-reassess", zone_id="z-reassess", irrigation_system_type="drip")

    fc_provisional = WeatherForecastContext(
        forecast_precipitation_mm=18.0,
        forecast_effective_rainfall_mm=None,  # Missing infiltration -> provisional policy
        forecast_etc_mm=4.0,
        forecast_period_hours=24.0,
        forecast_probability=0.75,
        issue_time=now_utc - timedelta(hours=1),
    )
    cfg = DecisionConfig(
        forecast_reassessment_interval_hours=12.0,
        allow_provisional_forecast_deferral=True,
    )
    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc_provisional, config=cfg, as_of_time=now_utc)

    assert res.action_type == DecisionAction.DELAY_AND_REASSESS
    assert DecisionReasonCode.FORECAST_DEFERRAL_PROVISIONAL_POLICY in res.reason_codes
    assert res.forecast_reassessment_interval_hours == 12.0
    assert res.forecast_reassessment_timestamp == now_utc + timedelta(hours=12)
    assert any("Provisional forecast-deferral reassessment scheduled" in a for a in res.assumptions)


# ==============================================================================
# 7. PHASE 5.2.1: EFFICIENCY PROVENANCE CLASSIFICATION MAPPING
# ==============================================================================

def test_efficiency_provenance_complete_mapping():
    """Verify strict provenance mapping:
    - MEASURED: COMPLETE_MEASURED with documented field measurement.
    - OPERATOR_ENTERED: COMPLETE_PROVISIONAL unless evidence verifies measurement.
    - PROVIDER_SOURCED: COMPLETE_PROVISIONAL (hardware spec is not field-measured).
    - ASSUMED_DEFAULT: COMPLETE_PROVISIONAL.
    - UNKNOWN: SUPPRESSED_UNKNOWN_EFFICIENCY.
    """
    farm_id = "farm-prov-mapping"
    wb = _make_test_wb(dr=50.0, raw=40.0)

    # 1. MEASURED with documented reference -> COMPLETE_MEASURED
    z_meas = FarmZoneContext(
        farm_id=farm_id,
        zone_id="zm",
        zone_area_ha=2.0,
        application_efficiency=0.92,
        application_efficiency_provenance=EfficiencyProvenance.MEASURED,
        efficiency_measurement_reference="AUDIT-2026-NASHIK-01",
    )
    s_meas = evaluate_farm_decisions(farm_id=farm_id, zone_contexts=[z_meas], water_balances={"zm": wb})
    assert s_meas.volume_calculation_status == VolumeCalculationStatus.COMPLETE_MEASURED
    assert s_meas.has_provisional_efficiency is False
    assert s_meas.prioritized_zone_decisions[0].is_efficiency_verified is True

    # 2. OPERATOR_ENTERED without verification -> COMPLETE_PROVISIONAL
    z_op_unverified = FarmZoneContext(
        farm_id=farm_id,
        zone_id="z_op_u",
        zone_area_ha=2.0,
        application_efficiency=0.88,
        application_efficiency_provenance=EfficiencyProvenance.OPERATOR_ENTERED,
        is_efficiency_measurement_verified=False,
    )
    s_op_u = evaluate_farm_decisions(farm_id=farm_id, zone_contexts=[z_op_unverified], water_balances={"z_op_u": wb})
    assert s_op_u.volume_calculation_status == VolumeCalculationStatus.COMPLETE_PROVISIONAL
    assert s_op_u.has_provisional_efficiency is True
    assert "z_op_u" in s_op_u.provisional_zone_ids
    assert s_op_u.prioritized_zone_decisions[0].is_efficiency_provisional is True
    assert DecisionReasonCode.EFFICIENCY_OPERATOR_UNVERIFIED in s_op_u.prioritized_zone_decisions[0].reason_codes

    # 3. OPERATOR_ENTERED with structured field measurement verification -> COMPLETE_MEASURED
    z_op_verified = FarmZoneContext(
        farm_id=farm_id,
        zone_id="z_op_v",
        zone_area_ha=2.0,
        application_efficiency=0.88,
        application_efficiency_provenance=EfficiencyProvenance.OPERATOR_ENTERED,
        is_efficiency_measurement_verified=True,
        efficiency_measurement_reference="CATCH-CAN-TEST-2026",
        efficiency_verification=EfficiencyVerificationRecord(
            verification_method="in_situ_catch_can_audit",
            measurement_date=date(2026, 6, 1),
            system_or_zone_id="z_op_v",
            measured_efficiency=0.88,
            supporting_audit_reference="CATCH-CAN-TEST-2026",
            verification_status="verified",
        ),
    )
    s_op_v = evaluate_farm_decisions(farm_id=farm_id, zone_contexts=[z_op_verified], water_balances={"z_op_v": wb})
    assert s_op_v.volume_calculation_status == VolumeCalculationStatus.COMPLETE_MEASURED
    assert s_op_v.has_provisional_efficiency is False
    assert s_op_v.prioritized_zone_decisions[0].is_efficiency_verified is True

    # 3b. OPERATOR_ENTERED with arbitrary reference string ONLY (no structured record) -> COMPLETE_PROVISIONAL
    z_op_str_only = FarmZoneContext(
        farm_id=farm_id,
        zone_id="z_op_str",
        zone_area_ha=2.0,
        application_efficiency=0.88,
        application_efficiency_provenance=EfficiencyProvenance.OPERATOR_ENTERED,
        is_efficiency_measurement_verified=True,
        efficiency_measurement_reference="ARBITRARY-STRING-NOT-STRUCTURED",
        efficiency_verification=None,
    )
    s_op_str = evaluate_farm_decisions(farm_id=farm_id, zone_contexts=[z_op_str_only], water_balances={"z_op_str": wb})
    assert s_op_str.volume_calculation_status == VolumeCalculationStatus.COMPLETE_PROVISIONAL
    assert s_op_str.prioritized_zone_decisions[0].is_efficiency_provisional is True

    # 4. PROVIDER_SOURCED (manufacturer hardware spec) -> COMPLETE_PROVISIONAL
    z_prov = FarmZoneContext(
        farm_id=farm_id,
        zone_id="z_prov",
        zone_area_ha=2.0,
        application_efficiency=0.90,
        application_efficiency_provenance=EfficiencyProvenance.PROVIDER_SOURCED,
    )
    s_prov = evaluate_farm_decisions(farm_id=farm_id, zone_contexts=[z_prov], water_balances={"z_prov": wb})
    assert s_prov.volume_calculation_status == VolumeCalculationStatus.COMPLETE_PROVISIONAL
    assert s_prov.has_provisional_efficiency is True
    assert "z_prov" in s_prov.provisional_zone_ids
    assert s_prov.prioritized_zone_decisions[0].is_efficiency_provisional is True
    assert DecisionReasonCode.EFFICIENCY_PROVIDER_SOURCED in s_prov.prioritized_zone_decisions[0].reason_codes

    # 5. ASSUMED_DEFAULT -> COMPLETE_PROVISIONAL
    z_assumed = FarmZoneContext(
        farm_id=farm_id,
        zone_id="z_assum",
        zone_area_ha=2.0,
        irrigation_system_type="drip",
    )
    s_assum = evaluate_farm_decisions(farm_id=farm_id, zone_contexts=[z_assumed], water_balances={"z_assum": wb})
    assert s_assum.volume_calculation_status == VolumeCalculationStatus.COMPLETE_PROVISIONAL
    assert s_assum.has_provisional_efficiency is True

    # 6. UNKNOWN -> SUPPRESSED_UNKNOWN_EFFICIENCY
    z_unknown = FarmZoneContext(
        farm_id=farm_id,
        zone_id="z_unk",
        zone_area_ha=2.0,
        application_efficiency=None,
        irrigation_system_type=None,
    )
    s_unk = evaluate_farm_decisions(farm_id=farm_id, zone_contexts=[z_unknown], water_balances={"z_unk": wb})
    assert s_unk.volume_calculation_status == VolumeCalculationStatus.SUPPRESSED_UNKNOWN_EFFICIENCY
    assert s_unk.total_estimated_irrigation_volume_m3 is None

    # 7. Mixed Measured + Provider Sourced -> COMPLETE_PROVISIONAL
    s_mixed = evaluate_farm_decisions(
        farm_id=farm_id,
        zone_contexts=[z_meas, z_prov],
        water_balances={"zm": wb, "z_prov": wb},
    )
    assert s_mixed.volume_calculation_status == VolumeCalculationStatus.COMPLETE_PROVISIONAL
    assert s_mixed.has_provisional_efficiency is True
    assert s_mixed.provisional_zone_ids == ["z_prov"]
    assert s_mixed.total_estimated_irrigation_volume_m3 is not None


# ==============================================================================
# Phase 5.2.2: Decision Engine Integrity Audit Tests
# ==============================================================================

def test_split_application_downward_rounding_and_exact_bound():
    """Verify split application algorithm down-rounds max_event_depth_mm and bounds every event."""
    # 1. max_event_depth_mm = 100.005 at precision 2 -> down-rounds to 100.00 mm (10000 cents)
    # Total depth = 100.01 mm -> requires 2 events [50.00, 50.01]
    depths_1, tot_1, cnt_1 = calculate_split_application_depths(
        gross_depth_mm=100.01,
        max_event_depth_mm=100.005,
        precision=2,
    )
    assert cnt_1 == 2
    assert len(depths_1) == 2
    assert depths_1 == [50.00, 50.01]
    assert round(sum(depths_1), 2) == 100.01
    assert tot_1 == 100.01
    for d in depths_1:
        assert d <= 100.005

    # 2. max_event_depth_mm = 100.004 -> down-rounds to 100.00 mm
    # 100.00 mm fits in 1 event
    depths_2, tot_2, cnt_2 = calculate_split_application_depths(
        gross_depth_mm=100.00,
        max_event_depth_mm=100.004,
        precision=2,
    )
    assert cnt_2 == 1
    assert depths_2 == [100.00]
    assert tot_2 == 100.00

    # 100.01 mm under 100.004 mm max -> requires 2 events
    depths_2b, tot_2b, cnt_2b = calculate_split_application_depths(
        gross_depth_mm=100.01,
        max_event_depth_mm=100.004,
        precision=2,
    )
    assert cnt_2b == 2
    assert depths_2b == [50.00, 50.01]
    for d in depths_2b:
        assert d <= 100.004

    # 3. Non-two-decimal maximum limits: 75.339 -> down-rounds to 75.33 mm (7533 cents)
    depths_3, tot_3, cnt_3 = calculate_split_application_depths(
        gross_depth_mm=150.66,
        max_event_depth_mm=75.339,
        precision=2,
    )
    assert cnt_3 == 2
    assert depths_3 == [75.33, 75.33]
    assert round(sum(depths_3), 2) == 150.66

    depths_3b, tot_3b, cnt_3b = calculate_split_application_depths(
        gross_depth_mm=150.67,
        max_event_depth_mm=75.339,
        precision=2,
    )
    assert cnt_3b == 3  # 150.67 > 2 * 75.33 (150.66) -> requires 3 events
    assert depths_3b == [50.22, 50.22, 50.23]
    assert round(sum(depths_3b), 2) == 150.67
    for d in depths_3b:
        assert d <= 75.339

    # 4. Large depth and event count: 2500.55 mm with 100.0 mm max limit
    depths_4, tot_4, cnt_4 = calculate_split_application_depths(
        gross_depth_mm=2500.55,
        max_event_depth_mm=100.0,
        precision=2,
    )
    assert cnt_4 == 26  # ceil(250055 / 10000) = 26
    assert len(depths_4) == 26
    assert round(sum(depths_4), 2) == 2500.55
    for d in depths_4:
        assert d <= 100.0

    # 5. Runtime safety exception on invalid inputs (not bare assert)
    with pytest.raises(ValueError, match="must be positive"):
        calculate_split_application_depths(50.0, 0.0)
    with pytest.raises(ValueError, match="must be positive"):
        calculate_split_application_depths(50.0, -10.0)
    with pytest.raises(ValueError, match="rounds downward to 0"):
        calculate_split_application_depths(50.0, 0.0001, precision=2)


def test_missing_forecast_etc_matrix_dr_below_raw():
    """Missing forecast ETc with current Dr below RAW: evaluates to NO_ACTION_REQUIRED."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=20.0, raw=50.0, taw=100.0, ks=1.0)
    zone = FarmZoneContext(farm_id="farm-f522", zone_id="z-below-raw", irrigation_system_type="drip")

    fc = WeatherForecastContext(
        forecast_precipitation_mm=25.0,
        forecast_effective_rainfall_mm=18.0,
        forecast_etc_mm=None,  # Missing ETc
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        issue_time=now_utc - timedelta(hours=1),
    )
    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc, as_of_time=now_utc)

    assert res.action_type == DecisionAction.NO_ACTION_REQUIRED
    assert DecisionReasonCode.ACTION_NO_ACTION_ROOT_ZONE_HEALTHY in res.reason_codes
    assert DecisionReasonCode.FORECAST_ETC_MISSING in res.reason_codes
    assert res.forecast_dependency["forecast_etc_mm"] is None
    assert res.forecast_dependency["projected_depletion_mm"] is None


def test_missing_forecast_etc_matrix_dr_approaching_raw():
    """Missing forecast ETc with current Dr approaching RAW: evaluates to MONITOR."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    # Dr = 42.0 >= 80% RAW (40.0 mm), Ks = 1.0
    wb = _make_test_wb(dr=42.0, raw=50.0, taw=100.0, ks=1.0)
    zone = FarmZoneContext(farm_id="farm-f522", zone_id="z-app-raw", irrigation_system_type="drip")

    fc = WeatherForecastContext(
        forecast_precipitation_mm=25.0,
        forecast_effective_rainfall_mm=18.0,
        forecast_etc_mm=None,  # Missing ETc
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        issue_time=now_utc - timedelta(hours=1),
    )
    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc, as_of_time=now_utc)

    assert res.action_type == DecisionAction.MONITOR
    assert DecisionReasonCode.ACTION_MONITOR_APPROACHING_RAW in res.reason_codes
    assert DecisionReasonCode.FORECAST_ETC_MISSING in res.reason_codes
    assert res.forecast_dependency["forecast_etc_mm"] is None
    assert res.forecast_dependency["projected_depletion_mm"] is None


def test_missing_forecast_etc_matrix_dr_above_raw():
    """Missing forecast ETc with current Dr above RAW: deferral withheld, evaluates to IRRIGATE."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=60.0, raw=50.0, taw=100.0, ks=0.85)
    zone = FarmZoneContext(farm_id="farm-f522", zone_id="z-above-raw", irrigation_system_type="drip")

    fc = WeatherForecastContext(
        forecast_precipitation_mm=25.0,
        forecast_effective_rainfall_mm=20.0,
        forecast_etc_mm=None,  # Missing ETc: cannot prove safe deferral
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        issue_time=now_utc - timedelta(hours=1),
    )
    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc, as_of_time=now_utc)

    assert res.action_type == DecisionAction.IRRIGATE
    assert DecisionReasonCode.ACTION_IRRIGATE_DEPLETION_EXCEEDS_RAW in res.reason_codes
    assert DecisionReasonCode.FORECAST_ETC_MISSING in res.reason_codes
    assert DecisionReasonCode.FORECAST_PREVENTS_STRESS not in res.reason_codes
    assert res.forecast_dependency["forecast_etc_mm"] is None
    assert res.forecast_dependency["projected_depletion_mm"] is None


def test_missing_forecast_etc_matrix_provisional_raw_rain_when_effective_rain_unavailable():
    """Missing forecast ETc with provisional raw rain policy: Phase 5.2.4 blocks deferral."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=42.0, raw=50.0, taw=100.0, ks=1.0)  # Dr < RAW (approaching RAW)
    zone = FarmZoneContext(farm_id="farm-f522", zone_id="z-provisional", irrigation_system_type="drip")

    fc = WeatherForecastContext(
        forecast_precipitation_mm=22.0,
        forecast_effective_rainfall_mm=None,  # Missing infiltration -> provisional policy
        forecast_etc_mm=None,  # Missing ETc -> cannot project root-zone depletion
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        issue_time=now_utc - timedelta(hours=1),
    )
    cfg = DecisionConfig(
        forecast_reassessment_interval_hours=12.0,
        allow_provisional_forecast_deferral=True,
    )
    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc, config=cfg, as_of_time=now_utc)

    # Phase 5.2.4: Missing ETc blocks provisional deferral; evaluates to MONITOR (approaching RAW)
    assert res.action_type == DecisionAction.MONITOR
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN not in res.reason_codes
    assert DecisionReasonCode.FORECAST_ETC_MISSING in res.reason_codes
    assert res.forecast_reassessment_interval_hours is None
    assert res.forecast_reassessment_timestamp is None


def test_missing_forecast_etc_matrix_emergency_condition():
    """Emergency wilting overrides all forecasts regardless of missing or present ETc."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    # Severe permanent wilting: Dr = 100.0 >= TAW = 100.0, Ks = 0.15 <= 0.20
    wb = _make_test_wb(dr=100.0, raw=50.0, taw=100.0, ks=0.15)
    zone = FarmZoneContext(farm_id="farm-f522", zone_id="z-emerg", irrigation_system_type="drip")

    fc = WeatherForecastContext(
        forecast_precipitation_mm=30.0,
        forecast_effective_rainfall_mm=25.0,
        forecast_etc_mm=None,  # Missing ETc
        forecast_period_hours=24.0,
        forecast_probability=0.90,
        issue_time=now_utc - timedelta(hours=1),
    )
    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc, as_of_time=now_utc)

    assert res.action_type == DecisionAction.IRRIGATE
    assert res.priority == DecisionPriority.CRITICAL
    assert DecisionReasonCode.ACTION_IRRIGATE_EMERGENCY_OVERRIDE in res.reason_codes
    assert DecisionReasonCode.ACTION_IRRIGATE_WILTING_POINT_HAZARD in res.reason_codes
    assert DecisionReasonCode.FORECAST_ETC_MISSING in res.reason_codes


def test_structured_efficiency_verification_evidence_validation():
    """Verify structured EfficiencyVerificationRecord validation rules:
    - Status 'verified', matching zone and efficiency -> COMPLETE_MEASURED.
    - Status 'rejected' -> COMPLETE_PROVISIONAL.
    - Mismatched zone ID -> COMPLETE_PROVISIONAL.
    - Mismatched measured efficiency -> COMPLETE_PROVISIONAL.
    - Arbitrary string alone -> COMPLETE_PROVISIONAL.
    """
    farm_id = "farm-audit-rec"
    wb = _make_test_wb(dr=50.0, raw=40.0)

    # 1. Valid verified record -> COMPLETE_MEASURED
    rec_valid = EfficiencyVerificationRecord(
        verification_method="in_situ_distribution_uniformity_audit",
        measurement_date=date(2026, 5, 20),
        system_or_zone_id="zone-v1",
        measured_efficiency=0.91,
        supporting_audit_reference="AUDIT-2026-NASHIK-V1",
        verification_status="verified",
    )
    z_valid = FarmZoneContext(
        farm_id=farm_id,
        zone_id="zone-v1",
        zone_area_ha=2.5,
        application_efficiency=0.91,
        application_efficiency_provenance=EfficiencyProvenance.OPERATOR_ENTERED,
        is_efficiency_measurement_verified=True,
        efficiency_verification=rec_valid,
    )
    s_v = evaluate_farm_decisions(farm_id=farm_id, zone_contexts=[z_valid], water_balances={"zone-v1": wb})
    assert s_v.volume_calculation_status == VolumeCalculationStatus.COMPLETE_MEASURED
    assert s_v.prioritized_zone_decisions[0].is_efficiency_verified is True
    assert s_v.prioritized_zone_decisions[0].is_efficiency_provisional is False

    # 2. Rejected status -> COMPLETE_PROVISIONAL
    rec_rejected = EfficiencyVerificationRecord(
        verification_method="in_situ_distribution_uniformity_audit",
        measurement_date=date(2026, 5, 20),
        system_or_zone_id="zone-rej",
        measured_efficiency=0.91,
        supporting_audit_reference="AUDIT-FAILED-CALIBRATION",
        verification_status="rejected",
    )
    z_rej = FarmZoneContext(
        farm_id=farm_id,
        zone_id="zone-rej",
        zone_area_ha=2.5,
        application_efficiency=0.91,
        application_efficiency_provenance=EfficiencyProvenance.OPERATOR_ENTERED,
        is_efficiency_measurement_verified=True,
        efficiency_verification=rec_rejected,
    )
    s_rej = evaluate_farm_decisions(farm_id=farm_id, zone_contexts=[z_rej], water_balances={"zone-rej": wb})
    assert s_rej.volume_calculation_status == VolumeCalculationStatus.COMPLETE_PROVISIONAL
    assert s_rej.prioritized_zone_decisions[0].is_efficiency_verified is False
    assert s_rej.prioritized_zone_decisions[0].is_efficiency_provisional is True

    # 3. Mismatched zone ID -> COMPLETE_PROVISIONAL
    rec_mismatched_zone = EfficiencyVerificationRecord(
        verification_method="in_situ_distribution_uniformity_audit",
        measurement_date=date(2026, 5, 20),
        system_or_zone_id="DIFFERENT-ZONE-ID",
        measured_efficiency=0.91,
        supporting_audit_reference="AUDIT-OTHER-PLOT",
        verification_status="verified",
    )
    z_mismatched = FarmZoneContext(
        farm_id=farm_id,
        zone_id="zone-target",
        zone_area_ha=2.5,
        application_efficiency=0.91,
        application_efficiency_provenance=EfficiencyProvenance.OPERATOR_ENTERED,
        is_efficiency_measurement_verified=True,
        efficiency_verification=rec_mismatched_zone,
    )
    s_mismatched = evaluate_farm_decisions(farm_id=farm_id, zone_contexts=[z_mismatched], water_balances={"zone-target": wb})
    assert s_mismatched.volume_calculation_status == VolumeCalculationStatus.COMPLETE_PROVISIONAL
    assert s_mismatched.prioritized_zone_decisions[0].is_efficiency_verified is False

    # 4. Mismatched measured efficiency -> COMPLETE_PROVISIONAL
    rec_mismatched_eff = EfficiencyVerificationRecord(
        verification_method="in_situ_distribution_uniformity_audit",
        measurement_date=date(2026, 5, 20),
        system_or_zone_id="zone-eff-diff",
        measured_efficiency=0.75,  # Measured 0.75 vs entered 0.91
        supporting_audit_reference="AUDIT-DISCREPANCY",
        verification_status="verified",
    )
    z_mismatched_eff = FarmZoneContext(
        farm_id=farm_id,
        zone_id="zone-eff-diff",
        zone_area_ha=2.5,
        application_efficiency=0.91,
        application_efficiency_provenance=EfficiencyProvenance.OPERATOR_ENTERED,
        is_efficiency_measurement_verified=True,
        efficiency_verification=rec_mismatched_eff,
    )
    s_mismatch_eff = evaluate_farm_decisions(farm_id=farm_id, zone_contexts=[z_mismatched_eff], water_balances={"zone-eff-diff": wb})
    assert s_mismatch_eff.volume_calculation_status == VolumeCalculationStatus.COMPLETE_PROVISIONAL
    assert s_mismatch_eff.prioritized_zone_decisions[0].is_efficiency_verified is False


# ==============================================================================
# Phase 5.2.3: Final Forecast Deferral Policy & Split-Input Validation Tests
# ==============================================================================

def test_provisional_forecast_deferral_depletion_boundary_matrix():
    """Verify Phase 5.2.3 policy:
    1. Dr < RAW:
       - Default policy (allow_provisional_forecast_deferral=False): blocked (opt-in required).
       - Opt-in policy (allow_provisional_forecast_deferral=True): DELAY_AND_REASSESS.
    2. Dr == RAW:
       - Blocked even with opt-in; evaluates to IRRIGATE (active deficit).
    3. Dr > RAW:
       - Blocked even with opt-in; evaluates to IRRIGATE (active deficit).
    4. Dr > RAW with confirmed effective rainfall but missing ETc:
       - Confirmed safe deferral cannot be claimed; evaluates to IRRIGATE.
    5. Emergency depletion:
       - Overrides all forecast rain; evaluates to IRRIGATE (CRITICAL).
    """
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    zone = FarmZoneContext(farm_id="farm-f523", zone_id="z-bnd", irrigation_system_type="drip")

    fc_provisional = WeatherForecastContext(
        forecast_precipitation_mm=25.0,
        forecast_effective_rainfall_mm=None,  # Missing infiltration -> provisional policy
        forecast_etc_mm=4.0,  # Valid ETc: Dr=40 + 4 = 44 < RAW 50
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        issue_time=now_utc - timedelta(hours=1),
    )

    # 1A. Dr < RAW (Dr = 40.0, RAW = 50.0) without opt-in (default config)
    wb_below_raw = _make_test_wb(dr=40.0, raw=50.0, taw=100.0, ks=1.0)
    res_default_below = evaluate_zone_decision(
        farm_zone=zone, water_balance=wb_below_raw, forecast=fc_provisional, as_of_time=now_utc
    )
    assert res_default_below.action_type == DecisionAction.MONITOR
    assert DecisionReasonCode.FORECAST_PROVISIONAL_OPT_IN_REQUIRED in res_default_below.reason_codes
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN not in res_default_below.reason_codes

    # 1B. Dr < RAW (Dr = 40.0, RAW = 50.0) with explicit opt-in
    cfg_opt_in = DecisionConfig(allow_provisional_forecast_deferral=True)
    res_opt_in_below = evaluate_zone_decision(
        farm_zone=zone, water_balance=wb_below_raw, forecast=fc_provisional, config=cfg_opt_in, as_of_time=now_utc
    )
    assert res_opt_in_below.action_type == DecisionAction.DELAY_AND_REASSESS
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN in res_opt_in_below.reason_codes
    assert DecisionReasonCode.FORECAST_DEFERRAL_PROVISIONAL_POLICY in res_opt_in_below.reason_codes
    assert res_opt_in_below.forecast_reassessment_interval_hours == 12.0
    assert res_opt_in_below.forecast_reassessment_timestamp is not None

    # 2. Dr == RAW (Dr = 50.0, RAW = 50.0) with opt-in
    wb_equal_raw = _make_test_wb(dr=50.0, raw=50.0, taw=100.0, ks=1.0)
    res_equal = evaluate_zone_decision(
        farm_zone=zone, water_balance=wb_equal_raw, forecast=fc_provisional, config=cfg_opt_in, as_of_time=now_utc
    )
    assert res_equal.action_type == DecisionAction.IRRIGATE
    assert DecisionReasonCode.ACTION_IRRIGATE_DEPLETION_EXCEEDS_RAW in res_equal.reason_codes
    assert DecisionReasonCode.FORECAST_PROVISIONAL_BLOCKED_ACTIVE_DEFICIT in res_equal.reason_codes
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN not in res_equal.reason_codes

    # 3. Dr > RAW (Dr = 60.0, RAW = 50.0) with opt-in
    wb_above_raw = _make_test_wb(dr=60.0, raw=50.0, taw=100.0, ks=0.85)
    res_above = evaluate_zone_decision(
        farm_zone=zone, water_balance=wb_above_raw, forecast=fc_provisional, config=cfg_opt_in, as_of_time=now_utc
    )
    assert res_above.action_type == DecisionAction.IRRIGATE
    assert DecisionReasonCode.ACTION_IRRIGATE_DEPLETION_EXCEEDS_RAW in res_above.reason_codes
    assert DecisionReasonCode.FORECAST_PROVISIONAL_BLOCKED_ACTIVE_DEFICIT in res_above.reason_codes
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN not in res_above.reason_codes

    # 4. Dr > RAW with confirmed effective rainfall but missing ETc
    fc_eff_no_etc = WeatherForecastContext(
        forecast_precipitation_mm=25.0,
        forecast_total_precipitation_mm=25.0,
        forecast_effective_rainfall_mm=20.0,
        forecast_etc_mm=None,  # Missing ETc
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        issue_time=now_utc - timedelta(hours=1),
    )
    res_eff_no_etc = evaluate_zone_decision(
        farm_zone=zone, water_balance=wb_above_raw, forecast=fc_eff_no_etc, config=cfg_opt_in, as_of_time=now_utc
    )
    assert res_eff_no_etc.action_type == DecisionAction.IRRIGATE
    assert DecisionReasonCode.ACTION_IRRIGATE_DEPLETION_EXCEEDS_RAW in res_eff_no_etc.reason_codes
    assert DecisionReasonCode.FORECAST_ETC_MISSING in res_eff_no_etc.reason_codes
    assert DecisionReasonCode.FORECAST_PREVENTS_STRESS not in res_eff_no_etc.reason_codes

    # 5. Emergency wilting condition (Dr = 100 >= TAW, Ks = 0.15)
    wb_emergency = _make_test_wb(dr=100.0, raw=50.0, taw=100.0, ks=0.15)
    res_emergency = evaluate_zone_decision(
        farm_zone=zone, water_balance=wb_emergency, forecast=fc_provisional, config=cfg_opt_in, as_of_time=now_utc
    )
    assert res_emergency.action_type == DecisionAction.IRRIGATE
    assert res_emergency.priority == DecisionPriority.CRITICAL
    assert DecisionReasonCode.ACTION_IRRIGATE_EMERGENCY_OVERRIDE in res_emergency.reason_codes
    assert DecisionReasonCode.ACTION_IRRIGATE_WILTING_POINT_HAZARD in res_emergency.reason_codes


def test_provisional_forecast_fresh_versus_stale_evidence():
    """Verify fresh vs stale forecast evidence with provisional forecast deferral."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    zone = FarmZoneContext(farm_id="farm-f523", zone_id="z-fresh-stale", irrigation_system_type="drip")
    wb = _make_test_wb(dr=42.0, raw=50.0, taw=100.0, ks=1.0)  # Dr < RAW
    cfg = DecisionConfig(allow_provisional_forecast_deferral=True, max_forecast_age_hours=24.0)

    # 1. Fresh forecast (age 2h <= 24h limit)
    fc_fresh = WeatherForecastContext(
        forecast_precipitation_mm=20.0,
        forecast_etc_mm=4.0,  # Valid ETc: Dr=42 + 4 = 46 < RAW 50
        forecast_period_hours=24.0,
        forecast_probability=0.75,
        issue_time=now_utc - timedelta(hours=2),
    )
    res_fresh = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc_fresh, config=cfg, as_of_time=now_utc)
    assert res_fresh.action_type == DecisionAction.DELAY_AND_REASSESS
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN in res_fresh.reason_codes

    # 2. Stale forecast (age 30h > 24h limit)
    fc_stale = WeatherForecastContext(
        forecast_precipitation_mm=20.0,
        forecast_period_hours=24.0,
        forecast_probability=0.75,
        issue_time=now_utc - timedelta(hours=30),
    )
    res_stale = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc_stale, config=cfg, as_of_time=now_utc)
    assert res_stale.action_type == DecisionAction.MONITOR  # Dr=42 approaching RAW -> MONITOR
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN not in res_stale.reason_codes
    assert res_stale.validation_results["evidence"]["is_valid"] is True
    assert res_stale.forecast_dependency["is_actionable"] is False


def test_split_application_input_boundary_validation():
    """Verify calculate_split_application_depths input validation boundaries:
    1. Exactly zero gross depth returns empty schedule ([], 0.0, 0).
    2. Negative gross depth raises ValueError.
    3. Non-negative integer precision validation (negative, float, bool raise ValueError).
    4. Precision 0 produces exact integer event scheduling.
    """
    # 1. Exactly zero gross depth
    depths_zero, tot_zero, cnt_zero = calculate_split_application_depths(
        gross_depth_mm=0.0,
        max_event_depth_mm=50.0,
        precision=2,
    )
    assert cnt_zero == 0
    assert depths_zero == []
    assert tot_zero == 0.0

    # 2. Negative gross depth raises ValueError
    with pytest.raises(ValueError, match="gross_depth_mm cannot be negative"):
        calculate_split_application_depths(
            gross_depth_mm=-15.0,
            max_event_depth_mm=50.0,
            precision=2,
        )

    # 3. Precision validation
    with pytest.raises(ValueError, match="precision must be a non-negative integer"):
        calculate_split_application_depths(50.0, 25.0, precision=-1)

    with pytest.raises(ValueError, match="precision must be a non-negative integer"):
        calculate_split_application_depths(50.0, 25.0, precision=1.5)  # float

    with pytest.raises(ValueError, match="precision must be a non-negative integer"):
        calculate_split_application_depths(50.0, 25.0, precision=True)  # bool

    # 4. Precision 0 (integer mm)
    depths_p0, tot_p0, cnt_p0 = calculate_split_application_depths(
        gross_depth_mm=75.0,
        max_event_depth_mm=30.0,
        precision=0,
    )
    assert cnt_p0 == 3  # (75 + 30 - 1) // 30 = 3
    assert depths_p0 == [25.0, 25.0, 25.0]
    assert tot_p0 == 75.0
    assert sum(depths_p0) == 75.0
    for d in depths_p0:
        assert d <= 30.0


# ==============================================================================
# 11. PHASE 5.2.4: PROVISIONAL FORECAST STRESS-ONSET GUARD & TIMING INTEGRITY
# ==============================================================================

def test_phase524_dr_below_raw_rain_before_stress_defers():
    """Phase 5.2.4: Dr < RAW with rain arriving before stress onset (t_rain < t_stress) defers."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=45.0, raw=50.0, taw=100.0, ks=1.0)  # 5.0 mm remaining to RAW
    zone = FarmZoneContext(farm_id="farm-f524", zone_id="z-safe-delay", irrigation_system_type="drip")

    # Rate: 24.0 mm / 24.0 h = 1.0 mm/h. Time to stress: (50 - 45) / 1.0 = 5.0 h.
    # Rain onset: 2.0 h (< 5.0 h). Dr at onset = 45.0 + 1.0 * 2.0 = 47.0 mm < RAW.
    fc = WeatherForecastContext(
        forecast_precipitation_mm=20.0,
        forecast_effective_rainfall_mm=None,  # Provisional raw NWP rain
        forecast_etc_mm=24.0,
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        expected_rainfall_start=now_utc + timedelta(hours=2),
        issue_time=now_utc - timedelta(hours=1),
    )
    cfg = DecisionConfig(
        forecast_reassessment_interval_hours=12.0,
        allow_provisional_forecast_deferral=True,
    )
    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc, config=cfg, as_of_time=now_utc)

    assert res.action_type == DecisionAction.DELAY_AND_REASSESS
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN in res.reason_codes
    assert DecisionReasonCode.FORECAST_DEFERRAL_PROVISIONAL_POLICY in res.reason_codes
    assert DecisionReasonCode.FORECAST_RAINFALL_AFTER_STRESS not in res.reason_codes
    assert res.forecast_reassessment_interval_hours == 12.0
    assert res.forecast_reassessment_timestamp == now_utc + timedelta(hours=12)
    assert res.forecast_dependency is not None
    assert res.forecast_dependency["is_provisional_deferral"] is True
    assert res.forecast_dependency["rainfall_onset_hours"] == 2.0
    assert res.forecast_dependency["stress_onset_hours"] == 5.0
    assert res.forecast_dependency["dr_at_rainfall_onset_mm"] == 47.0
    assert res.forecast_dependency["rainfall_after_stress"] is False


def test_phase524_dr_below_raw_rain_after_stress_blocks_deferral():
    """Phase 5.2.4: Dr < RAW with rain arriving after stress onset (t_rain > t_stress) blocks deferral."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=45.0, raw=50.0, taw=100.0, ks=1.0)  # 5.0 mm remaining to RAW
    zone = FarmZoneContext(farm_id="farm-f524", zone_id="z-stress-first", irrigation_system_type="drip")

    # Rate: 1.0 mm/h. Time to stress: 5.0 h.
    # Rain onset: 8.0 h (> 5.0 h). Dr at onset = 45.0 + 1.0 * 8.0 = 53.0 mm >= RAW (50.0 mm).
    fc = WeatherForecastContext(
        forecast_precipitation_mm=25.0,
        forecast_effective_rainfall_mm=None,  # Provisional raw NWP rain
        forecast_etc_mm=24.0,
        forecast_period_hours=24.0,
        forecast_probability=0.85,
        expected_rainfall_start=now_utc + timedelta(hours=8),
        issue_time=now_utc - timedelta(hours=1),
    )
    cfg = DecisionConfig(
        forecast_reassessment_interval_hours=12.0,
        allow_provisional_forecast_deferral=True,
    )
    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc, config=cfg, as_of_time=now_utc)

    # Deferral blocked: crop would experience moisture stress before rain arrives
    # Fallback to ordinary decision: Dr=45 >= 0.80*RAW (40 mm) -> MONITOR
    assert res.action_type == DecisionAction.MONITOR
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN not in res.reason_codes
    assert DecisionReasonCode.FORECAST_RAINFALL_AFTER_STRESS in res.reason_codes
    assert res.forecast_reassessment_timestamp is None
    assert res.forecast_reassessment_interval_hours is None
    assert res.forecast_dependency["rainfall_after_stress"] is True
    assert res.forecast_dependency["is_actionable"] is False
    assert res.forecast_dependency["is_provisional_deferral"] is False
    assert res.forecast_dependency["rainfall_onset_hours"] == 8.0
    assert res.forecast_dependency["stress_onset_hours"] == 5.0
    assert res.forecast_dependency["dr_at_rainfall_onset_mm"] == 53.0


def test_phase524_dr_above_raw_rain_after_stress_evaluates_to_irrigate():
    """Phase 5.2.4: Active depletion Dr >= RAW with rain arriving after stress evaluates to IRRIGATE."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=55.0, raw=50.0, taw=100.0, ks=0.90)  # Active stress Dr >= RAW
    zone = FarmZoneContext(farm_id="farm-f524", zone_id="z-active-stress", irrigation_system_type="drip")

    fc = WeatherForecastContext(
        forecast_precipitation_mm=30.0,
        forecast_effective_rainfall_mm=None,
        forecast_etc_mm=24.0,
        forecast_period_hours=24.0,
        forecast_probability=0.90,
        expected_rainfall_start=now_utc + timedelta(hours=4),
        issue_time=now_utc - timedelta(hours=1),
    )
    cfg = DecisionConfig(allow_provisional_forecast_deferral=True)
    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc, config=cfg, as_of_time=now_utc)

    assert res.action_type == DecisionAction.IRRIGATE
    assert DecisionReasonCode.ACTION_IRRIGATE_DEPLETION_EXCEEDS_RAW in res.reason_codes
    assert DecisionReasonCode.FORECAST_RAINFALL_AFTER_STRESS in res.reason_codes
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN not in res.reason_codes
    assert res.forecast_reassessment_timestamp is None


def test_phase524_missing_forecast_etc_blocks_provisional_deferral():
    """Phase 5.2.4: Missing forecast ETc blocks provisional deferral with FORECAST_ETC_MISSING."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=45.0, raw=50.0, taw=100.0, ks=1.0)
    zone = FarmZoneContext(farm_id="farm-f524", zone_id="z-missing-etc", irrigation_system_type="drip")

    fc = WeatherForecastContext(
        forecast_precipitation_mm=25.0,
        forecast_effective_rainfall_mm=None,
        forecast_etc_mm=None,  # Missing ETc
        forecast_period_hours=24.0,
        forecast_probability=0.85,
        expected_rainfall_start=now_utc + timedelta(hours=3),
        issue_time=now_utc - timedelta(hours=1),
    )
    cfg = DecisionConfig(allow_provisional_forecast_deferral=True)
    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc, config=cfg, as_of_time=now_utc)

    # Missing ETc: cannot substitute 0.0, cannot claim safe delay -> ordinary decision (MONITOR)
    assert res.action_type == DecisionAction.MONITOR
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN not in res.reason_codes
    assert DecisionReasonCode.FORECAST_ETC_MISSING in res.reason_codes
    assert res.forecast_reassessment_timestamp is None
    assert res.forecast_dependency["forecast_etc_mm"] is None
    assert res.forecast_dependency["stress_onset_hours"] is None
    assert res.forecast_dependency["is_actionable"] is False


def test_phase524_forecast_etc_period_shorter_than_rainfall_horizon():
    """Phase 5.2.4: ETc aggregation window shorter than rainfall horizon computes true rate."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=45.0, raw=50.0, taw=100.0, ks=1.0)  # 5.0 mm to RAW
    zone = FarmZoneContext(farm_id="farm-f524", zone_id="z-short-etc", irrigation_system_type="drip")

    # Rainfall horizon: 24h. ETc window: 12h, ETc: 12.0 mm -> True rate = 12.0 / 12.0 = 1.0 mm/h.
    # Time to stress: 5.0 / 1.0 = 5.0 h.
    # Rain onset: 7.0 h (> 5.0 h) -> stress precedes rain -> BLOCKED!
    # (If bug divided by 24h horizon, rate would be 0.5 mm/h -> time to stress 10h -> false delay)
    fc = WeatherForecastContext(
        forecast_precipitation_mm=25.0,
        forecast_effective_rainfall_mm=None,
        forecast_etc_mm=12.0,
        forecast_etc_period_hours=12.0,  # Explicit 12h window < 24h horizon
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        expected_rainfall_start=now_utc + timedelta(hours=7),
        issue_time=now_utc - timedelta(hours=1),
    )
    cfg = DecisionConfig(allow_provisional_forecast_deferral=True)
    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc, config=cfg, as_of_time=now_utc)

    assert res.action_type == DecisionAction.MONITOR
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN not in res.reason_codes
    assert DecisionReasonCode.FORECAST_RAINFALL_AFTER_STRESS in res.reason_codes
    assert res.forecast_dependency["forecast_etc_period_hours"] == 12.0
    assert res.forecast_dependency["forecast_etc_rate_mm_per_hour"] == 1.0
    assert res.forecast_dependency["stress_onset_hours"] == 5.0
    assert res.forecast_dependency["rainfall_onset_hours"] == 7.0


def test_phase524_forecast_etc_period_longer_than_rainfall_horizon():
    """Phase 5.2.4: ETc aggregation window longer than rainfall horizon computes true rate."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=45.0, raw=50.0, taw=100.0, ks=1.0)  # 5.0 mm to RAW
    zone = FarmZoneContext(farm_id="farm-f524", zone_id="z-long-etc", irrigation_system_type="drip")

    # Rainfall horizon: 24h. ETc window: 48h, ETc: 48.0 mm -> True rate = 48.0 / 48.0 = 1.0 mm/h.
    # Time to stress: 5.0 / 1.0 = 5.0 h.
    # Rain onset: 3.0 h (< 5.0 h) -> rain arrives before stress -> safe DELAY_AND_REASSESS!
    fc = WeatherForecastContext(
        forecast_precipitation_mm=20.0,
        forecast_effective_rainfall_mm=None,
        forecast_etc_mm=48.0,
        forecast_etc_period_hours=48.0,  # Explicit 48h window > 24h horizon
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        expected_rainfall_start=now_utc + timedelta(hours=3),
        issue_time=now_utc - timedelta(hours=1),
    )
    cfg = DecisionConfig(allow_provisional_forecast_deferral=True)
    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc, config=cfg, as_of_time=now_utc)

    assert res.action_type == DecisionAction.DELAY_AND_REASSESS
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN in res.reason_codes
    assert DecisionReasonCode.FORECAST_DEFERRAL_PROVISIONAL_POLICY in res.reason_codes
    assert res.forecast_dependency["forecast_etc_period_hours"] == 48.0
    assert res.forecast_dependency["forecast_etc_rate_mm_per_hour"] == 1.0
    assert res.forecast_dependency["stress_onset_hours"] == 5.0
    assert res.forecast_dependency["rainfall_onset_hours"] == 3.0


def test_phase524_rainfall_arrival_exactly_at_stress_crossing_blocked():
    """Phase 5.2.4: Rain arrival exactly at estimated RAW crossing (t_rain == t_stress) is blocked."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=45.0, raw=50.0, taw=100.0, ks=1.0)
    zone = FarmZoneContext(farm_id="farm-f524", zone_id="z-exact-crossing", irrigation_system_type="drip")

    # Rate: 1.0 mm/h. Time to stress: (50.0 - 45.0) / 1.0 = 5.0 h.
    # Rain onset: exactly 5.0 h.
    # Invariant: t_rain == t_stress must be blocked!
    fc = WeatherForecastContext(
        forecast_precipitation_mm=22.0,
        forecast_effective_rainfall_mm=None,
        forecast_etc_mm=24.0,
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        expected_rainfall_start=now_utc + timedelta(hours=5),
        issue_time=now_utc - timedelta(hours=1),
    )
    cfg = DecisionConfig(allow_provisional_forecast_deferral=True)
    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc, config=cfg, as_of_time=now_utc)

    assert res.action_type == DecisionAction.MONITOR
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN not in res.reason_codes
    assert DecisionReasonCode.FORECAST_RAINFALL_AFTER_STRESS in res.reason_codes
    assert res.forecast_reassessment_timestamp is None


def test_phase524_provisional_opt_in_disabled_blocks_deferral():
    """Phase 5.2.4: Provisional opt-in disabled (default) blocks deferral even when arrival is safe."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=45.0, raw=50.0, taw=100.0, ks=1.0)
    zone = FarmZoneContext(farm_id="farm-f524", zone_id="z-no-opt-in", irrigation_system_type="drip")

    fc = WeatherForecastContext(
        forecast_precipitation_mm=22.0,
        forecast_effective_rainfall_mm=None,
        forecast_etc_mm=24.0,
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        expected_rainfall_start=now_utc + timedelta(hours=2),  # Safe arrival in 2h
        issue_time=now_utc - timedelta(hours=1),
    )
    # Default: allow_provisional_forecast_deferral=False
    cfg = DecisionConfig(allow_provisional_forecast_deferral=False)
    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc, config=cfg, as_of_time=now_utc)

    assert res.action_type == DecisionAction.MONITOR
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN not in res.reason_codes
    assert DecisionReasonCode.FORECAST_PROVISIONAL_OPT_IN_REQUIRED in res.reason_codes
    assert res.forecast_reassessment_timestamp is None


def test_phase524_provisional_opt_in_enabled_permits_safe_deferral():
    """Phase 5.2.4: Provisional opt-in enabled permits deferral when arrival precedes stress."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=45.0, raw=50.0, taw=100.0, ks=1.0)
    zone = FarmZoneContext(farm_id="farm-f524", zone_id="z-opt-in-safe", irrigation_system_type="drip")

    fc = WeatherForecastContext(
        forecast_precipitation_mm=22.0,
        forecast_effective_rainfall_mm=None,
        forecast_etc_mm=24.0,
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        expected_rainfall_start=now_utc + timedelta(hours=2),  # Safe arrival in 2h < 5h stress
        issue_time=now_utc - timedelta(hours=1),
    )
    cfg = DecisionConfig(allow_provisional_forecast_deferral=True)
    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc, config=cfg, as_of_time=now_utc)

    assert res.action_type == DecisionAction.DELAY_AND_REASSESS
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN in res.reason_codes
    assert DecisionReasonCode.FORECAST_DEFERRAL_PROVISIONAL_POLICY in res.reason_codes
    assert res.forecast_reassessment_timestamp is not None
    assert res.forecast_reassessment_interval_hours == 12.0


def test_phase524_emergency_depletion_overrides_all_forecasts():
    """Phase 5.2.4: Severe permanent wilting hazard overrides all forecast deferrals."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    # Emergency wilting: Dr = 100.0 >= TAW = 100.0, Ks = 0.15 <= 0.20
    wb = _make_test_wb(dr=100.0, raw=50.0, taw=100.0, ks=0.15)
    zone = FarmZoneContext(farm_id="farm-f524", zone_id="z-emerg-override", irrigation_system_type="drip")

    # Heavy rain in 1 hour with opt-in enabled
    fc = WeatherForecastContext(
        forecast_precipitation_mm=50.0,
        forecast_effective_rainfall_mm=None,
        forecast_etc_mm=24.0,
        forecast_period_hours=24.0,
        forecast_probability=0.95,
        expected_rainfall_start=now_utc + timedelta(hours=1),
        issue_time=now_utc - timedelta(hours=1),
    )
    cfg = DecisionConfig(allow_provisional_forecast_deferral=True)
    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc, config=cfg, as_of_time=now_utc)

    # Precedence 2 emergency override must fire
    assert res.action_type == DecisionAction.IRRIGATE
    assert res.priority == DecisionPriority.CRITICAL
    assert DecisionReasonCode.ACTION_IRRIGATE_EMERGENCY_OVERRIDE in res.reason_codes
    assert DecisionReasonCode.ACTION_IRRIGATE_WILTING_POINT_HAZARD in res.reason_codes
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN not in res.reason_codes
    assert res.forecast_reassessment_timestamp is None


def test_phase524_reassessment_timestamp_only_on_permitted_deferrals():
    """Phase 5.2.4: 12-hour reassessment timestamp and interval preserved ONLY on permitted deferrals."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=45.0, raw=50.0, taw=100.0, ks=1.0)
    zone = FarmZoneContext(farm_id="farm-f524", zone_id="z-reassess-guard", irrigation_system_type="drip")
    cfg = DecisionConfig(
        allow_provisional_forecast_deferral=True,
        forecast_reassessment_interval_hours=12.0,
    )

    # Permitted case: rain in 2h < 5h stress
    fc_permitted = WeatherForecastContext(
        forecast_precipitation_mm=20.0,
        forecast_effective_rainfall_mm=None,
        forecast_etc_mm=24.0,
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        expected_rainfall_start=now_utc + timedelta(hours=2),
        issue_time=now_utc - timedelta(hours=1),
    )
    res_perm = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc_permitted, config=cfg, as_of_time=now_utc)
    assert res_perm.action_type == DecisionAction.DELAY_AND_REASSESS
    assert res_perm.forecast_reassessment_interval_hours == 12.0
    assert res_perm.forecast_reassessment_timestamp == now_utc + timedelta(hours=12)

    # Blocked case: rain in 8h > 5h stress
    fc_blocked = WeatherForecastContext(
        forecast_precipitation_mm=20.0,
        forecast_effective_rainfall_mm=None,
        forecast_etc_mm=24.0,
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        expected_rainfall_start=now_utc + timedelta(hours=8),
        issue_time=now_utc - timedelta(hours=1),
    )
    res_block = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc_blocked, config=cfg, as_of_time=now_utc)
    assert res_block.action_type != DecisionAction.DELAY_AND_REASSESS
    assert res_block.forecast_reassessment_interval_hours is None
    assert res_block.forecast_reassessment_timestamp is None


# ==============================================================================
# 12. PHASE 5.2.5: FORECAST ETC VALIDITY-WINDOW INTEGRITY & TEMPORAL TESTS
# ==============================================================================

def test_phase525_etc_interval_ending_before_rainfall_arrival():
    """Phase 5.2.5: ETc interval ending before rainfall arrival blocks deferral with FORECAST_ETC_WINDOW_INSUFFICIENT."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    # Dr = 42.0 approaching RAW (50.0 mm), Ks = 1.0
    wb = _make_test_wb(dr=42.0, raw=50.0, taw=100.0, ks=1.0)
    zone = FarmZoneContext(farm_id="farm-f525", zone_id="z-short-window", irrigation_system_type="drip")

    # Rain arrives in 6h. ETc validity window covers only 4h (ends before rainfall arrival).
    fc = WeatherForecastContext(
        forecast_precipitation_mm=25.0,
        forecast_effective_rainfall_mm=None,  # Provisional raw NWP rain
        forecast_etc_mm=4.0,
        forecast_etc_period_hours=4.0,
        forecast_etc_valid_from=now_utc,
        forecast_etc_valid_to=now_utc + timedelta(hours=4),
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        expected_rainfall_start=now_utc + timedelta(hours=6),
        issue_time=now_utc - timedelta(hours=1),
    )
    cfg = DecisionConfig(allow_provisional_forecast_deferral=True)
    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc, config=cfg, as_of_time=now_utc)

    # Incomplete temporal coverage: extrapolation prohibited, deferral blocked, evaluates to MONITOR
    assert res.action_type == DecisionAction.MONITOR
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN not in res.reason_codes
    assert DecisionReasonCode.FORECAST_ETC_WINDOW_INSUFFICIENT in res.reason_codes
    assert res.forecast_reassessment_timestamp is None
    assert res.forecast_dependency["is_etc_window_valid"] is False
    assert res.forecast_dependency["stress_onset_hours"] is None
    assert res.forecast_dependency["dr_at_rainfall_onset_mm"] is None
    assert res.forecast_dependency["is_stress_onset_estimated"] is False
    assert res.forecast_dependency["is_actionable"] is False


def test_phase525_etc_interval_ending_exactly_at_rainfall_arrival():
    """Phase 5.2.5: ETc interval ending exactly at rainfall arrival (t_to == t_rain) provides complete coverage."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=45.0, raw=50.0, taw=100.0, ks=1.0)  # 5.0 mm to RAW
    zone = FarmZoneContext(farm_id="farm-f525", zone_id="z-exact-window", irrigation_system_type="drip")

    # Rain arrives in 4h. ETc validity window covers exactly 4h (valid_to == expected_rainfall_start).
    # ETc: 2.0 mm over 4h -> rate 0.5 mm/h. Time to stress: 5.0 / 0.5 = 10.0 h > 4.0 h.
    fc = WeatherForecastContext(
        forecast_precipitation_mm=22.0,
        forecast_effective_rainfall_mm=None,
        forecast_etc_mm=2.0,
        forecast_etc_period_hours=4.0,
        forecast_etc_valid_from=now_utc,
        forecast_etc_valid_to=now_utc + timedelta(hours=4),
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        expected_rainfall_start=now_utc + timedelta(hours=4),
        issue_time=now_utc - timedelta(hours=1),
    )
    cfg = DecisionConfig(allow_provisional_forecast_deferral=True)
    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc, config=cfg, as_of_time=now_utc)

    # Valid window coverage: rain arrives before stress onset -> safe DELAY_AND_REASSESS
    assert res.action_type == DecisionAction.DELAY_AND_REASSESS
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN in res.reason_codes
    assert DecisionReasonCode.FORECAST_ETC_WINDOW_INSUFFICIENT not in res.reason_codes
    assert res.forecast_dependency["is_etc_window_valid"] is True
    assert res.forecast_dependency["is_stress_onset_estimated"] is True
    assert res.forecast_dependency["stress_onset_hours"] == 10.0
    assert res.forecast_dependency["rainfall_onset_hours"] == 4.0
    assert res.forecast_reassessment_timestamp is not None


def test_phase525_etc_interval_covering_rainfall_arrival():
    """Phase 5.2.5: ETc interval strictly covering rainfall arrival (t_to > t_rain) permits safe deferral."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=45.0, raw=50.0, taw=100.0, ks=1.0)
    zone = FarmZoneContext(farm_id="farm-f525", zone_id="z-covering-window", irrigation_system_type="drip")

    # Rain arrives in 3h. ETc window covers 8h (valid_to > expected_rainfall_start).
    # ETc: 4.0 mm over 8h -> rate 0.5 mm/h. Time to stress: 10.0 h > 3.0 h.
    fc = WeatherForecastContext(
        forecast_precipitation_mm=20.0,
        forecast_effective_rainfall_mm=None,
        forecast_etc_mm=4.0,
        forecast_etc_period_hours=8.0,
        forecast_etc_valid_from=now_utc,
        forecast_etc_valid_to=now_utc + timedelta(hours=8),
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        expected_rainfall_start=now_utc + timedelta(hours=3),
        issue_time=now_utc - timedelta(hours=1),
    )
    cfg = DecisionConfig(allow_provisional_forecast_deferral=True)
    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc, config=cfg, as_of_time=now_utc)

    assert res.action_type == DecisionAction.DELAY_AND_REASSESS
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN in res.reason_codes
    assert res.forecast_dependency["is_etc_window_valid"] is True
    assert res.forecast_dependency["is_stress_onset_estimated"] is True
    assert res.forecast_dependency["rainfall_onset_hours"] == 3.0
    assert res.forecast_dependency["stress_onset_hours"] == 10.0
    assert res.forecast_reassessment_timestamp is not None


def test_phase525_etc_interval_starting_after_decision_time():
    """Phase 5.2.5: ETc interval starting after decision time (valid_from > decision) is rejected."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=42.0, raw=50.0, taw=100.0, ks=1.0)
    zone = FarmZoneContext(farm_id="farm-f525", zone_id="z-late-start", irrigation_system_type="drip")

    # Decision at 12:00, but ETc validity starts at 14:00 (2h gap)
    fc = WeatherForecastContext(
        forecast_precipitation_mm=25.0,
        forecast_effective_rainfall_mm=None,
        forecast_etc_mm=6.0,
        forecast_etc_period_hours=6.0,
        forecast_etc_valid_from=now_utc + timedelta(hours=2),
        forecast_etc_valid_to=now_utc + timedelta(hours=8),
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        expected_rainfall_start=now_utc + timedelta(hours=4),
        issue_time=now_utc - timedelta(hours=1),
    )
    cfg = DecisionConfig(allow_provisional_forecast_deferral=True)
    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc, config=cfg, as_of_time=now_utc)

    # Incomplete lookahead coverage from decision time -> rejected
    assert res.action_type == DecisionAction.MONITOR
    assert DecisionReasonCode.FORECAST_ETC_WINDOW_INSUFFICIENT in res.reason_codes
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN not in res.reason_codes
    assert res.forecast_dependency["is_etc_window_valid"] is False
    assert res.forecast_dependency["stress_onset_hours"] is None


def test_phase525_etc_window_invalid_duration_mismatch():
    """Phase 5.2.5: Duration mismatch between timestamps and stated period is rejected."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=42.0, raw=50.0, taw=100.0, ks=1.0)
    zone = FarmZoneContext(farm_id="farm-f525", zone_id="z-dur-mismatch", irrigation_system_type="drip")

    # Timestamps span 12 hours, but stated period is 24.0 hours
    fc = WeatherForecastContext(
        forecast_precipitation_mm=25.0,
        forecast_effective_rainfall_mm=None,
        forecast_etc_mm=12.0,
        forecast_etc_period_hours=24.0,  # Mismatch: stated 24h != actual 12h
        forecast_etc_valid_from=now_utc,
        forecast_etc_valid_to=now_utc + timedelta(hours=12),
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        expected_rainfall_start=now_utc + timedelta(hours=4),
        issue_time=now_utc - timedelta(hours=1),
    )
    cfg = DecisionConfig(allow_provisional_forecast_deferral=True)
    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc, config=cfg, as_of_time=now_utc)

    assert res.action_type == DecisionAction.MONITOR
    assert DecisionReasonCode.FORECAST_ETC_WINDOW_INSUFFICIENT in res.reason_codes
    assert res.forecast_dependency["is_etc_window_valid"] is False
    assert res.forecast_dependency["stress_onset_hours"] is None


def test_phase525_naive_timestamps_blocked():
    """Phase 5.2.5: Offset-naive timestamps are cleanly rejected without uncaught exceptions."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=42.0, raw=50.0, taw=100.0, ks=1.0)
    zone = FarmZoneContext(farm_id="farm-f525", zone_id="z-naive-ts", irrigation_system_type="drip")

    # Naive valid_from / valid_to (tzinfo=None)
    fc_naive_window = WeatherForecastContext(
        forecast_precipitation_mm=25.0,
        forecast_effective_rainfall_mm=None,
        forecast_etc_mm=4.0,
        forecast_etc_period_hours=4.0,
        forecast_etc_valid_from=datetime(2026, 7, 15, 12, 0),  # Naive
        forecast_etc_valid_to=datetime(2026, 7, 15, 16, 0),    # Naive
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        expected_rainfall_start=now_utc + timedelta(hours=3),
        issue_time=now_utc - timedelta(hours=1),
    )
    cfg = DecisionConfig(allow_provisional_forecast_deferral=True)
    res_w = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc_naive_window, config=cfg, as_of_time=now_utc)

    assert res_w.action_type == DecisionAction.MONITOR
    assert DecisionReasonCode.FORECAST_ETC_WINDOW_INSUFFICIENT in res_w.reason_codes
    assert res_w.forecast_dependency["is_etc_window_valid"] is False

    # Naive rainfall onset
    fc_naive_rain = WeatherForecastContext(
        forecast_precipitation_mm=25.0,
        forecast_effective_rainfall_mm=None,
        forecast_etc_mm=4.0,
        forecast_etc_period_hours=8.0,
        forecast_etc_valid_from=now_utc,
        forecast_etc_valid_to=now_utc + timedelta(hours=8),
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        expected_rainfall_start=datetime(2026, 7, 15, 15, 0),  # Naive
        issue_time=now_utc - timedelta(hours=1),
    )
    res_r = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc_naive_rain, config=cfg, as_of_time=now_utc)
    assert res_r.action_type == DecisionAction.MONITOR
    assert DecisionReasonCode.FORECAST_ETC_WINDOW_INSUFFICIENT in res_r.reason_codes


def test_phase525_mixed_timezone_timestamps_normalized():
    """Phase 5.2.5: Mixed timezone timestamps normalize accurately to UTC and validate successfully."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=45.0, raw=50.0, taw=100.0, ks=1.0)  # 5.0 mm to RAW
    zone = FarmZoneContext(farm_id="farm-f525", zone_id="z-mixed-tz", irrigation_system_type="drip")

    tz_ist = timezone(timedelta(hours=5, minutes=30))  # IST (+05:30)
    tz_edt = timezone(timedelta(hours=-4))             # EDT (-04:00)
    tz_eet = timezone(timedelta(hours=2))              # EET (+02:00)

    # 17:30 IST == 12:00 UTC (matches decision time)
    valid_from_ist = datetime(2026, 7, 15, 17, 30, tzinfo=tz_ist)
    # 16:00 EDT == 20:00 UTC (span is exactly 8.0 hours from 12:00 UTC)
    valid_to_edt = datetime(2026, 7, 15, 16, 0, tzinfo=tz_edt)
    # 16:00 EET == 14:00 UTC (rainfall onset in 2.0h from 12:00 UTC)
    rain_start_eet = datetime(2026, 7, 15, 16, 0, tzinfo=tz_eet)

    # Rate: 4.0 mm / 8.0h = 0.5 mm/h. Time to stress: 5.0 / 0.5 = 10.0h.
    # Rain onset: 2.0h (< 10.0h).
    fc = WeatherForecastContext(
        forecast_precipitation_mm=22.0,
        forecast_effective_rainfall_mm=None,
        forecast_etc_mm=4.0,
        forecast_etc_period_hours=8.0,
        forecast_etc_valid_from=valid_from_ist,
        forecast_etc_valid_to=valid_to_edt,
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        expected_rainfall_start=rain_start_eet,
        issue_time=now_utc - timedelta(hours=1),
    )
    cfg = DecisionConfig(allow_provisional_forecast_deferral=True)
    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc, config=cfg, as_of_time=now_utc)

    assert res.action_type == DecisionAction.DELAY_AND_REASSESS
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN in res.reason_codes
    assert res.forecast_dependency["is_etc_window_valid"] is True
    assert res.forecast_dependency["is_stress_onset_estimated"] is True
    assert res.forecast_dependency["rainfall_onset_hours"] == 2.0
    assert res.forecast_dependency["stress_onset_hours"] == 10.0
    assert res.forecast_reassessment_timestamp is not None


def test_phase525_out_of_order_timestamps():
    """Phase 5.2.5: Inverted (valid_to < valid_from) or zero-length intervals are rejected."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=42.0, raw=50.0, taw=100.0, ks=1.0)
    zone = FarmZoneContext(farm_id="farm-f525", zone_id="z-inverted", irrigation_system_type="drip")
    cfg = DecisionConfig(allow_provisional_forecast_deferral=True)

    # 1. Inverted interval
    fc_inverted = WeatherForecastContext(
        forecast_precipitation_mm=25.0,
        forecast_effective_rainfall_mm=None,
        forecast_etc_mm=4.0,
        forecast_etc_period_hours=4.0,
        forecast_etc_valid_from=now_utc + timedelta(hours=4),
        forecast_etc_valid_to=now_utc,
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        expected_rainfall_start=now_utc + timedelta(hours=2),
        issue_time=now_utc - timedelta(hours=1),
    )
    res_inv = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc_inverted, config=cfg, as_of_time=now_utc)
    assert res_inv.action_type == DecisionAction.MONITOR
    assert DecisionReasonCode.FORECAST_ETC_WINDOW_INSUFFICIENT in res_inv.reason_codes
    assert res_inv.forecast_dependency["is_etc_window_valid"] is False

    # 2. Zero-length interval
    fc_zero = WeatherForecastContext(
        forecast_precipitation_mm=25.0,
        forecast_effective_rainfall_mm=None,
        forecast_etc_mm=4.0,
        forecast_etc_period_hours=4.0,
        forecast_etc_valid_from=now_utc,
        forecast_etc_valid_to=now_utc,
        forecast_period_hours=24.0,
        forecast_probability=0.80,
        expected_rainfall_start=now_utc + timedelta(hours=2),
        issue_time=now_utc - timedelta(hours=1),
    )
    res_z = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc_zero, config=cfg, as_of_time=now_utc)
    assert res_z.action_type == DecisionAction.MONITOR
    assert DecisionReasonCode.FORECAST_ETC_WINDOW_INSUFFICIENT in res_z.reason_codes
    assert res_z.forecast_dependency["is_etc_window_valid"] is False


def test_phase525_incomplete_coverage_blocks_provisional_deferral():
    """Phase 5.2.5: Incomplete window coverage strictly blocks provisional deferral even with opt-in."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=45.0, raw=50.0, taw=100.0, ks=1.0)
    zone = FarmZoneContext(farm_id="farm-f525", zone_id="z-incomplete-prov", irrigation_system_type="drip")

    # Rain arrives in 6h. Window only covers 3h.
    fc = WeatherForecastContext(
        forecast_precipitation_mm=25.0,
        forecast_effective_rainfall_mm=None,
        forecast_etc_mm=3.0,
        forecast_etc_period_hours=3.0,
        forecast_etc_valid_from=now_utc,
        forecast_etc_valid_to=now_utc + timedelta(hours=3),
        forecast_period_hours=24.0,
        forecast_probability=0.85,
        expected_rainfall_start=now_utc + timedelta(hours=6),
        issue_time=now_utc - timedelta(hours=1),
    )
    # Opt-in explicitly enabled
    cfg = DecisionConfig(allow_provisional_forecast_deferral=True)
    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc, config=cfg, as_of_time=now_utc)

    # Deferral must be blocked
    assert res.action_type == DecisionAction.MONITOR
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN not in res.reason_codes
    assert DecisionReasonCode.FORECAST_ETC_WINDOW_INSUFFICIENT in res.reason_codes
    assert res.forecast_reassessment_timestamp is None
    assert res.forecast_dependency["stress_onset_hours"] is None
    assert res.forecast_dependency["dr_at_rainfall_onset_mm"] is None
    assert res.forecast_dependency["is_provisional_deferral"] is False


def test_phase525_emergency_action_unaffected_by_missing_timing():
    """Phase 5.2.5: Emergency wilting action is unaffected by invalid or missing ETc timing evidence."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    # Emergency wilting: Dr = 100.0 >= TAW = 100.0, Ks = 0.15 <= 0.20
    wb = _make_test_wb(dr=100.0, raw=50.0, taw=100.0, ks=0.15)
    zone = FarmZoneContext(farm_id="farm-f525", zone_id="z-emerg-window", irrigation_system_type="drip")

    # Forecast has invalid / truncated ETc window (ending before rain)
    fc = WeatherForecastContext(
        forecast_precipitation_mm=40.0,
        forecast_effective_rainfall_mm=None,
        forecast_etc_mm=2.0,
        forecast_etc_period_hours=2.0,
        forecast_etc_valid_from=now_utc,
        forecast_etc_valid_to=now_utc + timedelta(hours=2),
        forecast_period_hours=24.0,
        forecast_probability=0.95,
        expected_rainfall_start=now_utc + timedelta(hours=5),
        issue_time=now_utc - timedelta(hours=1),
    )
    cfg = DecisionConfig(allow_provisional_forecast_deferral=True)
    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc, config=cfg, as_of_time=now_utc)

    # Precedence 2 Emergency override must fire with CRITICAL priority
    assert res.action_type == DecisionAction.IRRIGATE
    assert res.priority == DecisionPriority.CRITICAL
    assert DecisionReasonCode.ACTION_IRRIGATE_EMERGENCY_OVERRIDE in res.reason_codes
    assert DecisionReasonCode.ACTION_IRRIGATE_WILTING_POINT_HAZARD in res.reason_codes
    assert DecisionReasonCode.FORECAST_ETC_WINDOW_INSUFFICIENT in res.reason_codes
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN not in res.reason_codes
    assert res.forecast_reassessment_timestamp is None
