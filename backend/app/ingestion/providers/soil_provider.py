"""Soil measurement and laboratory test data ingestion provider.

Handles ingestion from:
1. In-situ capacitive / TDR root-zone soil moisture probes (sensor_measured).
2. Certified laboratory physicochemical soil test reports (laboratory_analyzed).
3. Farmer management entry records (farmer_entered).
4. Provider-modelled gridded soil moisture (provider_modelled, e.g. Open-Meteo).

Scientific and Agronomic Restrictions (per AGENTS.md, AI_SPEC.md, DATA_SOURCES.md):
- NEVER infer root-zone soil moisture from optical satellite vegetation indices (NDVI/NDMI).
- Explicit measurement depth (depth_min_cm, depth_max_cm) must be retained.
- Volumetric moisture values must be in physical units m³/m³ (or converted from %).
- Provenance type must be accurately recorded; modelled gridded values must NEVER be
  represented as in-situ field sensor measurements.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.ingestion.providers.base import BaseProvider, ProviderFetchResult


class SoilMeasurementProvider(BaseProvider):
    """Provider for in-situ probe observations, lab reports, and modelled soil layers."""

    def __init__(self, timeout_seconds: float = 5.0) -> None:
        super().__init__(timeout_seconds=timeout_seconds)

    @property
    def provider_name(self) -> str:
        return "Soil Evidence Adapter"

    def health_check(self) -> bool:
        return True

    def ingest_sensor_reading(
        self,
        sensor_id: str,
        depth_min_cm: float,
        depth_max_cm: float,
        volumetric_water_content: float,
        observed_at: datetime,
        battery_pct: Optional[float] = None,
        soil_temp_c: Optional[float] = None,
    ) -> ProviderFetchResult:
        """Package in-situ soil moisture sensor telemetry."""
        retrieved_at = datetime.now(timezone.utc)
        payload = {
            "source_type": "sensor_measured",
            "sensor_id": sensor_id,
            "depth_min_cm": depth_min_cm,
            "depth_max_cm": depth_max_cm,
            "volumetric_water_content_m3_m3": round(volumetric_water_content, 4),
            "observed_at": observed_at.isoformat(),
            "soil_temperature_c": soil_temp_c,
            "battery_pct": battery_pct,
        }
        return ProviderFetchResult(
            provider_name=f"In-Situ Sensor ({sensor_id})",
            endpoint_url="local://telemetry/soil",
            retrieved_at=retrieved_at,
            status_code=200,
            payload=payload,
            is_live=True,
            metadata={"provenance": "sensor_measured"},
        )

    def ingest_lab_report(
        self,
        report_id: str,
        lab_name: str,
        sample_date: datetime,
        texture_class: str,
        field_capacity_m3_m3: float,
        wilting_point_m3_m3: float,
        ph: Optional[float] = None,
        ec_ds_m: Optional[float] = None,
        organic_carbon_pct: Optional[float] = None,
    ) -> ProviderFetchResult:
        """Package certified laboratory soil analysis report."""
        retrieved_at = datetime.now(timezone.utc)
        payload = {
            "source_type": "laboratory_analyzed",
            "report_id": report_id,
            "lab_name": lab_name,
            "sample_date": sample_date.isoformat(),
            "texture_class": texture_class.lower(),
            "field_capacity_m3_m3": round(field_capacity_m3_m3, 4),
            "wilting_point_m3_m3": round(wilting_point_m3_m3, 4),
            "available_water_capacity_m3_m3": round(field_capacity_m3_m3 - wilting_point_m3_m3, 4),
            "ph": ph,
            "ec_ds_m": ec_ds_m,
            "organic_carbon_pct": organic_carbon_pct,
        }
        return ProviderFetchResult(
            provider_name=f"Soil Lab ({lab_name})",
            endpoint_url="local://lab_reports",
            retrieved_at=retrieved_at,
            status_code=200,
            payload=payload,
            is_live=True,
            metadata={"provenance": "laboratory_analyzed", "report_id": report_id},
        )
