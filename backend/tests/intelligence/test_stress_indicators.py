"""Tests for multimodal stress indicators: water, vegetation, weather, and soil."""

from datetime import datetime, timezone
import pytest

from backend.app.intelligence.agronomy.water_balance import (
    SoilWaterCapacities,
    WaterBalanceRainfallMode,
    WaterBalanceResult,
)
from backend.app.intelligence.features.soil import SoilFeatures
from backend.app.intelligence.features.vegetation import ZoneVegetationFeatures
from backend.app.intelligence.features.weather import WeatherFeatures
from backend.app.intelligence.stress.indicators import (
    CropStressThresholds,
    VegetationHistoricalBaseline,
    calculate_soil_condition_indicators,
    calculate_vapor_pressure_deficit,
    calculate_vegetation_stress_indicators,
    calculate_water_stress_indicators,
    calculate_weather_stress_indicators,
)
from backend.app.intelligence.types import (
    DataQualityStatus,
    ProvenanceType,
    WeatherWindowType,
)


def _make_sample_water_balance(dr: float, raw: float = 50.0, taw: float = 100.0) -> WaterBalanceResult:
    """Helper to construct a deterministic WaterBalanceResult for testing."""
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

    # Compute Ks using FAO-56 Eq. 84
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
# 1. WATER STRESS INDICATOR TESTS
# ==============================================================================

def test_water_stress_indicators_depletion_below_raw():
    """Verify water indicators when depletion is below RAW (no water stress, Ks = 1.0)."""
    wb = _make_sample_water_balance(dr=30.0, raw=50.0, taw=100.0)
    ind = calculate_water_stress_indicators(wb)

    assert ind.depletion_mm == 30.0
    assert ind.total_available_water_mm == 100.0
    assert ind.readily_available_water_mm == 50.0
    assert ind.water_stress_coefficient_ks == 1.0
    assert ind.stress_deficit_mm == 0.0
    assert ind.is_depletion_exceeding_raw is False
    assert ind.is_wilting_point_reached is False
    assert ind.is_approaching_raw is False
    assert ind.transpiration_reduction_pct == 0.0
    assert ind.quality_status == DataQualityStatus.GOOD


def test_water_stress_indicators_depletion_equal_to_raw():
    """Verify water indicators at the exact RAW boundary (threshold crossing point, Ks = 1.0)."""
    wb = _make_sample_water_balance(dr=50.0, raw=50.0, taw=100.0)
    ind = calculate_water_stress_indicators(wb)

    assert ind.depletion_mm == 50.0
    assert ind.water_stress_coefficient_ks == 1.0
    assert ind.stress_deficit_mm == 0.0
    assert ind.is_depletion_exceeding_raw is False
    assert ind.is_approaching_raw is True  # In the 80%-100% RAW warning zone
    assert ind.is_wilting_point_reached is False


def test_water_stress_indicators_depletion_above_raw():
    """Verify water indicators when Dr > RAW (active water stress, 0 < Ks < 1.0)."""
    # Dr = 75 mm, RAW = 50 mm, TAW = 100 mm -> Ks = (100 - 75) / 50 = 0.50
    wb = _make_sample_water_balance(dr=75.0, raw=50.0, taw=100.0)
    ind = calculate_water_stress_indicators(wb)

    assert ind.depletion_mm == 75.0
    assert ind.water_stress_coefficient_ks == 0.500
    assert ind.stress_deficit_mm == 25.0
    assert ind.is_depletion_exceeding_raw is True
    assert ind.is_wilting_point_reached is False
    assert ind.transpiration_reduction_pct == 50.0
    assert ind.depletion_fraction_taw == 0.7500


def test_water_stress_indicators_wilting_point_at_taw():
    """Verify water indicators when depletion reaches TAW (permanent wilting point, Ks = 0.0)."""
    wb = _make_sample_water_balance(dr=100.0, raw=50.0, taw=100.0)
    ind = calculate_water_stress_indicators(wb)

    assert ind.depletion_mm == 100.0
    assert ind.water_stress_coefficient_ks == 0.000
    assert ind.stress_deficit_mm == 50.0
    assert ind.is_depletion_exceeding_raw is True
    assert ind.is_wilting_point_reached is True
    assert ind.transpiration_reduction_pct == 100.0


def test_water_stress_indicators_missing_water_balance():
    """Verify missing water balance returns INSUFFICIENT quality and None for continuous metrics."""
    ind = calculate_water_stress_indicators(water_balance=None)

    assert ind.quality_status == DataQualityStatus.INSUFFICIENT
    assert ind.depletion_mm is None
    assert ind.water_stress_coefficient_ks is None
    assert ind.is_depletion_exceeding_raw is None
    assert any("Aborted" in note for note in ind.audit_trail)


def test_water_stress_indicators_measured_vs_modelled_distinction():
    """Verify that in-situ measured soil moisture is strictly distinguished from modelled depletion."""
    wb = _make_sample_water_balance(dr=40.0, raw=50.0, taw=100.0)
    ind = calculate_water_stress_indicators(
        water_balance=wb,
        in_situ_soil_moisture=0.265,
        moisture_provenance=ProvenanceType.SENSOR_MEASURED,
        moisture_depth_cm=(10.0, 30.0),
    )

    # Modelled volumetric moisture from water balance
    assert ind.modelled_root_zone_moisture_m3_m3 is not None
    assert pytest.approx(ind.modelled_root_zone_moisture_m3_m3, abs=1e-3) == 0.270

    # Measured volumetric moisture from in-situ sensor
    assert ind.measured_soil_moisture_m3_m3 == 0.265
    assert ind.measured_moisture_provenance == ProvenanceType.SENSOR_MEASURED
    assert ind.measured_moisture_depth_cm == (10.0, 30.0)
    assert any("Independent in-situ soil moisture sensor" in note for note in ind.audit_trail)


# ==============================================================================
# 2. VEGETATION STRESS INDICATOR TESTS
# ==============================================================================

def test_vegetation_stress_indicators_with_valid_baseline():
    """Verify vegetation anomaly detection against a valid historical baseline."""
    veg_feat = ZoneVegetationFeatures(
        scene_id="S2A_MSIL2A_20260715_TEST",
        observed_at=datetime(2026, 7, 15, 10, 30, tzinfo=timezone.utc),
        ndvi_mean=0.43,
        ndvi_median=0.42,
        vegetation_coverage_fraction=0.85,
        cloud_fraction=0.01,
        shadow_fraction=0.01,
        valid_observation_fraction=0.95,
        total_pixels_in_geometry=100,
        valid_vegetation_pixel_count=85,
        quality_status=DataQualityStatus.GOOD,
    )

    baseline = VegetationHistoricalBaseline(
        crop_type="cotton",
        growth_stage="flowering",
        baseline_ndvi=0.62,
        is_valid=True,
        baseline_source="5-year zone median",
    )

    ind = calculate_vegetation_stress_indicators(
        vegetation_features=veg_feat,
        baseline=baseline,
        crop_type="cotton",
        growth_stage="flowering",
    )

    assert ind.has_valid_baseline is True
    assert ind.baseline_ndvi == 0.62
    # Anomaly = 0.42 - 0.62 = -0.20
    assert pytest.approx(ind.ndvi_anomaly, abs=1e-3) == -0.200
    assert pytest.approx(ind.ndvi_anomaly_ratio, abs=1e-3) == 0.6774
    assert ind.is_canopy_anomaly_detected is True
    assert any("CANOPY ANOMALY DETECTED" in note for note in ind.audit_trail)


def test_vegetation_stress_indicators_insufficient_baseline():
    """Verify that anomaly calculation is withheld when no historical baseline is provided."""
    veg_feat = ZoneVegetationFeatures(
        scene_id="S2A_MSIL2A_20260715_TEST",
        observed_at=datetime(2026, 7, 15, 10, 30, tzinfo=timezone.utc),
        ndvi_mean=0.35,
        ndvi_median=0.34,
        vegetation_coverage_fraction=0.80,
        cloud_fraction=0.03,
        shadow_fraction=0.02,
        valid_observation_fraction=0.90,
        total_pixels_in_geometry=100,
        valid_vegetation_pixel_count=80,
        quality_status=DataQualityStatus.GOOD,
    )

    ind = calculate_vegetation_stress_indicators(
        vegetation_features=veg_feat,
        baseline=None,  # Missing baseline
    )

    assert ind.has_valid_baseline is False
    assert ind.baseline_ndvi is None
    assert ind.ndvi_anomaly is None
    assert ind.is_canopy_anomaly_detected is None
    assert any("No validated historical baseline" in note for note in ind.audit_trail)


def test_vegetation_stress_indicators_scl_contamination():
    """Verify that cloud or shadow contamination flags suspect quality and prevents false alarms."""
    veg_feat = ZoneVegetationFeatures(
        scene_id="S2A_MSIL2A_20260715_CLOUDY",
        observed_at=datetime(2026, 7, 15, 10, 30, tzinfo=timezone.utc),
        ndvi_mean=0.25,
        ndvi_median=0.24,
        vegetation_coverage_fraction=0.40,
        cloud_fraction=0.30,
        shadow_fraction=0.10,
        valid_observation_fraction=0.45,
        total_pixels_in_geometry=100,
        valid_vegetation_pixel_count=40,
        quality_status=DataQualityStatus.GOOD,
    )

    ind = calculate_vegetation_stress_indicators(veg_feat)

    assert ind.is_suspect is True
    assert ind.quality_status == DataQualityStatus.CLOUD_CONTAMINATED
    assert any("SCL CONTAMINATION WARNING" in note for note in ind.audit_trail)


# ==============================================================================
# 3. WEATHER STRESS INDICATOR TESTS
# ==============================================================================

def test_vapor_pressure_deficit_calculation():
    """Verify FAO-56 Tetens saturation vapour-pressure deficit calculation."""
    # Test case: T = 30°C, RH = 40%
    # es = 0.6108 * exp(17.27 * 30 / 267.3) = 4.243 kPa
    # ea = 4.243 * 0.40 = 1.697 kPa
    # VPD = 4.243 - 1.697 = 2.546 kPa
    vpd = calculate_vapor_pressure_deficit(temperature_c=30.0, relative_humidity_pct=40.0)
    assert pytest.approx(vpd, abs=0.02) == 2.55


def test_weather_stress_prolonged_heat_vs_instantaneous():
    """Verify prolonged heat stress requires sustained duration, not a single peak."""
    now = datetime(2026, 5, 20, 14, 0, tzinfo=timezone.utc)
    weath = WeatherFeatures(
        source_provider="Open-Meteo",
        window_type=WeatherWindowType.DAILY_SUMMARY,
        window_start=datetime(2026, 5, 20, 0, 0, tzinfo=timezone.utc),
        window_end=datetime(2026, 5, 20, 23, 59, tzinfo=timezone.utc),
        observed_at=now,
        temperature_max_c=38.0,  # Exceeds 35°C
        temperature_mean_c=29.0,
        relative_humidity_mean_pct=35.0,
        precipitation_mm=0.0,
        quality_status=DataQualityStatus.GOOD,
    )

    # Case 1: Single day exposure (sustained_high_temp_days = 1 < 2)
    ind_single = calculate_weather_stress_indicators(
        weather_features=weath,
        sustained_high_temp_days=1,
        as_of_time=now,
    )
    assert ind_single.is_prolonged_heat_stress is False
    assert any("ELEVATED TEMPERATURE DETECTED" in note for note in ind_single.audit_trail)

    # Case 2: Multi-day sustained exposure (sustained_high_temp_days = 3 >= 2)
    ind_prolonged = calculate_weather_stress_indicators(
        weather_features=weath,
        sustained_high_temp_days=3,
        as_of_time=now,
    )
    assert ind_prolonged.is_prolonged_heat_stress is True
    assert any("PROLONGED HEAT STRESS CONFIRMED" in note for note in ind_prolonged.audit_trail)


def test_crop_stage_threshold_applicability():
    """Verify crop-stage heat threshold sensitivity (wheat grain filling vs cotton)."""
    now = datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc)
    weath = WeatherFeatures(
        source_provider="IMD",
        window_type=WeatherWindowType.DAILY_SUMMARY,
        window_start=datetime(2026, 4, 10, 0, 0, tzinfo=timezone.utc),
        window_end=datetime(2026, 4, 10, 23, 59, tzinfo=timezone.utc),
        observed_at=now,
        temperature_max_c=34.0,
        temperature_mean_c=27.0,
        relative_humidity_mean_pct=40.0,
        quality_status=DataQualityStatus.GOOD,
    )

    # Wheat during grain filling: sensitive to Tmax > 32°C (Prasad et al. 2008)
    wheat_thresh = CropStressThresholds(
        crop_type="wheat",
        growth_stage="grain_filling",
        critical_temperature_max_c=32.0,
        critical_heat_duration_days=2,
    )
    ind_wheat = calculate_weather_stress_indicators(
        weath,
        crop_stage_thresholds=wheat_thresh,
        sustained_high_temp_days=2,
        as_of_time=now,
    )
    assert ind_wheat.is_prolonged_heat_stress is True

    # Cotton flowering: tolerant to Tmax up to 38°C
    cotton_thresh = CropStressThresholds(
        crop_type="cotton",
        growth_stage="flowering",
        critical_temperature_max_c=38.0,
        critical_heat_duration_days=2,
    )
    ind_cotton = calculate_weather_stress_indicators(
        weath,
        crop_stage_thresholds=cotton_thresh,
        sustained_high_temp_days=2,
        as_of_time=now,
    )
    assert ind_cotton.is_prolonged_heat_stress is False


# ==============================================================================
# 4. SOIL CONDITION INDICATOR TESTS
# ==============================================================================

def test_soil_condition_indicators_ec_method_provenance():
    """Verify soil EC evaluation distinguishes saturated paste ECe from dilute 1:5 extracts."""
    now = datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)

    # Case A: Standard saturated paste extract ECe = 4.8 dS/m (moderately saline)
    soil_ece = SoilFeatures(
        source_provider="Lab_Report_101",
        provenance_type=ProvenanceType.LABORATORY_ANALYZED,
        observed_at=now,
        electrical_conductivity_ds_m=4.8,
        ec_method="saturated_paste_extract_ECe",
        quality_status=DataQualityStatus.GOOD,
    )
    ind_ece = calculate_soil_condition_indicators(soil_ece, as_of_time=now)
    assert ind_ece.salinity_hazard_level == "moderate"
    assert ind_ece.is_salinity_stress is True

    # Case B: Dilute 1:5 extract EC = 1.8 dS/m (cannot be directly equated to ECe)
    soil_1_5 = SoilFeatures(
        source_provider="Lab_Report_102",
        provenance_type=ProvenanceType.LABORATORY_ANALYZED,
        observed_at=now,
        electrical_conductivity_ds_m=1.8,
        ec_method="1:5_extract",
        quality_status=DataQualityStatus.GOOD,
    )
    ind_1_5 = calculate_soil_condition_indicators(soil_1_5, as_of_time=now)
    assert ind_1_5.salinity_hazard_level is None
    assert any("METHOD PROVENANCE RESTRICTION" in note for note in ind_1_5.audit_trail)


def test_soil_condition_indicators_ph_reaction():
    """Verify soil pH reaction classifications (strongly acidic vs neutral vs alkaline)."""
    now = datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)

    # Strongly acidic: pH = 4.8
    soil_acidic = SoilFeatures(
        source_provider="Lab_Report_201",
        provenance_type=ProvenanceType.LABORATORY_ANALYZED,
        observed_at=now,
        soil_ph=4.8,
        ph_method="1:2.5_water",
        quality_status=DataQualityStatus.GOOD,
    )
    ind_acidic = calculate_soil_condition_indicators(soil_acidic, as_of_time=now)
    assert ind_acidic.ph_classification == "strongly_acidic"
    assert ind_acidic.is_ph_stress is True

    # Neutral / Optimal: pH = 7.1
    soil_neutral = SoilFeatures(
        source_provider="Lab_Report_202",
        provenance_type=ProvenanceType.LABORATORY_ANALYZED,
        observed_at=now,
        soil_ph=7.1,
        ph_method="1:2.5_water",
        quality_status=DataQualityStatus.GOOD,
    )
    ind_neutral = calculate_soil_condition_indicators(soil_neutral, as_of_time=now)
    assert ind_neutral.ph_classification == "neutral_optimal"
    assert ind_neutral.is_ph_stress is False

    # Strongly alkaline / sodic: pH = 8.9
    soil_alkaline = SoilFeatures(
        source_provider="Lab_Report_203",
        provenance_type=ProvenanceType.LABORATORY_ANALYZED,
        observed_at=now,
        soil_ph=8.9,
        ph_method="1:2.5_water",
        quality_status=DataQualityStatus.GOOD,
    )
    ind_alkaline = calculate_soil_condition_indicators(soil_alkaline, as_of_time=now)
    assert ind_alkaline.ph_classification == "strongly_alkaline"
    assert ind_alkaline.is_ph_stress is True


def test_soil_condition_hydraulic_limitations():
    """Verify detection of hydraulic limitation (low available water capacity AWC < 0.08)."""
    now = datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
    soil_coarse = SoilFeatures(
        source_provider="SoilGrids_Spatial",
        provenance_type=ProvenanceType.PROVIDER_MODELLED,
        observed_at=now,
        field_capacity_m3_m3=0.120,
        wilting_point_m3_m3=0.060,
        available_water_capacity_m3_m3=0.060,  # Coarse sand (AWC < 0.08)
        quality_status=DataQualityStatus.GOOD,
    )
    ind = calculate_soil_condition_indicators(soil_coarse, as_of_time=now)
    assert ind.has_low_awc_limitation is True
    assert any("Low Available Water Capacity" in lim for lim in ind.hydraulic_limitations)
