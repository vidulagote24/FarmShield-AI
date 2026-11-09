"""Weather feature engineering from normalized meteorological evidence.

Transforms weather station observations, gridded reanalysis, or NWP forecasts
into deterministic, unit-explicit, quality-evaluated features for agricultural intelligence.

Scientific and Agronomic Restrictions (per AGENTS.md, AI_SPEC.md, DATA_SOURCES.md):
1. FAO-56 Penman-Monteith ET0 and crop-water balance calculations MUST NOT be implemented here
   (strictly reserved for Phase 3).
2. Explicit physical units must be preserved: mm for precipitation, °C for temperature,
   % for relative humidity, m/s for wind speed, and MJ/m²/day for solar radiation.
3. Instantaneous readings must be distinguished from daily or window-accumulated measurements.
4. Modelled gridded reanalysis/forecasts (e.g., Open-Meteo) must remain PROVENANCE_TYPE =
   PROVIDER_MODELLED and must never be misrepresented as on-farm rain gauge observations.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import numpy as np
from pydantic import BaseModel, Field, model_validator

from backend.app.intelligence.config import default_freshness_config
from backend.app.intelligence.types import (
    DataQualityStatus,
    MeasurementHeightProvenance,
    ProvenanceType,
    SolarIrradianceType,
    WeatherWindowType,
)


class HourlyWeatherReading(BaseModel):
    """Normalized single-hour weather record."""

    timestamp: datetime = Field(..., description="UTC timestamp of the hourly observation")
    temperature_2m_c: Optional[float] = Field(default=None, description="Air temperature at 2 m in °C")
    precipitation_mm: Optional[float] = Field(default=None, ge=0.0, description="Hourly rainfall accumulation in mm")
    relative_humidity_2m_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="Relative humidity at 2 m in %")
    wind_speed_10m_m_s: Optional[float] = Field(default=None, ge=0.0, description="Wind speed at 10 m in m/s")
    shortwave_radiation_w_m2: Optional[float] = Field(default=None, ge=0.0, description="Global horizontal irradiance in W/m²")
    et0_fao_evapotranspiration_mm: Optional[float] = Field(default=None, ge=0.0, description="Provider-supplied hourly FAO ET0 in mm")


class WeatherFeatures(BaseModel):
    """Structured weather feature set covering an explicit temporal window."""

    source_provider: str = Field(
        default="Open-Meteo",
        description="Meteorological data provider (e.g., Open-Meteo, IMD, Local Station)"
    )
    provenance_type: ProvenanceType = Field(
        default=ProvenanceType.PROVIDER_MODELLED,
        description="Data provenance: provider_modelled, sensor_measured, or simulated"
    )
    window_type: WeatherWindowType = Field(
        default=WeatherWindowType.DAILY_SUMMARY,
        description="Temporal scope of this feature set (daily summary, 24h, 48h, etc.)"
    )
    window_start: datetime = Field(..., description="UTC timestamp marking start of the evaluation window")
    window_end: datetime = Field(..., description="UTC timestamp marking end of the evaluation window")
    observed_at: datetime = Field(..., description="UTC timestamp of the latest included observation")
    retrieved_at: Optional[datetime] = Field(default=None, description="Timestamp when weather data was retrieved")

    # Precipitation
    precipitation_mm: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Total accumulated precipitation within window in mm"
    )
    precipitation_hours_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Count of hours with non-zero precipitation"
    )

    # Temperature
    temperature_min_c: Optional[float] = Field(
        default=None,
        description="Minimum temperature recorded within window in °C"
    )
    temperature_max_c: Optional[float] = Field(
        default=None,
        description="Maximum temperature recorded within window in °C"
    )
    temperature_mean_c: Optional[float] = Field(
        default=None,
        description="Mean temperature within window in °C"
    )

    # Relative Humidity
    relative_humidity_mean_pct: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Mean relative humidity within window in %"
    )
    relative_humidity_min_pct: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Minimum relative humidity within window in %"
    )
    relative_humidity_max_pct: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Maximum relative humidity within window in %"
    )

    # Wind Speed (standard SI unit: m/s)
    wind_speed_mean_m_s: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Mean wind speed at specified measurement height in m/s"
    )
    wind_speed_max_m_s: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Peak wind gust or maximum wind speed in m/s"
    )
    wind_measurement_height_m: Optional[float] = Field(
        default=10.0,
        ge=0.5,
        le=100.0,
        description="Physical height of wind sensor above ground in meters (None if unknown)"
    )
    wind_height_provenance: MeasurementHeightProvenance = Field(
        default=MeasurementHeightProvenance.CONVENTION_ASSUMED,
        description="Provenance of wind measurement height (provider_reported, sensor_measured, convention_assumed, unknown)"
    )
    wind_measurement_type: str = Field(
        default="time_averaged_mean",
        description="Characterization of wind observation: 'time_averaged_mean', 'instantaneous_gust', etc."
    )

    # Solar Radiation
    solar_radiation_mj_m2_day: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Daily accumulated solar radiation in MJ/m²/day"
    )
    solar_irradiance_type: SolarIrradianceType = Field(
        default=SolarIrradianceType.INTERVAL_MEAN,
        description="Classification of irradiance inputs: interval_mean or instantaneous"
    )
    solar_radiation_integration_method: Optional[str] = Field(
        default="interval_mean_time_integration",
        description="Integration method used to convert irradiance into cumulative energy"
    )
    has_unbridged_solar_gaps: bool = Field(
        default=False,
        description="Whether unobserved temporal gaps exceeding max allowable gap were encountered and left unbridged"
    )
    unbridged_solar_gap_hours: float = Field(
        default=0.0,
        description="Total duration of unobserved solar time gaps in hours that were not bridged"
    )

    # Timezone & Physical Sensor Heights
    timezone: str = Field(
        default="UTC",
        description="Reference timezone of the weather station or aggregation window"
    )
    temperature_measurement_height_m: Optional[float] = Field(
        default=2.0,
        ge=0.5,
        le=10.0,
        description="Height of air temperature measurement above ground in meters (None if unknown)"
    )
    temperature_height_provenance: MeasurementHeightProvenance = Field(
        default=MeasurementHeightProvenance.CONVENTION_ASSUMED,
        description="Provenance of temperature measurement height (provider_reported, sensor_measured, convention_assumed, unknown)"
    )

    # External Provider Reference ET0 (preserved as reported; NOT calculated here)
    provider_et0_mm: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Provider-calculated reference ET0 in mm (if supplied directly by provider; not calculated locally)"
    )

    # Documentation of requirements for future FAO-56 reference evapotranspiration (Phase 3)
    fao56_inputs_documentation: str = Field(
        default=(
            "Expected inputs for FAO-56 Penman-Monteith ET0 in Phase 3: "
            "T_min (°C), T_max (°C), T_mean (°C) at 2m height; "
            "RH_mean (%) or actual vapor pressure e_a (kPa); "
            "Solar radiation R_s (MJ/m²/day) or sunshine hours n; "
            "Wind speed u_2 at 2m height (m/s), converted from u_z via logarithmic wind profile; "
            "Station latitude and elevation above sea level. "
            "CRITICAL PROVENANCE RULE: Phase 3 conversion of wind from u_z to u_2 requires "
            "a known height (wind_height_provenance != UNKNOWN and wind_measurement_height_m is not None). "
            "If height is unknown, Phase 3 must explicitly reject conversion or require manual elevation config."
        ),
        description="Documentation of expected inputs and height provenance rules for future Phase 3 FAO-56 calculations"
    )

    # Quality & Freshness
    quality_status: DataQualityStatus = Field(
        ...,
        description="Quality and completeness evaluation of weather evidence"
    )
    quality_note: Optional[str] = Field(
        default=None,
        description="Detailed quality note, warnings, or missing fields description"
    )
    is_stale: bool = Field(
        default=False,
        description="Whether weather evidence exceeds freshness threshold"
    )

    @model_validator(mode="after")
    def validate_temperature_consistency(self) -> "WeatherFeatures":
        """Verify that min, mean, and max temperatures are physically consistent."""
        t_min = self.temperature_min_c
        t_max = self.temperature_max_c
        t_mean = self.temperature_mean_c

        if t_min is not None and t_max is not None and t_min > t_max:
            raise ValueError(
                f"Physically inconsistent temperatures: min ({t_min}°C) > max ({t_max}°C)"
            )

        if t_mean is not None and t_min is not None and t_mean < t_min - 0.05:
            raise ValueError(
                f"Physically inconsistent temperatures: mean ({t_mean}°C) < min ({t_min}°C)"
            )

        if t_mean is not None and t_max is not None and t_mean > t_max + 0.05:
            raise ValueError(
                f"Physically inconsistent temperatures: mean ({t_mean}°C) > max ({t_max}°C)"
            )

        # Relative humidity bounds
        rh_min = self.relative_humidity_min_pct
        rh_max = self.relative_humidity_max_pct
        if rh_min is not None and rh_max is not None and rh_min > rh_max:
            raise ValueError(
                f"Physically inconsistent relative humidity: min ({rh_min}%) > max ({rh_max}%)"
            )

        return self


# ---------------------------------------------------------------------------
# Unit Conversion Utilities
# ---------------------------------------------------------------------------

def kmh_to_ms(wind_speed_kmh: float) -> float:
    """Convert wind speed from km/h to standard m/s (1 m/s = 3.6 km/h)."""
    if wind_speed_kmh < 0.0:
        raise ValueError(f"Wind speed cannot be negative: {wind_speed_kmh} km/h")
    return float(wind_speed_kmh / 3.6)


def ms_to_kmh(wind_speed_ms: float) -> float:
    """Convert wind speed from m/s to km/h."""
    if wind_speed_ms < 0.0:
        raise ValueError(f"Wind speed cannot be negative: {wind_speed_ms} m/s")
    return float(wind_speed_ms * 3.6)


def wm2_hourly_to_mj_m2(irradiance_w_m2: float) -> float:
    """Convert 1 hour of constant irradiance in W/m² (J/s/m²) to MJ/m².

    1 W/m² for 1 hour = 1 J/s/m² * 3600 s = 3600 J/m² = 0.0036 MJ/m².
    """
    if irradiance_w_m2 < 0.0:
        raise ValueError(f"Solar irradiance cannot be negative: {irradiance_w_m2} W/m²")
    return float(irradiance_w_m2 * 3600.0 / 1e6)


def kwh_m2_to_mj_m2(energy_kwh_m2: float) -> float:
    """Convert energy from kWh/m² to MJ/m² (1 kWh = 3.6 MJ)."""
    if energy_kwh_m2 < 0.0:
        raise ValueError(f"Solar radiation cannot be negative: {energy_kwh_m2} kWh/m²")
    return float(energy_kwh_m2 * 3.6)


# ---------------------------------------------------------------------------
# Weather Aggregation
# ---------------------------------------------------------------------------

def aggregate_hourly_weather(
    hourly_readings: List[HourlyWeatherReading],
    window_type: WeatherWindowType = WeatherWindowType.DAILY_SUMMARY,
    source_provider: str = "Open-Meteo",
    provenance_type: ProvenanceType = ProvenanceType.PROVIDER_MODELLED,
    as_of_time: Optional[datetime] = None,
    stale_hours: Optional[float] = None,
    timezone_str: str = "UTC",
    wind_measurement_height_m: Optional[float] = 10.0,
    wind_height_provenance: MeasurementHeightProvenance = MeasurementHeightProvenance.CONVENTION_ASSUMED,
    temperature_measurement_height_m: Optional[float] = 2.0,
    temperature_height_provenance: MeasurementHeightProvenance = MeasurementHeightProvenance.CONVENTION_ASSUMED,
    wind_measurement_type: str = "time_averaged_mean",
    irradiance_type: SolarIrradianceType = SolarIrradianceType.INTERVAL_MEAN,
    max_solar_gap_hours: float = 1.5,
) -> WeatherFeatures:
    """Deterministically aggregate hourly weather records into a window summary.

    Aggregation rules:
    - Precipitation: strict arithmetic sum (accumulation) in mm.
    - Temperature: min, max, and arithmetic mean in °C.
    - Relative Humidity: min, max, and arithmetic mean in %.
    - Wind Speed: arithmetic mean and peak value in m/s at native measurement height.
    - Solar Radiation: numeric time integration of irradiance (W/m²) over the actual
      elapsed measurement interval between readings into cumulative MJ/m²/day.
      Supports both:
      1. Interval-mean irradiance (accumulating I * dt / 1e6).
      2. Instantaneous spot flux (trapezoidal quadrature: 0.5 * (I_0 + I_1) * dt / 1e6).
      Missing intervals exceeding max_solar_gap_hours are NEVER bridged silently.
    - Missing hours: preserved as None; missing values are NOT silently zero-filled.

    Args:
        hourly_readings: List of HourlyWeatherReading objects.
        window_type: WeatherWindowType classification.
        source_provider: Source provider name.
        provenance_type: ProvenanceType classification.
        as_of_time: Reference timestamp for staleness checking.
        stale_hours: Maximum allowable age in hours before flagging stale.
        timezone_str: Timezone identifier for the weather window.
        wind_measurement_height_m: Height of wind measurement in meters (preserved, not converted in Phase 2).
        wind_height_provenance: MeasurementHeightProvenance enum.
        temperature_measurement_height_m: Height of temperature measurement in meters.
        temperature_height_provenance: MeasurementHeightProvenance enum.
        wind_measurement_type: Characterization of wind speed.
        irradiance_type: SolarIrradianceType (INTERVAL_MEAN vs INSTANTANEOUS).
        max_solar_gap_hours: Maximum gap in hours between readings before declaring an unbridged data gap.

    Returns:
        WeatherFeatures representing the aggregated temporal window.
    """
    if not hourly_readings:
        raise ValueError("Cannot aggregate empty list of hourly weather readings.")

    max_stale_hours = (
        stale_hours if stale_hours is not None
        else default_freshness_config.weather_stale_hours
    )

    # Sort readings chronologically
    sorted_readings = sorted(hourly_readings, key=lambda x: x.timestamp)
    window_start = sorted_readings[0].timestamp
    window_end = sorted_readings[-1].timestamp
    observed_at = window_end

    # Extract valid series
    temps = [r.temperature_2m_c for r in sorted_readings if r.temperature_2m_c is not None]
    precips = [r.precipitation_mm for r in sorted_readings if r.precipitation_mm is not None]
    rhs = [r.relative_humidity_2m_pct for r in sorted_readings if r.relative_humidity_2m_pct is not None]
    winds = [r.wind_speed_10m_m_s for r in sorted_readings if r.wind_speed_10m_m_s is not None]
    et0s = [r.et0_fao_evapotranspiration_mm for r in sorted_readings if r.et0_fao_evapotranspiration_mm is not None]

    # Deterministic Aggregations
    # Temperature
    t_min = float(np.min(temps)) if temps else None
    t_max = float(np.max(temps)) if temps else None
    t_mean = float(np.mean(temps)) if temps else None

    # Precipitation accumulation
    precip_total = float(np.sum(precips)) if precips else None
    precip_hours = sum(1 for p in precips if p > 0.05) if precips else None

    # Relative humidity
    rh_min = float(np.min(rhs)) if rhs else None
    rh_max = float(np.max(rhs)) if rhs else None
    rh_mean = float(np.mean(rhs)) if rhs else None

    # Wind speed
    wind_mean = float(np.mean(winds)) if winds else None
    wind_max = float(np.max(winds)) if winds else None

    # Solar radiation: time integration using the actual elapsed measurement interval between readings
    solar_total_mj: Optional[float] = None
    has_unbridged_solar_gaps = False
    unbridged_solar_gap_hours = 0.0
    integration_method_str: Optional[str] = None

    valid_rad_readings = [
        r for r in sorted_readings
        if r.shortwave_radiation_w_m2 is not None and np.isfinite(r.shortwave_radiation_w_m2)
    ]

    if valid_rad_readings:
        n_readings = len(sorted_readings)
        max_gap_seconds = max_solar_gap_hours * 3600.0
        accumulated_energy_mj = 0.0

        if irradiance_type == SolarIrradianceType.INTERVAL_MEAN:
            integration_method_str = "interval_mean_time_integration"
            for idx in range(n_readings):
                rad_w = sorted_readings[idx].shortwave_radiation_w_m2
                if rad_w is not None and np.isfinite(rad_w):
                    if idx > 0:
                        dt_sec = (sorted_readings[idx].timestamp - sorted_readings[idx - 1].timestamp).total_seconds()
                    elif n_readings > 1:
                        dt_sec = (sorted_readings[1].timestamp - sorted_readings[0].timestamp).total_seconds()
                    else:
                        dt_sec = 3600.0

                    if dt_sec <= 0:
                        dt_sec = 3600.0

                    if idx > 0 and dt_sec > max_gap_seconds:
                        has_unbridged_solar_gaps = True
                        gap_hrs = (dt_sec - 3600.0) / 3600.0
                        unbridged_solar_gap_hours += max(0.0, gap_hrs)
                        accumulated_energy_mj += (rad_w * 3600.0) / 1e6
                    else:
                        accumulated_energy_mj += (rad_w * dt_sec) / 1e6

        elif irradiance_type == SolarIrradianceType.INSTANTANEOUS:
            integration_method_str = "trapezoidal_instantaneous_quadrature"
            for idx in range(1, n_readings):
                r_prev = sorted_readings[idx - 1]
                r_curr = sorted_readings[idx]
                dt_sec = (r_curr.timestamp - r_prev.timestamp).total_seconds()

                if dt_sec > max_gap_seconds:
                    has_unbridged_solar_gaps = True
                    unbridged_solar_gap_hours += dt_sec / 3600.0
                else:
                    if (r_prev.shortwave_radiation_w_m2 is not None and np.isfinite(r_prev.shortwave_radiation_w_m2) and
                        r_curr.shortwave_radiation_w_m2 is not None and np.isfinite(r_curr.shortwave_radiation_w_m2)):
                        mean_irr = (r_prev.shortwave_radiation_w_m2 + r_curr.shortwave_radiation_w_m2) / 2.0
                        accumulated_energy_mj += (mean_irr * dt_sec) / 1e6

        if has_unbridged_solar_gaps:
            integration_method_str += "_with_unbridged_gaps"

        solar_total_mj = float(accumulated_energy_mj)

    # Provider ET0 accumulation
    provider_et0_total = float(np.sum(et0s)) if et0s else None

    # Staleness check
    is_stale = False
    if as_of_time is not None:
        age_hours = (as_of_time - observed_at).total_seconds() / 3600.0
        if age_hours > max_stale_hours:
            is_stale = True

    # Quality status
    total_hours = len(sorted_readings)
    expected_hours = 24 if window_type in {WeatherWindowType.DAILY_SUMMARY, WeatherWindowType.WINDOW_24H} else total_hours

    if is_stale:
        q_status = DataQualityStatus.STALE
        q_note = f"Weather observation age ({age_hours:.1f}h) exceeds freshness threshold ({max_stale_hours}h)."
    elif has_unbridged_solar_gaps:
        q_status = DataQualityStatus.PARTIAL
        q_note = f"Partial observation window: solar radiation contains {unbridged_solar_gap_hours:.1f}h of unobserved gaps not bridged."
    elif len(temps) >= int(0.75 * expected_hours) and len(precips) >= int(0.75 * expected_hours):
        q_status = DataQualityStatus.GOOD
        q_note = f"Complete observation window with {total_hours} hourly readings."
    elif temps or precips:
        q_status = DataQualityStatus.PARTIAL
        q_note = f"Partial observation window: {len(temps)}/{expected_hours} hours available."
    else:
        q_status = DataQualityStatus.INSUFFICIENT
        q_note = "Missing critical temperature and precipitation readings."

    return WeatherFeatures(
        source_provider=source_provider,
        provenance_type=provenance_type,
        window_type=window_type,
        window_start=window_start,
        window_end=window_end,
        observed_at=observed_at,
        retrieved_at=None,
        precipitation_mm=precip_total,
        precipitation_hours_count=precip_hours,
        temperature_min_c=t_min,
        temperature_max_c=t_max,
        temperature_mean_c=t_mean,
        relative_humidity_mean_pct=rh_mean,
        relative_humidity_min_pct=rh_min,
        relative_humidity_max_pct=rh_max,
        wind_speed_mean_m_s=wind_mean,
        wind_speed_max_m_s=wind_max,
        wind_measurement_height_m=wind_measurement_height_m,
        wind_height_provenance=wind_height_provenance,
        wind_measurement_type=wind_measurement_type,
        solar_radiation_mj_m2_day=solar_total_mj,
        solar_irradiance_type=irradiance_type,
        solar_radiation_integration_method=integration_method_str or "none",
        has_unbridged_solar_gaps=has_unbridged_solar_gaps,
        unbridged_solar_gap_hours=unbridged_solar_gap_hours,
        timezone=timezone_str,
        temperature_measurement_height_m=temperature_measurement_height_m,
        temperature_height_provenance=temperature_height_provenance,
        provider_et0_mm=provider_et0_total,
        quality_status=q_status,
        quality_note=q_note,
        is_stale=is_stale,
    )

