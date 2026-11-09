"""Tests for crop coefficient determination, phenological stage lookup, and interpolation."""

import pytest

from backend.app.intelligence.agronomy.crop_coefficient import (
    CropAgronomicParameters,
    CropCoefficientResult,
    FAO56_CROP_DATABASE,
    get_crop_coefficient,
)


def test_fao56_standard_crop_stage_coefficients():
    """Verify standard FAO-56 Table 12 crop coefficients across growth stages."""
    # 1. Wheat
    kc_wheat_ini = get_crop_coefficient("wheat", growth_stage="initial")
    assert kc_wheat_ini.kc == 0.30
    assert kc_wheat_ini.depletion_fraction_p == 0.55
    assert kc_wheat_ini.effective_rooting_depth_m == pytest.approx(0.3 * 1.2, abs=0.01)

    kc_wheat_mid = get_crop_coefficient("wheat", growth_stage="mid_season")
    assert kc_wheat_mid.kc == 1.15
    assert kc_wheat_mid.effective_rooting_depth_m == 1.20

    kc_wheat_end = get_crop_coefficient("wheat", growth_stage="harvest")
    assert kc_wheat_end.kc == 0.25

    # 2. Cotton
    kc_cotton_mid = get_crop_coefficient("cotton", growth_stage="mid_season")
    assert kc_cotton_mid.kc == 1.20
    assert kc_cotton_mid.depletion_fraction_p == 0.65
    assert kc_cotton_mid.effective_rooting_depth_m == 1.40

    # 3. Tomato
    kc_tomato_ini = get_crop_coefficient("tomato", growth_stage="initial")
    assert kc_tomato_ini.kc == 0.60
    assert kc_tomato_ini.depletion_fraction_p == 0.40


def test_growth_stage_linear_interpolation():
    """Verify mathematical linear interpolation of Kc during the development stage.

    Hand calculation for Wheat:
    Kc_ini = 0.30, Kc_mid = 1.15
    Stage duration = 30 days
    At day 15 (50% progress):
    Expected Kc = 0.30 + (15 / 30) * (1.15 - 0.30) = 0.30 + 0.425 = 0.725
    """
    res = get_crop_coefficient(
        crop_type="wheat",
        growth_stage="development",
        days_in_stage=15,
    )
    assert res.is_interpolated == True
    assert pytest.approx(res.kc, abs=1e-3) == 0.725
    assert any("50%" in a for a in res.assumptions)

    # Midpoint fallback when days_in_stage is absent
    res_fallback = get_crop_coefficient(
        crop_type="wheat",
        growth_stage="development",
    )
    assert res_fallback.is_interpolated == False
    assert pytest.approx(res_fallback.kc, abs=1e-3) == (0.30 + 1.15) / 2.0  # 0.725


def test_days_after_sowing_automatic_stage_mapping():
    """Verify automatic stage determination from calendar days after sowing."""
    # Wheat stage lengths: initial=20, dev=30 (ends 50), mid=40 (ends 90), late=30 (ends 120)
    # Day 10 -> initial
    kc_10 = get_crop_coefficient("wheat", days_after_sowing=10)
    assert kc_10.growth_stage == "initial"
    assert kc_10.kc == 0.30

    # Day 35 -> development (15 days into dev) -> 0.725
    kc_35 = get_crop_coefficient("wheat", days_after_sowing=35)
    assert kc_35.growth_stage == "development"
    assert pytest.approx(kc_35.kc, abs=1e-3) == 0.725

    # Day 70 -> mid_season -> 1.15
    kc_70 = get_crop_coefficient("wheat", days_after_sowing=70)
    assert kc_70.growth_stage == "mid_season"
    assert kc_70.kc == 1.15


def test_custom_crop_coefficient_override():
    """Verify that an explicit agronomist custom Kc override is preserved with provenance."""
    res = get_crop_coefficient(
        crop_type="wheat",
        custom_kc=0.88,
        custom_rooting_depth_m=0.75,
        custom_depletion_fraction_p=0.45,
    )
    assert res.kc == 0.88
    assert res.effective_rooting_depth_m == 0.75
    assert res.depletion_fraction_p == 0.45
    assert res.source_reference == "User / Agronomist Custom Override"


def test_unknown_crop_type_rejection():
    """Verify scientific restriction: unknown crops are NEVER assigned silent defaults."""
    with pytest.raises(ValueError, match="Unknown crop type 'dragonfruit'"):
        get_crop_coefficient("dragonfruit")

    # Invalid custom Kc
    with pytest.raises(ValueError, match="Custom Kc out of physical agronomic bounds"):
        get_crop_coefficient("wheat", custom_kc=2.5)

    # Invalid stage
    with pytest.raises(ValueError, match="Unrecognized growth stage 'flowering'"):
        get_crop_coefficient("wheat", growth_stage="flowering")


def test_fao56_climatic_adjustment_hand_calculated():
    """Verify FAO-56 Eqs. 62 & 65 climatic adjustment against exact hand calculations.

    Equation:
    Kc_adj = Kc_tab + [0.04 * (u2 - 2.0) - 0.004 * (RHmin - 45.0)] * (h / 3.0)^0.3

    Case 1: Arid, windy pre-monsoon conditions:
    Crop: Wheat (h = 1.0 m, Table 12 Kc_mid = 1.15)
    u2 = 4.0 m/s, RHmin = 25.0%
    Delta = [0.04*(2.0) - 0.004*(-20.0)] * (1.0 / 3.0)^0.3
          = [0.08 + 0.08] * (0.333333)^0.3
          = 0.16 * 0.718608 = 0.11498
    Expected Kc_adj = 1.15 + 0.115 = 1.265
    """
    res = get_crop_coefficient(
        crop_type="wheat",
        growth_stage="mid_season",
        wind_speed_2m_ms=4.0,
        rh_min_pct=25.0,
    )
    assert res.is_climate_adjusted is True
    assert res.kc_table_baseline == 1.15
    assert pytest.approx(res.kc, abs=0.005) == 1.265
    assert pytest.approx(res.climate_adjustment_delta, abs=0.005) == 0.115

    # Case 2: Subhumid reference conditions (u2=2.0 m/s, RHmin=45%):
    # Delta must be exactly 0.00
    res_subhumid = get_crop_coefficient(
        crop_type="wheat",
        growth_stage="mid_season",
        wind_speed_2m_ms=2.0,
        rh_min_pct=45.0,
    )
    assert res_subhumid.is_climate_adjusted is False
    assert res_subhumid.kc == 1.15
    assert res_subhumid.climate_adjustment_delta == 0.0

    # Case 3: Missing climatic inputs -> explicitly unadjusted
    res_no_climate = get_crop_coefficient(
        crop_type="wheat",
        growth_stage="mid_season",
    )
    assert res_no_climate.is_climate_adjusted is False
    assert res_no_climate.kc == 1.15
    assert any("not provided" in a for a in res_no_climate.assumptions)


def test_fao56_depletion_fraction_adjustment_hand_calculated():
    """Verify FAO-56 Table 22 depletion fraction adjustment for ETc rate.

    Formula:
    p_adj = p_table + 0.04 * (5.0 - ETc)
    Constrained to [0.10, 0.80].

    Wheat p_table = 0.55
    Case 1: ETc = 8.0 mm/day (high evaporative stress)
    p_adj = 0.55 + 0.04 * (5.0 - 8.0) = 0.55 - 0.12 = 0.43
    """
    res_high = get_crop_coefficient(
        crop_type="wheat",
        growth_stage="mid_season",
        etc_mm_day=8.0,
        adjust_p_for_etc=True,
    )
    assert res_high.is_p_adjusted is True
    assert res_high.depletion_fraction_p_table == 0.55
    assert pytest.approx(res_high.depletion_fraction_p, abs=1e-3) == 0.43

    # Case 2: ETc = 2.0 mm/day (cool, low demand)
    # p_adj = 0.55 + 0.04 * (5.0 - 2.0) = 0.55 + 0.12 = 0.67
    res_low = get_crop_coefficient(
        crop_type="wheat",
        growth_stage="mid_season",
        etc_mm_day=2.0,
        adjust_p_for_etc=True,
    )
    assert res_low.is_p_adjusted is True
    assert pytest.approx(res_low.depletion_fraction_p, abs=1e-3) == 0.67

    # Case 3: Configurable disable: adjust_p_for_etc=False
    res_disabled = get_crop_coefficient(
        crop_type="wheat",
        growth_stage="mid_season",
        etc_mm_day=8.0,
        adjust_p_for_etc=False,
    )
    assert res_disabled.is_p_adjusted is False
    assert res_disabled.depletion_fraction_p == 0.55

    # Case 4: Extreme clipping bounds [0.10, 0.80]
    # Cotton (p_table = 0.65) under ETc = 0.5 mm/day -> 0.65 + 0.04*(4.5) = 0.65 + 0.18 = 0.83 -> clipped to 0.80
    res_clip_high = get_crop_coefficient(
        crop_type="cotton",
        growth_stage="mid_season",
        etc_mm_day=0.5,
        adjust_p_for_etc=True,
    )
    assert res_clip_high.depletion_fraction_p == 0.80

    # Onion (p_table = 0.30) under extreme heat ETc = 15.0 mm/day -> 0.30 + 0.04*(-10) = -0.10 -> clipped to 0.10
    res_clip_low = get_crop_coefficient(
        crop_type="onion",
        growth_stage="mid_season",
        etc_mm_day=15.0,
        adjust_p_for_etc=True,
    )
    assert res_clip_low.depletion_fraction_p == 0.10


def test_fao56_climatic_inputs_range_validation():
    """Verify strict validation of FAO-56 Eqs. 62/65 input ranges (u2: 1-6 m/s, RHmin: 20-80%, h: 0.1-10 m)."""
    # Valid exact boundary cases: all must succeed without error
    res_min_bounds = get_crop_coefficient(
        "wheat",
        growth_stage="mid_season",
        wind_speed_2m_ms=1.0,
        rh_min_pct=20.0,
        plant_height_m=0.1,
    )
    assert res_min_bounds.is_climate_adjusted is True

    res_max_bounds = get_crop_coefficient(
        "wheat",
        growth_stage="mid_season",
        wind_speed_2m_ms=6.0,
        rh_min_pct=80.0,
        plant_height_m=10.0,
    )
    assert res_max_bounds.is_climate_adjusted is True

    # Out of range u2
    with pytest.raises(ValueError, match="Wind speed u2 .* is outside applicable FAO-56 adjustment range"):
        get_crop_coefficient("wheat", growth_stage="mid_season", wind_speed_2m_ms=0.5, rh_min_pct=45.0)

    with pytest.raises(ValueError, match="Wind speed u2 .* is outside applicable FAO-56 adjustment range"):
        get_crop_coefficient("wheat", growth_stage="mid_season", wind_speed_2m_ms=7.0, rh_min_pct=45.0)

    # Out of range RHmin
    with pytest.raises(ValueError, match="Minimum relative humidity RHmin .* is outside applicable FAO-56 adjustment range"):
        get_crop_coefficient("wheat", growth_stage="mid_season", wind_speed_2m_ms=2.0, rh_min_pct=15.0)

    with pytest.raises(ValueError, match="Minimum relative humidity RHmin .* is outside applicable FAO-56 adjustment range"):
        get_crop_coefficient("wheat", growth_stage="mid_season", wind_speed_2m_ms=2.0, rh_min_pct=85.0)

    # Out of range plant height
    with pytest.raises(ValueError, match="Plant height h .* is outside applicable FAO-56 range"):
        get_crop_coefficient("wheat", growth_stage="mid_season", wind_speed_2m_ms=2.0, rh_min_pct=45.0, plant_height_m=0.05)

    with pytest.raises(ValueError, match="Plant height h .* is outside applicable FAO-56 range"):
        get_crop_coefficient("wheat", growth_stage="mid_season", wind_speed_2m_ms=2.0, rh_min_pct=45.0, plant_height_m=12.0)


def test_out_of_validation_range_kc_without_silent_clipping():
    """Verify that calculated Kc outside standard [0.1, 2.0] is preserved unclipped and flagged."""
    # Sugarcane baseline Kc_mid = 1.25, h = 3.0 m.
    # Extreme windy arid pre-monsoon: u2 = 6.0 m/s, RHmin = 20.0%, h = 10.0 m (tall crop)
    # Delta = [0.04*(6-2) - 0.004*(20-45)] * (10/3)^0.3
    #       = [0.16 + 0.10] * (3.333)^0.3
    #       = 0.26 * 1.4344 = 0.373
    # Kc = 1.25 + 0.373 = 1.623 (within 2.0)
    # Now test with custom crop or high baseline:
    # Use sugarcane with custom Kc baseline or test calculate_climatic_kc_adjustment directly
    from backend.app.intelligence.agronomy.crop_coefficient import calculate_climatic_kc_adjustment

    kc_raw, delta, is_out, warnings = calculate_climatic_kc_adjustment(
        kc_baseline=1.85,
        wind_speed_2m_ms=6.0,
        rh_min_pct=20.0,
        plant_height_m=3.0,
    )
    # Delta = [0.04*4 - 0.004*(-25)] * (3/3)^0.3 = [0.16 + 0.10] * 1 = 0.26
    # kc_raw = 1.85 + 0.26 = 2.11 -> strictly > 2.0!
    assert kc_raw == 2.11
    assert delta == 0.26
    assert is_out is True
    assert any("falls outside standard FAO validation range [0.1, 2.0]" in w for w in warnings)
    assert any("Raw unclipped value preserved" in w for w in warnings)


def test_separate_mid_and_late_season_climatic_adjustments():
    """Verify separate representative inputs for mid-season and late-season stages."""
    # Mid-season: Hot, windy (u2=4.0 m/s, RHmin=25%) -> positive Delta
    # Late-season: Cool, calm, humid (u2=1.5 m/s, RHmin=70%) -> negative Delta
    res_mid = get_crop_coefficient(
        crop_type="cotton",
        growth_stage="mid_season",
        wind_speed_2m_mid_ms=4.0,
        rh_min_mid_pct=25.0,
        wind_speed_2m_end_ms=1.5,
        rh_min_end_pct=70.0,
    )
    assert res_mid.is_climate_adjusted is True
    assert res_mid.climate_adjustment_delta > 0.0  # Increased Kc_mid

    res_late = get_crop_coefficient(
        crop_type="cotton",
        growth_stage="harvest",
        wind_speed_2m_mid_ms=4.0,
        rh_min_mid_pct=25.0,
        wind_speed_2m_end_ms=1.5,
        rh_min_end_pct=70.0,
    )
    # Cotton Kc_end is 0.60 > 0.45, so late-season adjustment applies!
    assert res_late.is_climate_adjusted is True
    assert res_late.climate_adjustment_delta < 0.0  # Decreased Kc_end in calm humid conditions



