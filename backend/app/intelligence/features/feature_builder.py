"""Central multimodal feature builder for zone-level agricultural intelligence.

Synthesizes normalized satellite vegetation, meteorological, edaphic (soil),
and crop metadata into a unified, traceable, and quality-aware feature representation.

Scientific and Agronomic Restrictions (per AGENTS.md, AI_SPEC.md, DATA_SOURCES.md):
1. Provenance Integrity: Every feature retains its explicit source provider,
   provenance type (measured vs satellite-derived vs modelled vs farmer-entered),
   and observation timestamps.
2. No Silent Imputation: Missing evidence MUST remain None. Default or fabricated values
   must NEVER be silently substituted for absent sensors or cloudy satellite passes.
3. No Invented Confidence: Quality status must be derived deterministically from physical
   coverage, instrument validity, and freshness thresholds—never from arbitrary synthetic scores.
4. Temporal Misalignment Auditing: Significant time gaps between optical satellite passes
   and weather observations must be explicitly audited and flagged as quality caveats.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.intelligence.config import (
    FeatureFreshnessConfig,
    default_freshness_config,
)
from backend.app.intelligence.features.crop import CropFeatures
from backend.app.intelligence.features.soil import SoilFeatures
from backend.app.intelligence.features.vegetation import ZoneVegetationFeatures
from backend.app.intelligence.features.weather import WeatherFeatures
from backend.app.intelligence.types import DataQualityStatus, ProvenanceType


class MultimodalZoneFeatureSet(BaseModel):
    """Unified zone-level multimodal feature representation for decision support."""

    zone_id: str = Field(..., description="Unique zone identifier")
    farm_id: Optional[str] = Field(default=None, description="Unique farm identifier")
    as_of_time: datetime = Field(..., description="Evaluation reference UTC timestamp")
    builder_version: str = Field(
        default="0.2.0",
        description="Version of the multimodal feature builder"
    )

    # Feature Groups (Each maintains independent provenance and quality)
    vegetation: Optional[ZoneVegetationFeatures] = Field(
        default=None,
        description="Satellite-derived vegetation indices, cover fractions, and SCL statistics"
    )
    weather: Optional[WeatherFeatures] = Field(
        default=None,
        description="Meteorological features (rainfall, temperature, humidity, wind, radiation)"
    )
    soil: Optional[SoilFeatures] = Field(
        default=None,
        description="Soil moisture measurements, texture, and hydraulic properties"
    )
    crop: Optional[CropFeatures] = Field(
        default=None,
        description="Crop species context, phenological stage, planting date, and rooting depth"
    )

    # Overall Synthesized Quality & Provenance
    overall_quality: DataQualityStatus = Field(
        ...,
        description="Synthesized data quality classification across all multimodal inputs"
    )
    domain_qualities: Dict[str, DataQualityStatus] = Field(
        default_factory=dict,
        description="Itemized data quality classification for each present domain"
    )
    stale_domains: List[str] = Field(
        default_factory=list,
        description="Domains whose evidence age exceeds freshness policy"
    )
    suspect_domains: List[str] = Field(
        default_factory=list,
        description="Domains that failed instrument, physical range, or consistency checks"
    )
    provenance_summary: Dict[str, ProvenanceType] = Field(
        default_factory=dict,
        description="Mapping of each present feature domain to its exact data provenance"
    )
    itemized_provenance: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Detailed itemized provenance metadata per feature domain"
    )
    freshness_summary: Dict[str, bool] = Field(
        default_factory=dict,
        description="Mapping of each present feature domain to its freshness evaluation"
    )
    is_provisional_freshness_applied: bool = Field(
        default=True,
        description="Whether freshness checks were governed by provisional operational thresholds"
    )
    missing_evidence: List[str] = Field(
        default_factory=list,
        description="List of feature domains that are absent or unobserved"
    )
    quality_caveats: List[str] = Field(
        default_factory=list,
        description="Audit log of data warnings, missing parameters, or temporal misalignments"
    )


def build_zone_feature_set(
    zone_id: str,
    farm_id: Optional[str] = None,
    as_of_time: Optional[datetime] = None,
    vegetation_features: Optional[ZoneVegetationFeatures] = None,
    weather_features: Optional[WeatherFeatures] = None,
    soil_features: Optional[SoilFeatures] = None,
    crop_features: Optional[CropFeatures] = None,
    config: Optional[FeatureFreshnessConfig] = None,
) -> MultimodalZoneFeatureSet:
    """Build a unified MultimodalZoneFeatureSet from individual domain features.

    Validates cross-domain temporal alignment, aggregates provenance, audits missing
    modalities, and deterministically evaluates overall feature quality.

    Args:
        zone_id: Zone identifier.
        farm_id: Optional farm identifier.
        as_of_time: Reference UTC timestamp for feature evaluation (defaults to now UTC).
        vegetation_features: Optional ZoneVegetationFeatures.
        weather_features: Optional WeatherFeatures.
        soil_features: Optional SoilFeatures.
        crop_features: Optional CropFeatures.
        config: Optional FeatureFreshnessConfig.

    Returns:
        MultimodalZoneFeatureSet containing unified features and quality audit.
    """
    if not zone_id or not zone_id.strip():
        raise ValueError("zone_id cannot be empty or blank.")

    eval_time = as_of_time or datetime.now(timezone.utc)
    cfg = config or default_freshness_config

    provenance_summary: Dict[str, ProvenanceType] = {}
    itemized_provenance: Dict[str, Dict[str, Any]] = {}
    freshness_summary: Dict[str, bool] = {}
    domain_qualities: Dict[str, DataQualityStatus] = {}
    stale_domains: List[str] = []
    suspect_domains: List[str] = []
    missing_evidence: List[str] = []
    quality_caveats: List[str] = []

    # 1. Audit Vegetation Evidence
    if vegetation_features is not None:
        provenance_summary["vegetation"] = vegetation_features.provenance_type
        freshness_summary["vegetation"] = not vegetation_features.is_stale
        domain_qualities["vegetation"] = vegetation_features.quality_status
        if vegetation_features.is_stale:
            stale_domains.append("vegetation")
            quality_caveats.append(
                f"Vegetation evidence is stale (acquired {vegetation_features.observed_at.isoformat()})."
            )
        if vegetation_features.quality_status == DataQualityStatus.SUSPECT:
            suspect_domains.append("vegetation")
            quality_caveats.append("Vegetation evidence is marked SUSPECT due to out-of-bounds index values.")
        elif vegetation_features.quality_status == DataQualityStatus.CLOUD_CONTAMINATED:
            quality_caveats.append("Vegetation evidence is contaminated by clouds or shadows.")
        elif vegetation_features.quality_status == DataQualityStatus.PARTIAL:
            quality_caveats.append("Vegetation evidence has partial or limited spatial coverage.")

        itemized_provenance["vegetation"] = {
            "source_provider": vegetation_features.source_provider,
            "provenance_type": vegetation_features.provenance_type.value,
            "observed_at": vegetation_features.observed_at.isoformat(),
            "scene_id": vegetation_features.scene_id,
            "total_pixels_in_geometry": vegetation_features.total_pixels_in_geometry,
            "valid_vegetation_pixel_count": vegetation_features.valid_vegetation_pixel_count,
            "valid_observation_fraction": vegetation_features.valid_observation_fraction,
            "quality_status": vegetation_features.quality_status.value,
            "is_stale": vegetation_features.is_stale,
        }
    else:
        missing_evidence.append("vegetation")

    # 2. Audit Weather Evidence
    if weather_features is not None:
        provenance_summary["weather"] = weather_features.provenance_type
        freshness_summary["weather"] = not weather_features.is_stale
        domain_qualities["weather"] = weather_features.quality_status
        if weather_features.is_stale:
            stale_domains.append("weather")
            quality_caveats.append(
                f"Weather evidence is stale (observed {weather_features.observed_at.isoformat()})."
            )
        if weather_features.quality_status == DataQualityStatus.SUSPECT:
            suspect_domains.append("weather")
            quality_caveats.append("Weather evidence failed physical meteorology consistency checks.")
        elif weather_features.quality_status == DataQualityStatus.PARTIAL:
            quality_caveats.append("Weather evidence window contains missing hourly observations.")

        itemized_provenance["weather"] = {
            "source_provider": weather_features.source_provider,
            "provenance_type": weather_features.provenance_type.value,
            "observed_at": weather_features.observed_at.isoformat(),
            "window_type": weather_features.window_type.value,
            "timezone": weather_features.timezone,
            "wind_measurement_height_m": weather_features.wind_measurement_height_m,
            "wind_height_provenance": weather_features.wind_height_provenance.value,
            "wind_measurement_type": weather_features.wind_measurement_type,
            "temperature_measurement_height_m": weather_features.temperature_measurement_height_m,
            "temperature_height_provenance": weather_features.temperature_height_provenance.value,
            "solar_radiation_integration_method": weather_features.solar_radiation_integration_method,
            "solar_irradiance_type": weather_features.solar_irradiance_type.value,
            "has_unbridged_solar_gaps": weather_features.has_unbridged_solar_gaps,
            "quality_status": weather_features.quality_status.value,
            "is_stale": weather_features.is_stale,
        }
    else:
        missing_evidence.append("weather")

    # 3. Audit Soil Evidence
    if soil_features is not None:
        provenance_summary["soil"] = soil_features.provenance_type
        freshness_summary["soil"] = not soil_features.is_stale
        domain_qualities["soil"] = soil_features.quality_status
        if soil_features.is_stale:
            stale_domains.append("soil")
            quality_caveats.append(
                f"Soil evidence is stale (observed {soil_features.observed_at.isoformat()})."
            )
        if soil_features.quality_status == DataQualityStatus.SUSPECT:
            suspect_domains.append("soil")
            quality_caveats.append("Soil evidence failed hydraulic consistency checks (e.g. WP >= FC).")
        if soil_features.soil_moisture_m3_m3 is None:
            quality_caveats.append("Soil moisture measurement is absent; only static soil properties available.")

        itemized_provenance["soil"] = {
            "source_provider": soil_features.source_provider,
            "provenance_type": soil_features.provenance_type.value,
            "observed_at": soil_features.observed_at.isoformat(),
            "depth_min_cm": soil_features.depth_min_cm,
            "depth_max_cm": soil_features.depth_max_cm,
            "soil_texture": soil_features.soil_texture.value if soil_features.soil_texture else None,
            "ph_method": soil_features.ph_method,
            "ec_method": soil_features.ec_method,
            "moisture_sensor_type": soil_features.moisture_sensor_type,
            "quality_status": soil_features.quality_status.value,
            "is_stale": soil_features.is_stale,
        }
    else:
        missing_evidence.append("soil")

    # 4. Audit Crop Evidence
    if crop_features is not None:
        provenance_summary["crop"] = crop_features.provenance_type
        freshness_summary["crop"] = not crop_features.is_stale
        domain_qualities["crop"] = crop_features.quality_status
        if crop_features.is_stale:
            stale_domains.append("crop")
            quality_caveats.append(
                f"Crop record is stale (recorded {crop_features.observed_at.isoformat()})."
            )
        if crop_features.quality_status == DataQualityStatus.SUSPECT:
            suspect_domains.append("crop")
            quality_caveats.append("Crop record failed phenological consistency checks.")
        if crop_features.growth_stage is None:
            quality_caveats.append("Crop growth stage is unrecorded.")
        if crop_features.planting_date is None:
            quality_caveats.append("Crop planting date is unrecorded.")

        itemized_provenance["crop"] = {
            "source_provider": crop_features.source_provider,
            "provenance_type": crop_features.provenance_type.value,
            "observed_at": crop_features.observed_at.isoformat(),
            "crop_type": crop_features.crop_type,
            "growth_stage": crop_features.growth_stage,
            "planting_date": crop_features.planting_date.isoformat() if crop_features.planting_date else None,
            "quality_status": crop_features.quality_status.value,
            "is_stale": crop_features.is_stale,
        }
    else:
        missing_evidence.append("crop")

    # 5. Temporal Alignment Cross-Check
    if vegetation_features is not None and weather_features is not None:
        gap_seconds = abs((vegetation_features.observed_at - weather_features.observed_at).total_seconds())
        gap_days = gap_seconds / 86400.0
        if gap_days > cfg.temporal_alignment_warning_days:
            quality_caveats.append(
                f"Temporal misalignment: Satellite pass ({vegetation_features.observed_at.date()}) and "
                f"weather window ({weather_features.observed_at.date()}) diverge by {gap_days:.1f} days "
                f"(exceeds {cfg.temporal_alignment_warning_days}d threshold)."
            )

    # 6. Overall Quality Evaluation
    # Rule A: Complete absence of evidence
    if len(missing_evidence) == 4:
        overall_quality = DataQualityStatus.INSUFFICIENT
        quality_caveats.append("No multimodal evidence provided for this zone.")

    # Rule B: Missing both primary dynamic drivers (vegetation AND weather)
    elif "vegetation" in missing_evidence and "weather" in missing_evidence:
        overall_quality = DataQualityStatus.INSUFFICIENT
        quality_caveats.append("Crucial dynamic evidence missing: both satellite and weather data are absent.")

    # Rule C: Suspect evidence present in any active domain
    elif len(suspect_domains) > 0 or any(
        feat.quality_status == DataQualityStatus.SUSPECT
        for feat in [vegetation_features, weather_features, soil_features, crop_features]
        if feat is not None
    ):
        overall_quality = DataQualityStatus.SUSPECT
        quality_caveats.append("One or more evidence domains failed physical or sensor quality checks.")

    # Rule D: Stale evidence in critical dynamic domains
    elif "vegetation" in stale_domains or "weather" in stale_domains:
        overall_quality = DataQualityStatus.STALE

    # Rule E: Cloud contamination in satellite imagery
    elif vegetation_features is not None and vegetation_features.quality_status == DataQualityStatus.CLOUD_CONTAMINATED:
        overall_quality = DataQualityStatus.CLOUD_CONTAMINATED

    # Rule F: Missing modalities (e.g. soil sensor missing, crop metadata missing)
    elif missing_evidence or any(
        feat.quality_status == DataQualityStatus.PARTIAL
        for feat in [vegetation_features, weather_features, soil_features, crop_features]
        if feat is not None
    ):
        overall_quality = DataQualityStatus.PARTIAL

    # Rule G: Complete, fresh, and valid multimodal evidence
    else:
        overall_quality = DataQualityStatus.GOOD

    return MultimodalZoneFeatureSet(
        zone_id=zone_id,
        farm_id=farm_id,
        as_of_time=eval_time,
        builder_version="0.2.0",
        vegetation=vegetation_features,
        weather=weather_features,
        soil=soil_features,
        crop=crop_features,
        overall_quality=overall_quality,
        domain_qualities=domain_qualities,
        stale_domains=stale_domains,
        suspect_domains=suspect_domains,
        provenance_summary=provenance_summary,
        itemized_provenance=itemized_provenance,
        freshness_summary=freshness_summary,
        is_provisional_freshness_applied=cfg.is_provisional,
        missing_evidence=missing_evidence,
        quality_caveats=quality_caveats,
    )

