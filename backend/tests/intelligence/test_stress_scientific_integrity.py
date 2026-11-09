"""Phase 4.1 Scientific Integrity Tests for Multimodal Stress Assessment.

Validates the 12 targeted integrity requirements:
1. NDVI threshold anomaly vs statistical significance.
2. Historical baseline insufficiency (missing variance or sample size).
3. High pH (> 8.5) without SAR/ESP classified as strongly alkaline, not sodic.
4. Sodic hazard confirmed only with sufficient sodium evidence (SAR >= 13 or ESP >= 15%).
5. VPD threshold marked provisional operational warning.
6. Heat threshold crop-stage and duration applicability (wheat 32°C vs cotton 38°C).
7. Configurable satellite quality thresholds.
8. Cloud shadow (SCL 2) vs cast/topographic shadow (SCL 3) distinction.
9. Crop-specific salinity interpretation.
10. Low AWC marked as storage constraint without active water stress or inferred texture.
11. Absence of composite numerical score and absence of priority ranking.
12. Overall status aggregation with incomplete evidence.
"""

from datetime import datetime, timezone
import math
import pytest

from backend.app.intelligence.agronomy.water_balance import (
    SoilWaterCapacities,
    WaterBalanceRainfallMode,
    WaterBalanceResult,
)
from backend.app.intelligence.features.soil import SoilFeatures
from backend.app.intelligence.features.vegetation import ZoneVegetationFeatures
from backend.app.intelligence.features.weather import WeatherFeatures
from backend.app.intelligence.geospatial.grid_alignment import (
    SCL_CLASS_DESCRIPTIONS,
    ZoneSCLBreakdown,
    compute_zone_scl_breakdown,
)
from backend.app.intelligence.stress.assessment import (
    ZoneStressAssessment,
    assess_zone_stress,
)
from backend.app.intelligence.stress.indicators import (
    CITATION_HEAT_STRESS_COTTON,
    CITATION_HEAT_STRESS_WHEAT,
    CITATION_VPD_DEMAND,
    CITATION_VPD_FAO56_PAIRED,
    CITATION_VPD_FAO56_RH_MAX_MIN,
    CITATION_VPD_FAO56_RH_MEAN,
    CropStressThresholds,
    HypothesisTestConvention,
    SoilConditionIndicators,
    VegetationHistoricalBaseline,
    VegetationStressIndicators,
    VPDCalculationMethod,
    calculate_soil_condition_indicators,
    calculate_vapor_pressure_deficit,
    calculate_vapor_pressure_deficit_diurnal_proxy,
    calculate_vapor_pressure_deficit_fao56_mean_rh,
    calculate_vapor_pressure_deficit_fao56_rh_max_min,
    calculate_vapor_pressure_deficit_paired,
    calculate_vegetation_stress_indicators,
    calculate_weather_stress_indicators,
    get_student_t_critical_value,
    resolve_scl_class_2_label,
    resolve_scl_class_2_semantics,
)
from backend.app.intelligence.stress.scoring import (
    DomainStressEvaluation,
    StressReasonCode,
    evaluate_soil_stress_domain,
    evaluate_vegetation_stress_domain,
    evaluate_weather_stress_domain,
    synthesize_overall_stress_status,
)
from backend.app.intelligence.types import (
    DataQualityStatus,
    ProvenanceType,
    StressStatus,
    WeatherWindowType,
)


def _make_sample_water_balance(dr: float, raw: float = 50.0, taw: float = 100.0) -> WaterBalanceResult:
    caps = SoilWaterCapacities(
        field_capacity_m3_m3=0.350,
        wilting_point_m3_m3=0.150,
        available_water_capacity_m3_m3=0.200,
        effective_rooting_depth_m=0.5,
        depletion_fraction_p=raw / taw,
        depletion_fraction_p_table=0.50,
        total_available_water_mm=taw,
        readily_available_water_mm=raw,
    )
    if dr <= raw:
        ks = 1.0
    elif dr >= taw:
        ks = 0.0
    else:
        ks = (taw - dr) / (taw - raw)

    return WaterBalanceResult(
        rainfall_mode=WaterBalanceRainfallMode.PHYSICAL,
        soil_capacities=caps,
        initial_depletion_mm=dr,
        final_depletion_mm=dr,
        crop_evapotranspiration_mm=4.0,
        adjusted_crop_evapotranspiration_mm=round(4.0 * ks, 2),
        water_stress_coefficient_ks=round(ks, 3),
        total_available_water_mm=taw,
        readily_available_water_mm=raw,
        root_zone_moisture_m3_m3=round(0.350 - (dr / 1000.0) / 0.5, 4),
        is_in_stress_zone=(dr > raw),
        stress_deficit_mm=max(0.0, dr - raw),
        quality_status=DataQualityStatus.GOOD,
    )


# ==============================================================================
# 1. NDVI THRESHOLD ANOMALY VS STATISTICAL SIGNIFICANCE
# ==============================================================================

def test_ndvi_threshold_anomaly_vs_statistical_significance():
    """Verify distinction between formal hypothesis test (N >= 10, df >= 9) and descriptive z-score (N < 10)."""
    veg = ZoneVegetationFeatures(
        scene_id="S2A_TEST_01",
        observed_at=datetime(2026, 7, 15, 10, 30, tzinfo=timezone.utc),
        ndvi_mean=0.45,
        ndvi_median=0.45,
        vegetation_coverage_fraction=0.85,
        cloud_fraction=0.01,
        shadow_fraction=0.01,
        valid_observation_fraction=0.98,
        total_pixels_in_geometry=100,
        valid_vegetation_pixel_count=85,
        quality_status=DataQualityStatus.GOOD,
    )

    # Case A: Adequate sample size (N = 12 >= 10, df = 11), documented variance (std = 0.05)
    # Anomaly = 0.45 - 0.60 = -0.15. t = -0.15 / (0.05 * sqrt(1 + 1/12)) = -2.879 <= -2.262
    robust_baseline = VegetationHistoricalBaseline(
        crop_type="wheat",
        baseline_ndvi=0.60,
        baseline_std=0.05,
        sample_size_years=12,
        is_valid=True,
        baseline_source="12-year zone historical median",
    )
    assert robust_baseline.is_statistically_robust is True
    assert robust_baseline.degrees_of_freedom == 11

    ind_robust = calculate_vegetation_stress_indicators(veg, baseline=robust_baseline)
    assert ind_robust.z_score == -3.0
    assert ind_robust.is_statistically_significant_anomaly is True
    assert ind_robust.is_material_vegetation_decline is True
    assert ind_robust.statistical_test_details is not None
    assert ind_robust.statistical_test_details["sample_size_N"] == 12
    assert ind_robust.statistical_test_details["degrees_of_freedom"] == 11
    assert ind_robust.statistical_test_details["sample_standard_deviation_s"] == 0.05
    assert pytest.approx(ind_robust.statistical_test_details["prediction_standard_error_se"], abs=1e-3) == 0.052
    assert ind_robust.statistical_test_details["t_critical_alpha_0_05"] == 2.201
    assert ind_robust.statistical_test_details["quantile_used"] == "t_0.975"
    assert ind_robust.statistical_test_details["assumed_distribution"] == "normal"
    assert "operational threshold" in ind_robust.statistical_test_details["operational_minimum_sample_policy"].lower()

    ev_robust = evaluate_vegetation_stress_domain(ind_robust)
    assert ev_robust.status == StressStatus.ATTENTION
    assert StressReasonCode.VEGETATION_STATISTICAL_ANOMALY in ev_robust.reason_codes
    assert StressReasonCode.VEGETATION_MATERIAL_DECLINE in ev_robust.reason_codes

    # Case B: Small sample size (N = 5 < 10, df = 4)
    # Standardized anomaly (z = -3.0) is retained, but formal statistical significance is SUPPRESSED.
    small_baseline = VegetationHistoricalBaseline(
        crop_type="wheat",
        baseline_ndvi=0.60,
        baseline_std=0.05,
        sample_size_years=5,
        is_valid=True,
        baseline_source="5-year zone historical median",
    )
    assert small_baseline.is_statistically_robust is False
    assert small_baseline.degrees_of_freedom == 4

    ind_small = calculate_vegetation_stress_indicators(veg, baseline=small_baseline)
    assert ind_small.z_score == -3.0  # Descriptive standardized anomaly is kept
    assert ind_small.is_statistically_significant_anomaly is None  # Formal significance is suppressed!
    assert ind_small.is_material_vegetation_decline is True  # Threshold check still applies
    assert any("DESCRIPTIVE STANDARDIZED ANOMALY ONLY" in note for note in ind_small.audit_trail)
    assert any("claiming statistical significance from z <= -2 is scientifically invalid" in note for note in ind_small.audit_trail)

    ev_small = evaluate_vegetation_stress_domain(ind_small)
    assert StressReasonCode.VEGETATION_STATISTICAL_ANOMALY not in ev_small.reason_codes
    assert StressReasonCode.VEGETATION_MATERIAL_DECLINE in ev_small.reason_codes


def test_student_t_critical_values_and_both_hypothesis_conventions():
    """Independent numerical test verifying Student's t critical values, SE_pred, and one-sided vs two-sided testing."""
    # 1. Independent numerical check of t critical values
    # One-sided lower tail alpha=0.05 uses 0.95 quantile (t_0.95)
    assert get_student_t_critical_value(9, alpha=0.05, two_sided=False) == 1.833   # N = 10
    assert get_student_t_critical_value(11, alpha=0.05, two_sided=False) == 1.796  # N = 12
    assert get_student_t_critical_value(20, alpha=0.05, two_sided=False) == 1.725  # N = 21
    assert get_student_t_critical_value(30, alpha=0.05, two_sided=False) == 1.697
    assert pytest.approx(get_student_t_critical_value(60, alpha=0.05, two_sided=False), abs=0.01) == 1.671
    assert pytest.approx(get_student_t_critical_value(120, alpha=0.05, two_sided=False), abs=0.01) == 1.658

    # Two-sided alpha=0.05 uses 0.975 quantile (t_0.975)
    assert get_student_t_critical_value(9, alpha=0.05, two_sided=True) == 2.262   # N = 10
    assert get_student_t_critical_value(11, alpha=0.05, two_sided=True) == 2.201  # N = 12
    assert get_student_t_critical_value(20, alpha=0.05, two_sided=True) == 2.086  # N = 21
    assert get_student_t_critical_value(30, alpha=0.05, two_sided=True) == 2.042
    assert pytest.approx(get_student_t_critical_value(60, alpha=0.05, two_sided=True), abs=0.01) == 2.000
    assert pytest.approx(get_student_t_critical_value(120, alpha=0.05, two_sided=True), abs=0.01) == 1.980

    # 2. Independent numerical test for SE_pred and one-sided vs two-sided hypothesis tests:
    # N = 12, df = 11, s = 0.05.
    # Prediction SE = s * sqrt(1 + 1/N) = 0.05 * sqrt(13/12) = 0.0520416...
    # Baseline NDVI = 0.60. Set observed NDVI = 0.4959 -> diff = -0.1041.
    # t_stat = -0.1041 / 0.0520416 = -2.000.
    # For df = 11:
    # - One-sided lower tail critical boundary: t <= -1.796.
    #   Since -2.000 <= -1.796 -> REJECTS H0 (one-sided is statistically significant!).
    # - Two-sided critical boundary: t <= -2.201.
    #   Since -2.000 > -2.201 -> FAILS TO REJECT H0 (two-sided is NOT statistically significant!).
    veg_test = ZoneVegetationFeatures(
        scene_id="S2A_TEST_NUMERICAL",
        observed_at=datetime(2026, 7, 15, 10, 30, tzinfo=timezone.utc),
        ndvi_mean=0.4959,
        ndvi_median=0.4959,
        vegetation_coverage_fraction=0.85,
        valid_observation_fraction=0.95,
        total_pixels_in_geometry=100,
        valid_vegetation_pixel_count=85,
        quality_status=DataQualityStatus.GOOD,
    )
    baseline_12yr = VegetationHistoricalBaseline(
        crop_type="cotton",
        growth_stage="flowering",
        baseline_ndvi=0.60,
        baseline_std=0.05,
        sample_size_years=12,
        is_valid=True,
        baseline_source="12-year flowering baseline",
    )

    # Test Convention A: ONE-SIDED LOWER TAIL (H1: mu_new < mu_0, uses t_0.95 = 1.796)
    ind_one_sided = calculate_vegetation_stress_indicators(
        veg_test,
        growth_stage="flowering",
        baseline=baseline_12yr,
        hypothesis_test_convention=HypothesisTestConvention.ONE_SIDED_LOWER,
    )
    assert ind_one_sided.statistical_test_details["t_statistic"] == -2.0
    assert ind_one_sided.statistical_test_details["t_critical_alpha_0_05"] == 1.796
    assert ind_one_sided.statistical_test_details["quantile_used"] == "t_0.95"
    assert "one-sided lower tail" in ind_one_sided.statistical_test_details["alternative_hypothesis"].lower()
    assert ind_one_sided.is_statistically_significant_anomaly is True  # -2.00 <= -1.796 -> REJECTS H0!

    # Test Convention B: TWO-SIDED (H1: mu_new != mu_0, uses t_0.975 = 2.201)
    ind_two_sided = calculate_vegetation_stress_indicators(
        veg_test,
        growth_stage="flowering",
        baseline=baseline_12yr,
        hypothesis_test_convention=HypothesisTestConvention.TWO_SIDED,
    )
    assert ind_two_sided.statistical_test_details["t_statistic"] == -2.0
    assert ind_two_sided.statistical_test_details["t_critical_alpha_0_05"] == 2.201
    assert ind_two_sided.statistical_test_details["quantile_used"] == "t_0.975"
    assert "two-sided" in ind_two_sided.statistical_test_details["alternative_hypothesis"].lower()
    assert ind_two_sided.is_statistically_significant_anomaly is False  # -2.00 > -2.201 -> FAILS TO REJECT!

    # 3. Operational sample size policy: N = 9 (df = 8) is suppressed even with std > 0
    baseline_9yr = VegetationHistoricalBaseline(
        crop_type="cotton",
        growth_stage="flowering",
        baseline_ndvi=0.60,
        baseline_std=0.05,
        sample_size_years=9,  # < 10 operational threshold
        is_valid=True,
        baseline_source="9-year flowering baseline",
    )
    assert baseline_9yr.is_statistically_robust is False
    assert baseline_9yr.degrees_of_freedom == 8
    ind_9yr = calculate_vegetation_stress_indicators(veg_test, growth_stage="flowering", baseline=baseline_9yr)
    assert ind_9yr.is_statistically_significant_anomaly is None
    assert ind_9yr.z_score is not None  # Descriptive standardized anomaly preserved
    assert any("operational minimum-sample policy" in note for note in ind_9yr.audit_trail)


def test_student_t_hypothesis_testing_rigorous_cases():
    """Verify Student's t hypothesis testing across large negative, large positive, small, boundary, and invalid cases."""
    # Setup baseline: N = 12 years, df = 11, s = 0.05, baseline_ndvi = 0.60
    # SE_pred = s * sqrt(1 + 1/N) = 0.05 * sqrt(13/12) = 0.0520416...
    # For df = 11:
    #   t_0.95 = 1.796 (one-sided lower tail critical boundary: t <= -1.796)
    #   t_0.975 = 2.201 (two-sided critical boundary: |t| >= 2.201)
    se_pred = 0.05 * math.sqrt(13.0 / 12.0)
    baseline_12yr = VegetationHistoricalBaseline(
        crop_type="cotton",
        growth_stage="flowering",
        baseline_ndvi=0.60,
        baseline_std=0.05,
        sample_size_years=12,
        is_valid=True,
        baseline_source="12-year flowering baseline",
    )

    def _make_veg(ndvi_val: float) -> ZoneVegetationFeatures:
        return ZoneVegetationFeatures(
            scene_id="S2A_TEST_T_RIGOROUS",
            observed_at=datetime(2026, 7, 15, 10, 30, tzinfo=timezone.utc),
            ndvi_mean=ndvi_val,
            ndvi_median=ndvi_val,
            vegetation_coverage_fraction=0.85,
            valid_observation_fraction=0.95,
            total_pixels_in_geometry=100,
            valid_vegetation_pixel_count=85,
            quality_status=DataQualityStatus.GOOD,
        )

    # 1. Large negative t: detected by both tests (t = -3.50)
    # diff = -3.50 * se_pred = -3.50 * 0.0520416 = -0.1821456 -> ndvi = 0.60 - 0.1821456 = 0.41785
    veg_neg = _make_veg(0.41785)
    ind_neg_one = calculate_vegetation_stress_indicators(
        veg_neg,
        growth_stage="flowering",
        baseline=baseline_12yr,
        hypothesis_test_convention=HypothesisTestConvention.ONE_SIDED_LOWER,
    )
    ind_neg_two = calculate_vegetation_stress_indicators(
        veg_neg,
        growth_stage="flowering",
        baseline=baseline_12yr,
        hypothesis_test_convention=HypothesisTestConvention.TWO_SIDED,
    )
    assert ind_neg_one.statistical_test_details["t_statistic"] == -3.5
    assert ind_neg_one.is_statistically_significant_anomaly is True
    assert ind_neg_one.is_statistically_significant_decline is True

    assert ind_neg_two.statistical_test_details["t_statistic"] == -3.5
    assert ind_neg_two.is_statistically_significant_anomaly is True
    assert ind_neg_two.is_statistically_significant_decline is True

    # Check reason codes for large negative: lower vegetation decline
    ev_neg_one = evaluate_vegetation_stress_domain(ind_neg_one)
    assert StressReasonCode.VEGETATION_STATISTICAL_ANOMALY in ev_neg_one.reason_codes
    assert StressReasonCode.VEGETATION_STATISTICAL_DECLINE in ev_neg_one.reason_codes
    assert StressReasonCode.VEGETATION_ANOMALY_NEGATIVE in ev_neg_one.reason_codes
    assert ev_neg_one.status == StressStatus.ATTENTION
    assert ev_neg_one.stress_detected is True

    ev_neg_two = evaluate_vegetation_stress_domain(ind_neg_two)
    assert StressReasonCode.VEGETATION_STATISTICAL_ANOMALY in ev_neg_two.reason_codes
    assert StressReasonCode.VEGETATION_STATISTICAL_DECLINE in ev_neg_two.reason_codes
    assert StressReasonCode.VEGETATION_ANOMALY_NEGATIVE in ev_neg_two.reason_codes
    assert ev_neg_two.status == StressStatus.ATTENTION
    assert ev_neg_two.stress_detected is True

    # 2. Large positive t: detected by two-sided test but NOT lower-tail test (t = +3.50)
    # diff = +3.50 * se_pred = +0.1821456 -> ndvi = 0.60 + 0.1821456 = 0.78215
    veg_pos = _make_veg(0.78215)
    ind_pos_one = calculate_vegetation_stress_indicators(
        veg_pos,
        growth_stage="flowering",
        baseline=baseline_12yr,
        hypothesis_test_convention=HypothesisTestConvention.ONE_SIDED_LOWER,
    )
    ind_pos_two = calculate_vegetation_stress_indicators(
        veg_pos,
        growth_stage="flowering",
        baseline=baseline_12yr,
        hypothesis_test_convention=HypothesisTestConvention.TWO_SIDED,
    )
    # One-sided lower tail checks t <= -1.796; here t = +3.5 -> NOT significant
    assert ind_pos_one.statistical_test_details["t_statistic"] == 3.5
    assert ind_pos_one.is_statistically_significant_anomaly is False
    assert ind_pos_one.is_statistically_significant_decline is False

    # Two-sided checks |t| >= 2.201; here |+3.5| >= 2.201 -> REJECTS H0!
    assert ind_pos_two.statistical_test_details["t_statistic"] == 3.5
    assert ind_pos_two.is_statistically_significant_anomaly is True
    assert ind_pos_two.is_statistically_significant_decline is False  # NOT a lower decline

    # Reason codes for large positive: positive anomaly, not decline
    ev_pos_two = evaluate_vegetation_stress_domain(ind_pos_two)
    assert StressReasonCode.VEGETATION_STATISTICAL_ANOMALY in ev_pos_two.reason_codes
    assert StressReasonCode.VEGETATION_ANOMALY_POSITIVE in ev_pos_two.reason_codes
    assert StressReasonCode.VEGETATION_STATISTICAL_DECLINE not in ev_pos_two.reason_codes
    assert StressReasonCode.VEGETATION_ANOMALY_NEGATIVE not in ev_pos_two.reason_codes
    assert ev_pos_two.stress_detected is False  # Positive greenness is not water stress

    # 3. Small absolute t: not detected by either test (t = -0.30)
    # diff = -0.30 * se_pred = -0.01561 -> ndvi = 0.60 - 0.01561 = 0.58439
    veg_small = _make_veg(0.58439)
    ind_small_one = calculate_vegetation_stress_indicators(
        veg_small,
        growth_stage="flowering",
        baseline=baseline_12yr,
        hypothesis_test_convention=HypothesisTestConvention.ONE_SIDED_LOWER,
    )
    ind_small_two = calculate_vegetation_stress_indicators(
        veg_small,
        growth_stage="flowering",
        baseline=baseline_12yr,
        hypothesis_test_convention=HypothesisTestConvention.TWO_SIDED,
    )
    assert ind_small_one.is_statistically_significant_anomaly is False
    assert ind_small_two.is_statistically_significant_anomaly is False

    # 4. Exact critical-value boundary behaviour (df = 11, t_0.95 = 1.796, t_0.975 = 2.201)
    # 4a. Exactly at one-sided lower boundary: t = -1.796 (inclusive <=)
    diff_exact_one = -1.796 * se_pred
    veg_b_one = _make_veg(0.60 + diff_exact_one)
    ind_b_one = calculate_vegetation_stress_indicators(
        veg_b_one,
        growth_stage="flowering",
        baseline=baseline_12yr,
        hypothesis_test_convention=HypothesisTestConvention.ONE_SIDED_LOWER,
    )
    assert ind_b_one.statistical_test_details["t_statistic"] == -1.796
    assert ind_b_one.is_statistically_significant_anomaly is True  # -1.796 <= -1.796 is True

    # 4b. Just inside one-sided boundary: t = -1.795
    diff_inside_one = -1.795 * se_pred
    veg_in_one = _make_veg(0.60 + diff_inside_one)
    ind_in_one = calculate_vegetation_stress_indicators(
        veg_in_one,
        growth_stage="flowering",
        baseline=baseline_12yr,
        hypothesis_test_convention=HypothesisTestConvention.ONE_SIDED_LOWER,
    )
    assert ind_in_one.statistical_test_details["t_statistic"] == -1.795
    assert ind_in_one.is_statistically_significant_anomaly is False  # -1.795 > -1.796 is False

    # 4c. Exactly at two-sided positive boundary: t = +2.201 (inclusive >=)
    diff_exact_two_pos = +2.201 * se_pred
    veg_b_two_pos = _make_veg(0.60 + diff_exact_two_pos)
    ind_b_two_pos = calculate_vegetation_stress_indicators(
        veg_b_two_pos,
        growth_stage="flowering",
        baseline=baseline_12yr,
        hypothesis_test_convention=HypothesisTestConvention.TWO_SIDED,
    )
    assert ind_b_two_pos.statistical_test_details["t_statistic"] == 2.201
    assert ind_b_two_pos.is_statistically_significant_anomaly is True  # |2.201| >= 2.201 is True

    # 4d. Just inside two-sided positive boundary: t = +2.200
    diff_inside_two_pos = +2.200 * se_pred
    veg_in_two_pos = _make_veg(0.60 + diff_inside_two_pos)
    ind_in_two_pos = calculate_vegetation_stress_indicators(
        veg_in_two_pos,
        growth_stage="flowering",
        baseline=baseline_12yr,
        hypothesis_test_convention=HypothesisTestConvention.TWO_SIDED,
    )
    assert ind_in_two_pos.statistical_test_details["t_statistic"] == 2.200
    assert ind_in_two_pos.is_statistically_significant_anomaly is False  # |2.200| < 2.201 is False

    # 5. Insufficient sample size and invalid variance
    # 5a. N = 9 (< 10 operational threshold)
    base_n9 = VegetationHistoricalBaseline(
        crop_type="cotton",
        growth_stage="flowering",
        baseline_ndvi=0.60,
        baseline_std=0.05,
        sample_size_years=9,
        is_valid=True,
        baseline_source="9-year flowering baseline",
    )
    ind_n9 = calculate_vegetation_stress_indicators(veg_neg, growth_stage="flowering", baseline=base_n9)
    assert ind_n9.is_statistically_significant_anomaly is None
    assert ind_n9.is_statistically_significant_decline is None

    # 5b. Invalid variance: baseline_std is None
    base_none_std = VegetationHistoricalBaseline(
        crop_type="cotton",
        growth_stage="flowering",
        baseline_ndvi=0.60,
        baseline_std=None,
        sample_size_years=12,
        is_valid=True,
        baseline_source="12-year flowering baseline without std",
    )
    ind_none_std = calculate_vegetation_stress_indicators(veg_neg, growth_stage="flowering", baseline=base_none_std)
    assert ind_none_std.is_statistically_significant_anomaly is None
    assert ind_none_std.is_statistically_significant_decline is None

    # 5c. Invalid variance: baseline_std <= 0
    base_zero_std = VegetationHistoricalBaseline(
        crop_type="cotton",
        growth_stage="flowering",
        baseline_ndvi=0.60,
        baseline_std=0.0,
        sample_size_years=12,
        is_valid=True,
        baseline_source="12-year flowering baseline with zero std",
    )
    ind_zero_std = calculate_vegetation_stress_indicators(veg_neg, growth_stage="flowering", baseline=base_zero_std)
    assert ind_zero_std.is_statistically_significant_anomaly is None
    assert ind_zero_std.is_statistically_significant_decline is None


# ==============================================================================
# 2. HISTORICAL BASELINE INSUFFICIENCY (MISSING VARIANCE, SAMPLE SIZE, PHENOLOGY)
# ==============================================================================

def test_historical_baseline_insufficiency_suppresses_statistical_claims():
    """Verify missing variance, small sample size, or phenology mismatch suppresses anomaly claims."""
    veg = ZoneVegetationFeatures(
        scene_id="S2A_TEST_02",
        observed_at=datetime(2026, 7, 15, 10, 30, tzinfo=timezone.utc),
        ndvi_mean=0.45,
        ndvi_median=0.45,
        vegetation_coverage_fraction=0.85,
        cloud_fraction=0.01,
        shadow_fraction=0.01,
        valid_observation_fraction=0.98,
        total_pixels_in_geometry=100,
        valid_vegetation_pixel_count=85,
        quality_status=DataQualityStatus.GOOD,
    )

    # Case A: Missing std entirely
    baseline_no_std = VegetationHistoricalBaseline(
        crop_type="cotton",
        baseline_ndvi=0.60,
        baseline_std=None,
        sample_size_years=12,
        is_valid=True,
        baseline_source="Multi-year median without variance",
    )
    assert baseline_no_std.is_statistically_robust is False

    ind_no_std = calculate_vegetation_stress_indicators(veg, baseline=baseline_no_std)
    assert ind_no_std.z_score is None
    assert ind_no_std.is_statistically_significant_anomaly is None
    assert ind_no_std.is_material_vegetation_decline is True  # -0.15 <= -0.12
    assert any("baseline lacks documented variance (std)" in note for note in ind_no_std.audit_trail)

    ev_no_std = evaluate_vegetation_stress_domain(ind_no_std)
    assert StressReasonCode.VEGETATION_STATISTICAL_ANOMALY not in ev_no_std.reason_codes
    assert StressReasonCode.VEGETATION_MATERIAL_DECLINE in ev_no_std.reason_codes

    # Case B: Sample size < 10 (e.g. N = 2)
    baseline_small_n = VegetationHistoricalBaseline(
        crop_type="cotton",
        baseline_ndvi=0.60,
        baseline_std=0.04,
        sample_size_years=2,
        is_valid=True,
        baseline_source="2-year record",
    )
    assert baseline_small_n.is_statistically_robust is False

    ind_small_n = calculate_vegetation_stress_indicators(veg, baseline=baseline_small_n)
    assert ind_small_n.is_statistically_significant_anomaly is None
    assert ind_small_n.is_material_vegetation_decline is True

    # Case C: Phenological stage mismatch (observation is vegetative, baseline is flowering)
    baseline_flowering = VegetationHistoricalBaseline(
        crop_type="wheat",
        growth_stage="flowering",
        baseline_ndvi=0.75,
        baseline_std=0.04,
        sample_size_years=12,
        is_valid=True,
        baseline_source="Historical flowering record",
    )
    ind_mismatch = calculate_vegetation_stress_indicators(
        veg,
        crop_stage="vegetative",
        crop_type="wheat",
        baseline=baseline_flowering,
    )
    assert ind_mismatch.ndvi_anomaly is None
    assert ind_mismatch.z_score is None
    assert ind_mismatch.is_statistically_significant_anomaly is None
    assert any("PHENOLOGICAL STAGE MISMATCH" in note for note in ind_mismatch.audit_trail)

    ev_mismatch = evaluate_vegetation_stress_domain(ind_mismatch)
    assert StressReasonCode.VEGETATION_PHENOLOGY_MISMATCH in ev_mismatch.reason_codes
    assert StressReasonCode.VEGETATION_BASELINE_MISSING in ev_mismatch.reason_codes


# ==============================================================================
# 3. HIGH PH (> 8.5) WITHOUT SAR/ESP CLASSIFIED AS STRONGLY ALKALINE, NOT SODIC
# ==============================================================================

def test_high_ph_without_sar_classified_strongly_alkaline_not_sodic():
    """Verify pH > 8.5 is classified strongly_alkaline and sodicity is NOT diagnosed from pH alone."""
    now = datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc)
    soil = SoilFeatures(
        source_provider="Lab_Report_Calcareous",
        provenance_type=ProvenanceType.LABORATORY_ANALYZED,
        observed_at=now,
        soil_ph=8.8,
        ph_method="1:2.5_water",
        quality_status=DataQualityStatus.GOOD,
    )

    ind = calculate_soil_condition_indicators(soil, as_of_time=now)
    assert ind.ph_classification == "strongly_alkaline"
    assert ind.is_ph_stress is True
    assert ind.is_sodic_hazard is None  # Sodicity unassessed without SAR/ESP
    assert any("Sodicity is unassessed" in note for note in ind.audit_trail)
    assert any("Sodicity is NOT diagnosed from pH alone" in note for note in ind.audit_trail)

    ev = evaluate_soil_stress_domain(ind)
    assert ev.status == StressStatus.ATTENTION
    assert StressReasonCode.SOIL_PH_ALKALINE in ev.reason_codes
    assert StressReasonCode.SOIL_SODIC_HAZARD not in ev.reason_codes


# ==============================================================================
# 4. SODIC HAZARD CONFIRMED ONLY WITH SUFFICIENT SODIUM EVIDENCE
# ==============================================================================

def test_sodic_hazard_confirmed_only_with_sufficient_sodium_evidence():
    """Verify sodic hazard requires SAR >= 13 or ESP >= 15%."""
    now = datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc)
    soil = SoilFeatures(
        source_provider="Lab_Report_SalineSodic",
        provenance_type=ProvenanceType.LABORATORY_ANALYZED,
        observed_at=now,
        soil_ph=8.9,
        ph_method="1:2.5_water",
        quality_status=DataQualityStatus.GOOD,
    )

    # Case A: SAR >= 13.0
    ind_sar = calculate_soil_condition_indicators(soil, sodium_adsorption_ratio_sar=14.5, as_of_time=now)
    assert ind_sar.is_sodic_hazard is True
    ev_sar = evaluate_soil_stress_domain(ind_sar)
    assert StressReasonCode.SOIL_SODIC_HAZARD in ev_sar.reason_codes

    # Case B: ESP >= 15.0%
    ind_esp = calculate_soil_condition_indicators(soil, exchangeable_sodium_pct_esp=16.0, as_of_time=now)
    assert ind_esp.is_sodic_hazard is True
    ev_esp = evaluate_soil_stress_domain(ind_esp)
    assert StressReasonCode.SOIL_SODIC_HAZARD in ev_esp.reason_codes

    # Case C: High pH (8.9) with normal sodium (SAR = 4.0, ESP = 3.0%)
    ind_normal_na = calculate_soil_condition_indicators(
        soil,
        sodium_adsorption_ratio_sar=4.0,
        exchangeable_sodium_pct_esp=3.0,
        as_of_time=now,
    )
    assert ind_normal_na.ph_classification == "strongly_alkaline"
    assert ind_normal_na.is_sodic_hazard is False
    ev_normal_na = evaluate_soil_stress_domain(ind_normal_na)
    assert StressReasonCode.SOIL_PH_ALKALINE in ev_normal_na.reason_codes
    assert StressReasonCode.SOIL_SODIC_HAZARD not in ev_normal_na.reason_codes


# ==============================================================================
# 5. VPD THRESHOLD MARKED PROVISIONAL OPERATIONAL WARNING & CALCULATION METHODS
# ==============================================================================

def test_vpd_threshold_marked_provisional_operational_warning():
    """Verify 2.2 kPa VPD is marked as provisional operational warning, not universal tissue necrosis."""
    vpd = calculate_vapor_pressure_deficit(temperature_c=32.0, relative_humidity_pct=35.0)
    # es = 0.6108 * exp(17.27 * 32 / (32 + 237.3)) = 4.757 kPa
    # ea = 4.757 * 0.35 = 1.665 kPa -> VPD = 3.092 kPa
    assert pytest.approx(vpd, abs=0.05) == 3.09

    now = datetime(2026, 5, 20, 14, 0, tzinfo=timezone.utc)
    weath = WeatherFeatures(
        source_provider="Open-Meteo",
        window_type=WeatherWindowType.DAILY_SUMMARY,
        window_start=datetime(2026, 5, 20, 0, 0, tzinfo=timezone.utc),
        window_end=datetime(2026, 5, 20, 23, 59, tzinfo=timezone.utc),
        observed_at=now,
        temperature_mean_c=32.0,
        relative_humidity_mean_pct=35.0,
        quality_status=DataQualityStatus.GOOD,
    )

    ind = calculate_weather_stress_indicators(weath, as_of_time=now)
    assert ind.is_high_vpd_stress is True
    assert ind.is_vpd_provisional is True
    assert any("HIGH ATMOSPHERIC DEMAND WARNING" in note for note in ind.audit_trail)
    assert any("NOT a universal crop damage threshold" in note for note in ind.audit_trail)
    assert CITATION_VPD_DEMAND in ind.threshold_source


def test_vpd_calculation_methods_and_citations():
    """Verify distinct VPD methods, accurate citations, and strict avoidance of Eq. 17 when RH_max/min absent."""
    # Method 1: Instantaneous paired T and RH (Tetens formula, FAO-56 Eq. 11)
    vpd_paired, cit1 = calculate_vapor_pressure_deficit_paired(temperature_c=25.0, relative_humidity_pct=50.0)
    # es = 0.6108 * exp(17.27*25 / (25+237.3)) = 3.167 kPa. ea = 3.167 * 0.50 = 1.584 kPa -> VPD = 1.584 kPa
    assert pytest.approx(vpd_paired, abs=0.01) == 1.58
    assert "Equation 11" in cit1 or "Eq. 11" in cit1

    # Method 2: FAO-56 Daily summary from RH_max and RH_min (FAO-56 Eq. 12 & Eq. 17)
    # Tmax = 30°C (es = 4.246 kPa), Tmin = 20°C (es = 2.338 kPa) -> es_mean = 3.292 kPa
    # RHmax = 80%, RHmin = 40% -> ea = (2.338*0.80 + 4.246*0.40) / 2 = (1.870 + 1.698) / 2 = 1.784 kPa
    # VPD = 3.292 - 1.784 = 1.508 kPa
    vpd_rh_min_max, cit2 = calculate_vapor_pressure_deficit_fao56_rh_max_min(
        t_max_c=30.0,
        t_min_c=20.0,
        rh_max_pct=80.0,
        rh_min_pct=40.0,
    )
    assert pytest.approx(vpd_rh_min_max, abs=0.02) == 1.51
    assert "Eq. 17" in cit2 or "Equation 17" in cit2

    # Method 3: FAO-56 Daily summary from RH_mean approx (FAO-56 Eq. 12 & Eq. 19)
    # es_mean = 3.292 kPa. ea = 3.292 * 0.60 = 1.975 kPa -> VPD = 1.317 kPa
    vpd_mean_rh, cit3 = calculate_vapor_pressure_deficit_fao56_mean_rh(
        t_max_c=30.0,
        t_min_c=20.0,
        rh_mean_pct=60.0,
    )
    assert pytest.approx(vpd_mean_rh, abs=0.02) == 1.32
    assert "Eq. 19" in cit3 or "Equation 19" in cit3
    assert "does NOT cite Eq. 17" in cit3

    # Method 4: Diurnal midday peak demand proxy (from Tmax and RH_mean)
    # es(30) = 4.246 kPa. ea = 4.246 * 0.60 = 2.548 kPa -> VPD = 1.698 kPa
    vpd_proxy, cit4 = calculate_vapor_pressure_deficit_diurnal_proxy(
        t_max_c=30.0,
        rh_mean_pct=60.0,
    )
    assert pytest.approx(vpd_proxy, abs=0.02) == 1.70

    # WeatherFeatures integration test:
    now = datetime(2026, 5, 20, 14, 0, tzinfo=timezone.utc)

    # Integration A: Daily summary WITH rh_max and rh_min -> FAO56_RH_MAX_MIN (Eq. 12 & Eq. 17)
    weath_full = WeatherFeatures(
        source_provider="Open-Meteo",
        window_type=WeatherWindowType.DAILY_SUMMARY,
        window_start=datetime(2026, 5, 20, 0, 0, tzinfo=timezone.utc),
        window_end=datetime(2026, 5, 20, 23, 59, tzinfo=timezone.utc),
        observed_at=now,
        temperature_max_c=30.0,
        temperature_min_c=20.0,
        relative_humidity_max_pct=80.0,
        relative_humidity_min_pct=40.0,
        quality_status=DataQualityStatus.GOOD,
    )
    ind_full = calculate_weather_stress_indicators(weath_full, as_of_time=now)
    assert ind_full.vpd_calculation_method == VPDCalculationMethod.FAO56_RH_MAX_MIN
    assert "Eq. 17" in ind_full.vpd_equation_citation
    assert "Eq. 12" in ind_full.vpd_equation_citation

    # Integration B: Daily summary WITHOUT rh_max/rh_min (only rh_mean) -> FAO56_MEAN_RH_APPROX (Eq. 12 & Eq. 19)
    # CRITICAL: Must cite Eq. 19, and MUST NOT cite Eq. 17!
    weath_mean_only = WeatherFeatures(
        source_provider="Open-Meteo",
        window_type=WeatherWindowType.DAILY_SUMMARY,
        window_start=datetime(2026, 5, 20, 0, 0, tzinfo=timezone.utc),
        window_end=datetime(2026, 5, 20, 23, 59, tzinfo=timezone.utc),
        observed_at=now,
        temperature_max_c=30.0,
        temperature_min_c=20.0,
        relative_humidity_mean_pct=60.0,
        quality_status=DataQualityStatus.GOOD,
    )
    ind_mean_only = calculate_weather_stress_indicators(weath_mean_only, as_of_time=now)
    assert ind_mean_only.vpd_calculation_method == VPDCalculationMethod.FAO56_MEAN_RH_APPROX
    assert "Eq. 19" in ind_mean_only.vpd_equation_citation
    assert "does NOT cite Eq. 17" in ind_mean_only.vpd_equation_citation  # SCIENTIFIC INTEGRITY ENFORCED!

    # Integration C: Hourly/Instantaneous paired -> PAIRED_INSTANTANEOUS (Eq. 11)
    weath_inst = WeatherFeatures(
        source_provider="Open-Meteo",
        window_type=WeatherWindowType.INSTANTANEOUS,
        window_start=now,
        window_end=now,
        observed_at=now,
        temperature_mean_c=25.0,
        relative_humidity_mean_pct=50.0,
        quality_status=DataQualityStatus.GOOD,
    )
    ind_inst = calculate_weather_stress_indicators(weath_inst, as_of_time=now)
    assert ind_inst.vpd_calculation_method == VPDCalculationMethod.PAIRED_INSTANTANEOUS
    assert "Eq. 11" in ind_inst.vpd_equation_citation


# ==============================================================================
# 6. HEAT THRESHOLD CROP-STAGE AND DURATION APPLICABILITY
# ==============================================================================

def test_heat_threshold_crop_stage_and_duration_applicability():
    """Verify wheat 32°C (Prasad 2008) vs cotton 38°C (Craufurd 2009) and sustained duration requirements."""
    now = datetime(2026, 5, 20, 14, 0, tzinfo=timezone.utc)

    # Wheat flowering thresholds
    wheat_thresh = CropStressThresholds(
        crop_type="wheat",
        growth_stage="flowering",
        critical_temperature_max_c=32.0,
        critical_heat_duration_days=2,
        source_cultivar="cv. Karl 92",
        experimental_conditions="controlled growth chambers",
        is_threshold_provisional=True,
        threshold_source=CITATION_HEAT_STRESS_WHEAT,
    )

    # Weather with Tmax = 34°C (above 32°C, below 38°C)
    weath = WeatherFeatures(
        source_provider="Open-Meteo",
        window_type=WeatherWindowType.DAILY_SUMMARY,
        window_start=datetime(2026, 5, 20, 0, 0, tzinfo=timezone.utc),
        window_end=datetime(2026, 5, 20, 23, 59, tzinfo=timezone.utc),
        observed_at=now,
        temperature_max_c=34.0,
        temperature_mean_c=28.0,
        relative_humidity_mean_pct=40.0,
        quality_status=DataQualityStatus.GOOD,
    )

    # Wheat with single day (1 day < 2 days): Not prolonged heat stress
    ind_wheat_single = calculate_weather_stress_indicators(
        weath,
        crop_stage_thresholds=wheat_thresh,
        sustained_high_temp_days=1,
        as_of_time=now,
    )
    assert ind_wheat_single.is_prolonged_heat_stress is False
    assert any("ELEVATED TEMPERATURE DETECTED" in note for note in ind_wheat_single.audit_trail)

    # Wheat with multi-day (3 days >= 2 days): Prolonged heat stress
    ind_wheat_sustained = calculate_weather_stress_indicators(
        weath,
        crop_stage_thresholds=wheat_thresh,
        sustained_high_temp_days=3,
        as_of_time=now,
    )
    assert ind_wheat_sustained.is_prolonged_heat_stress is True
    assert ind_wheat_sustained.source_cultivar == "cv. Karl 92"
    assert ind_wheat_sustained.experimental_conditions == "controlled growth chambers"
    assert ind_wheat_sustained.is_heat_threshold_provisional is True

    # Cotton flowering thresholds (38°C)
    cotton_thresh = CropStressThresholds(
        crop_type="cotton",
        growth_stage="flowering",
        critical_temperature_max_c=38.0,
        critical_heat_duration_days=2,
        source_cultivar="provisional cotton baseline",
        experimental_conditions="field shelter",
        threshold_source=CITATION_HEAT_STRESS_COTTON,
    )
    ind_cotton = calculate_weather_stress_indicators(
        weath,
        crop_stage_thresholds=cotton_thresh,
        sustained_high_temp_days=3,
        as_of_time=now,
    )
    # Tmax (34°C) is below cotton threshold (38°C)
    assert ind_cotton.is_prolonged_heat_stress is False


# ==============================================================================
# 7. CONFIGURABLE SATELLITE QUALITY THRESHOLDS
# ==============================================================================

def test_configurable_satellite_quality_thresholds():
    """Verify satellite clear-fraction and cloud-fraction screening are configurable policies."""
    veg = ZoneVegetationFeatures(
        scene_id="S2A_TEST_07",
        observed_at=datetime(2026, 7, 15, 10, 30, tzinfo=timezone.utc),
        ndvi_mean=0.50,
        ndvi_median=0.50,
        vegetation_coverage_fraction=0.80,
        cloud_fraction=0.15,
        shadow_fraction=0.05,
        valid_observation_fraction=0.70,  # 70% clear
        total_pixels_in_geometry=100,
        valid_vegetation_pixel_count=80,
        quality_status=DataQualityStatus.GOOD,
    )

    # Default policy (min_clear = 0.60, max_cloud = 0.20): 70% clear passes!
    ind_default = calculate_vegetation_stress_indicators(
        veg,
        min_clear_observation_fraction=0.60,
        max_cloud_shadow_fraction=0.20,
    )
    assert ind_default.is_suspect is False
    assert ind_default.is_quality_threshold_provisional is True

    # Strict custom policy (min_clear = 0.80): 70% clear is suppressed!
    ind_strict = calculate_vegetation_stress_indicators(
        veg,
        min_clear_observation_fraction=0.80,
        max_cloud_shadow_fraction=0.20,
    )
    assert ind_strict.is_suspect is True
    assert ind_strict.quality_status == DataQualityStatus.CLOUD_CONTAMINATED
    assert any("PROVISIONAL QUALITY SCREENING" in note for note in ind_strict.audit_trail)


# ==============================================================================
# 8. CLOUD SHADOW (SCL 3) VS CAST SHADOW (SCL 2) & PROCESSING BASELINES
# ==============================================================================

def test_sentinel2_scl_processing_baseline_classification():
    """Verify SCL Class 2 nomenclature and semantics per Copernicus PSD baseline, and strictly Class 3 as Cloud Shadow."""
    # Pre-PB 04.00 (< 04.00): DARK_AREA_PIXELS
    lbl_0214, norm_pb_0214, sem_0214 = resolve_scl_class_2_semantics("02.14")
    assert lbl_0214 == "DARK_AREA_PIXELS"
    assert norm_pb_0214 == "02.14"
    assert "NOT exclusively cast shadow" in sem_0214
    assert "never cloud shadow" in sem_0214
    assert resolve_scl_class_2_label("02.14")[0] == "DARK_AREA_PIXELS"
    assert resolve_scl_class_2_label("03.01")[0] == "DARK_AREA_PIXELS"
    assert resolve_scl_class_2_label("03.99")[0] == "DARK_AREA_PIXELS"

    # PB 04.00 to PB 05.10: DARK_FEATURES
    lbl_0400, norm_pb_0400, sem_0400 = resolve_scl_class_2_semantics("04.00")
    assert lbl_0400 == "DARK_FEATURES"
    assert norm_pb_0400 == "04.00"
    assert "dark soils and burned areas were separated to Class 7" in sem_0400
    assert "computation unchanged through PB 05.11 rename to CAST_SHADOW" in sem_0400
    assert "NOT cloud shadow" in sem_0400
    assert resolve_scl_class_2_label("04.00")[0] == "DARK_FEATURES"
    assert resolve_scl_class_2_label("05.00")[0] == "DARK_FEATURES"
    assert resolve_scl_class_2_label("05.10")[0] == "DARK_FEATURES"

    # PB 05.11 onwards: CAST_SHADOW
    lbl_0511, norm_pb_0511, sem_0511 = resolve_scl_class_2_semantics("05.11")
    assert lbl_0511 == "CAST_SHADOW"
    assert norm_pb_0511 == "05.11"
    assert "exclusively cast/topographic shadow" in sem_0511
    assert resolve_scl_class_2_label("05.11")[0] == "CAST_SHADOW"
    assert resolve_scl_class_2_label("05.12")[0] == "CAST_SHADOW"
    assert resolve_scl_class_2_label("06.00")[0] == "CAST_SHADOW"

    # Missing / unspecified baseline metadata
    lbl_none, _, sem_none = resolve_scl_class_2_semantics(None)
    assert lbl_none == "DARK_FEATURES_OR_CAST_SHADOW_UNSPECIFIED_BASELINE"
    assert "Ambiguous legacy classification" in sem_none
    assert resolve_scl_class_2_label(None)[0] == "DARK_FEATURES_OR_CAST_SHADOW_UNSPECIFIED_BASELINE"
    assert resolve_scl_class_2_label("")[0] == "DARK_FEATURES_OR_CAST_SHADOW_UNSPECIFIED_BASELINE"

    # Verify SCL 2 is NEVER labelled cloud shadow
    for bl in ["02.14", "04.00", "05.11", None]:
        assert "CLOUD" not in resolve_scl_class_2_label(bl)[0].upper()

    # Verify SCL Class 3 is strictly Cloud Shadows in descriptions
    assert "CLOUD_SHADOW" in SCL_CLASS_DESCRIPTIONS[3].upper()
    assert "Cloud" not in SCL_CLASS_DESCRIPTIONS[2]


def test_sentinel2_class_2_schema_semantics_and_diagnostics():
    """Verify SCL Class 2 and 3 schema fields, actual class numbers, and baseline-aware semantics in ZoneSCLBreakdown."""
    # 1. Test ZoneSCLBreakdown baseline-aware diagnostic fields for pre-PB 04.00
    breakdown_legacy = ZoneSCLBreakdown(
        total_pixels=100,
        vegetation_pixels=70,
        vegetation_fraction=0.70,
        bare_soil_pixels=10,
        bare_soil_fraction=0.10,
        water_pixels=0,
        water_fraction=0.0,
        cloud_shadow_pixels=15,
        cloud_shadow_fraction=0.15,
        scl_2_pixels=8,
        scl_2_fraction=0.08,
        scl_2_class_number=2,
        scl_2_original_class_label="DARK_AREA_PIXELS",
        scl_2_semantic_interpretation="Legacy dark surface features and general topographic/cast shadows (pre-PB 04.00; NOT exclusively cast shadow; never cloud shadow)",
        scl_2_cast_shadow_pixels=8,
        scl_2_cast_shadow_fraction=0.08,
        scl_3_pixels=7,
        scl_3_fraction=0.07,
        scl_3_class_number=3,
        scl_3_original_class_label="CLOUD_SHADOW",
        scl_3_semantic_interpretation="Cloud shadow cast on surface (exclusively cloud shadow; NOT cast/topographic shadow)",
        scl_3_cloud_shadow_pixels=7,
        scl_3_cloud_shadow_fraction=0.07,
        processing_baseline="02.14",
        cloud_pixels=5,
        cloud_fraction=0.05,
        other_pixels=0,
        other_fraction=0.0,
    )
    assert breakdown_legacy.scl_2_class_number == 2
    assert breakdown_legacy.scl_2_original_class_label == "DARK_AREA_PIXELS"
    assert "NOT exclusively cast shadow" in breakdown_legacy.scl_2_semantic_interpretation
    assert breakdown_legacy.scl_3_class_number == 3
    assert breakdown_legacy.scl_3_original_class_label == "CLOUD_SHADOW"
    assert breakdown_legacy.scl_2_cast_shadow_pixels == 8
    assert breakdown_legacy.scl_3_cloud_shadow_pixels == 7

    # 2. Test VegetationStressIndicators baseline-aware fields
    veg = ZoneVegetationFeatures(
        scene_id="S2A_TEST_SCHEMA_SEMANTICS",
        observed_at=datetime(2026, 7, 15, 10, 30, tzinfo=timezone.utc),
        ndvi_mean=0.48,
        ndvi_median=0.48,
        vegetation_coverage_fraction=0.75,
        cloud_fraction=0.02,
        shadow_fraction=0.06,
        valid_observation_fraction=0.85,
        total_pixels_in_geometry=100,
        valid_vegetation_pixel_count=75,
        quality_status=DataQualityStatus.GOOD,
    )
    ind_legacy = calculate_vegetation_stress_indicators(
        veg,
        cloud_shadow_fraction=0.06,
        cast_shadow_fraction=0.08,
        processing_baseline="02.14",
    )
    assert ind_legacy.scl_2_class_number == 2
    assert ind_legacy.scl_2_fraction == 0.08
    assert ind_legacy.scl_2_original_label == "DARK_AREA_PIXELS"
    assert "NOT exclusively cast shadow" in ind_legacy.scl_2_semantic_interpretation
    assert ind_legacy.scl_3_class_number == 3
    assert ind_legacy.scl_3_fraction == 0.06
    assert ind_legacy.scl_3_original_label == "CLOUD_SHADOW"
    assert "exclusively cloud shadow" in ind_legacy.scl_3_semantic_interpretation
    assert ind_legacy.processing_baseline == "02.14"

    # 3. Test ZoneStressAssessment evidence summary integration
    wb = _make_sample_water_balance(dr=20.0, raw=50.0, taw=100.0)
    assessment = assess_zone_stress(
        zone_id="zone-schema-semantics",
        water_balance=wb,
        vegetation_features=veg,
        cloud_shadow_fraction=0.06,
        cast_shadow_fraction=0.08,
        processing_baseline="02.14",
        as_of_time=datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc),
    )
    veg_summary = assessment.evidence_summary["vegetation"]
    assert veg_summary["scl_2_class_number"] == 2
    assert veg_summary["scl_2_original_label"] == "DARK_AREA_PIXELS"
    assert "NOT exclusively cast shadow" in veg_summary["scl_2_semantic_interpretation"]
    assert veg_summary["scl_3_class_number"] == 3
    assert veg_summary["scl_3_original_label"] == "CLOUD_SHADOW"
    assert "exclusively cloud shadow" in veg_summary["scl_3_semantic_interpretation"]
    assert veg_summary["processing_baseline"] == "02.14"


def test_cloud_shadow_vs_cast_shadow_distinction():
    """Verify SCL 2 (cast shadow / dark features) and SCL 3 (cloud shadow) are rigorously distinguished."""
    veg = ZoneVegetationFeatures(
        scene_id="S2A_TEST_08",
        observed_at=datetime(2026, 7, 15, 10, 30, tzinfo=timezone.utc),
        ndvi_mean=0.48,
        ndvi_median=0.48,
        vegetation_coverage_fraction=0.75,
        cloud_fraction=0.02,
        shadow_fraction=0.06,  # Overall shadow fraction
        valid_observation_fraction=0.85,
        total_pixels_in_geometry=100,
        valid_vegetation_pixel_count=75,
        quality_status=DataQualityStatus.GOOD,
    )

    # Test with PB 05.11+ (modern baseline: CAST_SHADOW)
    ind_modern = calculate_vegetation_stress_indicators(
        veg,
        cloud_shadow_fraction=0.06,
        cast_shadow_fraction=0.08,
        processing_baseline="05.11",
    )
    assert ind_modern.cloud_shadow_fraction == 0.06
    assert ind_modern.cast_shadow_fraction == 0.08
    assert ind_modern.scl_class_2_label == "CAST_SHADOW"
    assert ind_modern.processing_baseline == "05.11"
    assert any("Shadow breakdown: SCL 2 (CAST_SHADOW) = 8.00%, SCL 3 (CLOUD_SHADOW) = 6.00%" in note for note in ind_modern.audit_trail)

    # Test with PB 02.14 (legacy baseline: DARK_AREA_PIXELS)
    ind_legacy = calculate_vegetation_stress_indicators(
        veg,
        cloud_shadow_fraction=0.06,
        cast_shadow_fraction=0.08,
        processing_baseline="02.14",
    )
    assert ind_legacy.scl_class_2_label == "DARK_AREA_PIXELS"
    assert any("Shadow breakdown: SCL 2 (DARK_AREA_PIXELS) = 8.00%, SCL 3 (CLOUD_SHADOW) = 6.00%" in note for note in ind_legacy.audit_trail)

    # Test with unspecified baseline
    ind_unspec = calculate_vegetation_stress_indicators(
        veg,
        cloud_shadow_fraction=0.06,
        cast_shadow_fraction=0.08,
        processing_baseline=None,
    )
    assert ind_unspec.scl_class_2_label == "DARK_FEATURES_OR_CAST_SHADOW_UNSPECIFIED_BASELINE"


def test_shadow_contamination_reason_codes_and_suppression():
    """Verify that excessive cloud shadow (SCL 3) or cast shadow (SCL 2) triggers specific reason codes."""
    veg = ZoneVegetationFeatures(
        scene_id="S2A_TEST_SHADOW_CONTAM",
        observed_at=datetime(2026, 7, 15, 10, 30, tzinfo=timezone.utc),
        ndvi_mean=0.48,
        ndvi_median=0.48,
        vegetation_coverage_fraction=0.75,
        cloud_fraction=0.01,
        shadow_fraction=0.20,
        valid_observation_fraction=0.75,
        total_pixels_in_geometry=100,
        valid_vegetation_pixel_count=75,
        quality_status=DataQualityStatus.GOOD,
    )

    # Excess cloud shadow (SCL 3 = 0.20 > 0.15 policy threshold)
    ind_cloud_shadow = calculate_vegetation_stress_indicators(
        veg,
        cloud_shadow_fraction=0.20,
        cast_shadow_fraction=0.02,
        max_cloud_shadow_fraction=0.15,
        processing_baseline="05.11",
    )
    assert ind_cloud_shadow.is_suspect is True
    assert ind_cloud_shadow.quality_status == DataQualityStatus.CLOUD_CONTAMINATED
    ev_cloud = evaluate_vegetation_stress_domain(ind_cloud_shadow)
    assert StressReasonCode.VEGETATION_CLOUD_SHADOW_CONTAMINATED in ev_cloud.reason_codes

    # Excess cast shadow (SCL 2 = 0.20 > 0.15 policy threshold)
    ind_cast_shadow = calculate_vegetation_stress_indicators(
        veg,
        cloud_shadow_fraction=0.02,
        cast_shadow_fraction=0.20,
        max_cloud_shadow_fraction=0.15,
        processing_baseline="05.11",
    )
    assert ind_cast_shadow.is_suspect is True
    assert ind_cast_shadow.quality_status == DataQualityStatus.CLOUD_CONTAMINATED
    ev_cast = evaluate_vegetation_stress_domain(ind_cast_shadow)
    assert StressReasonCode.VEGETATION_CAST_SHADOW_CONTAMINATED in ev_cast.reason_codes


# ==============================================================================
# 9. CROP-SPECIFIC SALINITY INTERPRETATION
# ==============================================================================

def test_crop_specific_salinity_interpretation():
    """Verify general USDA Handbook 60 classification vs crop-specific tolerance thresholds."""
    now = datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc)
    soil = SoilFeatures(
        source_provider="Lab_Report_Salinity",
        provenance_type=ProvenanceType.LABORATORY_ANALYZED,
        observed_at=now,
        electrical_conductivity_ds_m=5.0,
        ec_method="saturated_paste_extract_ECe",
        quality_status=DataQualityStatus.GOOD,
    )

    # General classification: ECe = 5.0 is "moderate" (between 4.0 and 8.0)
    ind_general = calculate_soil_condition_indicators(soil, as_of_time=now)
    assert ind_general.salinity_hazard_level == "moderate"

    # Crop A: Tolerant crop (e.g. barley, tolerance = 6.0 dS/m)
    ind_tolerant = calculate_soil_condition_indicators(
        soil,
        crop_salinity_tolerance_ece=6.0,
        as_of_time=now,
    )
    assert any("within documented crop tolerance (6.00 dS/m)" in note for note in ind_tolerant.audit_trail)

    # Crop B: Sensitive crop (e.g. onion/bean, tolerance = 2.0 dS/m)
    ind_sensitive = calculate_soil_condition_indicators(
        soil,
        crop_salinity_tolerance_ece=2.0,
        as_of_time=now,
    )
    assert any("CROP-SPECIFIC SALINITY HAZARD" in note for note in ind_sensitive.audit_trail)


# ==============================================================================
# 10. LOW AWC MARKED AS STORAGE CONSTRAINT WITHOUT ACTIVE STRESS OR TEXTURE INFERENCE
# ==============================================================================

def test_low_awc_marked_as_storage_constraint():
    """Verify AWC < 0.08 is flagged as low water-storage capacity without diagnosing active stress or texture."""
    now = datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc)
    soil = SoilFeatures(
        source_provider="SoilGrids_Spatial",
        provenance_type=ProvenanceType.PROVIDER_MODELLED,
        observed_at=now,
        field_capacity_m3_m3=0.120,
        wilting_point_m3_m3=0.060,
        available_water_capacity_m3_m3=0.060,  # AWC < 0.08
        quality_status=DataQualityStatus.GOOD,
    )

    ind = calculate_soil_condition_indicators(soil, as_of_time=now)
    assert ind.has_low_water_storage_capacity is True
    assert ind.has_low_awc_limitation is True
    assert any("NOT proof of active water stress" in note for note in ind.audit_trail)
    assert any("Soil texture cannot be inferred from AWC alone" in note for note in ind.audit_trail)

    ev = evaluate_soil_stress_domain(ind)
    assert StressReasonCode.SOIL_AWC_LOW in ev.reason_codes
    assert any("Physical storage constraint; NOT proof of active water stress" in note for note in ev.evidence_notes)


# ==============================================================================
# 11. ABSENCE OF COMPOSITE NUMERICAL SCORE AND ABSENCE OF PRIORITY RANKING
# ==============================================================================

def test_absence_of_composite_numerical_score_and_priority_ranking():
    """Confirm no composite numerical score is calculated and no Phase 5 priority ranking exists."""
    now = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
    wb = _make_sample_water_balance(dr=70.0, raw=50.0, taw=100.0)  # Ks = 0.60, 1 - Ks = 0.40

    assessment = assess_zone_stress(
        zone_id="zone-101",
        water_balance=wb,
        as_of_time=now,
    )

    # water_stress_severity is strictly (1.0 - Ks)
    assert pytest.approx(assessment.water_stress_severity, abs=1e-2) == 0.40
    # Backward compatibility property works
    assert pytest.approx(assessment.stress_score, abs=1e-2) == 0.40

    # Ensure no composite numerical score field exists
    assert not hasattr(assessment, "composite_stress_score")
    assert not hasattr(assessment, "numerical_stress_index")

    # Ensure no Phase 5 priority ranking or action codes exist
    assert not hasattr(assessment, "priority_rank")
    assert not hasattr(assessment, "action_code")
    assert not hasattr(assessment, "recommended_irrigation_depth_mm")


# ==============================================================================
# 12. OVERALL STATUS AGGREGATION WITH INCOMPLETE EVIDENCE
# ==============================================================================

def test_overall_status_aggregation_incomplete_evidence():
    """Verify evidence synthesis hierarchy and that missing water balance cannot be declared healthy."""
    now = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)

    # 1. Missing water balance with favorable weather and optimal soil
    weath_favorable = WeatherFeatures(
        source_provider="Open-Meteo",
        window_type=WeatherWindowType.DAILY_SUMMARY,
        window_start=datetime(2026, 7, 20, 0, 0, tzinfo=timezone.utc),
        window_end=datetime(2026, 7, 20, 23, 59, tzinfo=timezone.utc),
        observed_at=now,
        temperature_max_c=28.0,
        temperature_mean_c=24.0,
        relative_humidity_mean_pct=60.0,
        quality_status=DataQualityStatus.GOOD,
    )
    soil_opt = SoilFeatures(
        source_provider="Lab_Report",
        provenance_type=ProvenanceType.LABORATORY_ANALYZED,
        observed_at=now,
        soil_ph=7.0,
        electrical_conductivity_ds_m=1.0,
        ec_method="saturated_paste_extract_ECe",
        quality_status=DataQualityStatus.GOOD,
    )

    assessment_no_wb = assess_zone_stress(
        zone_id="zone-incomplete",
        water_balance=None,
        weather_features=weath_favorable,
        soil_features=soil_opt,
        as_of_time=now,
    )
    # CRITICAL: Missing water balance CANNOT be classified as HEALTHY
    assert assessment_no_wb.status == StressStatus.INSUFFICIENT_DATA
    assert assessment_no_wb.water_stress_severity is None
    assert assessment_no_wb.stress_score is None

    # 2. Water balance verified HEALTHY (Dr = 20 < RAW = 50), weather is MONITOR
    wb_healthy = _make_sample_water_balance(dr=20.0, raw=50.0, taw=100.0)
    weath_monitor = WeatherFeatures(
        source_provider="Open-Meteo",
        window_type=WeatherWindowType.DAILY_SUMMARY,
        window_start=datetime(2026, 7, 20, 0, 0, tzinfo=timezone.utc),
        window_end=datetime(2026, 7, 20, 23, 59, tzinfo=timezone.utc),
        observed_at=now,
        temperature_mean_c=31.0,
        relative_humidity_mean_pct=35.0,  # High VPD > 2.2 kPa -> MONITOR
        quality_status=DataQualityStatus.GOOD,
    )
    assessment_monitor = assess_zone_stress(
        zone_id="zone-monitor",
        water_balance=wb_healthy,
        weather_features=weath_monitor,
        as_of_time=now,
    )
    assert assessment_monitor.status == StressStatus.MONITOR

    # 3. Water balance verified HEALTHY, soil is ATTENTION (strongly alkaline pH)
    soil_alkaline = SoilFeatures(
        source_provider="Lab_Report",
        provenance_type=ProvenanceType.LABORATORY_ANALYZED,
        observed_at=now,
        soil_ph=8.8,
        ph_method="1:2.5_water",
        quality_status=DataQualityStatus.GOOD,
    )
    assessment_attention = assess_zone_stress(
        zone_id="zone-attention",
        water_balance=wb_healthy,
        soil_features=soil_alkaline,
        as_of_time=now,
    )
    assert assessment_attention.status == StressStatus.ATTENTION

    # 4. Any domain HIGH_STRESS (e.g. severe salinity ECe = 9.0 dS/m)
    soil_severe = SoilFeatures(
        source_provider="Lab_Report",
        provenance_type=ProvenanceType.LABORATORY_ANALYZED,
        observed_at=now,
        electrical_conductivity_ds_m=9.0,
        ec_method="saturated_paste_extract_ECe",
        quality_status=DataQualityStatus.GOOD,
    )
    assessment_high = assess_zone_stress(
        zone_id="zone-high-stress",
        water_balance=wb_healthy,
        soil_features=soil_severe,
        as_of_time=now,
    )
    assert assessment_high.status == StressStatus.HIGH_STRESS
