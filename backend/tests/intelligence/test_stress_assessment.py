"""Tests for ZoneStressAssessment integration, multimodal synthesis, and data-quality governance."""

from datetime import datetime, timezone
import pytest

from backend.app.intelligence.agronomy.water_balance import (
    SoilWaterCapacities,
    WaterBalanceRainfallMode,
    WaterBalanceResult,
)
from backend.app.intelligence.config import (
    FeatureFreshnessConfig,
    default_freshness_config,
)
from backend.app.intelligence.features.soil import SoilFeatures
from backend.app.intelligence.features.vegetation import ZoneVegetationFeatures
from backend.app.intelligence.features.weather import WeatherFeatures
from backend.app.intelligence.stress.assessment import (
    ZoneStressAssessment,
    assess_zone_stress,
)
from backend.app.intelligence.stress.indicators import (
    CropStressThresholds,
    VegetationHistoricalBaseline,
)
from backend.app.intelligence.stress.scoring import StressReasonCode
from backend.app.intelligence.types import (
    DataQualityStatus,
    ProvenanceType,
    StressStatus,
    WeatherWindowType,
)


def _sample_water_balance(dr: float, raw: float = 50.0, taw: float = 100.0) -> WaterBalanceResult:
    """Helper to create sample WaterBalanceResult."""
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


def test_zone_stress_assessment_full_integration():
    """Verify complete multimodal zone stress assessment with all 4 domains present."""
    now = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)

    # 1. Water: Dr = 75 mm > RAW (50 mm) -> active water stress (Ks = 0.50)
    wb = _sample_water_balance(dr=75.0, raw=50.0, taw=100.0)

    # 2. Vegetation: valid pass with negative anomaly vs baseline
    veg = ZoneVegetationFeatures(
        scene_id="S2A_MSIL2A_20260718_TEST",
        observed_at=datetime(2026, 7, 18, 10, 30, tzinfo=timezone.utc),
        ndvi_mean=0.42,
        ndvi_median=0.40,
        vegetation_coverage_fraction=0.85,
        cloud_fraction=0.01,
        shadow_fraction=0.01,
        valid_observation_fraction=0.98,
        total_pixels_in_geometry=120,
        valid_vegetation_pixel_count=102,
        quality_status=DataQualityStatus.GOOD,
    )
    baseline = VegetationHistoricalBaseline(
        crop_type="cotton",
        growth_stage="flowering",
        baseline_ndvi=0.60,
        baseline_source="5-year median",
    )

    # 3. Weather: high evaporative demand (VPD > 2.2 kPa), dry spell
    weath = WeatherFeatures(
        source_provider="Open-Meteo",
        window_type=WeatherWindowType.DAILY_SUMMARY,
        window_start=datetime(2026, 7, 20, 0, 0, tzinfo=timezone.utc),
        window_end=datetime(2026, 7, 20, 23, 59, tzinfo=timezone.utc),
        observed_at=now,
        temperature_max_c=36.0,
        temperature_mean_c=30.0,
        relative_humidity_mean_pct=35.0,
        precipitation_mm=0.0,
        quality_status=DataQualityStatus.GOOD,
    )

    # 4. Soil: optimal physicochemical properties
    soil = SoilFeatures(
        source_provider="Lab_Analysis",
        provenance_type=ProvenanceType.LABORATORY_ANALYZED,
        observed_at=datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc),
        soil_ph=7.2,
        ph_method="1:2.5_water",
        electrical_conductivity_ds_m=1.2,
        ec_method="saturated_paste_extract_ECe",
        field_capacity_m3_m3=0.350,
        wilting_point_m3_m3=0.150,
        available_water_capacity_m3_m3=0.200,
        quality_status=DataQualityStatus.GOOD,
    )

    assessment = assess_zone_stress(
        zone_id="zone-cotton-01",
        farm_id="farm-vidarbha-01",
        water_balance=wb,
        vegetation_features=veg,
        weather_features=weath,
        soil_features=soil,
        historical_vegetation_baseline=baseline,
        consecutive_dry_days=8,
        as_of_time=now,
    )

    # Overall contract checks
    assert assessment.zone_id == "zone-cotton-01"
    assert assessment.farm_id == "farm-vidarbha-01"
    assert assessment.method_version == "0.4.0"
    assert assessment.status == StressStatus.ATTENTION
    assert assessment.data_quality_status == DataQualityStatus.GOOD
    assert pytest.approx(assessment.stress_score, abs=1e-2) == 0.50  # 1.0 - Ks = 0.50

    # Domain evaluations check
    assert len(assessment.domain_assessments) == 4
    assert assessment.domain_assessments["water"].status == StressStatus.ATTENTION
    assert assessment.domain_assessments["vegetation"].status == StressStatus.ATTENTION
    assert assessment.domain_assessments["weather"].status == StressStatus.ATTENTION
    assert assessment.domain_assessments["soil"].status == StressStatus.HEALTHY

    # Reason codes check
    assert StressReasonCode.WATER_DEPLETION_EXCEEDS_RAW in assessment.reason_codes
    assert StressReasonCode.WATER_STRESS_KS_REDUCED in assessment.reason_codes
    assert StressReasonCode.VEGETATION_ANOMALY_NEGATIVE in assessment.reason_codes
    assert StressReasonCode.WEATHER_HIGH_VAPOR_PRESSURE_DEFICIT in assessment.reason_codes
    assert StressReasonCode.WEATHER_EXTENDED_DRY_SPELL in assessment.reason_codes

    # Evidence summary check
    assert assessment.evidence_summary["water"]["depletion_mm"] == 75.0
    assert assessment.evidence_summary["water"]["water_stress_coefficient_ks"] == 0.500
    assert assessment.evidence_summary["vegetation"]["ndvi_anomaly"] == -0.20
    assert assessment.evidence_summary["weather"]["is_high_vpd_stress"] is True
    assert assessment.evidence_summary["soil"]["salinity_hazard_level"] == "none"

    # Limitations check
    assert len(assessment.uncertainty_and_limitations) > 0
    assert any("spectral greenness" in lim for lim in assessment.uncertainty_and_limitations)


def test_missing_initial_soil_moisture_cannot_be_healthy():
    """Verify that missing water balance prevents zone from ever being classified as HEALTHY."""
    now = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)

    # Weather and soil are optimal, but water balance is missing (None)
    weath = WeatherFeatures(
        source_provider="IMD",
        window_type=WeatherWindowType.DAILY_SUMMARY,
        window_start=datetime(2026, 7, 20, 0, 0, tzinfo=timezone.utc),
        window_end=datetime(2026, 7, 20, 23, 59, tzinfo=timezone.utc),
        observed_at=now,
        temperature_max_c=28.0,
        temperature_mean_c=24.0,
        relative_humidity_mean_pct=60.0,
        quality_status=DataQualityStatus.GOOD,
    )
    soil = SoilFeatures(
        source_provider="Lab",
        provenance_type=ProvenanceType.LABORATORY_ANALYZED,
        observed_at=now,
        soil_ph=7.0,
        electrical_conductivity_ds_m=0.8,
        ec_method="saturated_paste_extract_ECe",
        quality_status=DataQualityStatus.GOOD,
    )

    assessment = assess_zone_stress(
        zone_id="zone-02",
        water_balance=None,  # Missing!
        weather_features=weath,
        soil_features=soil,
        as_of_time=now,
    )

    assert assessment.status == StressStatus.INSUFFICIENT_DATA
    assert assessment.data_quality_status == DataQualityStatus.PARTIAL
    assert assessment.stress_score is None
    assert any("Water Balance" in m for m in assessment.missing_evidence)
    assert StressReasonCode.WATER_BALANCE_INSUFFICIENT in assessment.reason_codes


def test_stale_and_suspect_inputs_tracking():
    """Verify stale observations and SCL cloud contamination are properly tracked."""
    now = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)

    # Satellite scene is 25 days old (stale > 14 days) and cloud-contaminated (cloud > 20%)
    veg_stale_cloudy = ZoneVegetationFeatures(
        scene_id="S2A_MSIL2A_20260625_OLD",
        observed_at=datetime(2026, 6, 25, 10, 30, tzinfo=timezone.utc),
        ndvi_mean=0.20,
        ndvi_median=0.19,
        vegetation_coverage_fraction=0.30,
        cloud_fraction=0.35,  # Cloud contaminated
        shadow_fraction=0.05,
        valid_observation_fraction=0.50,
        total_pixels_in_geometry=100,
        valid_vegetation_pixel_count=30,
        quality_status=DataQualityStatus.GOOD,
    )

    assessment = assess_zone_stress(
        zone_id="zone-03",
        vegetation_features=veg_stale_cloudy,
        as_of_time=now,
    )

    assert any("Satellite scene exceeds freshness" in s for s in assessment.stale_evidence)
    assert any("SCL cloud/shadow contamination" in s for s in assessment.suspect_evidence)
    assert assessment.domain_assessments["vegetation"].is_stale is True
    assert assessment.domain_assessments["vegetation"].is_suspect is True


def test_all_domains_missing_evidence():
    """Verify zone assessment when all evidence inputs are absent."""
    assessment = assess_zone_stress(zone_id="zone-empty")

    assert assessment.status == StressStatus.INSUFFICIENT_DATA
    assert assessment.data_quality_status == DataQualityStatus.INSUFFICIENT
    assert assessment.stress_score is None
    assert len(assessment.missing_evidence) == 4
    assert StressReasonCode.WATER_BALANCE_INSUFFICIENT in assessment.reason_codes
    assert StressReasonCode.VEGETATION_EVIDENCE_INSUFFICIENT in assessment.reason_codes
    assert StressReasonCode.WEATHER_EVIDENCE_INSUFFICIENT in assessment.reason_codes
    assert StressReasonCode.SOIL_EVIDENCE_INSUFFICIENT in assessment.reason_codes


def test_healthy_zone_when_water_balance_and_domains_non_stressed():
    """Verify zone is HEALTHY when root-zone depletion is well below RAW and no stress is present."""
    now = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)

    wb_healthy = _sample_water_balance(dr=20.0, raw=50.0, taw=100.0)  # Dr < 0.8 * RAW, Ks = 1.0

    weath_favorable = WeatherFeatures(
        source_provider="Open-Meteo",
        window_type=WeatherWindowType.DAILY_SUMMARY,
        window_start=datetime(2026, 7, 20, 0, 0, tzinfo=timezone.utc),
        window_end=datetime(2026, 7, 20, 23, 59, tzinfo=timezone.utc),
        observed_at=now,
        temperature_max_c=29.0,
        temperature_mean_c=24.0,
        relative_humidity_mean_pct=65.0,
        precipitation_mm=12.0,
        quality_status=DataQualityStatus.GOOD,
    )

    assessment = assess_zone_stress(
        zone_id="zone-healthy",
        water_balance=wb_healthy,
        weather_features=weath_favorable,
        as_of_time=now,
    )

    assert assessment.status == StressStatus.HEALTHY
    assert assessment.stress_score == 0.0
    assert StressReasonCode.WATER_DEPLETION_NORMAL in assessment.reason_codes
    assert StressReasonCode.WEATHER_CONDITIONS_FAVORABLE in assessment.reason_codes

