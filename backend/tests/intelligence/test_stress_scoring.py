"""Tests for domain stress scoring, diagnostic reason codes, and multi-criteria synthesis."""

import pytest

from backend.app.intelligence.stress.indicators import (
    SoilConditionIndicators,
    VegetationStressIndicators,
    WaterStressIndicators,
    WeatherStressIndicators,
)
from backend.app.intelligence.stress.scoring import (
    DomainStressEvaluation,
    StressReasonCode,
    evaluate_soil_stress_domain,
    evaluate_vegetation_stress_domain,
    evaluate_water_stress_domain,
    evaluate_weather_stress_domain,
    synthesize_overall_stress_status,
)
from backend.app.intelligence.types import DataQualityStatus, StressStatus


# ==============================================================================
# 1. WATER DOMAIN SCORING TESTS
# ==============================================================================

def test_water_domain_scoring_depletion_normal():
    """Verify water domain produces HEALTHY when Dr < 0.8 * RAW (Ks = 1.0)."""
    ind = WaterStressIndicators(
        depletion_mm=25.0,
        readily_available_water_mm=50.0,
        total_available_water_mm=100.0,
        water_stress_coefficient_ks=1.0,
        is_depletion_exceeding_raw=False,
        is_approaching_raw=False,
        is_wilting_point_reached=False,
        quality_status=DataQualityStatus.GOOD,
    )
    ev = evaluate_water_stress_domain(ind)
    assert ev.domain == "water"
    assert ev.status == StressStatus.HEALTHY
    assert ev.stress_detected is False
    assert ev.continuous_severity == 0.0
    assert StressReasonCode.WATER_DEPLETION_NORMAL in ev.reason_codes


def test_water_domain_scoring_approaching_raw():
    """Verify water domain produces MONITOR when 0.8 * RAW <= Dr <= RAW."""
    ind = WaterStressIndicators(
        depletion_mm=45.0,
        readily_available_water_mm=50.0,
        total_available_water_mm=100.0,
        water_stress_coefficient_ks=1.0,
        is_depletion_exceeding_raw=False,
        is_approaching_raw=True,
        is_wilting_point_reached=False,
        quality_status=DataQualityStatus.GOOD,
    )
    ev = evaluate_water_stress_domain(ind)
    assert ev.status == StressStatus.MONITOR
    assert ev.stress_detected is False
    assert StressReasonCode.WATER_DEPLETION_APPROACHING_RAW in ev.reason_codes


def test_water_domain_scoring_depletion_exceeds_raw():
    """Verify water domain produces ATTENTION when Dr > RAW (Ks in [0.50, 1.0))."""
    ind = WaterStressIndicators(
        depletion_mm=65.0,
        readily_available_water_mm=50.0,
        total_available_water_mm=100.0,
        water_stress_coefficient_ks=0.70,
        is_depletion_exceeding_raw=True,
        is_approaching_raw=False,
        is_wilting_point_reached=False,
        quality_status=DataQualityStatus.GOOD,
    )
    ev = evaluate_water_stress_domain(ind)
    assert ev.status == StressStatus.ATTENTION
    assert ev.stress_detected is True
    assert ev.continuous_severity == 0.30
    assert StressReasonCode.WATER_DEPLETION_EXCEEDS_RAW in ev.reason_codes
    assert StressReasonCode.WATER_STRESS_KS_REDUCED in ev.reason_codes


def test_water_domain_scoring_severe_wilting_point():
    """Verify water domain produces HIGH_STRESS when wilting point is reached (Dr >= TAW, Ks = 0.0)."""
    ind = WaterStressIndicators(
        depletion_mm=105.0,
        readily_available_water_mm=50.0,
        total_available_water_mm=100.0,
        water_stress_coefficient_ks=0.0,
        is_depletion_exceeding_raw=True,
        is_approaching_raw=False,
        is_wilting_point_reached=True,
        quality_status=DataQualityStatus.GOOD,
    )
    ev = evaluate_water_stress_domain(ind)
    assert ev.status == StressStatus.HIGH_STRESS
    assert ev.stress_detected is True
    assert ev.continuous_severity == 1.0
    assert StressReasonCode.SEVERE_DEPLETION_AT_WILTING_POINT in ev.reason_codes


def test_water_domain_scoring_missing_evidence():
    """Verify water domain produces INSUFFICIENT_DATA when water balance is missing."""
    ind = WaterStressIndicators(
        quality_status=DataQualityStatus.INSUFFICIENT,
    )
    ev = evaluate_water_stress_domain(ind)
    assert ev.status == StressStatus.INSUFFICIENT_DATA
    assert ev.stress_detected is None
    assert ev.continuous_severity is None
    assert StressReasonCode.WATER_BALANCE_INSUFFICIENT in ev.reason_codes


# ==============================================================================
# 2. VEGETATION DOMAIN SCORING TESTS
# ==============================================================================

def test_vegetation_domain_scoring_healthy_vs_anomaly():
    """Verify vegetation domain evaluates canopy anomaly against baseline."""
    # Case A: Healthy (NDVI consistent with baseline)
    ind_healthy = VegetationStressIndicators(
        ndvi_median=0.60,
        baseline_ndvi=0.62,
        ndvi_anomaly=-0.02,
        has_valid_baseline=True,
        quality_status=DataQualityStatus.GOOD,
    )
    ev_h = evaluate_vegetation_stress_domain(ind_healthy)
    assert ev_h.status == StressStatus.HEALTHY
    assert StressReasonCode.VEGETATION_CANOPY_HEALTHY in ev_h.reason_codes

    # Case B: Significant negative anomaly (< -0.15) -> ATTENTION
    ind_anomaly = VegetationStressIndicators(
        ndvi_median=0.40,
        baseline_ndvi=0.60,
        ndvi_anomaly=-0.20,
        has_valid_baseline=True,
        quality_status=DataQualityStatus.GOOD,
    )
    ev_a = evaluate_vegetation_stress_domain(ind_anomaly)
    assert ev_a.status == StressStatus.ATTENTION
    assert ev_a.stress_detected is True
    assert StressReasonCode.VEGETATION_ANOMALY_NEGATIVE in ev_a.reason_codes


def test_vegetation_domain_scoring_missing_baseline_or_cloudy():
    """Verify vegetation domain produces INSUFFICIENT_DATA on missing baseline or clouds."""
    # Missing baseline
    ind_no_base = VegetationStressIndicators(
        ndvi_median=0.45,
        has_valid_baseline=False,
        quality_status=DataQualityStatus.GOOD,
    )
    ev_nb = evaluate_vegetation_stress_domain(ind_no_base)
    assert ev_nb.status == StressStatus.INSUFFICIENT_DATA
    assert StressReasonCode.VEGETATION_BASELINE_MISSING in ev_nb.reason_codes

    # Cloud contaminated
    ind_cloudy = VegetationStressIndicators(
        ndvi_median=0.25,
        has_valid_baseline=True,
        is_suspect=True,
        quality_status=DataQualityStatus.CLOUD_CONTAMINATED,
    )
    ev_c = evaluate_vegetation_stress_domain(ind_cloudy)
    assert ev_c.status == StressStatus.INSUFFICIENT_DATA
    assert ev_c.is_suspect is True
    assert StressReasonCode.VEGETATION_SCL_CONTAMINATED in ev_c.reason_codes


# ==============================================================================
# 3. WEATHER DOMAIN SCORING TESTS
# ==============================================================================

def test_weather_domain_scoring_heat_and_vpd():
    """Verify weather domain evaluates prolonged heat, high VPD, and dry spells."""
    # Prolonged heat -> HIGH_STRESS
    ind_heat = WeatherStressIndicators(
        temperature_max_c=39.0,
        is_prolonged_heat_stress=True,
        quality_status=DataQualityStatus.GOOD,
    )
    ev_heat = evaluate_weather_stress_domain(ind_heat)
    assert ev_heat.status == StressStatus.HIGH_STRESS
    assert StressReasonCode.WEATHER_HEAT_STRESS_PROLONGED in ev_heat.reason_codes

    # High VPD -> MONITOR
    ind_vpd = WeatherStressIndicators(
        temperature_max_c=31.0,
        vapor_pressure_deficit_kpa=2.45,
        is_high_vpd_stress=True,
        is_prolonged_heat_stress=False,
        quality_status=DataQualityStatus.GOOD,
    )
    ev_vpd = evaluate_weather_stress_domain(ind_vpd)
    assert ev_vpd.status == StressStatus.MONITOR
    assert StressReasonCode.WEATHER_HIGH_VAPOR_PRESSURE_DEFICIT in ev_vpd.reason_codes


# ==============================================================================
# 4. SOIL DOMAIN SCORING TESTS
# ==============================================================================

def test_soil_domain_scoring_salinity_and_ph():
    """Verify soil domain evaluates salinity hazard and pH extremes."""
    # Severe salinity -> HIGH_STRESS
    ind_saline = SoilConditionIndicators(
        electrical_conductivity_ds_m=9.2,
        salinity_hazard_level="severe",
        is_salinity_stress=True,
        quality_status=DataQualityStatus.GOOD,
    )
    ev_saline = evaluate_soil_stress_domain(ind_saline)
    assert ev_saline.status == StressStatus.HIGH_STRESS
    assert StressReasonCode.SOIL_SALINITY_SEVERE in ev_saline.reason_codes

    # Strongly alkaline sodic pH -> ATTENTION
    ind_alkaline = SoilConditionIndicators(
        soil_ph=8.9,
        ph_classification="strongly_alkaline_sodic",
        is_ph_stress=True,
        quality_status=DataQualityStatus.GOOD,
    )
    ev_alk = evaluate_soil_stress_domain(ind_alkaline)
    assert ev_alk.status == StressStatus.ATTENTION
    assert StressReasonCode.SOIL_PH_ALKALINE in ev_alk.reason_codes


# ==============================================================================
# 5. MULTIMODAL SYNTHESIS TESTS
# ==============================================================================

def test_multimodal_synthesis_hierarchy():
    """Verify multi-criteria synthesis respects priority hierarchy without forced single score."""
    water_att = DomainStressEvaluation(
        domain="water",
        status=StressStatus.ATTENTION,
        stress_detected=True,
        continuous_severity=0.40,
        reason_codes=[StressReasonCode.WATER_DEPLETION_EXCEEDS_RAW],
    )
    veg_healthy = DomainStressEvaluation(
        domain="vegetation",
        status=StressStatus.HEALTHY,
        stress_detected=False,
        reason_codes=[StressReasonCode.VEGETATION_CANOPY_HEALTHY],
    )
    weath_monitor = DomainStressEvaluation(
        domain="weather",
        status=StressStatus.MONITOR,
        stress_detected=True,
        reason_codes=[StressReasonCode.WEATHER_HIGH_VAPOR_PRESSURE_DEFICIT],
    )
    soil_healthy = DomainStressEvaluation(
        domain="soil",
        status=StressStatus.HEALTHY,
        stress_detected=False,
        reason_codes=[StressReasonCode.SOIL_CONDITIONS_OPTIMAL],
    )

    evals = {
        "water": water_att,
        "vegetation": veg_healthy,
        "weather": weath_monitor,
        "soil": soil_healthy,
    }

    status, quality, reasons = synthesize_overall_stress_status(evals)

    # Attention takes priority over monitor and healthy
    assert status == StressStatus.ATTENTION
    assert quality == DataQualityStatus.GOOD
    assert StressReasonCode.WATER_DEPLETION_EXCEEDS_RAW in reasons
    assert StressReasonCode.WEATHER_HIGH_VAPOR_PRESSURE_DEFICIT in reasons


def test_multimodal_synthesis_missing_water_balance_cannot_be_healthy():
    """Verify that a zone with missing water balance is NEVER classified as HEALTHY."""
    water_missing = DomainStressEvaluation(
        domain="water",
        status=StressStatus.INSUFFICIENT_DATA,
        stress_detected=None,
        quality_status=DataQualityStatus.INSUFFICIENT,
        reason_codes=[StressReasonCode.WATER_BALANCE_INSUFFICIENT],
    )
    veg_healthy = DomainStressEvaluation(
        domain="vegetation",
        status=StressStatus.HEALTHY,
        stress_detected=False,
        reason_codes=[StressReasonCode.VEGETATION_CANOPY_HEALTHY],
    )
    weath_healthy = DomainStressEvaluation(
        domain="weather",
        status=StressStatus.HEALTHY,
        stress_detected=False,
        reason_codes=[StressReasonCode.WEATHER_CONDITIONS_FAVORABLE],
    )

    evals = {
        "water": water_missing,
        "vegetation": veg_healthy,
        "weather": weath_healthy,
    }

    status, quality, reasons = synthesize_overall_stress_status(evals)

    # Cannot be HEALTHY because primary irrigation water balance is absent!
    assert status == StressStatus.INSUFFICIENT_DATA
    assert quality == DataQualityStatus.PARTIAL
    assert StressReasonCode.WATER_BALANCE_INSUFFICIENT in reasons

