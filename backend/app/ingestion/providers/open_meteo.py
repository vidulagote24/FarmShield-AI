"""Open-Meteo weather and meteorological data ingestion provider.

Connects to Open-Meteo Forecast and Historical Weather APIs to retrieve
high-resolution hourly meteorological variables and modelled soil moisture estimates.

Scientific and Provenance Requirements (per AGENTS.md, AI_SPEC.md, DATA_SOURCES.md):
- Retains provider identification: 'Open-Meteo Forecast API'
- Uses UTC timestamps explicitly.
- Explicit physical units: mm (precipitation), °C (temperature), % (relative humidity),
  m/s (wind speed), W/m² (solar irradiance), mm (FAO ET0).
- Modelled gridded soil moisture (0-7cm, 7-28cm) must retain provenance as PROVIDER_MODELLED
  and NEVER be represented as field sensor measurements.
"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional
import urllib.error
import urllib.parse
import urllib.request

from app.ingestion.providers.base import BaseProvider, ProviderFetchResult


class OpenMeteoProvider(BaseProvider):
    """Client for Open-Meteo meteorological reanalysis and forecast endpoints."""

    FORECAST_BASE_URL = "https://api.open-meteo.com/v1/forecast"
    HISTORICAL_BASE_URL = "https://archive-api.open-meteo.com/v1/archive"

    HOURLY_VARIABLES = [
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation",
        "wind_speed_10m",
        "shortwave_radiation_instant",
        "et0_fao_evapotranspiration",
        "soil_moisture_0_to_7cm",
        "soil_moisture_7_to_28cm",
    ]

    def __init__(self, timeout_seconds: float = 12.0) -> None:
        super().__init__(timeout_seconds=timeout_seconds)

    @property
    def provider_name(self) -> str:
        return "Open-Meteo"

    def health_check(self) -> bool:
        """Verify Open-Meteo API availability with a minimal query."""
        try:
            params = {
                "latitude": 18.15,
                "longitude": 74.58,
                "hourly": "temperature_2m",
                "forecast_days": 1,
            }
            url = f"{self.FORECAST_BASE_URL}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url, headers={"User-Agent": "FarmShield-AI/1.0"})
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                return resp.status == 200
        except Exception:
            return False

    def fetch_forecast(
        self,
        latitude: float,
        longitude: float,
        forecast_days: int = 3,
        past_days: int = 1,
        fallback_fixture: Optional[Dict[str, Any]] = None,
    ) -> ProviderFetchResult:
        """Fetch hourly weather forecast and recent reanalysis from Open-Meteo.

        Args:
            latitude: Geographic latitude in decimal degrees.
            longitude: Geographic longitude in decimal degrees.
            forecast_days: Number of forecast days (1 to 7).
            past_days: Number of past reanalysis days (0 to 7).
            fallback_fixture: Optional fixture data to use when network is unreachable.

        Returns:
            ProviderFetchResult containing parsed response and retrieval metadata.
        """
        retrieved_at = datetime.now(timezone.utc)
        params = {
            "latitude": round(latitude, 4),
            "longitude": round(longitude, 4),
            "hourly": ",".join(self.HOURLY_VARIABLES),
            "wind_speed_unit": "ms",
            "timezone": "UTC",
            "forecast_days": max(1, min(forecast_days, 14)),
            "past_days": max(0, min(past_days, 7)),
        }
        url = f"{self.FORECAST_BASE_URL}?{urllib.parse.urlencode(params)}"

        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "FarmShield-AI/1.0 (Climate-Resilient Agriculture Platform)",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                status_code = resp.status
                payload = json.loads(resp.read().decode("utf-8"))
                return ProviderFetchResult(
                    provider_name=self.provider_name,
                    endpoint_url=url,
                    retrieved_at=retrieved_at,
                    status_code=status_code,
                    payload=payload,
                    is_live=True,
                    metadata={
                        "latitude": latitude,
                        "longitude": longitude,
                        "forecast_days": forecast_days,
                        "past_days": past_days,
                        "source": "Open-Meteo Forecast API",
                    },
                )
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as err:
            if fallback_fixture is not None:
                return ProviderFetchResult(
                    provider_name=self.provider_name,
                    endpoint_url=url,
                    retrieved_at=retrieved_at,
                    status_code=200,
                    payload=fallback_fixture,
                    is_live=False,
                    metadata={
                        "latitude": latitude,
                        "longitude": longitude,
                        "note": "Loaded from recorded fallback fixture due to network unavailability",
                        "network_error": str(err),
                    },
                )
            return ProviderFetchResult(
                provider_name=self.provider_name,
                endpoint_url=url,
                retrieved_at=retrieved_at,
                status_code=503,
                payload={},
                is_live=False,
                error_message=f"Open-Meteo network request failed: {err}",
            )
