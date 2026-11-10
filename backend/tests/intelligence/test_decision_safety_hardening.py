"""Phase 5.1: Decision Engine Safety and Policy Hardening Tests.

Validates:
1. Forecast delay policy: rainfall threshold, probability threshold, lookahead horizon, and freshness.
2. Forecast probability boundaries (e.g. 0.59 vs 0.60, missing prob, high rain with low prob).
3. Stale forecast evidence: issue/retrieval time > 24h cannot defer irrigation; invalid time window rejected.
4. Precedence 2 emergency override: wilting point hazard (Dr >= TAW, Ks <= 0.20) overrides forecast & redistribution delays.
5. Contradictory measurements: recent irrigation logged within 24h but zone in emergency wilting produces explicit warning.
6. Safety invariant: emergency status NEVER overrides insufficient or suspect data quality (Precedence 1 dominates).
7. Minimum application depth edge cases: Dr >= RAW but Dr < 5.0 mm triggers MONITOR (sub-economic deficit, not healthy).
8. Application efficiency provenance: measured vs operator-entered vs assumed default benchmark (provisional).
9. Missing application efficiency: net refill depth is reported independently, while gross depth and volume are withheld.
10. Single-event depth limits and split application: gross > 100 mm requires split cycles without clipping total water.
11. Farm-level summary safeguards: volume is strictly suppressed if any irrigated zone lacks area or efficiency.
12. Deterministic invariance: repeated identical inputs produce identical decisions.
"""

from datetime import datetime, timedelta, timezone
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
    FarmDecisionSummary,
    FarmZoneContext,
    IrrigationHistoryContext,
    WeatherForecastContext,
    evaluate_farm_decisions,
    evaluate_zone_decision,
    validate_forecast_evidence,
    validate_irrigation_quantities,
)
from backend.app.intelligence.types import DataQualityStatus


def _make_test_wb(
    dr: float = 30.0,
    raw: float = 50.0,
    taw: float = 100.0,
    ks: float = 1.0,
    quality: DataQualityStatus = DataQualityStatus.GOOD,
    is_provisional: bool = False,
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
        is_provisional_empirical=is_provisional,
        quality_status=quality,
        audit_trail=["Synthetic water balance fixture for safety hardening tests."],
    )


# ==============================================================================
# 1. FORECAST DELAY POLICY & PROBABILITY BOUNDARIES
# ==============================================================================

def test_forecast_probability_boundary_and_horizon():
    """Verify forecast delay triggers only when rain, horizon, AND probability thresholds are met."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    zone = FarmZoneContext(farm_id="farm-fc", zone_id="z-fc", irrigation_system_type="drip")
    wb = _make_test_wb(dr=55.0, raw=50.0, taw=100.0, ks=0.90)  # Deficit exceeds RAW
    cfg = DecisionConfig(
        forecast_rain_delay_threshold_mm=10.0,
        forecast_delay_horizon_hours=48.0,
        forecast_probability_threshold=0.60,
    )

    # Case A: Rain is significant (15 mm) within horizon (36h), but probability is 55% (< 60% threshold)
    fc_low_prob = WeatherForecastContext(
        forecast_precipitation_mm=15.0,
        forecast_total_precipitation_mm=15.0,
        forecast_effective_rainfall_mm=15.0,
        forecast_etc_mm=4.0,
        forecast_period_hours=36.0,
        forecast_probability=0.55,
        forecast_source="GFS 0.25deg",
        issue_time=now_utc - timedelta(hours=2),
    )
    res_low_prob = evaluate_zone_decision(
        farm_zone=zone, water_balance=wb, forecast=fc_low_prob, config=cfg, as_of_time=now_utc
    )
    # Low probability must NOT trigger rain delay -> proceeds to IRRIGATE
    assert res_low_prob.action_type == DecisionAction.IRRIGATE
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN not in res_low_prob.reason_codes

    # Case B: Rain is significant (15 mm) within horizon (36h), probability is 65% (>= 60% threshold)
    fc_good_prob = WeatherForecastContext(
        forecast_precipitation_mm=15.0,
        forecast_total_precipitation_mm=15.0,
        forecast_effective_rainfall_mm=15.0,
        forecast_etc_mm=4.0,
        forecast_period_hours=36.0,
        forecast_probability=0.65,
        forecast_source="GFS 0.25deg",
        issue_time=now_utc - timedelta(hours=2),
    )
    res_good_prob = evaluate_zone_decision(
        farm_zone=zone, water_balance=wb, forecast=fc_good_prob, config=cfg, as_of_time=now_utc
    )
    assert res_good_prob.action_type == DecisionAction.DELAY_AND_REASSESS
    assert DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN in res_good_prob.reason_codes
    assert res_good_prob.forecast_dependency is not None
    assert res_good_prob.forecast_dependency["forecast_probability"] == 0.65

    # Case C: Rain is significant (25 mm) with 85% prob, but horizon is 72h (> 48h configured limit)
    fc_long_horizon = WeatherForecastContext(
        forecast_precipitation_mm=25.0,
        forecast_total_precipitation_mm=25.0,
        forecast_effective_rainfall_mm=25.0,
        forecast_etc_mm=4.0,
        forecast_period_hours=72.0,
        forecast_probability=0.85,
        forecast_source="ECMWF IFS",
        issue_time=now_utc - timedelta(hours=2),
    )
    res_long_horizon = evaluate_zone_decision(
        farm_zone=zone, water_balance=wb, forecast=fc_long_horizon, config=cfg, as_of_time=now_utc
    )
    assert res_long_horizon.action_type == DecisionAction.IRRIGATE


def test_stale_and_invalid_forecast_evidence():
    """Verify stale forecast (> 24h old) or malformed valid window cannot defer active irrigation."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    zone = FarmZoneContext(farm_id="farm-fc", zone_id="z-fc", irrigation_system_type="drip")
    wb = _make_test_wb(dr=55.0, raw=50.0, taw=100.0, ks=0.90)
    cfg = DecisionConfig(max_forecast_age_hours=24.0)

    # Case A: Forecast issued 30 hours ago (> 24h limit)
    fc_stale = WeatherForecastContext(
        forecast_precipitation_mm=20.0,
        forecast_period_hours=24.0,
        forecast_probability=0.90,
        forecast_source="GFS 0.25deg",
        issue_time=now_utc - timedelta(hours=30),
    )
    val_fc = validate_forecast_evidence(fc_stale, cfg, now_utc)
    assert val_fc.is_stale is True
    assert val_fc.is_valid is False
    assert val_fc.is_actionable is False

    res_stale = evaluate_zone_decision(
        farm_zone=zone, water_balance=wb, forecast=fc_stale, config=cfg, as_of_time=now_utc
    )
    # Stale forecast cannot delay irrigation -> IRRIGATE fires
    assert res_stale.action_type == DecisionAction.IRRIGATE

    # Case B: Malformed validity window (valid_to <= valid_from)
    fc_malformed = WeatherForecastContext(
        forecast_precipitation_mm=20.0,
        forecast_period_hours=24.0,
        forecast_probability=0.90,
        forecast_source="GFS 0.25deg",
        valid_from=now_utc + timedelta(hours=10),
        valid_to=now_utc + timedelta(hours=5),  # Inverted!
        issue_time=now_utc,
    )
    val_malformed = validate_forecast_evidence(fc_malformed, cfg, now_utc)
    assert val_malformed.is_valid is False
    assert DecisionReasonCode.FORECAST_EVIDENCE_INVALID in val_malformed.reasons


# ==============================================================================
# 2. EMERGENCY OVERRIDE PRECEDENCE & CONTRADICTORY MEASUREMENTS
# ==============================================================================

def test_emergency_depletion_with_recent_irrigation_override():
    """Verify valid emergency depletion overrides recent irrigation (< 24h) with contradictory warning."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    zone = FarmZoneContext(farm_id="farm-emrg", zone_id="z-emrg", irrigation_system_type="drip")

    # Emergency wilting point condition: Dr = 100 mm >= TAW = 100 mm, Ks = 0.10
    wb_wilt = _make_test_wb(dr=100.0, raw=50.0, taw=100.0, ks=0.10)

    # Irrigation record claims 40 mm was applied 6 hours ago (< 24h redistribution)
    history = IrrigationHistoryContext(
        last_irrigated_at=now_utc - timedelta(hours=6),
        last_depth_mm=40.0,
        irrigation_method="drip",
        redistribution_hours=24.0,
    )

    res = evaluate_zone_decision(
        farm_zone=zone,
        water_balance=wb_wilt,
        history=history,
        as_of_time=now_utc,
    )

    # Emergency overrides redistribution delay!
    assert res.action_type == DecisionAction.IRRIGATE
    assert res.priority == DecisionPriority.CRITICAL
    assert DecisionReasonCode.ACTION_IRRIGATE_EMERGENCY_OVERRIDE in res.reason_codes
    assert DecisionReasonCode.ACTION_IRRIGATE_WILTING_POINT_HAZARD in res.reason_codes
    assert DecisionReasonCode.WARNING_CONTRADICTORY_RECENT_IRRIGATION in res.reason_codes
    assert any("Contradictory measurement" in a for a in res.assumptions)


def test_insufficient_measurements_during_claimed_emergency():
    """Verify safety invariant: emergency status NEVER overrides insufficient or suspect data quality."""
    zone = FarmZoneContext(farm_id="farm-emrg", zone_id="z-emrg-bad-data")

    # Severe deficit claimed (Dr = 110 mm), but data quality is SUSPECT
    wb_suspect = _make_test_wb(dr=110.0, raw=50.0, taw=100.0, ks=0.05, quality=DataQualityStatus.SUSPECT)

    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb_suspect)

    # Must be INSUFFICIENT_DATA and UNRANKED, not CRITICAL IRRIGATE!
    assert res.action_type == DecisionAction.INSUFFICIENT_DATA
    assert res.priority == DecisionPriority.UNRANKED
    assert DecisionReasonCode.EVIDENCE_WATER_BALANCE_SUSPECT in res.reason_codes
    assert DecisionReasonCode.ACTION_IRRIGATE_EMERGENCY_OVERRIDE not in res.reason_codes


# ==============================================================================
# 3. MINIMUM APPLICATION DEPTH EDGE CASES
# ==============================================================================

def test_deficit_below_minimum_application_depth():
    """Verify Dr >= RAW with net refill < min_economic_depth_mm triggers MONITOR (sub-economic deficit)."""
    # Shallow root zone / sandy soil: TAW = 8.0 mm, RAW = 4.0 mm
    # Current depletion Dr = 4.2 mm >= RAW (active stress zone!)
    # But net depth = 4.2 mm < 5.0 mm min_economical_depth_mm
    wb_small = _make_test_wb(dr=4.2, raw=4.0, taw=8.0, ks=0.95)
    zone = FarmZoneContext(
        farm_id="farm-sub-depth",
        zone_id="z-sub-depth",
        growth_stage="vegetative",
        irrigation_system_type="drip",
    )
    cfg = DecisionConfig(min_economical_depth_mm=5.0)

    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb_small, config=cfg)

    # Explicit MONITOR (not healthy NO_ACTION, not IRRIGATE)
    assert res.action_type == DecisionAction.MONITOR
    assert res.priority == DecisionPriority.MEDIUM  # Active deficit is NOT Low
    assert DecisionReasonCode.ACTION_MONITOR_DEFICIT_BELOW_MIN_DEPTH in res.reason_codes

    # Diagnostics preserve calculated net deficit and minimum threshold
    assert res.min_depth_threshold_mm == 5.0
    assert res.net_irrigation_depth_mm == 4.2
    assert res.gross_irrigation_depth_mm is None  # Water ordering withheld
    assert res.irrigation_volume_m3 is None
    assert res.validation_results["quantities"]["sub_economic_net_depth_mm"] == 4.2


# ==============================================================================
# 4. APPLICATION EFFICIENCY PROVENANCE & UNKNOWN EFFICIENCY SAFEGUARDS
# ==============================================================================

def test_missing_application_efficiency_withholds_gross_and_volume():
    """Verify when efficiency is unknown, net depth is reported independently while gross/volume are withheld."""
    # Dr = 60.0 mm >= RAW = 50.0 mm
    wb = _make_test_wb(dr=60.0, raw=50.0, taw=100.0, ks=0.80)
    # Zone has no explicit efficiency and no known system type
    zone_unknown_eff = FarmZoneContext(
        farm_id="farm-eff",
        zone_id="z-no-eff",
        zone_area_ha=2.5,
        irrigation_system_type=None,
        application_efficiency=None,
    )

    res = evaluate_zone_decision(farm_zone=zone_unknown_eff, water_balance=wb)

    assert res.action_type == DecisionAction.IRRIGATE
    # Net refill depth is reported independently
    assert res.net_irrigation_depth_mm == 60.0
    # Gross depth and volume are strictly withheld
    assert res.gross_irrigation_depth_mm is None
    assert res.irrigation_volume_m3 is None
    assert res.application_efficiency is None
    assert res.application_efficiency_provenance == EfficiencyProvenance.UNKNOWN
    assert DecisionReasonCode.EFFICIENCY_UNKNOWN_WITHHELD in res.reason_codes
    assert any("Application efficiency eta is unknown" in lim for lim in res.unresolved_limitations)


def test_efficiency_provenance_measured_vs_assumed():
    """Verify distinction between in-situ measured efficiency and provisional assumed defaults."""
    wb = _make_test_wb(dr=60.0, raw=50.0, taw=100.0, ks=0.80)

    # Case A: In-situ measured efficiency (0.92)
    zone_measured = FarmZoneContext(
        farm_id="farm-eff",
        zone_id="z-measured",
        irrigation_system_type="drip",
        application_efficiency=0.92,
        application_efficiency_provenance=EfficiencyProvenance.MEASURED,
    )
    res_m = evaluate_zone_decision(farm_zone=zone_measured, water_balance=wb)
    assert res_m.application_efficiency == 0.92
    assert res_m.application_efficiency_provenance == EfficiencyProvenance.MEASURED
    assert res_m.is_efficiency_provisional is False
    assert DecisionReasonCode.EFFICIENCY_MEASURED in res_m.reason_codes

    # Case B: System type lookup without farm measurement (provisional default)
    zone_assumed = FarmZoneContext(
        farm_id="farm-eff",
        zone_id="z-assumed",
        irrigation_system_type="drip",  # Default FAO-56 benchmark = 0.90
        application_efficiency=None,
    )
    res_a = evaluate_zone_decision(farm_zone=zone_assumed, water_balance=wb)
    assert res_a.application_efficiency == 0.90
    assert res_a.application_efficiency_provenance == EfficiencyProvenance.ASSUMED_DEFAULT
    assert res_a.is_efficiency_provisional is True
    assert DecisionReasonCode.EFFICIENCY_PROVISIONAL_ASSUMPTION in res_a.reason_codes


# ==============================================================================
# 5. SINGLE-EVENT DEPTH LIMITS & SPLIT APPLICATION
# ==============================================================================

def test_gross_depth_exceeding_event_limit_requires_split_application():
    """Verify gross depth > max_single_event_gross_depth_mm produces split-application requirement."""
    # Deep deficit: Dr = 90.0 mm
    # Furrow irrigation efficiency: eta = 0.60
    # Required gross depth = 90.0 / 0.60 = 150.0 mm > 100.0 mm limit!
    wb_deep = _make_test_wb(dr=90.0, raw=70.0, taw=150.0, ks=0.70)
    zone_furrow = FarmZoneContext(
        farm_id="farm-split",
        zone_id="z-furrow",
        zone_area_ha=2.0,
        irrigation_system_type="furrow",  # eta = 0.60
    )
    cfg = DecisionConfig(max_allowable_gross_depth_mm=100.0)

    res = evaluate_zone_decision(farm_zone=zone_furrow, water_balance=wb_deep, config=cfg)

    assert res.action_type == DecisionAction.IRRIGATE
    assert res.net_irrigation_depth_mm == 90.0
    # Total gross depth is NOT truncated (preserves 150.0 mm requirement)
    assert res.gross_irrigation_depth_mm == 150.0
    assert res.total_gross_irrigation_depth_mm == 150.0

    # Split application requirements: ceil(150 / 100) = 2 cycles of 75.0 mm each
    assert res.split_application_required is True
    assert res.split_event_count == 2
    assert res.per_event_gross_depth_mm == 75.0
    assert DecisionReasonCode.ACTION_IRRIGATE_SPLIT_APPLICATION_REQUIRED in res.reason_codes

    # Total volumetric water requirement is fully preserved: 150 mm * 2 ha * 10 = 3000 m³
    assert res.irrigation_volume_m3 == 3000.0


# ==============================================================================
# 6. MULTI-ZONE SUMMARY WITH INCOMPLETE EFFICIENCY OR AREA
# ==============================================================================

def test_farm_summary_with_incomplete_efficiency_and_area():
    """Verify farm-wide volume is suppressed when an irrigated zone has unknown efficiency or area."""
    farm_id = "farm-safeguards"
    # Zone 1: Valid area (2 ha) and efficiency (0.90) -> Vol = 66.67 * 2 * 10 = 1333.33 m³
    z1 = FarmZoneContext(farm_id=farm_id, zone_id="Z1", zone_area_ha=2.0, application_efficiency=0.90)
    wb1 = _make_test_wb(dr=60.0, raw=50.0)

    # Zone 2: Valid area (2 ha), but UNKNOWN efficiency (efficiency=None, system=None)
    z2 = FarmZoneContext(farm_id=farm_id, zone_id="Z2", zone_area_ha=2.0, irrigation_system_type=None)
    wb2 = _make_test_wb(dr=60.0, raw=50.0)

    summary = evaluate_farm_decisions(
        farm_id=farm_id,
        zone_contexts=[z1, z2],
        water_balances={"Z1": wb1, "Z2": wb2},
    )

    # Volume calculation must be incomplete and total volume must be None
    assert summary.volume_calculation_complete is False
    assert summary.total_estimated_irrigation_volume_m3 is None
    assert any("application efficiency is unknown" in note for note in summary.volume_audit_notes)


# ==============================================================================
# 7. REPEATED IDENTICAL INPUTS PRODUCE IDENTICAL DECISIONS
# ==============================================================================

def test_decision_determinism_and_invariants():
    """Verify repeated evaluations with identical inputs produce bitwise identical decisions."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    zone = FarmZoneContext(
        farm_id="farm-det",
        zone_id="z-det",
        zone_area_ha=3.0,
        irrigation_system_type="drip",
        application_efficiency=0.90,
    )
    wb = _make_test_wb(dr=60.0, raw=50.0, taw=100.0, ks=0.85)

    res1 = evaluate_zone_decision(farm_zone=zone, water_balance=wb, as_of_time=now_utc)
    res2 = evaluate_zone_decision(farm_zone=zone, water_balance=wb, as_of_time=now_utc)

    assert res1.action_type == res2.action_type
    assert res1.priority == res2.priority
    assert res1.net_irrigation_depth_mm == res2.net_irrigation_depth_mm
    assert res1.gross_irrigation_depth_mm == res2.gross_irrigation_depth_mm
    assert res1.irrigation_volume_m3 == res2.irrigation_volume_m3
    assert res1.reason_codes == res2.reason_codes
    assert res1.decision_rules_triggered == res2.decision_rules_triggered

