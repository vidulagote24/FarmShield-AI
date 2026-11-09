"""Tests for crop evapotranspiration (ETc = Kc * ET0) calculation."""

import pytest

from backend.app.intelligence.agronomy.crop_coefficient import get_crop_coefficient
from backend.app.intelligence.agronomy.et0 import ET0CalculationResult
from backend.app.intelligence.agronomy.etc import (
    CropETResult,
    calculate_crop_evapotranspiration,
)
from backend.app.intelligence.types import DataQualityStatus, MeasurementHeightProvenance


def test_hand_calculated_etc_multiplication():
    """Verify ETc calculation against hand-calculated reference: ETc = Kc * ET0.

    Reference calculation:
    ET0 = 5.60 mm/day
    Wheat mid-season Kc = 1.15
    Expected ETc = 5.60 * 1.15 = 6.44 mm/day
    """
    res: CropETResult = calculate_crop_evapotranspiration(
        et0=5.60,
        crop_coefficient=1.15,
    )
    assert pytest.approx(res.etc_mm_day, abs=1e-3) == 6.440
    assert res.et0_mm_day == 5.60
    assert res.kc == 1.15
    assert res.calculation_formula == "ETc = Kc * ET0"
    assert "NOT a direct in-situ physical measurement" in res.scientific_disclaimer


def test_etc_with_structured_result_objects():
    """Verify ETc calculation using full ET0CalculationResult and CropCoefficientResult."""
    kc_res = get_crop_coefficient("cotton", growth_stage="mid_season")

    mock_et0 = ET0CalculationResult(
        et0_mm_day=6.25,
        t_mean_c=28.0,
        u2_m_s=2.5,
        es_kpa=3.78,
        ea_kpa=1.80,
        vpd_kpa=1.98,
        delta_kpa_c=0.22,
        gamma_kpa_c=0.065,
        rn_mj_m2_day=15.5,
        g_mj_m2_day=0.0,
        calculation_method="FAO-56 Penman-Monteith Daily",
        vapour_pressure_method="Dewpoint",
        wind_height_conversion_applied=False,
        original_wind_speed_m_s=2.5,
        original_wind_height_m=2.0,
        wind_height_provenance=MeasurementHeightProvenance.SENSOR_MEASURED,
        quality_status=DataQualityStatus.GOOD,
    )

    # Cotton mid-season Kc = 1.20
    # Expected ETc = 6.25 * 1.20 = 7.50 mm/day
    res = calculate_crop_evapotranspiration(
        et0=mock_et0,
        crop_coefficient=kc_res,
    )
    assert pytest.approx(res.etc_mm_day, abs=1e-3) == 7.500
    assert res.crop_type == "cotton"
    assert res.growth_stage == "mid_season"
    assert res.depletion_fraction_p == 0.65
    assert res.effective_rooting_depth_m == 1.40
    assert res.quality_status == DataQualityStatus.GOOD


def test_etc_quality_propagation():
    """Verify that stale or suspect ET0 quality propagates into ETc."""
    mock_stale_et0 = ET0CalculationResult(
        et0_mm_day=4.50,
        t_mean_c=22.0,
        u2_m_s=1.8,
        es_kpa=2.64,
        ea_kpa=1.20,
        vpd_kpa=1.44,
        delta_kpa_c=0.16,
        gamma_kpa_c=0.065,
        rn_mj_m2_day=12.0,
        calculation_method="FAO-56 Penman-Monteith Daily",
        vapour_pressure_method="RH",
        wind_height_conversion_applied=False,
        original_wind_speed_m_s=1.8,
        wind_height_provenance=MeasurementHeightProvenance.CONVENTION_ASSUMED,
        quality_status=DataQualityStatus.STALE,
        quality_notes=["Weather observation is stale."],
    )

    res = calculate_crop_evapotranspiration(
        et0=mock_stale_et0,
        crop_coefficient=0.80,
    )
    assert res.quality_status == DataQualityStatus.STALE
    assert any("Weather observation is stale" in n for n in res.quality_notes)


def test_etc_physical_validation_rejections():
    """Verify rejection of negative ET0 or non-physical Kc."""
    with pytest.raises(ValueError, match="Reference evapotranspiration ET0 cannot be negative"):
        calculate_crop_evapotranspiration(et0=-1.0, crop_coefficient=1.0)

    with pytest.raises(ValueError, match="Crop coefficient Kc out of agronomic bounds"):
        calculate_crop_evapotranspiration(et0=5.0, crop_coefficient=0.05)

    with pytest.raises(ValueError, match="Crop coefficient Kc out of agronomic bounds"):
        calculate_crop_evapotranspiration(et0=5.0, crop_coefficient=2.5)


def test_adjusted_etc_with_water_stress_coefficient():
    """Verify FAO-56 adjusted crop evapotranspiration ETc,adj = Ks * ETc.

    ET0 = 5.0 mm/day, Kc = 1.20 -> standard ETc = 6.00 mm/day
    Case 1: No stress (Ks = 1.0) -> ETc,adj = 6.00 mm/day
    Case 2: Moderate stress (Ks = 0.50) -> ETc,adj = 3.00 mm/day
    Case 3: Severe drought / wilting point (Ks = 0.0) -> ETc,adj = 0.00 mm/day
    """
    # Case 1
    res_full = calculate_crop_evapotranspiration(et0=5.0, crop_coefficient=1.20, ks=1.0)
    assert res_full.etc_mm_day == 6.0
    assert res_full.etc_adj_mm_day == 6.0
    assert res_full.water_stress_coefficient_ks == 1.0

    # Case 2
    res_mod = calculate_crop_evapotranspiration(et0=5.0, crop_coefficient=1.20, ks=0.50)
    assert res_mod.etc_mm_day == 6.0
    assert res_mod.etc_adj_mm_day == 3.0
    assert res_mod.water_stress_coefficient_ks == 0.50
    assert "ETc,adj = Ks * ETc" in res_mod.calculation_formula

    # Case 3
    res_zero = calculate_crop_evapotranspiration(et0=5.0, crop_coefficient=1.20, ks=0.0)
    assert res_zero.etc_mm_day == 6.0
    assert res_zero.etc_adj_mm_day == 0.0
    assert res_zero.water_stress_coefficient_ks == 0.0


def test_adjusted_etc_bounds_validation():
    """Verify that non-physical Ks values are strictly rejected."""
    with pytest.raises(ValueError, match="Water stress coefficient Ks must be in"):
        calculate_crop_evapotranspiration(et0=5.0, crop_coefficient=1.0, ks=-0.1)

    with pytest.raises(ValueError, match="Water stress coefficient Ks must be in"):
        calculate_crop_evapotranspiration(et0=5.0, crop_coefficient=1.0, ks=1.1)


