"""FAO-56 Penman-Monteith Reference Evapotranspiration (ET0) Engine.

Implements the standard daily FAO-56 Penman-Monteith equation (Allen et al., 1998)
for a hypothetical grass reference crop with an assumed crop height of 0.12 m,
a fixed surface resistance of 70 s/m, and an albedo of 0.23.

Standard Equation:
    ET0 = [0.408 * Delta * (Rn - G) + gamma * (900 / (Tmean + 273)) * u2 * (es - ea)] /
          [Delta + gamma * (1 + 0.34 * u2)]

Units:
    ET0: mm/day
    Rn: Net radiation at crop surface (MJ/m²/day)
    G: Soil heat flux density (MJ/m²/day, G approx 0 for daily intervals)
    Tmean: Mean daily air temperature at 2 m height (°C)
    u2: Wind speed at 2 m height (m/s)
    es: Saturation vapour pressure (kPa)
    ea: Actual vapour pressure (kPa)
    Delta: Slope of saturation vapour pressure curve (kPa/°C)
    gamma: Psychrometric constant (kPa/°C)

Scientific & Provenance Guardrails:
1. Wind Height: Measured wind speed must be converted to 2 m using the FAO-56
   logarithmic profile equation. Unknown wind heights MUST be rejected unless
   an explicit operator configuration override is supplied.
2. Vapour Pressure: Derived deterministically from dewpoint temperature, daily
   RH_max/RH_min, or directly supplied ea. Assumptions are explicitly recorded.
3. Zero Fabrication: If required input evidence is missing, calculation is aborted
   with a clear InsufficientAgronomicData error or quality flag.
"""

from datetime import date, datetime
import math
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from backend.app.intelligence.types import (
    DataQualityStatus,
    MeasurementHeightProvenance,
    ProvenanceType,
)


class ET0CalculationResult(BaseModel):
    """Structured, reproducible output of FAO-56 Penman-Monteith daily ET0 calculation."""

    et0_mm_day: float = Field(..., ge=0.0, description="Reference evapotranspiration in mm/day")
    t_mean_c: float = Field(..., description="Mean daily temperature in °C")
    u2_m_s: float = Field(..., ge=0.0, description="Wind speed standardized to 2 m height in m/s")
    es_kpa: float = Field(..., ge=0.0, description="Mean saturation vapour pressure in kPa")
    ea_kpa: float = Field(..., ge=0.0, description="Actual vapour pressure in kPa")
    vpd_kpa: float = Field(..., ge=0.0, description="Vapour pressure deficit (es - ea) in kPa")
    delta_kpa_c: float = Field(..., ge=0.0, description="Slope of saturation vapour pressure curve in kPa/°C")
    gamma_kpa_c: float = Field(..., ge=0.0, description="Psychrometric constant in kPa/°C")
    rn_mj_m2_day: float = Field(..., description="Net radiation at crop surface in MJ/m²/day")
    g_mj_m2_day: float = Field(default=0.0, description="Soil heat flux density in MJ/m²/day (0 for daily step)")

    # Radiation sub-components (if computed)
    ra_mj_m2_day: Optional[float] = Field(default=None, description="Extraterrestrial radiation in MJ/m²/day")
    rso_mj_m2_day: Optional[float] = Field(default=None, description="Clear-sky solar radiation in MJ/m²/day")
    rns_mj_m2_day: Optional[float] = Field(default=None, description="Net shortwave radiation in MJ/m²/day")
    rnl_mj_m2_day: Optional[float] = Field(default=None, description="Net longwave radiation in MJ/m²/day")
    rs_mj_m2_day: Optional[float] = Field(default=None, description="Incoming global shortwave radiation in MJ/m²/day")

    # Provenance and methodology tracking
    calculation_method: str = Field(
        default="FAO-56 Penman-Monteith Daily",
        description="Formal equation and methodology standard applied"
    )
    vapour_pressure_method: str = Field(..., description="Method used to derive ea (dewpoint, rh_range, rh_mean, direct)")
    wind_height_conversion_applied: bool = Field(..., description="Whether logarithmic wind conversion was performed")
    original_wind_speed_m_s: float = Field(..., description="Original raw wind speed before conversion in m/s")
    original_wind_height_m: Optional[float] = Field(default=None, description="Raw wind sensor height in meters")
    wind_height_provenance: MeasurementHeightProvenance = Field(..., description="Provenance of the wind height")

    quality_status: DataQualityStatus = Field(default=DataQualityStatus.GOOD, description="Synthesized quality of inputs and calculation")
    quality_notes: List[str] = Field(default_factory=list, description="Quality caveats or assumptions applied")


# --- FAO-56 Intermediate Equations ---

def atmospheric_pressure(elevation_m: float) -> float:
    """Calculate mean atmospheric pressure from elevation above sea level (FAO-56 Eq. 7).

    P = 101.3 * ((293 - 0.0065 * z) / 293)^5.26

    Args:
        elevation_m: Elevation above sea level in meters (z >= -500).

    Returns:
        Atmospheric pressure in kPa.
    """
    if elevation_m < -500.0 or elevation_m > 9000.0:
        raise ValueError(f"Physically invalid elevation: {elevation_m} m. Must be between -500m and 9000m.")
    base = (293.0 - 0.0065 * elevation_m) / 293.0
    return float(101.3 * math.pow(base, 5.26))


def psychrometric_constant(elevation_m: float) -> float:
    """Calculate psychrometric constant gamma from elevation (FAO-56 Eq. 8).

    gamma = 0.665 * 10^-3 * P

    Args:
        elevation_m: Elevation above sea level in meters.

    Returns:
        Psychrometric constant gamma in kPa/°C.
    """
    p_kpa = atmospheric_pressure(elevation_m)
    return float(0.665e-3 * p_kpa)


def saturation_vapour_pressure(temp_c: float) -> float:
    """Calculate saturation vapour pressure at temperature T (FAO-56 Eq. 11).

    e°(T) = 0.6108 * exp((17.27 * T) / (T + 237.3))

    Args:
        temp_c: Air temperature in °C.

    Returns:
        Saturation vapour pressure in kPa.
    """
    if temp_c < -60.0 or temp_c > 70.0:
        raise ValueError(f"Air temperature out of physical meteorological bounds: {temp_c}°C.")
    return float(0.6108 * math.exp((17.27 * temp_c) / (temp_c + 237.3)))


def mean_saturation_vapour_pressure(t_max_c: float, t_min_c: float) -> float:
    """Calculate mean daily saturation vapour pressure es (FAO-56 Eq. 12).

    IMPORTANT SCIENTIFIC RULE:
    Because the saturation vapour pressure curve is non-linear, es MUST be computed
    as the mean of e°(Tmax) and e°(Tmin), NOT as e°(Tmean).

    es = (e°(Tmax) + e°(Tmin)) / 2

    Args:
        t_max_c: Daily maximum temperature in °C.
        t_min_c: Daily minimum temperature in °C.

    Returns:
        Mean saturation vapour pressure es in kPa.
    """
    if t_min_c > t_max_c:
        raise ValueError(f"Physical impossibility: T_min ({t_min_c}°C) > T_max ({t_max_c}°C).")
    e_tmax = saturation_vapour_pressure(t_max_c)
    e_tmin = saturation_vapour_pressure(t_min_c)
    return float((e_tmax + e_tmin) / 2.0)


def slope_vapour_pressure_curve(t_mean_c: float) -> float:
    """Calculate slope of saturation vapour pressure curve Delta at Tmean (FAO-56 Eq. 13).

    Delta = (4098 * [0.6108 * exp((17.27 * Tmean) / (Tmean + 237.3))]) / (Tmean + 237.3)^2

    Args:
        t_mean_c: Mean air temperature in °C.

    Returns:
        Slope Delta in kPa/°C.
    """
    es_tmean = saturation_vapour_pressure(t_mean_c)
    denom = (t_mean_c + 237.3) ** 2
    return float((4098.0 * es_tmean) / denom)


def actual_vapour_pressure_from_dewpoint(t_dew_c: float) -> float:
    """Calculate actual vapour pressure ea from dewpoint temperature (FAO-56 Eq. 14).

    ea = e°(Tdew) = 0.6108 * exp((17.27 * Tdew) / (Tdew + 237.3))

    Args:
        t_dew_c: Dewpoint temperature in °C.

    Returns:
        Actual vapour pressure ea in kPa.
    """
    return saturation_vapour_pressure(t_dew_c)


def actual_vapour_pressure_from_rh(
    t_max_c: float,
    t_min_c: float,
    rh_max_pct: Optional[float] = None,
    rh_min_pct: Optional[float] = None,
    rh_mean_pct: Optional[float] = None,
) -> Tuple[float, str]:
    """Derive actual vapour pressure ea from available relative humidity evidence.

    Hierarchy per FAO-56:
    1. Method B (Eq. 17): Using both RH_max and RH_min (standard daily procedure).
       ea = (e°(Tmin) * (RHmax / 100) + e°(Tmax) * (RHmin / 100)) / 2
    2. Method C (Eq. 18): Using RH_max only when RH_min is suspect or absent.
       ea = e°(Tmin) * (RHmax / 100)
    3. Method D (Eq. 19): Using RH_mean when max/min RH are unavailable.
       ea = (RHmean / 100) * ((e°(Tmax) + e°(Tmin)) / 2)

    Args:
        t_max_c: Maximum daily temperature in °C.
        t_min_c: Minimum daily temperature in °C.
        rh_max_pct: Maximum daily relative humidity in % (0 - 100).
        rh_min_pct: Minimum daily relative humidity in % (0 - 100).
        rh_mean_pct: Mean daily relative humidity in % (0 - 100).

    Returns:
        Tuple of (ea_kpa, method_description_str).

    Raises:
        ValueError: If insufficient or physically impossible RH data is provided.
    """
    e_tmax = saturation_vapour_pressure(t_max_c)
    e_tmin = saturation_vapour_pressure(t_min_c)

    # Validate physical bounds if supplied
    for name, val in [("RH_max", rh_max_pct), ("RH_min", rh_min_pct), ("RH_mean", rh_mean_pct)]:
        if val is not None and (val < 0.0 or val > 100.0):
            raise ValueError(f"Relative humidity out of physical bounds [0, 100]: {name} = {val}%")

    if rh_max_pct is not None and rh_min_pct is not None and rh_min_pct > rh_max_pct:
        raise ValueError(f"Inconsistent RH: RH_min ({rh_min_pct}%) > RH_max ({rh_max_pct}%)")

    # Method 1: Both RH_max and RH_min available (FAO-56 Eq. 17)
    if rh_max_pct is not None and rh_min_pct is not None:
        ea = (e_tmin * (rh_max_pct / 100.0) + e_tmax * (rh_min_pct / 100.0)) / 2.0
        return float(ea), "FAO-56 Eq. 17 (RH_max and RH_min)"

    # Method 2: Only RH_max available (FAO-56 Eq. 18)
    if rh_max_pct is not None:
        ea = e_tmin * (rh_max_pct / 100.0)
        return float(ea), "FAO-56 Eq. 18 (RH_max only)"

    # Method 3: Only RH_mean available (FAO-56 Eq. 19)
    if rh_mean_pct is not None:
        es = (e_tmax + e_tmin) / 2.0
        ea = (rh_mean_pct / 100.0) * es
        return float(ea), "FAO-56 Eq. 19 (RH_mean approximation)"

    raise ValueError(
        "Insufficient humidity data to derive actual vapour pressure ea. "
        "Must provide either T_dew, (RH_max, RH_min), RH_max, or RH_mean."
    )


def wind_speed_2m_conversion(
    wind_speed_m_s: float,
    height_m: Optional[float],
    height_provenance: MeasurementHeightProvenance,
    allow_unverified_override: bool = False,
    override_height_m: Optional[float] = None,
) -> Tuple[float, Dict[str, Any]]:
    """Standardize wind speed from measurement height zw to 2 m using FAO-56 logarithmic profile (Eq. 47).

    u2 = uz * (4.87 / ln(67.8 * zw - 5.42))

    Scientific Guardrails:
    - If zw == 2.0 m: factor is identically 1.0 (no conversion needed).
    - If height is unknown or provenance is UNKNOWN: conversion is REJECTED with ValueError
      unless allow_unverified_override=True and override_height_m is explicitly passed.
    - Never converts negative wind speed.

    Args:
        wind_speed_m_s: Measured wind speed in m/s (>= 0).
        height_m: Measurement height above surface in meters.
        height_provenance: Provenance of the measurement height.
        allow_unverified_override: Explicit flag to allow user-supplied fallback height.
        override_height_m: User-supplied height in meters if override is permitted.

    Returns:
        Tuple of (u2_m_s, conversion_metadata_dict).
    """
    if wind_speed_m_s < 0.0:
        raise ValueError(f"Wind speed cannot be negative: {wind_speed_m_s} m/s")

    effective_height = height_m
    effective_provenance = height_provenance

    if effective_height is None or effective_provenance == MeasurementHeightProvenance.UNKNOWN:
        if allow_unverified_override and override_height_m is not None and override_height_m >= 0.5:
            effective_height = override_height_m
            effective_provenance = MeasurementHeightProvenance.CONVENTION_ASSUMED
        else:
            raise ValueError(
                "Cannot perform FAO-56 wind-height conversion: measurement height is UNKNOWN. "
                "FAO-56 requires verifiable anemometer height to avoid severe ET0 error."
            )

    if effective_height < 0.5 or effective_height > 100.0:
        raise ValueError(f"Anemometer height out of physical validity bounds [0.5m, 100m]: {effective_height} m")

    # If already at 2.0 m, identity conversion
    if abs(effective_height - 2.0) < 1e-4:
        return float(wind_speed_m_s), {
            "conversion_applied": False,
            "original_wind_speed_m_s": wind_speed_m_s,
            "measurement_height_m": 2.0,
            "height_provenance": effective_provenance.value,
            "conversion_factor": 1.0,
        }

    # Logarithmic wind profile (FAO-56 Eq. 47)
    factor = 4.87 / math.log(67.8 * effective_height - 5.42)
    u2 = wind_speed_m_s * factor

    return float(u2), {
        "conversion_applied": True,
        "original_wind_speed_m_s": wind_speed_m_s,
        "measurement_height_m": effective_height,
        "height_provenance": effective_provenance.value,
        "conversion_factor": float(factor),
    }


def solar_radiation_parameters(
    latitude_deg: float,
    day_of_year: int,
    elevation_m: float,
    solar_radiation_mj_m2_day: float,
    t_max_c: float,
    t_min_c: float,
    ea_kpa: float,
) -> Dict[str, float]:
    """Calculate radiation balance components (Ra, Rso, Rns, Rnl, Rn) per FAO-56 (Eqs. 21-40).

    Args:
        latitude_deg: Station latitude in decimal degrees (-90 to +90).
        day_of_year: Calendar day of year J (1 to 366).
        elevation_m: Station elevation in meters above sea level.
        solar_radiation_mj_m2_day: Global incoming solar shortwave radiation Rs (MJ/m²/day).
        t_max_c: Daily maximum temperature in °C.
        t_min_c: Daily minimum temperature in °C.
        ea_kpa: Actual vapour pressure in kPa.

    Returns:
        Dict containing ra, rso, rns, rnl, rn in MJ/m²/day.
    """
    if latitude_deg < -90.0 or latitude_deg > 90.0:
        raise ValueError(f"Invalid latitude: {latitude_deg}°. Must be in [-90, +90].")
    if day_of_year < 1 or day_of_year > 366:
        raise ValueError(f"Invalid day of year: {day_of_year}. Must be in [1, 366].")
    if solar_radiation_mj_m2_day < 0.0:
        raise ValueError(f"Solar radiation cannot be negative: {solar_radiation_mj_m2_day} MJ/m²/day.")

    phi = math.radians(latitude_deg)

    # 1. Inverse relative distance Earth-Sun dr (Eq. 23)
    dr = 1.0 + 0.033 * math.cos((2.0 * math.pi / 365.0) * day_of_year)

    # 2. Solar declination delta (Eq. 24)
    delta = 0.409 * math.sin((2.0 * math.pi / 365.0) * day_of_year - 1.39)

    # 3. Sunset hour angle omega_s (Eq. 25)
    x = -math.tan(phi) * math.tan(delta)
    if x <= -1.0:
        omega_s = math.pi  # Polar day
    elif x >= 1.0:
        omega_s = 0.0      # Polar night
    else:
        omega_s = math.acos(x)

    # 4. Extraterrestrial radiation Ra (Eq. 21)
    g_sc = 0.0820  # MJ / (m² * min)
    ra = (24.0 * 60.0 / math.pi) * g_sc * dr * (
        omega_s * math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.sin(omega_s)
    )
    ra = max(0.0, float(ra))

    # 5. Clear-sky solar radiation Rso (Eq. 37)
    rso = (0.75 + 2e-5 * elevation_m) * ra
    rso = max(1e-4, float(rso))

    # 6. Net shortwave radiation Rns for grass surface (albedo alpha = 0.23, Eq. 38)
    rs = solar_radiation_mj_m2_day
    rns = (1.0 - 0.23) * rs

    # 7. Net longwave radiation Rnl (Eq. 39)
    sigma = 4.903e-9  # Stefan-Boltzmann constant in MJ / (K^4 * m² * day)
    t_max_k = t_max_c + 273.16
    t_min_k = t_min_c + 273.16
    temp_term = sigma * ((t_max_k ** 4 + t_min_k ** 4) / 2.0)

    # Humidity term (0.34 - 0.14 * sqrt(ea))
    humidity_term = 0.34 - 0.14 * math.sqrt(max(0.0, ea_kpa))

    # Cloudiness term (1.35 * (Rs / Rso) - 0.35), clamped to [0.05, 1.0] to prevent non-physical extremes
    rs_rso_ratio = max(0.3, min(1.0, rs / rso))
    cloud_term = 1.35 * rs_rso_ratio - 0.35

    rnl = temp_term * humidity_term * cloud_term
    rnl = max(0.0, float(rnl))

    # 8. Net radiation Rn (Eq. 40)
    rn = float(rns - rnl)

    return {
        "ra": ra,
        "rso": rso,
        "rns": float(rns),
        "rnl": rnl,
        "rn": rn,
        "rs": rs,
    }


def calculate_fao56_penman_monteith_et0(
    t_max_c: float,
    t_min_c: float,
    wind_speed_m_s: float,
    wind_measurement_height_m: Optional[float],
    wind_height_provenance: MeasurementHeightProvenance,
    solar_radiation_mj_m2_day: float,
    latitude_deg: float,
    elevation_m: float,
    day_of_year: int,
    t_dew_c: Optional[float] = None,
    rh_max_pct: Optional[float] = None,
    rh_min_pct: Optional[float] = None,
    rh_mean_pct: Optional[float] = None,
    ea_direct_kpa: Optional[float] = None,
    soil_heat_flux_g_mj_m2_day: float = 0.0,
    allow_wind_height_override: bool = False,
    wind_height_override_m: Optional[float] = None,
) -> ET0CalculationResult:
    """Compute daily reference evapotranspiration (ET0) using the standardized FAO-56 Penman-Monteith method.

    Standard equation:
        ET0 = [0.408 * Delta * (Rn - G) + gamma * (900 / (Tmean + 273)) * u2 * (es - ea)] /
              [Delta + gamma * (1 + 0.34 * u2)]

    Args:
        t_max_c: Maximum daily temperature in °C.
        t_min_c: Minimum daily temperature in °C.
        wind_speed_m_s: Wind speed in m/s.
        wind_measurement_height_m: Height of anemometer in meters.
        wind_height_provenance: MeasurementHeightProvenance classification.
        solar_radiation_mj_m2_day: Global incoming solar radiation Rs (MJ/m²/day).
        latitude_deg: Latitude in decimal degrees.
        elevation_m: Elevation above sea level in meters.
        day_of_year: Day of the year J (1 - 366).
        t_dew_c: Optional dewpoint temperature in °C.
        rh_max_pct: Optional maximum relative humidity in %.
        rh_min_pct: Optional minimum relative humidity in %.
        rh_mean_pct: Optional mean relative humidity in %.
        ea_direct_kpa: Optional direct actual vapour pressure in kPa.
        soil_heat_flux_g_mj_m2_day: Soil heat flux G (default 0.0 for daily interval).
        allow_wind_height_override: Whether to permit fallback height override when unknown.
        wind_height_override_m: Fallback height in meters if override is permitted.

    Returns:
        ET0CalculationResult with full diagnostics and intermediate parameters.
    """
    quality_notes: List[str] = []

    # 1. Temperatures
    if t_min_c > t_max_c:
        raise ValueError(f"T_min ({t_min_c}°C) cannot exceed T_max ({t_max_c}°C).")
    t_mean_c = (t_max_c + t_min_c) / 2.0

    # 2. Vapour pressures
    es_kpa = mean_saturation_vapour_pressure(t_max_c, t_min_c)
    if ea_direct_kpa is not None:
        ea_kpa = float(ea_direct_kpa)
        vp_method = "Directly supplied actual vapour pressure"
    elif t_dew_c is not None:
        ea_kpa = actual_vapour_pressure_from_dewpoint(t_dew_c)
        vp_method = "FAO-56 Eq. 14 (Dewpoint temperature)"
    else:
        ea_kpa, vp_method = actual_vapour_pressure_from_rh(
            t_max_c=t_max_c,
            t_min_c=t_min_c,
            rh_max_pct=rh_max_pct,
            rh_min_pct=rh_min_pct,
            rh_mean_pct=rh_mean_pct,
        )

    # Physical check: ea cannot exceed es
    if ea_kpa > es_kpa:
        quality_notes.append(f"Derived ea ({ea_kpa:.3f} kPa) exceeded es ({es_kpa:.3f} kPa); clamped ea to es.")
        ea_kpa = es_kpa

    vpd_kpa = max(0.0, es_kpa - ea_kpa)

    # 3. Psychrometric constant and slope of vapour curve
    gamma_kpa_c = psychrometric_constant(elevation_m)
    delta_kpa_c = slope_vapour_pressure_curve(t_mean_c)

    # 4. Wind speed height conversion to 2 m
    u2_m_s, wind_meta = wind_speed_2m_conversion(
        wind_speed_m_s=wind_speed_m_s,
        height_m=wind_measurement_height_m,
        height_provenance=wind_height_provenance,
        allow_unverified_override=allow_wind_height_override,
        override_height_m=wind_height_override_m,
    )
    if wind_meta.get("conversion_applied", False):
        quality_notes.append(
            f"Wind converted from {wind_meta['original_wind_speed_m_s']:.2f} m/s at "
            f"{wind_meta['measurement_height_m']:.1f}m to {u2_m_s:.2f} m/s at 2m (factor {wind_meta['conversion_factor']:.3f})."
        )

    # 5. Radiation balance
    rad_params = solar_radiation_parameters(
        latitude_deg=latitude_deg,
        day_of_year=day_of_year,
        elevation_m=elevation_m,
        solar_radiation_mj_m2_day=solar_radiation_mj_m2_day,
        t_max_c=t_max_c,
        t_min_c=t_min_c,
        ea_kpa=ea_kpa,
    )
    rn_mj_m2_day = rad_params["rn"]
    g_mj_m2_day = float(soil_heat_flux_g_mj_m2_day)

    # 6. FAO-56 Penman-Monteith Combination Equation
    # Numerator term 1: Radiation term
    rad_term = 0.408 * delta_kpa_c * (rn_mj_m2_day - g_mj_m2_day)

    # Numerator term 2: Aerodynamic convective term
    aero_term = gamma_kpa_c * (900.0 / (t_mean_c + 273.0)) * u2_m_s * vpd_kpa

    # Denominator
    denom = delta_kpa_c + gamma_kpa_c * (1.0 + 0.34 * u2_m_s)

    et0 = (rad_term + aero_term) / denom
    et0_val = max(0.0, float(et0))  # Physical lower bound

    # Evaluate quality
    q_status = DataQualityStatus.GOOD
    if wind_height_provenance == MeasurementHeightProvenance.CONVENTION_ASSUMED:
        quality_notes.append("Anemometer height was assumed by meteorological convention, not directly sensor-measured.")

    return ET0CalculationResult(
        et0_mm_day=round(et0_val, 3),
        t_mean_c=round(t_mean_c, 2),
        u2_m_s=round(u2_m_s, 3),
        es_kpa=round(es_kpa, 4),
        ea_kpa=round(ea_kpa, 4),
        vpd_kpa=round(vpd_kpa, 4),
        delta_kpa_c=round(delta_kpa_c, 4),
        gamma_kpa_c=round(gamma_kpa_c, 4),
        rn_mj_m2_day=round(rn_mj_m2_day, 3),
        g_mj_m2_day=round(g_mj_m2_day, 3),
        ra_mj_m2_day=round(rad_params["ra"], 3),
        rso_mj_m2_day=round(rad_params["rso"], 3),
        rns_mj_m2_day=round(rad_params["rns"], 3),
        rnl_mj_m2_day=round(rad_params["rnl"], 3),
        rs_mj_m2_day=round(rad_params["rs"], 3),
        calculation_method="FAO-56 Penman-Monteith Daily",
        vapour_pressure_method=vp_method,
        wind_height_conversion_applied=wind_meta["conversion_applied"],
        original_wind_speed_m_s=wind_speed_m_s,
        original_wind_height_m=wind_measurement_height_m,
        wind_height_provenance=wind_height_provenance,
        quality_status=q_status,
        quality_notes=quality_notes,
    )

