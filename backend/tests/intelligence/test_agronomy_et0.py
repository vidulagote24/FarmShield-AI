"""Hand-calculated benchmark tests for FAO-56 Penman-Monteith daily ET0 calculation."""

import math
from datetime import date
import pytest

from backend.app.intelligence.agronomy.et0 import (
    ET0CalculationResult,
    actual_vapour_pressure_from_dewpoint,
    actual_vapour_pressure_from_rh,
    atmospheric_pressure,
    calculate_fao56_penman_monteith_et0,
    mean_saturation_vapour_pressure,
    psychrometric_constant,
    saturation_vapour_pressure,
    slope_vapour_pressure_curve,
    solar_radiation_parameters,
    wind_speed_2m_conversion,
)
from backend.app.intelligence.types import DataQualityStatus, MeasurementHeightProvenance


def test_fao56_atmospheric_pressure_and_psychrometric_constant():
    """Verify atmospheric pressure and gamma against FAO-56 Chapter 3 Example 17 (z = 1800 m).

    Reference values (FAO-56):
    z = 1800 m:
    P = 101.3 * ((293 - 0.0065 * 1800) / 293)^5.26 = 81.8 kPa
    gamma = 0.665 * 10^-3 * 81.8 = 0.054 kPa/°C
    """
    p = atmospheric_pressure(1800.0)
    assert pytest.approx(p, abs=0.1) == 81.8

    gamma = psychrometric_constant(1800.0)
    assert pytest.approx(gamma, abs=0.001) == 0.054

    # Sea level check: z = 0 m -> P = 101.3 kPa, gamma = 0.067 kPa/°C
    assert pytest.approx(atmospheric_pressure(0.0), abs=0.1) == 101.3
    assert pytest.approx(psychrometric_constant(0.0), abs=0.001) == 0.067

    # Bounds check
    with pytest.raises(ValueError, match="Physically invalid elevation"):
        atmospheric_pressure(-600.0)
    with pytest.raises(ValueError, match="Physically invalid elevation"):
        atmospheric_pressure(10000.0)


def test_fao56_vapour_pressure_functions():
    """Verify saturation vapour pressure and slope curve against FAO-56 Chapter 3 benchmarks.

    FAO-56 reference values:
    T = 0°C: e°(0) = 0.6108 kPa
    T = 24.5°C: e°(24.5) = 3.075 kPa
    T = 15.0°C: e°(15.0) = 1.705 kPa
    Tmean = (24.5 + 15.0) / 2 = 19.75°C
    es = (3.075 + 1.705) / 2 = 2.390 kPa
    e°(Tmean) = e°(19.75) = 2.301 kPa  (Notice es != e°(Tmean) due to non-linearity!)
    Delta at 19.75°C: 0.143 kPa/°C
    """
    assert pytest.approx(saturation_vapour_pressure(0.0), abs=0.001) == 0.611
    assert pytest.approx(saturation_vapour_pressure(24.5), abs=0.001) == 3.075
    assert pytest.approx(saturation_vapour_pressure(15.0), abs=0.001) == 1.705

    # Mean es must be average of e°(Tmax) and e°(Tmin)
    es = mean_saturation_vapour_pressure(24.5, 15.0)
    assert pytest.approx(es, abs=0.002) == 2.390

    # Verify that es is mathematically strictly greater than e°(Tmean)
    e_tmean = saturation_vapour_pressure(19.75)
    assert pytest.approx(e_tmean, abs=0.002) == 2.301
    assert es > e_tmean

    # Slope Delta
    delta = slope_vapour_pressure_curve(19.75)
    assert pytest.approx(delta, abs=0.002) == 0.143


def test_fao56_actual_vapour_pressure_methods():
    """Verify all four FAO-56 actual vapour pressure derivation methods."""
    # Method 1: Dewpoint temperature (Tdew = 12.0°C) -> e°(12.0) = 1.403 kPa
    ea_dew = actual_vapour_pressure_from_dewpoint(12.0)
    assert pytest.approx(ea_dew, abs=0.002) == 1.403

    # Method 2: RH_max (75%) and RH_min (30%) with Tmax=24.5°C, Tmin=15.0°C
    # ea = (1.705 * 0.75 + 3.075 * 0.30) / 2 = (1.2788 + 0.9225) / 2 = 1.101 kPa
    ea_rh_range, method_range = actual_vapour_pressure_from_rh(
        t_max_c=24.5,
        t_min_c=15.0,
        rh_max_pct=75.0,
        rh_min_pct=30.0,
    )
    assert pytest.approx(ea_rh_range, abs=0.002) == 1.101
    assert "Eq. 17" in method_range

    # Method 3: RH_max only (75%), RH_min missing
    # ea = 1.705 * 0.75 = 1.279 kPa
    ea_rh_max, method_max = actual_vapour_pressure_from_rh(
        t_max_c=24.5,
        t_min_c=15.0,
        rh_max_pct=75.0,
        rh_min_pct=None,
    )
    assert pytest.approx(ea_rh_max, abs=0.002) == 1.279
    assert "Eq. 18" in method_max

    # Method 4: RH_mean only (50%)
    # ea = (50 / 100) * 2.390 = 1.195 kPa
    ea_rh_mean, method_mean = actual_vapour_pressure_from_rh(
        t_max_c=24.5,
        t_min_c=15.0,
        rh_mean_pct=50.0,
    )
    assert pytest.approx(ea_rh_mean, abs=0.002) == 1.195
    assert "Eq. 19" in method_mean

    # Error: Insufficient data
    with pytest.raises(ValueError, match="Insufficient humidity data"):
        actual_vapour_pressure_from_rh(t_max_c=25.0, t_min_c=15.0)

    # Error: RH out of bounds
    with pytest.raises(ValueError, match="Relative humidity out of physical bounds"):
        actual_vapour_pressure_from_rh(t_max_c=25.0, t_min_c=15.0, rh_mean_pct=110.0)


def test_fao56_wind_speed_2m_conversion():
    """Verify logarithmic wind profile height conversion (FAO-56 Eq. 47).

    Benchmark (FAO-56 Eq. 47):
    At 10 m: factor = 4.87 / ln(67.8 * 10 - 5.42) = 4.87 / ln(672.58) = 4.87 / 6.5111 = 0.7479
    uz = 2.07 m/s -> u2 = 2.07 * 0.7479 = 1.55 m/s
    """
    u2, meta = wind_speed_2m_conversion(
        wind_speed_m_s=2.07,
        height_m=10.0,
        height_provenance=MeasurementHeightProvenance.PROVIDER_REPORTED,
    )
    assert meta["conversion_applied"] == True
    assert pytest.approx(meta["conversion_factor"], abs=1e-3) == 0.748
    assert pytest.approx(u2, abs=0.01) == 1.55

    # At 2 m: factor must be identically 1.0 (no conversion)
    u2_2m, meta_2m = wind_speed_2m_conversion(
        wind_speed_m_s=3.0,
        height_m=2.0,
        height_provenance=MeasurementHeightProvenance.SENSOR_MEASURED,
    )
    assert meta_2m["conversion_applied"] == False
    assert u2_2m == 3.0

    # Error on unknown height without override
    with pytest.raises(ValueError, match="Cannot perform FAO-56 wind-height conversion: measurement height is UNKNOWN"):
        wind_speed_2m_conversion(
            wind_speed_m_s=3.0,
            height_m=None,
            height_provenance=MeasurementHeightProvenance.UNKNOWN,
        )

    # Allowed override when explicitly enabled
    u2_override, meta_ov = wind_speed_2m_conversion(
        wind_speed_m_s=2.07,
        height_m=None,
        height_provenance=MeasurementHeightProvenance.UNKNOWN,
        allow_unverified_override=True,
        override_height_m=10.0,
    )
    assert pytest.approx(u2_override, abs=0.01) == 1.55
    assert meta_ov["height_provenance"] == MeasurementHeightProvenance.CONVENTION_ASSUMED.value


def test_fao56_solar_radiation_parameters():
    """Verify extraterrestrial radiation and net radiation equations.

    Test parameters:
    Latitude: 18.52° N (Pune, Maharashtra)
    Day of year: J = 100 (April 10)
    Elevation: 560 m
    Solar radiation Rs: 22.0 MJ/m²/day
    Tmax = 35.0°C, Tmin = 20.0°C, ea = 1.50 kPa
    """
    rad = solar_radiation_parameters(
        latitude_deg=18.52,
        day_of_year=100,
        elevation_m=560.0,
        solar_radiation_mj_m2_day=22.0,
        t_max_c=35.0,
        t_min_c=20.0,
        ea_kpa=1.50,
    )

    # Extraterrestrial radiation Ra around 36-38 MJ/m²/day for tropical latitude in April
    assert 35.0 <= rad["ra"] <= 39.0
    # Clear-sky radiation Rso must be ~ (0.75 + 2e-5 * 560) * Ra = 0.7612 * Ra
    assert rad["rso"] < rad["ra"]
    # Net shortwave radiation: Rns = 0.77 * 22.0 = 16.94 MJ/m²/day
    assert pytest.approx(rad["rns"], abs=0.01) == 16.94
    # Net longwave radiation Rnl must be positive and smaller than Rns
    assert 2.0 <= rad["rnl"] <= 7.0
    # Net radiation Rn = Rns - Rnl
    assert rad["rn"] == pytest.approx(rad["rns"] - rad["rnl"], abs=1e-4)


def test_end_to_end_fao56_penman_monteith_hand_calculated_benchmark():
    """Verify complete end-to-end ET0 calculation against hand-calculated FAO-56 benchmark.

    Benchmark scenario:
    Location: 18.52° N, elevation 560 m, Day of Year J = 100 (April)
    Tmax = 34.0°C, Tmin = 20.0°C -> Tmean = 27.0°C
    Wind speed uz = 3.5 m/s at 10 m
    Solar radiation Rs = 22.0 MJ/m²/day
    RH_max = 70%, RH_min = 25%

    Intermediate hand verification:
    - P = 101.3 * ((293 - 0.0065 * 560) / 293)^5.26 = 95.0 kPa
    - gamma = 0.665e-3 * 95.0 = 0.0632 kPa/°C
    - e°(34.0) = 5.323 kPa, e°(20.0) = 2.338 kPa -> es = 3.831 kPa
    - ea = (2.338 * 0.70 + 5.323 * 0.25) / 2 = (1.637 + 1.331) / 2 = 1.484 kPa
    - vpd = 3.831 - 1.484 = 2.347 kPa
    - Delta(27.0) = 4098 * 3.567 / (27.0 + 237.3)^2 = 0.2085 kPa/°C
    - u2 = 3.5 * 0.748 = 2.618 m/s
    - Expected daily ET0 in peak hot summer in Maharashtra: 5.5 to 7.0 mm/day
    """
    res: ET0CalculationResult = calculate_fao56_penman_monteith_et0(
        t_max_c=34.0,
        t_min_c=20.0,
        wind_speed_m_s=3.5,
        wind_measurement_height_m=10.0,
        wind_height_provenance=MeasurementHeightProvenance.PROVIDER_REPORTED,
        solar_radiation_mj_m2_day=22.0,
        latitude_deg=18.52,
        elevation_m=560.0,
        day_of_year=100,
        rh_max_pct=70.0,
        rh_min_pct=25.0,
    )

    assert res.t_mean_c == 27.0
    assert pytest.approx(res.u2_m_s, abs=0.02) == 2.62
    assert pytest.approx(res.es_kpa, abs=0.05) == 3.83
    assert pytest.approx(res.ea_kpa, abs=0.05) == 1.48
    assert pytest.approx(res.vpd_kpa, abs=0.05) == 2.35
    assert pytest.approx(res.delta_kpa_c, abs=0.01) == 0.21
    assert pytest.approx(res.gamma_kpa_c, abs=0.01) == 0.06

    # Verify realistic daily ET0 for hot dry spring day
    assert 5.0 <= res.et0_mm_day <= 7.5
    assert res.calculation_method == "FAO-56 Penman-Monteith Daily"
    assert res.wind_height_conversion_applied == True
    assert res.quality_status == DataQualityStatus.GOOD


def test_et0_physical_inconsistency_rejections():
    """Verify that physically impossible or missing meteorological inputs raise validation errors."""
    # 1. Tmin > Tmax
    with pytest.raises(ValueError, match="cannot exceed T_max"):
        calculate_fao56_penman_monteith_et0(
            t_max_c=20.0,
            t_min_c=30.0,
            wind_speed_m_s=2.0,
            wind_measurement_height_m=2.0,
            wind_height_provenance=MeasurementHeightProvenance.SENSOR_MEASURED,
            solar_radiation_mj_m2_day=15.0,
            latitude_deg=18.5,
            elevation_m=500.0,
            day_of_year=100,
            rh_mean_pct=50.0,
        )

    # 2. Negative wind speed
    with pytest.raises(ValueError, match="Wind speed cannot be negative"):
        calculate_fao56_penman_monteith_et0(
            t_max_c=30.0,
            t_min_c=20.0,
            wind_speed_m_s=-1.5,
            wind_measurement_height_m=2.0,
            wind_height_provenance=MeasurementHeightProvenance.SENSOR_MEASURED,
            solar_radiation_mj_m2_day=15.0,
            latitude_deg=18.5,
            elevation_m=500.0,
            day_of_year=100,
            rh_mean_pct=50.0,
        )

    # 3. Unknown wind height without override
    with pytest.raises(ValueError, match="Cannot perform FAO-56 wind-height conversion"):
        calculate_fao56_penman_monteith_et0(
            t_max_c=30.0,
            t_min_c=20.0,
            wind_speed_m_s=2.5,
            wind_measurement_height_m=None,
            wind_height_provenance=MeasurementHeightProvenance.UNKNOWN,
            solar_radiation_mj_m2_day=15.0,
            latitude_deg=18.5,
            elevation_m=500.0,
            day_of_year=100,
            rh_mean_pct=50.0,
        )

