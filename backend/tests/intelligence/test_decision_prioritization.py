"""Tests for Phase 5 priority classification, multi-zone ranking, and farm-wide summaries.

Validates:
1. Priority assignment: CRITICAL (wilting hazard or flowering deficit), HIGH, MEDIUM, LOW, UNRANKED.
2. Crop-stage-aware sensitivity elevating operational urgency.
3. Multi-zone deterministic prioritization and sorting.
4. Farm-wide summary volume aggregation with complete zones.
5. Farm-wide volume suppression when any irrigated zone lacks area data.
6. Farm-wide summary with zero irrigated zones.
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
    DecisionPriority,
    DecisionReasonCode,
    FarmDecisionSummary,
    FarmZoneContext,
    evaluate_farm_decisions,
    evaluate_zone_decision,
)
from backend.app.intelligence.types import DataQualityStatus


def _make_sample_wb(
    zone_id: str,
    dr: float = 30.0,
    raw: float = 50.0,
    taw: float = 100.0,
    ks: float = 1.0,
    quality: DataQualityStatus = DataQualityStatus.GOOD,
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
        quality_status=quality,
        audit_trail=["Synthetic water balance fixture."],
    )


# ==============================================================================
# 1. PRIORITY ASSIGNMENT & CROP-STAGE SENSITIVITY
# ==============================================================================

def test_priority_critical_for_wilting_point_hazard():
    """Verify CRITICAL priority when root-zone depletion reaches wilting point (Dr >= TAW, Ks <= 0.20)."""
    # Dr = 100.0 mm >= TAW = 100.0 mm, Ks = 0.05
    wb_wilt = _make_sample_wb("zone-wilt", dr=100.0, raw=50.0, taw=100.0, ks=0.05)
    zone = FarmZoneContext(farm_id="farm-prio", zone_id="zone-wilt", growth_stage="vegetative")

    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb_wilt)

    assert res.action_type == DecisionAction.IRRIGATE
    assert res.priority == DecisionPriority.CRITICAL
    assert DecisionReasonCode.PRIORITY_CRITICAL_WILTING_POINT in res.reason_codes


def test_priority_critical_for_flowering_deficit():
    """Verify CRITICAL priority when crop is in sensitive flowering stage with moisture deficit."""
    # Dr = 55.0 mm >= RAW = 50.0 mm, Ks = 0.90, growth_stage = 'flowering'
    wb_stress = _make_sample_wb("zone-flower", dr=55.0, raw=50.0, taw=100.0, ks=0.90)
    zone_flower = FarmZoneContext(
        farm_id="farm-prio",
        zone_id="zone-flower",
        crop_type="cotton",
        growth_stage="flowering",  # Sensitive stage!
    )

    res = evaluate_zone_decision(farm_zone=zone_flower, water_balance=wb_stress)

    assert res.action_type == DecisionAction.IRRIGATE
    assert res.priority == DecisionPriority.CRITICAL
    assert DecisionReasonCode.PRIORITY_CRITICAL_FLOWERING_DEFICIT in res.reason_codes

    # Same deficit in vegetative stage results in HIGH priority
    zone_veg = FarmZoneContext(
        farm_id="farm-prio",
        zone_id="zone-veg",
        crop_type="cotton",
        growth_stage="vegetative",  # Standard stage
    )
    res_veg = evaluate_zone_decision(farm_zone=zone_veg, water_balance=wb_stress)
    assert res_veg.action_type == DecisionAction.IRRIGATE
    assert res_veg.priority == DecisionPriority.HIGH


def test_priority_high_for_flowering_stage_approaching_raw():
    """Verify crop in sensitive flowering stage approaching RAW is elevated to HIGH priority under MONITOR."""
    # Dr = 38.0 mm (76% RAW >= 70% sensitive threshold), Ks = 1.00
    wb_approach = _make_sample_wb("zone-flower-appr", dr=38.0, raw=50.0, taw=100.0, ks=1.00)
    zone = FarmZoneContext(
        farm_id="farm-prio",
        zone_id="zone-flower-appr",
        crop_type="wheat",
        growth_stage="anthesis",  # Sensitive stage
    )

    res = evaluate_zone_decision(farm_zone=zone, water_balance=wb_approach)

    assert res.action_type == DecisionAction.MONITOR
    assert res.priority == DecisionPriority.HIGH
    assert DecisionReasonCode.PRIORITY_HIGH_SENSITIVE_STAGE in res.reason_codes


# ==============================================================================
# 2. MULTI-ZONE RANKING & FARM-WIDE SYNTHESIS
# ==============================================================================

def test_multi_zone_prioritization_hierarchy():
    """Verify multi-zone ranking sorts zones by deterministic operational urgency."""
    farm_id = "farm-multi"
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)

    # Zone 1: Critical (wilting point hazard, Dr = 100 mm)
    z1 = FarmZoneContext(farm_id=farm_id, zone_id="Z1_Wilt", zone_area_ha=2.0)
    wb1 = _make_sample_wb("Z1_Wilt", dr=100.0, raw=50.0, taw=100.0, ks=0.05)

    # Zone 2: Critical (flowering stage with deficit, Dr = 60 mm)
    z2 = FarmZoneContext(farm_id=farm_id, zone_id="Z2_Flower", zone_area_ha=2.0, growth_stage="flowering")
    wb2 = _make_sample_wb("Z2_Flower", dr=60.0, raw=50.0, taw=100.0, ks=0.80)

    # Zone 3: High (vegetative stage with deficit, Dr = 55 mm)
    z3 = FarmZoneContext(farm_id=farm_id, zone_id="Z3_Veg_Deficit", zone_area_ha=2.0, growth_stage="vegetative")
    wb3 = _make_sample_wb("Z3_Veg_Deficit", dr=55.0, raw=50.0, taw=100.0, ks=0.90)

    # Zone 4: Medium (vegetative stage approaching RAW, Dr = 42 mm)
    z4 = FarmZoneContext(farm_id=farm_id, zone_id="Z4_Monitor", zone_area_ha=2.0, growth_stage="vegetative")
    wb4 = _make_sample_wb("Z4_Monitor", dr=42.0, raw=50.0, taw=100.0, ks=1.00)

    # Zone 5: Low (healthy, Dr = 15 mm)
    z5 = FarmZoneContext(farm_id=farm_id, zone_id="Z5_Healthy", zone_area_ha=2.0)
    wb5 = _make_sample_wb("Z5_Healthy", dr=15.0, raw=50.0, taw=100.0, ks=1.00)

    # Zone 6: Unranked (insufficient data)
    z6 = FarmZoneContext(farm_id=farm_id, zone_id="Z6_Insufficient", zone_area_ha=2.0)
    wb6 = _make_sample_wb("Z6_Insufficient", dr=60.0, quality=DataQualityStatus.INSUFFICIENT)

    zones = [z5, z3, z6, z1, z4, z2]  # Intentionally scrambled
    wbs = {z.zone_id: wb for z, wb in zip([z1, z2, z3, z4, z5, z6], [wb1, wb2, wb3, wb4, wb5, wb6])}

    summary: FarmDecisionSummary = evaluate_farm_decisions(
        farm_id=farm_id,
        zone_contexts=zones,
        water_balances=wbs,
        as_of_time=now_utc,
    )

    assert summary.total_zones == 6
    assert summary.actions_by_category["irrigate"] == 3
    assert summary.actions_by_category["monitor"] == 1
    assert summary.actions_by_category["no_action_required"] == 1
    assert summary.actions_by_category["insufficient_data"] == 1

    ranked = summary.prioritized_zone_decisions
    # Check priority levels in strict descending order
    priorities = [r.priority for r in ranked]
    assert priorities == [
        DecisionPriority.CRITICAL,  # Z1 (Dr = 100)
        DecisionPriority.CRITICAL,  # Z2 (Dr = 60)
        DecisionPriority.HIGH,      # Z3 (Dr = 55)
        DecisionPriority.MEDIUM,    # Z4 (Monitor)
        DecisionPriority.LOW,       # Z5 (Healthy)
        DecisionPriority.UNRANKED,  # Z6 (Insufficient)
    ]

    # Z1 (Dr=100) is ranked ahead of Z2 (Dr=60) within CRITICAL due to greater deficit
    assert ranked[0].zone_id == "Z1_Wilt"
    assert ranked[1].zone_id == "Z2_Flower"
    assert ranked[2].zone_id == "Z3_Veg_Deficit"
    assert ranked[3].zone_id == "Z4_Monitor"
    assert ranked[4].zone_id == "Z5_Healthy"
    assert ranked[5].zone_id == "Z6_Insufficient"


# ==============================================================================
# 3. FARM-WIDE VOLUME AGGREGATION & INCOMPLETE DATA SAFEGUARD
# ==============================================================================

def test_farm_wide_volume_aggregation_complete():
    """Verify total irrigation volume is accurately aggregated when all irrigated zones have areas."""
    farm_id = "farm-vol-sum"
    # Zone A: Dr = 40 mm, area = 2.0 ha, eta = 0.90 -> Gross = 44.44 mm -> Vol = 44.44 * 2.0 * 10 = 888.89 m³
    za = FarmZoneContext(farm_id=farm_id, zone_id="ZA", zone_area_ha=2.0, application_efficiency=0.90)
    wba = _make_sample_wb("ZA", dr=40.0, raw=35.0)

    # Zone B: Dr = 60 mm, area = 1.5 ha, eta = 0.90 -> Gross = 66.67 mm -> Vol = 66.67 * 1.5 * 10 = 1000.0 m³
    zb = FarmZoneContext(farm_id=farm_id, zone_id="ZB", zone_area_ha=1.5, application_efficiency=0.90)
    wbb = _make_sample_wb("ZB", dr=60.0, raw=40.0)

    # Zone C: Healthy (no water needed)
    zc = FarmZoneContext(farm_id=farm_id, zone_id="ZC", zone_area_ha=3.0)
    wbc = _make_sample_wb("ZC", dr=10.0, raw=40.0)

    summary = evaluate_farm_decisions(
        farm_id=farm_id,
        zone_contexts=[za, zb, zc],
        water_balances={"ZA": wba, "ZB": wbb, "ZC": wbc},
    )

    assert summary.volume_calculation_complete is True
    # Expected total = 888.89 + 1000.0 = 1888.89 m³
    assert pytest.approx(summary.total_estimated_irrigation_volume_m3, abs=0.5) == 1888.89


def test_farm_wide_volume_suppressed_when_zone_area_missing():
    """Verify total irrigation volume is strictly suppressed (None) if any irrigated zone lacks area."""
    farm_id = "farm-missing-area"
    # Zone A: Irrigated, known area 2.0 ha
    za = FarmZoneContext(farm_id=farm_id, zone_id="ZA", zone_area_ha=2.0, application_efficiency=0.90)
    wba = _make_sample_wb("ZA", dr=40.0, raw=35.0)

    # Zone B: Irrigated, MISSING AREA (None)
    zb = FarmZoneContext(farm_id=farm_id, zone_id="ZB", zone_area_ha=None, application_efficiency=0.90)
    wbb = _make_sample_wb("ZB", dr=60.0, raw=40.0)

    summary = evaluate_farm_decisions(
        farm_id=farm_id,
        zone_contexts=[za, zb],
        water_balances={"ZA": wba, "ZB": wbb},
    )

    # Must NOT compute partial misleading total!
    assert summary.volume_calculation_complete is False
    assert summary.total_estimated_irrigation_volume_m3 is None
    assert any("Zone 'ZB' requires irrigation but lacks recorded area" in note for note in summary.volume_audit_notes)


def test_farm_wide_volume_zero_when_no_zones_require_irrigation():
    """Verify total irrigation volume is 0.0 m³ when all zones are healthy or monitoring."""
    farm_id = "farm-zero-irr"
    za = FarmZoneContext(farm_id=farm_id, zone_id="ZA", zone_area_ha=2.0)
    wba = _make_sample_wb("ZA", dr=15.0, raw=40.0)

    zb = FarmZoneContext(farm_id=farm_id, zone_id="ZB", zone_area_ha=1.5)
    wbb = _make_sample_wb("ZB", dr=20.0, raw=50.0)

    summary = evaluate_farm_decisions(
        farm_id=farm_id,
        zone_contexts=[za, zb],
        water_balances={"ZA": wba, "ZB": wbb},
    )

    assert summary.volume_calculation_complete is True
    assert summary.total_estimated_irrigation_volume_m3 == 0.0
    assert summary.actions_by_category["irrigate"] == 0
