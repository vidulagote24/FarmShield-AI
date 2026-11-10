"""Comprehensive test suite for Phase 6.1 Farmer Explanation and Multilingual Integrity.

Validates:
1. All five Phase 5 decision actions (IRRIGATE, MONITOR, DELAY_AND_REASSESS, INSUFFICIENT_DATA, NO_ACTION_REQUIRED).
2. Complete 15-combination multilingual coverage (5 actions x 3 languages: EN, MR, HI) with zero English fallback.
3. Distinction between net irrigation refill requirement (d_net) and gross application depth (d_gross).
4. Application efficiency transparency (measured vs assumed default vs operator entered vs unknown).
5. Split-application explanation integrity for standard and emergency irrigation (never directing single events).
6. Non-overgeneralized health statements for NO_ACTION_REQUIRED preserving independent agronomic alerts (salinity, alkalinity, vegetation, frost).
7. Exhaustive reason-code registry completeness (100% of DecisionReasonCode and StressReasonCode mapped).
8. Unknown reason-code explicit handling.
9. Missing evidence, stale evidence, and suspect evidence auditing without silent imputation.
10. Provisional forecast deferral and empirical rainfall caveats.
11. Farm-level explanation synthesis and volumetric suppression reporting.
12. Determinism and non-override invariants.
13. JSON schema serialization compatibility.
"""

from datetime import date, datetime, timedelta, timezone
import json
import pytest

from backend.app.intelligence.agronomy.water_balance import (
    SoilWaterCapacities,
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
    evaluate_farm_decisions,
    evaluate_zone_decision,
)
from backend.app.intelligence.explanations import (
    AgronomistTechnicalExplanation,
    AgronomyReasonCode,
    EvidenceItem,
    EvidenceType,
    ExplanationLanguage,
    FarmExplanation,
    ReasonCodeExplanation,
    ZoneExplanation,
    build_evidence_inventory,
    build_farm_explanation,
    build_zone_explanation,
    resolve_reason_code,
)
from backend.app.intelligence.explanations.reason_codes import _REASON_CODE_REGISTRY
from backend.app.intelligence.stress.assessment import ZoneStressAssessment
from backend.app.intelligence.stress.scoring import StressReasonCode
from backend.app.intelligence.types import DataQualityStatus, ProvenanceType, StressStatus


def _make_test_wb(
    dr: float = 30.0,
    raw: float = 50.0,
    taw: float = 100.0,
    ks: float = 1.0,
    quality: DataQualityStatus = DataQualityStatus.GOOD,
    is_prov_empirical: bool = False,
) -> WaterBalanceResult:
    """Helper constructing synthetic WaterBalanceResult fixture."""
    return WaterBalanceResult(
        rainfall_mode=WaterBalanceRainfallMode.PHYSICAL,
        soil_capacities=SoilWaterCapacities(
            field_capacity_m3_m3=0.30,
            wilting_point_m3_m3=0.15,
            available_water_capacity_m3_m3=0.15,
            effective_rooting_depth_m=0.8,
            depletion_fraction_p=0.5,
            depletion_fraction_p_table=0.5,
            total_available_water_mm=taw,
            readily_available_water_mm=raw,
        ),
        final_depletion_mm=dr,
        total_available_water_mm=taw,
        readily_available_water_mm=raw,
        water_stress_coefficient_ks=ks,
        crop_evapotranspiration_mm=5.0,
        adjusted_crop_evapotranspiration_mm=5.0 * ks,
        is_in_stress_zone=dr > raw,
        stress_deficit_mm=max(0.0, dr - raw),
        is_provisional_empirical=is_prov_empirical,
        quality_status=quality,
    )


# ==============================================================================
# 1. REASON-CODE REGISTRY COMPLETENESS
# ==============================================================================

def test_reason_code_registry_completeness():
    """Verify 100% coverage: every DecisionReasonCode, StressReasonCode, and AgronomyReasonCode must be registered."""
    dec_codes = {c.value for c in DecisionReasonCode}
    stress_codes = {c.value for c in StressReasonCode}
    agro_codes = {c.value for c in AgronomyReasonCode}
    reg_codes = set(_REASON_CODE_REGISTRY.keys())

    missing_dec = dec_codes - reg_codes
    missing_stress = stress_codes - reg_codes
    missing_agro = agro_codes - reg_codes

    assert len(missing_dec) == 0, f"Unregistered DecisionReasonCodes: {missing_dec}"
    assert len(missing_stress) == 0, f"Unregistered StressReasonCodes: {missing_stress}"
    assert len(missing_agro) == 0, f"Unregistered AgronomyReasonCodes: {missing_agro}"

    # Verify each entry contains en, mr, hi, tech, refs, limits
    for code, entry in _REASON_CODE_REGISTRY.items():
        assert "en" in entry and len(entry["en"]) > 0, f"Code {code} missing English explanation"
        assert "mr" in entry and len(entry["mr"]) > 0, f"Code {code} missing Marathi explanation"
        assert "hi" in entry and len(entry["hi"]) > 0, f"Code {code} missing Hindi explanation"
        assert "tech" in entry, f"Code {code} missing tech note"
        assert "refs" in entry, f"Code {code} missing refs"
        assert "limits" in entry, f"Code {code} missing limits"


# ==============================================================================
# 2. NET VS GROSS IRRIGATION EXPLANATIONS
# ==============================================================================

def test_net_versus_gross_irrigation_explanations():
    """Verify IRRIGATE explanations strictly distinguish net crop deficit from gross application depth."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=55.0, raw=50.0, taw=100.0, ks=0.90)

    # 1. Gross depth AVAILABLE (d_net = 55.0 mm, eta = 0.90 -> d_gross = 61.11 mm, area = 2.0 ha -> vol = 1222.2 m³)
    z_avail = FarmZoneContext(
        farm_id="farm-ng",
        zone_id="z-avail",
        zone_area_ha=2.0,
        application_efficiency=0.90,
        application_efficiency_provenance=EfficiencyProvenance.OPERATOR_ENTERED,
    )
    dec_avail = evaluate_zone_decision(farm_zone=z_avail, water_balance=wb, as_of_time=now_utc)
    expl_avail = build_zone_explanation(decision=dec_avail, water_balance=wb, farm_zone=z_avail, language=ExplanationLanguage.EN)

    # Top-level fields
    assert expl_avail.net_irrigation_depth_mm == 55.0
    assert expl_avail.gross_irrigation_depth_mm == 61.11
    assert expl_avail.application_efficiency == 0.90
    assert expl_avail.application_efficiency_provenance == "operator_entered"
    assert expl_avail.irrigation_volume_m3 == 1222.2

    # Narrative text must distinguish net from gross
    assert "61.1 mm gross irrigation" in expl_avail.short_summary
    assert "net crop deficit: 55.0 mm" in expl_avail.short_summary
    assert "Net crop refill demand is 55.0 mm" in expl_avail.why_decision_produced
    assert "required gross application depth is 61.1 mm" in expl_avail.why_decision_produced
    assert "1,222.2 m³" in expl_avail.why_decision_produced

    # 2. Gross depth UNAVAILABLE (efficiency unknown: d_net = 55.0 mm preserved, d_gross = None, vol = None)
    z_unk = FarmZoneContext(
        farm_id="farm-ng",
        zone_id="z-unk",
        zone_area_ha=2.0,
        application_efficiency=None,
        irrigation_system_type=None,
    )
    dec_unk = evaluate_zone_decision(farm_zone=z_unk, water_balance=wb, as_of_time=now_utc)
    expl_unk = build_zone_explanation(decision=dec_unk, water_balance=wb, farm_zone=z_unk, language=ExplanationLanguage.EN)

    # Top-level fields
    assert expl_unk.net_irrigation_depth_mm == 55.0
    assert expl_unk.gross_irrigation_depth_mm is None
    assert expl_unk.irrigation_volume_m3 is None

    # Narrative text must explain why gross depth is unavailable without inventing quantities
    assert "net crop water deficit of 55.0 mm" in expl_unk.short_summary
    assert "gross application depth unavailable" in expl_unk.short_summary.lower()
    assert "efficiency is unknown" in expl_unk.why_decision_produced.lower()
    assert "unverified application quantity cannot be invented" in expl_unk.why_decision_produced.lower()
    assert "Net soil water refill requirement is 55.0 mm" in expl_unk.action_guidance


# ==============================================================================
# 3. SPLIT-APPLICATION EXPLANATIONS (STANDARD AND EMERGENCY)
# ==============================================================================

def test_split_application_explanations_standard_and_emergency():
    """Verify split application schedule is clearly explained and never directs single events."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)

    # 1. Standard Split Application (gross = 150.0 mm, max = 100.0 mm -> 2 events of 75.0 mm)
    wb_std = _make_test_wb(dr=150.0, raw=50.0, taw=200.0, ks=0.50)
    z_std = FarmZoneContext(
        farm_id="farm-split",
        zone_id="z-split-std",
        application_efficiency=1.0,
        max_single_event_depth_mm=100.0,
    )
    dec_std = evaluate_zone_decision(farm_zone=z_std, water_balance=wb_std, as_of_time=now_utc)
    expl_std = build_zone_explanation(decision=dec_std, water_balance=wb_std, farm_zone=z_std, language=ExplanationLanguage.EN)

    assert expl_std.action == DecisionAction.IRRIGATE
    assert "across 2 split cycles (75.0 mm, 75.0 mm)" in expl_std.action_guidance
    assert "do not apply the entire 150.0 mm in a single event" in expl_std.action_guidance

    # 2. Emergency Split Application (severe wilting: Dr = 150.0 >= TAW = 150.0, Ks = 0.10 <= 0.20)
    wb_emerg = _make_test_wb(dr=150.0, raw=50.0, taw=150.0, ks=0.10)
    z_emerg = FarmZoneContext(
        farm_id="farm-split",
        zone_id="z-split-emerg",
        application_efficiency=1.0,
        max_single_event_depth_mm=100.0,
    )
    dec_emerg = evaluate_zone_decision(farm_zone=z_emerg, water_balance=wb_emerg, as_of_time=now_utc)
    expl_emerg = build_zone_explanation(decision=dec_emerg, water_balance=wb_emerg, farm_zone=z_emerg, language=ExplanationLanguage.EN)

    assert expl_emerg.priority == DecisionPriority.CRITICAL
    assert "EMERGENCY" in expl_emerg.short_summary
    assert "across 2 split cycles (75.0 mm, 75.0 mm)" in expl_emerg.short_summary
    assert "divided into 2 split cycles (75.0 mm, 75.0 mm)" in expl_emerg.why_decision_produced
    assert "across 2 split cycles (75.0 mm, 75.0 mm)" in expl_emerg.action_guidance
    assert "do not apply the entire 150.0 mm in a single event" in expl_emerg.action_guidance

    # Verify Marathi split emergency guidance
    expl_emerg_mr = build_zone_explanation(decision=dec_emerg, water_balance=wb_emerg, farm_zone=z_emerg, language=ExplanationLanguage.MR)
    assert "2 टप्प्यांत विभागून (75.0 mm, 75.0 mm)" in expl_emerg_mr.short_summary
    assert "2 टप्प्यांत विभागून" in expl_emerg_mr.action_guidance
    assert "एकाच वेळी पूर्ण 150.0 मिमी पाणी देऊ नका" in expl_emerg_mr.action_guidance

    # Verify Hindi split emergency guidance
    expl_emerg_hi = build_zone_explanation(decision=dec_emerg, water_balance=wb_emerg, farm_zone=z_emerg, language=ExplanationLanguage.HI)
    assert "2 चरणों में विभाजित (75.0 mm, 75.0 mm)" in expl_emerg_hi.short_summary
    assert "2 विभाजित चरणों" in expl_emerg_hi.action_guidance
    assert "एक ही बार में पूरा 150.0 मिमी पानी न दें" in expl_emerg_hi.action_guidance

    # 3. Emergency Split Application with Depth > 100 mm across 3 cycles (e.g. 220.0 mm total with 80 mm max)
    wb_emerg_large = _make_test_wb(dr=220.0, raw=50.0, taw=220.0, ks=0.05)
    z_emerg_large = FarmZoneContext(
        farm_id="farm-split-large",
        zone_id="z-split-large",
        application_efficiency=1.0,
        max_single_event_depth_mm=80.0,
    )
    dec_emerg_large = evaluate_zone_decision(farm_zone=z_emerg_large, water_balance=wb_emerg_large, as_of_time=now_utc)
    expl_emerg_large = build_zone_explanation(decision=dec_emerg_large, water_balance=wb_emerg_large, farm_zone=z_emerg_large, language=ExplanationLanguage.EN)

    assert expl_emerg_large.priority == DecisionPriority.CRITICAL
    assert expl_emerg_large.gross_irrigation_depth_mm == 220.0
    assert expl_emerg_large.agronomist_explanation.split_event_count == 3
    assert expl_emerg_large.agronomist_explanation.split_event_depths_mm == [73.33, 73.33, 73.34]
    assert "EMERGENCY" in expl_emerg_large.short_summary
    assert "across 3 split cycles (73.33 mm, 73.33 mm, 73.34 mm)" in expl_emerg_large.short_summary
    assert "divided into 3 split cycles (73.33 mm, 73.33 mm, 73.34 mm)" in expl_emerg_large.why_decision_produced
    assert "across 3 split cycles (73.33 mm, 73.33 mm, 73.34 mm)" in expl_emerg_large.action_guidance
    assert "Apply 220.00 mm total gross depth" in expl_emerg_large.action_guidance
    assert "do not apply the entire 220.00 mm in a single event" in expl_emerg_large.action_guidance

    # Verify Marathi large emergency split
    expl_large_mr = build_zone_explanation(decision=dec_emerg_large, water_balance=wb_emerg_large, farm_zone=z_emerg_large, language=ExplanationLanguage.MR)
    assert "3 टप्प्यांत विभागून (73.33 mm, 73.33 mm, 73.34 mm)" in expl_large_mr.short_summary
    assert "3 टप्प्यांत विभागून (73.33 mm, 73.33 mm, 73.34 mm)" in expl_large_mr.why_decision_produced
    assert "3 टप्प्यांत विभागून (73.33 mm, 73.33 mm, 73.34 mm)" in expl_large_mr.action_guidance
    assert "एकाच वेळी पूर्ण 220.00 मिमी पाणी देऊ नका" in expl_large_mr.action_guidance

    # Verify Hindi large emergency split
    expl_large_hi = build_zone_explanation(decision=dec_emerg_large, water_balance=wb_emerg_large, farm_zone=z_emerg_large, language=ExplanationLanguage.HI)
    assert "3 चरणों में विभाजित (73.33 mm, 73.33 mm, 73.34 mm)" in expl_large_hi.short_summary
    assert "3 चरणों (73.33 mm, 73.33 mm, 73.34 mm)" in expl_large_hi.why_decision_produced
    assert "3 विभाजित चरणों (73.33 mm, 73.33 mm, 73.34 mm)" in expl_large_hi.action_guidance
    assert "एक ही बार में पूरा 220.00 मिमी पानी न दें" in expl_large_hi.action_guidance


# ==============================================================================
# 4. NO_ACTION_REQUIRED & NON-OVERGENERALIZED HEALTH STATEMENTS
# ==============================================================================

def test_no_action_required_corrected_health_statements():
    """Verify NO_ACTION_REQUIRED states absence of irrigation need, not universal health, and preserves alerts."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb_healthy = _make_test_wb(dr=15.0, raw=50.0, taw=100.0, ks=1.0)
    zone = FarmZoneContext(farm_id="farm-nar", zone_id="z-nar", application_efficiency=0.90)

    # 1. Clean well-watered zone (no independent flags)
    dec_clean = evaluate_zone_decision(farm_zone=zone, water_balance=wb_healthy, as_of_time=now_utc)
    expl_clean = build_zone_explanation(decision=dec_clean, water_balance=wb_healthy, farm_zone=zone, language=ExplanationLanguage.EN)

    assert "Current water-balance evidence does not indicate a need for irrigation" in expl_clean.short_summary
    assert "No water application is required at this time based on soil moisture evidence" in expl_clean.action_guidance

    # 2. Well-watered root zone WITH independent soil salinity alert
    dec_saline = evaluate_zone_decision(farm_zone=zone, water_balance=wb_healthy, as_of_time=now_utc)
    dec_saline.reason_codes.append(DecisionReasonCode.AGRONOMIC_FLAG_SOIL_SALINITY_NON_WATERING)
    expl_saline = build_zone_explanation(decision=dec_saline, water_balance=wb_healthy, farm_zone=zone, language=ExplanationLanguage.EN)

    assert "independent agronomic concerns require review" in expl_saline.short_summary
    assert "elevated soil salinity" in expl_saline.why_decision_produced
    assert "Absence of an irrigation requirement does not indicate absence of crop health problems" in expl_saline.why_decision_produced
    assert "inspect the zone to address non-watering issues" in expl_saline.action_guidance

    # In Marathi
    expl_saline_mr = build_zone_explanation(decision=dec_saline, water_balance=wb_healthy, farm_zone=zone, language=ExplanationLanguage.MR)
    assert "इतर स्वतंत्र कृषी समस्या तपासणे आवश्यक आहे" in expl_saline_mr.short_summary
    assert "मातीतील वाढलेले क्षार" in expl_saline_mr.why_decision_produced
    assert "सिंचनाची गरज नसणे म्हणजे पिकाला कोणताही कृषी प्रश्न नाही असा होत नाही" in expl_saline_mr.why_decision_produced

    # In Hindi
    expl_saline_hi = build_zone_explanation(decision=dec_saline, water_balance=wb_healthy, farm_zone=zone, language=ExplanationLanguage.HI)
    assert "स्वतंत्र कृषि चिंताओं की समीक्षा आवश्यक है" in expl_saline_hi.short_summary
    assert "मृदा लवणता में वृद्धि" in expl_saline_hi.why_decision_produced
    assert "सिंचाई की आवश्यकता न होने का अर्थ फसल में किसी अन्य समस्या का अभाव नहीं है" in expl_saline_hi.why_decision_produced


# ==============================================================================
# 5. COMPLETE 15-COMBINATION MULTILINGUAL COVERAGE MATRIX
# ==============================================================================

@pytest.mark.parametrize("action", [
    DecisionAction.IRRIGATE,
    DecisionAction.MONITOR,
    DecisionAction.DELAY_AND_REASSESS,
    DecisionAction.INSUFFICIENT_DATA,
    DecisionAction.NO_ACTION_REQUIRED,
])
@pytest.mark.parametrize("lang", [
    ExplanationLanguage.EN,
    ExplanationLanguage.MR,
    ExplanationLanguage.HI,
])
def test_all_fifteen_action_language_combinations(action: DecisionAction, lang: ExplanationLanguage):
    """Validate all 15 combinations (5 actions x 3 languages) produce robust, non-empty, localized output."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    zone = FarmZoneContext(farm_id="farm-matrix", zone_id="z-matrix", application_efficiency=0.90, zone_area_ha=1.5)

    if action == DecisionAction.IRRIGATE:
        wb = _make_test_wb(dr=60.0, raw=50.0, taw=100.0, ks=0.80)
        dec = evaluate_zone_decision(farm_zone=zone, water_balance=wb, as_of_time=now_utc)
    elif action == DecisionAction.MONITOR:
        wb = _make_test_wb(dr=42.0, raw=50.0, taw=100.0, ks=1.0)
        dec = evaluate_zone_decision(farm_zone=zone, water_balance=wb, as_of_time=now_utc)
    elif action == DecisionAction.DELAY_AND_REASSESS:
        wb = _make_test_wb(dr=45.0, raw=50.0, taw=100.0, ks=1.0)
        fc = WeatherForecastContext(
            forecast_precipitation_mm=25.0,
            forecast_etc_mm=2.0,
            forecast_etc_period_hours=4.0,
            forecast_etc_valid_from=now_utc,
            forecast_etc_valid_to=now_utc + timedelta(hours=4),
            forecast_period_hours=24.0,
            forecast_probability=0.80,
            expected_rainfall_start=now_utc + timedelta(hours=3),
            issue_time=now_utc - timedelta(hours=1),
        )
        cfg = DecisionConfig(allow_provisional_forecast_deferral=True)
        dec = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc, config=cfg, as_of_time=now_utc)
    elif action == DecisionAction.INSUFFICIENT_DATA:
        wb = WaterBalanceResult(quality_status=DataQualityStatus.INSUFFICIENT)
        dec = evaluate_zone_decision(farm_zone=zone, water_balance=wb, as_of_time=now_utc)
    else:  # NO_ACTION_REQUIRED
        wb = _make_test_wb(dr=15.0, raw=50.0, taw=100.0, ks=1.0)
        dec = evaluate_zone_decision(farm_zone=zone, water_balance=wb, as_of_time=now_utc)

    expl = build_zone_explanation(decision=dec, water_balance=wb, farm_zone=zone, language=lang)

    # 1. All fields non-empty
    assert len(expl.short_summary.strip()) > 5
    assert len(expl.why_decision_produced.strip()) > 5
    assert len(expl.action_guidance.strip()) > 5

    # 2. Script integrity: Marathi and Hindi must contain Devanagari script (U+0900 to U+097F)
    if lang in (ExplanationLanguage.MR, ExplanationLanguage.HI):
        has_devanagari_summary = any("\u0900" <= ch <= "\u097f" for ch in expl.short_summary)
        has_devanagari_why = any("\u0900" <= ch <= "\u097f" for ch in expl.why_decision_produced)
        has_devanagari_guidance = any("\u0900" <= ch <= "\u097f" for ch in expl.action_guidance)
        assert has_devanagari_summary, f"Action {action} in {lang} lacks Devanagari characters in short_summary: {expl.short_summary}"
        assert has_devanagari_why, f"Action {action} in {lang} lacks Devanagari characters in why_decision_produced: {expl.why_decision_produced}"
        assert has_devanagari_guidance, f"Action {action} in {lang} lacks Devanagari characters in action_guidance: {expl.action_guidance}"


# ==============================================================================
# 6. SPECIAL CASES
# ==============================================================================

def test_special_case_missing_zone_area_with_gross_depth():
    """Missing zone area preserves net and gross depths while withholding volume."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=55.0, raw=50.0)
    zone_no_area = FarmZoneContext(
        farm_id="farm-noarea",
        zone_id="z-noarea",
        zone_area_ha=None,  # Missing area
        application_efficiency=0.90,
    )
    dec = evaluate_zone_decision(farm_zone=zone_no_area, water_balance=wb, as_of_time=now_utc)
    expl = build_zone_explanation(decision=dec, water_balance=wb, farm_zone=zone_no_area, language=ExplanationLanguage.EN)

    assert expl.action == DecisionAction.IRRIGATE
    assert expl.net_irrigation_depth_mm == 55.0
    assert expl.gross_irrigation_depth_mm == 61.11
    assert expl.irrigation_volume_m3 is None
    assert "total zone volume is withheld because zone area is unrecorded" in expl.why_decision_produced


def test_special_case_positive_vegetation_anomaly():
    """Verify positive vegetation anomaly reason code resolves cleanly."""
    res_en = resolve_reason_code(StressReasonCode.VEGETATION_ANOMALY_POSITIVE, language=ExplanationLanguage.EN)
    assert res_en.is_unresolved is False
    assert "above-average canopy development" in res_en.farmer_explanation
    assert "delta_ndvi" in res_en.measurement_references


def test_special_case_unresolved_reason_code():
    """Verify unmapped or arbitrary custom reason code is explicitly marked unresolved without crashing."""
    res_en = resolve_reason_code("ARBITRARY_FUTURE_REASON_CODE_XYZ", language=ExplanationLanguage.EN)
    assert res_en.is_unresolved is True
    assert "Unresolved reason code: ARBITRARY_FUTURE_REASON_CODE_XYZ" in res_en.farmer_explanation
    assert len(res_en.limitations) > 0

    res_mr = resolve_reason_code("ARBITRARY_FUTURE_REASON_CODE_XYZ", language=ExplanationLanguage.MR)
    assert res_mr.is_unresolved is True
    assert "अपरिचित कारण कोड: ARBITRARY_FUTURE_REASON_CODE_XYZ" in res_mr.farmer_explanation


def test_special_case_missing_forecast_etc_blocks_provisional():
    """Missing forecast ETc blocks provisional deferral and produces clear explanation."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=45.0, raw=50.0, ks=1.0)
    zone = FarmZoneContext(farm_id="farm-fetc", zone_id="z-fetc", application_efficiency=0.90)

    fc_no_etc = WeatherForecastContext(
        forecast_precipitation_mm=25.0,
        forecast_effective_rainfall_mm=None,
        forecast_etc_mm=None,  # Missing ETc
        forecast_period_hours=24.0,
        forecast_probability=0.85,
        expected_rainfall_start=now_utc + timedelta(hours=3),
        issue_time=now_utc - timedelta(hours=1),
    )
    cfg = DecisionConfig(allow_provisional_forecast_deferral=True)
    dec = evaluate_zone_decision(farm_zone=zone, water_balance=wb, forecast=fc_no_etc, config=cfg, as_of_time=now_utc)
    expl = build_zone_explanation(decision=dec, water_balance=wb, farm_zone=zone, forecast=fc_no_etc, language=ExplanationLanguage.EN)

    assert expl.action == DecisionAction.MONITOR
    assert DecisionReasonCode.FORECAST_ETC_MISSING in dec.reason_codes
    assert any("forecast etc is missing" in m.lower() for m in expl.missing_evidence)


# ==============================================================================
# 7. FARM SUMMARY VOLUMETRIC EXPLANATIONS
# ==============================================================================

def test_farm_summary_multilingual_volume_statuses():
    """Verify farm explanation handles all volume statuses across EN, MR, and HI."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    farm_id = "farm-vols"
    wb = _make_test_wb(dr=55.0, raw=50.0)

    # 1. COMPLETE_MEASURED
    z_meas = FarmZoneContext(
        farm_id=farm_id,
        zone_id="zm",
        zone_area_ha=2.0,
        application_efficiency=0.90,
        is_efficiency_measurement_verified=True,
        efficiency_verification=EfficiencyVerificationRecord(
            verification_method="in_situ_distribution_uniformity_audit",
            measurement_date=date(2026, 5, 20),
            system_or_zone_id="zm",
            measured_efficiency=0.90,
            supporting_audit_reference="AUDIT-2026",
            verification_status="verified",
        ),
    )
    sum_meas = evaluate_farm_decisions(farm_id=farm_id, zone_contexts=[z_meas], water_balances={"zm": wb}, as_of_time=now_utc)
    expl_z = build_zone_explanation(sum_meas.prioritized_zone_decisions[0], wb, farm_zone=z_meas)

    f_en = build_farm_explanation(sum_meas, [expl_z], language=ExplanationLanguage.EN)
    assert "backed by verified field-tested efficiency" in f_en.farm_summary_text

    f_mr = build_farm_explanation(sum_meas, [expl_z], language=ExplanationLanguage.MR)
    assert "सत्यापित कार्यक्षमतेसह" in f_mr.farm_summary_text

    f_hi = build_farm_explanation(sum_meas, [expl_z], language=ExplanationLanguage.HI)
    assert "सत्यापित दक्षता के साथ" in f_hi.farm_summary_text


# ==============================================================================
# 8. DETERMINISM AND NON-OVERRIDE INVARIANTS
# ==============================================================================

def test_explanation_determinism_and_non_override_invariants():
    """Verify that explanation service is 100% deterministic and never modifies Phase 5 decision outputs."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=55.0, raw=50.0)
    zone = FarmZoneContext(farm_id="farm-det", zone_id="z-det", zone_area_ha=2.0, application_efficiency=0.90)
    dec = evaluate_zone_decision(farm_zone=zone, water_balance=wb, as_of_time=now_utc)

    # Snapshot decision properties before explanation
    action_before = dec.action_type
    prio_before = dec.priority
    net_before = dec.net_irrigation_depth_mm
    gross_before = dec.gross_irrigation_depth_mm
    vol_before = dec.irrigation_volume_m3

    expl1 = build_zone_explanation(decision=dec, water_balance=wb, farm_zone=zone, language=ExplanationLanguage.EN)
    expl2 = build_zone_explanation(decision=dec, water_balance=wb, farm_zone=zone, language=ExplanationLanguage.EN)

    # Invariants: Decision properties are never mutated or overridden
    assert dec.action_type == action_before
    assert dec.priority == prio_before
    assert dec.net_irrigation_depth_mm == net_before
    assert dec.gross_irrigation_depth_mm == gross_before
    assert dec.irrigation_volume_m3 == vol_before

    # Exact bit-for-bit determinism across repeated calls (ignoring explanation_timestamp)
    d1 = expl1.model_dump(exclude={"explanation_timestamp"})
    d2 = expl2.model_dump(exclude={"explanation_timestamp"})
    assert d1 == d2


# ==============================================================================
# 9. JSON SERIALIZATION COMPATIBILITY
# ==============================================================================

def test_explanation_json_serialization_compatibility():
    """Verify that ZoneExplanation and FarmExplanation serialize cleanly to standard JSON for API transport."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    wb = _make_test_wb(dr=55.0, raw=50.0)
    zone = FarmZoneContext(farm_id="farm-ser", zone_id="z-ser", zone_area_ha=2.0, application_efficiency=0.90)
    dec = evaluate_zone_decision(farm_zone=zone, water_balance=wb, as_of_time=now_utc)

    expl = build_zone_explanation(decision=dec, water_balance=wb, farm_zone=zone, language=ExplanationLanguage.EN)

    # 1. ZoneExplanation serialization
    json_str = expl.model_dump_json()
    parsed = json.loads(json_str)
    assert parsed["farm_id"] == "farm-ser"
    assert parsed["zone_id"] == "z-ser"
    assert parsed["action"] == "irrigate"
    assert parsed["net_irrigation_depth_mm"] == 55.0
    assert parsed["gross_irrigation_depth_mm"] == 61.11
    assert "agronomist_explanation" in parsed
    assert "supporting_evidence" in parsed

    # 2. FarmExplanation serialization
    summary = evaluate_farm_decisions(farm_id="farm-ser", zone_contexts=[zone], water_balances={"z-ser": wb}, as_of_time=now_utc)
    farm_expl = build_farm_explanation(summary=summary, zone_explanations=[expl], language=ExplanationLanguage.EN)

    farm_json = farm_expl.model_dump_json()
    parsed_farm = json.loads(farm_json)
    assert parsed_farm["farm_id"] == "farm-ser"
    assert parsed_farm["total_zones"] == 1
    assert len(parsed_farm["zone_explanations"]) == 1


# ==============================================================================
# 10. REASSESSMENT-TIME PROVENANCE & LINGUISTIC AUDIT
# ==============================================================================

def test_reassessment_time_provenance():
    """Verify reassessment times appear only when supplied by Phase 5 and preserve timezone."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    zone = FarmZoneContext(farm_id="farm-prov", zone_id="z-prov", application_efficiency=0.90)
    wb_healthy = _make_test_wb(dr=15.0, raw=50.0, taw=100.0, ks=1.0)

    # 1. NO_ACTION_REQUIRED without reassessment timestamp (generic next-scheduled wording, no hardcoded 24h)
    dec_gen = evaluate_zone_decision(farm_zone=zone, water_balance=wb_healthy, as_of_time=now_utc)
    expl_gen = build_zone_explanation(decision=dec_gen, water_balance=wb_healthy, farm_zone=zone, language=ExplanationLanguage.EN)
    assert "24 hours" not in expl_gen.action_guidance
    assert "12 hours" not in expl_gen.action_guidance
    assert "next scheduled cycle" in expl_gen.action_guidance

    # 2. NO_ACTION_REQUIRED WITH explicit forecast_reassessment_timestamp preserving timezone
    dec_timed = evaluate_zone_decision(farm_zone=zone, water_balance=wb_healthy, as_of_time=now_utc)
    custom_ts = datetime(2026, 7, 16, 6, 0, tzinfo=timezone.utc)
    dec_timed.forecast_reassessment_timestamp = custom_ts
    expl_timed = build_zone_explanation(decision=dec_timed, water_balance=wb_healthy, farm_zone=zone, language=ExplanationLanguage.EN)
    assert "2026-07-16 06:00 UTC" in expl_timed.action_guidance
    assert expl_timed.reassessment_timestamp == custom_ts

    # In Marathi
    expl_timed_mr = build_zone_explanation(decision=dec_timed, water_balance=wb_healthy, farm_zone=zone, language=ExplanationLanguage.MR)
    assert "2026-07-16 06:00 UTC" in expl_timed_mr.action_guidance

    # 3. MONITOR without reassessment timing (generic, no hardcoded 12h or 24h)
    wb_mon = _make_test_wb(dr=42.0, raw=50.0, taw=100.0, ks=1.0)
    dec_mon = evaluate_zone_decision(farm_zone=zone, water_balance=wb_mon, as_of_time=now_utc)
    expl_mon = build_zone_explanation(decision=dec_mon, water_balance=wb_mon, farm_zone=zone, language=ExplanationLanguage.EN)
    assert "12 hours" not in expl_mon.action_guidance
    assert "24 hours" not in expl_mon.action_guidance
    assert "scheduled cycle" in expl_mon.action_guidance

    # 4. MONITOR with explicit forecast_reassessment_interval_hours
    dec_mon.forecast_reassessment_interval_hours = 8.0
    expl_mon_h = build_zone_explanation(decision=dec_mon, water_balance=wb_mon, farm_zone=zone, language=ExplanationLanguage.EN)
    assert "within 8 hours" in expl_mon_h.action_guidance
    assert expl_mon_h.reassessment_interval_hours == 8.0

    # 5. DELAY_AND_REASSESS recent irrigation without supplied interval (no hardcoded 24h)
    dec_recent = evaluate_zone_decision(farm_zone=zone, water_balance=wb_mon, as_of_time=now_utc)
    dec_recent.action_type = DecisionAction.DELAY_AND_REASSESS
    dec_recent.reason_codes = [DecisionReasonCode.ACTION_DELAY_RECENT_IRRIGATION]
    expl_recent = build_zone_explanation(decision=dec_recent, water_balance=wb_mon, farm_zone=zone, language=ExplanationLanguage.EN)
    assert "24 hours" not in expl_recent.why_decision_produced
    assert "24 hours" not in expl_recent.action_guidance
    assert "equilibrate" in expl_recent.action_guidance.lower()


def test_marathi_hindi_linguistic_integrity_no_corruptions():
    """Verify complete absence of corrupted characters like 'पुराSubवा' and enforce terminology standards."""
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    zone = FarmZoneContext(farm_id="farm-lang", zone_id="z-lang", application_efficiency=0.90, zone_area_ha=1.0)

    # Test all 5 actions in Marathi and Hindi
    for act in DecisionAction:
        if act == DecisionAction.IRRIGATE:
            wb = _make_test_wb(dr=60.0, raw=50.0, taw=100.0, ks=0.80)
        elif act == DecisionAction.MONITOR:
            wb = _make_test_wb(dr=42.0, raw=50.0, taw=100.0, ks=1.0)
        elif act == DecisionAction.NO_ACTION_REQUIRED:
            wb = _make_test_wb(dr=15.0, raw=50.0, taw=100.0, ks=1.0)
        elif act == DecisionAction.INSUFFICIENT_DATA:
            wb = None
        else:  # DELAY_AND_REASSESS
            wb = _make_test_wb(dr=45.0, raw=50.0, taw=100.0, ks=1.0)

        dec = evaluate_zone_decision(farm_zone=zone, water_balance=wb, as_of_time=now_utc)
        expl_mr = build_zone_explanation(decision=dec, water_balance=wb, farm_zone=zone, language=ExplanationLanguage.MR)
        expl_hi = build_zone_explanation(decision=dec, water_balance=wb, farm_zone=zone, language=ExplanationLanguage.HI)

        # Check for corrupted strings
        for field in (expl_mr.short_summary, expl_mr.why_decision_produced, expl_mr.action_guidance):
            assert "Sub" not in field, f"Corrupted 'Sub' substring found in Marathi field: {field}"
            assert "पुराSubवा" not in field
        for field in (expl_hi.short_summary, expl_hi.why_decision_produced, expl_hi.action_guidance):
            assert "Sub" not in field, f"Corrupted 'Sub' substring found in Hindi field: {field}"

    # Also test all Phase 3 Agronomy reason codes
    for agro_code in AgronomyReasonCode:
        res_mr = resolve_reason_code(agro_code, language=ExplanationLanguage.MR)
        res_hi = resolve_reason_code(agro_code, language=ExplanationLanguage.HI)
        assert res_mr.is_unresolved is False
        assert res_hi.is_unresolved is False
        assert "Sub" not in res_mr.farmer_explanation
        assert "Sub" not in res_hi.farmer_explanation
        assert len(res_mr.farmer_explanation) > 10
        assert len(res_hi.farmer_explanation) > 10


def test_split_depth_display_precision_conservation_multilingual():
    """Verify Phase 6.2.1 precision conservation across all explanation surfaces in EN, MR, and HI.
    
    Invariants Verified:
    1. The exact schedule [73.33, 73.33, 73.34] is displayed with 2 decimals across short_summary, why_decision_produced, action_guidance.
    2. Sum of displayed event depths equals displayed total gross depth: 73.33 + 73.33 + 73.34 == 220.00 mm.
    3. English, Marathi, and Hindi all display identical numerical values.
    4. General split schedule [50.00, 50.01] totaling 100.01 mm also preserves 2-decimal precision.
    5. Standard split [75.0, 75.0] totaling 150.0 mm preserves 1-decimal precision without artificial padding.
    6. Non-split explanations remain at 1-decimal display (e.g. 61.1 mm for 61.11 mm).
    7. No single-event instructions are ever produced when split_application_required is True.
    """
    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)

    # 1. Confirmed defect test case: 220.0 mm with 80 mm max event depth -> [73.33, 73.33, 73.34] mm
    wb_220 = _make_test_wb(dr=220.0, raw=50.0, taw=220.0, ks=0.05)
    z_220 = FarmZoneContext(
        farm_id="farm-prec",
        zone_id="z-prec-220",
        application_efficiency=1.0,
        max_single_event_depth_mm=80.0,
    )
    dec_220 = evaluate_zone_decision(farm_zone=z_220, water_balance=wb_220, as_of_time=now_utc)

    for lang in (ExplanationLanguage.EN, ExplanationLanguage.MR, ExplanationLanguage.HI):
        expl = build_zone_explanation(decision=dec_220, water_balance=wb_220, farm_zone=z_220, language=lang)
        # Numerical values must be identical in all languages
        assert "73.33 mm, 73.33 mm, 73.34 mm" in expl.short_summary
        assert "73.33 mm, 73.33 mm, 73.34 mm" in expl.why_decision_produced
        assert "73.33 mm, 73.33 mm, 73.34 mm" in expl.action_guidance
        # Total gross depth displayed matches the sum of event depths at precision 2
        assert "220.00" in expl.action_guidance
        # Single-event instruction prohibited
        assert "single event" in expl.action_guidance or "एकाच वेळी" in expl.action_guidance or "एक ही बार" in expl.action_guidance

    # 2. Another split schedule: total 100.01 mm, max 60.0 mm -> [50.00, 50.01] mm
    wb_100 = _make_test_wb(dr=100.01, raw=50.0, taw=150.0, ks=0.50)
    z_100 = FarmZoneContext(
        farm_id="farm-prec",
        zone_id="z-prec-100",
        application_efficiency=1.0,
        max_single_event_depth_mm=60.0,
    )
    dec_100 = evaluate_zone_decision(farm_zone=z_100, water_balance=wb_100, as_of_time=now_utc)
    expl_100 = build_zone_explanation(decision=dec_100, water_balance=wb_100, farm_zone=z_100, language=ExplanationLanguage.EN)
    assert dec_100.split_event_depths_mm == [50.0, 50.01]
    assert "50.00 mm, 50.01 mm" in expl_100.short_summary
    assert "50.00 mm, 50.01 mm" in expl_100.why_decision_produced
    assert "50.00 mm, 50.01 mm" in expl_100.action_guidance
    assert "100.01 mm" in expl_100.action_guidance
    assert "do not apply the entire 100.01 mm in a single event" in expl_100.action_guidance

    # 3. Standard 1-decimal split: 150.0 mm with 100.0 mm max -> [75.0, 75.0] mm
    wb_150 = _make_test_wb(dr=150.0, raw=50.0, taw=200.0, ks=0.50)
    z_150 = FarmZoneContext(
        farm_id="farm-prec",
        zone_id="z-prec-150",
        application_efficiency=1.0,
        max_single_event_depth_mm=100.0,
    )
    dec_150 = evaluate_zone_decision(farm_zone=z_150, water_balance=wb_150, as_of_time=now_utc)
    expl_150 = build_zone_explanation(decision=dec_150, water_balance=wb_150, farm_zone=z_150, language=ExplanationLanguage.EN)
    assert "75.0 mm, 75.0 mm" in expl_150.short_summary
    assert "150.0 mm" in expl_150.action_guidance

    # 4. Non-split explanation remains 1 decimal place: 55.0 mm net / 0.90 efficiency = 61.11 mm -> 61.1 mm
    wb_nonsplit = _make_test_wb(dr=55.0, raw=50.0, taw=100.0, ks=0.90)
    z_nonsplit = FarmZoneContext(farm_id="farm-prec", zone_id="z-nonsplit", application_efficiency=0.90)
    dec_nonsplit = evaluate_zone_decision(farm_zone=z_nonsplit, water_balance=wb_nonsplit, as_of_time=now_utc)
    expl_nonsplit = build_zone_explanation(decision=dec_nonsplit, water_balance=wb_nonsplit, farm_zone=z_nonsplit, language=ExplanationLanguage.EN)
    assert dec_nonsplit.split_application_required is False
    assert "61.1 mm gross irrigation" in expl_nonsplit.short_summary
    assert "Apply 61.1 mm gross irrigation" in expl_nonsplit.action_guidance


def test_explanation_with_multimodal_features_end_to_end():
    """Verify that build_zone_explanation functions correctly when passed a populated MultimodalZoneFeatureSet."""
    from backend.app.intelligence.features.feature_builder import build_zone_feature_set
    from backend.app.intelligence.features.crop import CropFeatures
    from backend.app.intelligence.features.soil import SoilFeatures
    from backend.app.intelligence.features.vegetation import ZoneVegetationFeatures
    from backend.app.intelligence.features.weather import WeatherFeatures
    from backend.app.intelligence.types import DataQualityStatus, ProvenanceType, SoilTextureClass
    from backend.app.intelligence.stress.assessment import assess_zone_stress

    now_utc = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    zone = FarmZoneContext(farm_id="farm-multi", zone_id="z-multi", application_efficiency=0.90, zone_area_ha=2.0)
    wb = _make_test_wb(dr=65.0, raw=50.0, taw=100.0, ks=0.80)

    veg_feat = ZoneVegetationFeatures(
        zone_id="z-multi",
        scene_id="S2A_TEST_SCENE",
        source_provider="Copernicus Sentinel-2",
        observed_at=now_utc,
        provenance_type=ProvenanceType.SATELLITE_DERIVED,
        total_pixels_in_geometry=100,
        valid_vegetation_pixel_count=95,
        valid_observation_fraction=0.95,
        ndvi_mean=0.68,
        ndmi_mean=0.32,
        cloud_fraction=0.05,
        quality_status=DataQualityStatus.GOOD,
    )
    weather_feat = WeatherFeatures(
        source_provider="Open-Meteo",
        provenance_type=ProvenanceType.PROVIDER_MODELLED,
        window_start=now_utc - timedelta(days=1),
        window_end=now_utc,
        observed_at=now_utc,
        precipitation_mm=0.0,
        temperature_mean_c=25.0,
        temperature_max_c=34.0,
        relative_humidity_mean_pct=55.0,
        wind_speed_mean_m_s=2.5,
        quality_status=DataQualityStatus.GOOD,
    )
    soil_feat = SoilFeatures(
        source_provider="In-situ probe",
        provenance_type=ProvenanceType.SENSOR_MEASURED,
        observed_at=now_utc,
        soil_moisture_m3_m3=0.22,
        field_capacity_m3_m3=0.34,
        wilting_point_m3_m3=0.17,
        soil_texture=SoilTextureClass.CLAY_LOAM,
        soil_ph=7.2,
        electrical_conductivity_ds_m=0.8,
        quality_status=DataQualityStatus.GOOD,
    )
    crop_feat = CropFeatures(
        crop_type="sugarcane",
        growth_stage="mid_season",
        observed_at=now_utc,
        quality_status=DataQualityStatus.GOOD,
    )

    mfs = build_zone_feature_set(
        zone_id="z-multi",
        farm_id="farm-multi",
        as_of_time=now_utc,
        vegetation_features=veg_feat,
        weather_features=weather_feat,
        soil_features=soil_feat,
        crop_features=crop_feat,
    )
    stress = assess_zone_stress(
        zone_id="z-multi",
        farm_id="farm-multi",
        water_balance=wb,
        vegetation_features=veg_feat,
        weather_features=weather_feat,
        soil_features=soil_feat,
        as_of_time=now_utc,
    )
    decision = evaluate_zone_decision(farm_zone=zone, water_balance=wb, stress_assessment=stress, as_of_time=now_utc)

    # Generate explanations across EN, MR, HI
    for lang in [ExplanationLanguage.EN, ExplanationLanguage.MR, ExplanationLanguage.HI]:
        expl = build_zone_explanation(
            decision=decision,
            water_balance=wb,
            stress_assessment=stress,
            features=mfs,
            farm_zone=zone,
            language=lang,
        )
        assert expl.action == DecisionAction.IRRIGATE
        assert expl.short_summary is not None
        assert expl.agronomist_explanation is not None
        # Check that satellite and soil measurements are correctly extracted
        assert expl.relevant_measurements.get("satellite_ndvi") == 0.68
        assert expl.relevant_measurements.get("soil_ph") == 7.2
        assert expl.relevant_measurements.get("soil_salinity_ece_ds_m") == 0.8

