"""Tests for weather feature engineering, unit conversions, and aggregation."""

from datetime import datetime, timezone, timedelta
import numpy as np
import pytest

from backend.app.intelligence.features.weather import (
    HourlyWeatherReading,
    WeatherFeatures,
    aggregate_hourly_weather,
    kmh_to_ms,
    kwh_m2_to_mj_m2,
    ms_to_kmh,
    wm2_hourly_to_mj_m2,
)
from backend.app.intelligence.types import (
    DataQualityStatus,
    ProvenanceType,
    WeatherWindowType,
)


def test_weather_unit_conversions():
    """Verify physical unit conversions against exact mathematical references."""
    # 1. Wind speed: 36 km/h = 10 m/s
    assert pytest.approx(kmh_to_ms(36.0), abs=1e-6) == 10.0
    assert pytest.approx(kmh_to_ms(0.0), abs=1e-6) == 0.0
    assert pytest.approx(ms_to_kmh(10.0), abs=1e-6) == 36.0

    with pytest.raises(ValueError, match="cannot be negative"):
        kmh_to_ms(-5.0)

    # 2. Solar irradiance to energy: 1000 W/m² for 1 hour = 3.6 MJ/m²
    # 1000 W = 1000 J/s * 3600 s = 3,600,000 J = 3.6 MJ
    assert pytest.approx(wm2_hourly_to_mj_m2(1000.0), abs=1e-6) == 3.6

    # 3. Energy: 1 kWh = 3.6 MJ
    assert pytest.approx(kwh_m2_to_mj_m2(5.0), abs=1e-6) == 18.0


def test_24h_weather_aggregation_hand_calculated():
    """Verify daily aggregation over 24 hours against hand-calculated references."""
    start_time = datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)

    readings = []
    # Synthetic 24-hour diurnal cycle
    # Temperatures: 15.0°C at night rising to 35.0°C at mid-day
    # Rain at hour 2 (5.0 mm), hour 14 (12.5 mm), hour 20 (2.5 mm) -> Total = 20.0 mm
    temps = [
        15.0, 15.0, 16.0, 17.0, 18.0, 20.0,
        24.0, 28.0, 31.0, 33.0, 35.0, 34.0,
        32.0, 30.0, 28.0, 26.0, 24.0, 22.0,
        20.0, 19.0, 18.0, 17.0, 16.0, 15.0,
    ]
    # Sum of temps = 544.0 -> Mean = 544.0 / 24 = 22.6667 °C
    # Min = 15.0 °C, Max = 35.0 °C

    precips = [0.0] * 24
    precips[2] = 5.0
    precips[14] = 12.5
    precips[20] = 2.5
    # Total rain = 20.0 mm, 3 rain hours

    rhs = [80.0] * 12 + [40.0] * 12
    # Mean RH = (80 * 12 + 40 * 12) / 24 = 60.0%
    # Min RH = 40.0%, Max RH = 80.0%

    winds = [2.0] * 20 + [5.0] * 4
    # Mean wind = (2.0 * 20 + 5.0 * 4) / 24 = 60.0 / 24 = 2.50 m/s
    # Max wind = 5.0 m/s

    # Solar radiation: 12 hours night (0), 12 hours daylight (500 W/m² each)
    # Total solar = 12 hours * 500 W/m²
    # 500 W/m² for 1 hr = 1.8 MJ/m² -> 12 * 1.8 = 21.6 MJ/m²/day
    rads = [0.0] * 6 + [500.0] * 12 + [0.0] * 6

    for h in range(24):
        t = start_time + timedelta(hours=h)
        readings.append(HourlyWeatherReading(
            timestamp=t,
            temperature_2m_c=temps[h],
            precipitation_mm=precips[h],
            relative_humidity_2m_pct=rhs[h],
            wind_speed_10m_m_s=winds[h],
            shortwave_radiation_w_m2=rads[h],
            et0_fao_evapotranspiration_mm=0.2 if rads[h] > 0 else 0.05,
        ))

    summary = aggregate_hourly_weather(
        hourly_readings=readings,
        window_type=WeatherWindowType.DAILY_SUMMARY,
        source_provider="Open-Meteo",
        provenance_type=ProvenanceType.PROVIDER_MODELLED,
        as_of_time=datetime(2026, 11, 2, tzinfo=timezone.utc),
    )

    assert summary.source_provider == "Open-Meteo"
    assert summary.provenance_type == ProvenanceType.PROVIDER_MODELLED
    assert summary.window_type == WeatherWindowType.DAILY_SUMMARY
    assert summary.quality_status == DataQualityStatus.GOOD
    assert summary.is_stale == False

    # Precipitation
    assert pytest.approx(summary.precipitation_mm, abs=1e-4) == 20.0
    assert summary.precipitation_hours_count == 3

    # Temperature
    assert pytest.approx(summary.temperature_min_c, abs=1e-4) == 15.0
    assert pytest.approx(summary.temperature_max_c, abs=1e-4) == 35.0
    # Sum of 24 hourly temps = 553.0 -> Mean = 553.0 / 24 = 23.0417 °C
    assert pytest.approx(summary.temperature_mean_c, abs=1e-4) == 23.0417

    # Relative humidity
    assert pytest.approx(summary.relative_humidity_min_pct, abs=1e-4) == 40.0
    assert pytest.approx(summary.relative_humidity_max_pct, abs=1e-4) == 80.0
    assert pytest.approx(summary.relative_humidity_mean_pct, abs=1e-4) == 60.0

    # Wind speed
    assert pytest.approx(summary.wind_speed_mean_m_s, abs=1e-4) == 2.50
    assert pytest.approx(summary.wind_speed_max_m_s, abs=1e-4) == 5.0

    # Solar radiation
    assert pytest.approx(summary.solar_radiation_mj_m2_day, abs=1e-4) == 21.60

    # Provider ET0: 12 * 0.2 + 12 * 0.05 = 2.4 + 0.6 = 3.0 mm
    assert pytest.approx(summary.provider_et0_mm, abs=1e-4) == 3.0


def test_weather_physical_consistency_validation():
    """Verify that physically impossible weather values raise validation errors."""
    now = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)

    # 1. Min temp > Max temp
    with pytest.raises(ValueError, match="min .* > max"):
        WeatherFeatures(
            window_start=now - timedelta(days=1),
            window_end=now,
            observed_at=now,
            temperature_min_c=30.0,
            temperature_max_c=20.0,
            quality_status=DataQualityStatus.GOOD,
        )

    # 2. Mean temp outside [min, max]
    with pytest.raises(ValueError, match="mean .* < min"):
        WeatherFeatures(
            window_start=now - timedelta(days=1),
            window_end=now,
            observed_at=now,
            temperature_min_c=20.0,
            temperature_max_c=30.0,
            temperature_mean_c=15.0,
            quality_status=DataQualityStatus.GOOD,
        )

    # 3. Min RH > Max RH
    with pytest.raises(ValueError, match="min .* > max"):
        WeatherFeatures(
            window_start=now - timedelta(days=1),
            window_end=now,
            observed_at=now,
            relative_humidity_min_pct=80.0,
            relative_humidity_max_pct=50.0,
            quality_status=DataQualityStatus.GOOD,
        )


def test_weather_missing_evidence_preservation():
    """Verify that missing weather fields are preserved as None without zero-filling."""
    t = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
    # Only temperature recorded, no rain gauge or solar sensor
    reading = HourlyWeatherReading(
        timestamp=t,
        temperature_2m_c=25.0,
        precipitation_mm=None,
        shortwave_radiation_w_m2=None,
    )

    summary = aggregate_hourly_weather(
        hourly_readings=[reading],
        window_type=WeatherWindowType.HOURLY,
    )

    assert summary.temperature_mean_c == 25.0
    assert summary.precipitation_mm is None  # MUST remain None, NOT 0.0
    assert summary.solar_radiation_mj_m2_day is None


def test_weather_metadata_preservation_and_variable_interval_solar_integration():
    """Verify wind height, sensor height, timezone, and non-uniform solar radiation integration.

    Per Phase 2.1:
    - Native wind height (10.0m) and measurement type ('time_averaged_mean') are preserved.
    - No 10m-to-2m wind conversion is applied in Phase 2 (reserved for Phase 3).
    - Solar irradiance is integrated across actual elapsed time intervals dt.
    - Expected FAO-56 inputs are documented.
    """
    t0 = datetime(2026, 11, 1, 8, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(minutes=30)  # dt = 1800 s

    readings = [
        HourlyWeatherReading(
            timestamp=t0,
            temperature_2m_c=22.0,
            shortwave_radiation_w_m2=400.0,
            wind_speed_10m_m_s=3.0,
        ),
        HourlyWeatherReading(
            timestamp=t1,
            temperature_2m_c=24.0,
            shortwave_radiation_w_m2=600.0,
            wind_speed_10m_m_s=4.0,
        ),
    ]

    summary = aggregate_hourly_weather(
        hourly_readings=readings,
        window_type=WeatherWindowType.HOURLY,
        source_provider="IMD Automatic Weather Station",
        provenance_type=ProvenanceType.SENSOR_MEASURED,
    )

    # 1. Height and metadata preservation
    assert summary.wind_measurement_height_m == 10.0
    assert summary.wind_measurement_type == "time_averaged_mean"
    assert summary.temperature_measurement_height_m == 2.0
    assert summary.timezone == "UTC"
    assert summary.solar_radiation_integration_method == "interval_mean_time_integration"

    # 2. Wind speed must remain native (mean of 3.0 and 4.0 = 3.5 m/s); NO conversion factor applied
    assert pytest.approx(summary.wind_speed_mean_m_s, abs=1e-4) == 3.5

    # 3. FAO-56 input documentation
    assert "FAO-56 Penman-Monteith" in summary.fao56_inputs_documentation
    assert "logarithmic wind profile" in summary.fao56_inputs_documentation

    # 4. Solar radiation integration:
    # Reading 0: 400 W/m² * 1800 s = 720,000 J/m² = 0.72 MJ/m²
    # Reading 1: 600 W/m² * 1800 s = 1,080,000 J/m² = 1.08 MJ/m²
    # Total = 1.80 MJ/m²
    assert pytest.approx(summary.solar_radiation_mj_m2_day, abs=1e-3) == 1.80


def test_instantaneous_solar_radiation_trapezoidal_integration():
    """Verify trapezoidal quadrature for instantaneous spot flux measurements.

    Hand calculation:
    Reading 0 at 08:00: I_0 = 400 W/m²
    Reading 1 at 08:30: I_1 = 600 W/m² (dt = 1800 s)
    Trapezoid energy = 0.5 * (400 + 600) * 1800 / 1e6 = 500 * 1800 / 1e6 = 0.90 MJ/m²

    Reading 2 at 09:15: I_2 = 800 W/m² (dt = 2700 s)
    Trapezoid energy = 0.5 * (600 + 800) * 2700 / 1e6 = 700 * 2700 / 1e6 = 1.89 MJ/m²

    Total cumulative energy = 0.90 + 1.89 = 2.79 MJ/m²
    """
    from backend.app.intelligence.types import SolarIrradianceType

    t0 = datetime(2026, 11, 1, 8, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(minutes=30)  # dt = 1800 s
    t2 = t1 + timedelta(minutes=45)  # dt = 2700 s

    readings = [
        HourlyWeatherReading(timestamp=t0, shortwave_radiation_w_m2=400.0),
        HourlyWeatherReading(timestamp=t1, shortwave_radiation_w_m2=600.0),
        HourlyWeatherReading(timestamp=t2, shortwave_radiation_w_m2=800.0),
    ]

    summary = aggregate_hourly_weather(
        hourly_readings=readings,
        window_type=WeatherWindowType.HOURLY,
        irradiance_type=SolarIrradianceType.INSTANTANEOUS,
    )

    assert summary.solar_irradiance_type == SolarIrradianceType.INSTANTANEOUS
    assert summary.solar_radiation_integration_method == "trapezoidal_instantaneous_quadrature"
    assert pytest.approx(summary.solar_radiation_mj_m2_day, abs=1e-3) == 2.79
    assert summary.has_unbridged_solar_gaps == False


def test_solar_radiation_unbridged_missing_intervals():
    """Verify that unobserved time gaps (> max_solar_gap_hours) are NEVER bridged silently.

    Setup:
    Reading at 08:00 (500 W/m²)
    Reading at 09:00 (600 W/m²)
    5-hour missing data gap! (Next reading at 14:00, 400 W/m²)
    Reading at 15:00 (300 W/m²)

    Expected:
    - Gap between 09:00 and 14:00 (5.0 hours) exceeds max_solar_gap_hours (1.5h).
    - Gap is NOT bridged.
    - has_unbridged_solar_gaps is True.
    - quality_status is downgraded to PARTIAL.
    - integration_method reflects unbridged gaps.
    """
    from backend.app.intelligence.types import SolarIrradianceType

    t0 = datetime(2026, 11, 1, 8, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(hours=1)
    t2 = t1 + timedelta(hours=5)  # 5-hour unobserved gap!
    t3 = t2 + timedelta(hours=1)

    readings = [
        HourlyWeatherReading(timestamp=t0, temperature_2m_c=20.0, shortwave_radiation_w_m2=500.0),
        HourlyWeatherReading(timestamp=t1, temperature_2m_c=22.0, shortwave_radiation_w_m2=600.0),
        HourlyWeatherReading(timestamp=t2, temperature_2m_c=30.0, shortwave_radiation_w_m2=400.0),
        HourlyWeatherReading(timestamp=t3, temperature_2m_c=29.0, shortwave_radiation_w_m2=300.0),
    ]

    summary = aggregate_hourly_weather(
        hourly_readings=readings,
        window_type=WeatherWindowType.HOURLY,
        irradiance_type=SolarIrradianceType.INTERVAL_MEAN,
        max_solar_gap_hours=1.5,
    )

    assert summary.has_unbridged_solar_gaps == True
    assert summary.unbridged_solar_gap_hours >= 4.0
    assert summary.quality_status == DataQualityStatus.PARTIAL
    assert "with_unbridged_gaps" in summary.solar_radiation_integration_method
    assert "not bridged" in summary.quality_note


def test_weather_measurement_height_provenance():
    """Verify height provenance distinguishes provider-reported, sensor-measured, convention-assumed, and unknown.

    Ensures Phase 3 can reject or handle unknown heights when logarithmic wind profile conversion is required.
    """
    from backend.app.intelligence.types import MeasurementHeightProvenance

    t0 = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)
    reading = HourlyWeatherReading(timestamp=t0, wind_speed_10m_m_s=3.0, temperature_2m_c=25.0)

    # Case A: Explicitly sensor-measured on mast
    summary_sensor = aggregate_hourly_weather(
        hourly_readings=[reading],
        wind_measurement_height_m=3.0,
        wind_height_provenance=MeasurementHeightProvenance.SENSOR_MEASURED,
        temperature_measurement_height_m=1.5,
        temperature_height_provenance=MeasurementHeightProvenance.SENSOR_MEASURED,
    )
    assert summary_sensor.wind_measurement_height_m == 3.0
    assert summary_sensor.wind_height_provenance == MeasurementHeightProvenance.SENSOR_MEASURED
    assert summary_sensor.temperature_measurement_height_m == 1.5
    assert summary_sensor.temperature_height_provenance == MeasurementHeightProvenance.SENSOR_MEASURED

    # Case B: Unknown height (e.g. uncalibrated or unspecified station)
    summary_unknown = aggregate_hourly_weather(
        hourly_readings=[reading],
        wind_measurement_height_m=None,
        wind_height_provenance=MeasurementHeightProvenance.UNKNOWN,
    )
    assert summary_unknown.wind_measurement_height_m is None
    assert summary_unknown.wind_height_provenance == MeasurementHeightProvenance.UNKNOWN

    # Verify FAO-56 documentation states Phase 3 height rule
    assert "wind_height_provenance != UNKNOWN" in summary_unknown.fao56_inputs_documentation
    assert "reject conversion" in summary_unknown.fao56_inputs_documentation


