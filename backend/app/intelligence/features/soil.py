"""Soil feature engineering and measurement validation.

Supports normalized evidence from in-situ soil moisture sensors, laboratory
physicochemical tests, farmer-entered records, or background soil maps.

Scientific and Agronomic Restrictions (per AGENTS.md, AI_SPEC.md, DATA_SOURCES.md):
1. Root-zone soil moisture MUST NOT be inferred from NDVI, NDMI, or satellite reflectance.
   Spectral indices measure canopy properties, not sub-surface soil moisture.
2. Missing soil properties MUST remain None. Assumed or fabricated default measurements
   must NEVER be silently substituted for real soil evidence.
3. Every soil observation must retain its measurement depth (depth_min_cm, depth_max_cm),
   provenance type (sensor_measured, laboratory_analyzed, farmer_entered, provider_modelled),
   units, and observation timestamp.
4. Physical consistency rules: Wilting Point < Field Capacity <= 1.0 m³/m³;
   Available Water Capacity = Field Capacity - Wilting Point.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator

from backend.app.intelligence.config import default_freshness_config
from backend.app.intelligence.types import (
    DataQualityStatus,
    ProvenanceType,
    SoilTextureClass,
)

STANDARD_SOIL_CAVEATS: List[str] = [
    "Soil moisture is a localized, depth-specific physical measurement and CANNOT be inferred from satellite NDVI or NDMI.",
    "Gridded soil maps (e.g. SoilGrids) represent spatial model estimates with inherent uncertainty and are not live field readings.",
    "Farmer-entered soil data reflects management recall and must not be reported as instrument-measured data.",
    "Analytical Method Warning: Electrical conductivity from different extraction ratios (e.g. 1:5 extract vs saturated paste ECe) are NOT directly interchangeable. Similarly, 1:2.5 and 1:5 pH methods differ systematically.",
]


class SoilFeatures(BaseModel):
    """Structured soil context and moisture measurements for a zone or farm."""

    source_provider: str = Field(
        ...,
        description="Data source: sensor model, laboratory report ID, or 'Farmer Manual Entry'"
    )
    provenance_type: ProvenanceType = Field(
        ...,
        description="Provenance classification: sensor_measured, laboratory_analyzed, farmer_entered, or provider_modelled"
    )
    observed_at: datetime = Field(
        ...,
        description="UTC timestamp when the measurement or soil sample was taken"
    )
    retrieved_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp when data was ingested into the system"
    )

    # Measurement Depth
    depth_min_cm: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Top of the measured soil layer in cm"
    )
    depth_max_cm: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Bottom of the measured soil layer in cm"
    )

    # Volumetric Soil Moisture (m³/m³, typically 0.05 to 0.55 for mineral soils)
    soil_moisture_m3_m3: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Volumetric soil water content (m³/m³)"
    )

    # Soil Texture
    soil_texture: Optional[SoilTextureClass] = Field(
        default=None,
        description="USDA soil texture classification"
    )

    # Hydraulic Properties (m³/m³)
    field_capacity_m3_m3: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Volumetric water content at Field Capacity (-33 kPa / -0.33 bar) in m³/m³"
    )
    wilting_point_m3_m3: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Volumetric water content at Permanent Wilting Point (-1500 kPa / -15 bar) in m³/m³"
    )
    available_water_capacity_m3_m3: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Available Water Capacity (AWC = FC - WP) in m³/m³"
    )

    # Physicochemical Properties
    soil_ph: Optional[float] = Field(
        default=None,
        ge=3.0,
        le=11.0,
        description="Soil pH (acidity/alkalinity) measured in water suspension"
    )
    ph_method: Optional[str] = Field(
        default=None,
        description="Analytical method for soil pH (e.g., '1:2.5_water', '1:5_water', 'saturated_paste')"
    )
    electrical_conductivity_ds_m: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Electrical conductivity in dS/m"
    )
    ec_method: Optional[str] = Field(
        default=None,
        description="Analytical extraction method for EC (e.g., 'saturated_paste_extract_ECe', '1:2.5_extract', '1:5_extract')"
    )
    moisture_sensor_type: Optional[str] = Field(
        default=None,
        description="Physical sensor technology if measured: 'capacitance_fdr', 'tdr', 'gravimetric', etc."
    )

    # Quality & Freshness Assessment
    quality_status: DataQualityStatus = Field(
        ...,
        description="Quality classification of soil evidence"
    )
    quality_note: Optional[str] = Field(
        default=None,
        description="Detailed quality note, caveats, or missing field audit"
    )
    is_stale: bool = Field(
        default=False,
        description="Whether observation exceeds freshness policy (dynamic vs static)"
    )
    scientific_caveats: List[str] = Field(
        default_factory=lambda: STANDARD_SOIL_CAVEATS.copy(),
        description="Mandatory scientific restrictions and caveats"
    )

    @model_validator(mode="after")
    def validate_soil_physics(self) -> "SoilFeatures":
        """Validate physical and hydraulic consistency of soil measurements."""
        fc = self.field_capacity_m3_m3
        wp = self.wilting_point_m3_m3
        awc = self.available_water_capacity_m3_m3
        sm = self.soil_moisture_m3_m3

        # 1. Hydraulic limits
        if fc is not None and wp is not None:
            if wp >= fc:
                raise ValueError(
                    f"Physically impossible soil hydraulics: Wilting Point ({wp:.3f}) >= Field Capacity ({fc:.3f})"
                )
            expected_awc = fc - wp
            if awc is not None and abs(awc - expected_awc) > 0.01:
                raise ValueError(
                    f"AWC inconsistency: provided AWC ({awc:.3f}) does not match FC - WP ({expected_awc:.3f})"
                )

        # 2. Depth limits
        if self.depth_min_cm is not None and self.depth_max_cm is not None:
            if self.depth_min_cm >= self.depth_max_cm:
                raise ValueError(
                    f"Invalid soil depth layer: depth_min ({self.depth_min_cm} cm) >= depth_max ({self.depth_max_cm} cm)"
                )

        return self


def create_soil_features(
    source_provider: str,
    provenance_type: ProvenanceType,
    observed_at: datetime,
    depth_min_cm: Optional[float] = None,
    depth_max_cm: Optional[float] = None,
    soil_moisture_m3_m3: Optional[float] = None,
    soil_texture: Optional[SoilTextureClass] = None,
    field_capacity_m3_m3: Optional[float] = None,
    wilting_point_m3_m3: Optional[float] = None,
    available_water_capacity_m3_m3: Optional[float] = None,
    soil_ph: Optional[float] = None,
    ph_method: Optional[str] = None,
    electrical_conductivity_ds_m: Optional[float] = None,
    ec_method: Optional[str] = None,
    moisture_sensor_type: Optional[str] = None,
    as_of_time: Optional[datetime] = None,
    dynamic_stale_days: Optional[float] = None,
    static_stale_days: Optional[float] = None,
) -> SoilFeatures:
    """Construct and validate a structured SoilFeatures instance.

    Automatically computes available_water_capacity_m3_m3 if FC and WP are supplied,
    and applies domain-specific freshness policies (high-frequency moisture vs static texture).

    Args:
        source_provider: Sensor identifier, lab name, or survey reference.
        provenance_type: Data provenance.
        observed_at: Observation UTC timestamp.
        depth_min_cm: Top depth of measurement in cm.
        depth_max_cm: Bottom depth of measurement in cm.
        soil_moisture_m3_m3: Volumetric moisture content (m³/m³).
        soil_texture: USDA texture class.
        field_capacity_m3_m3: Volumetric field capacity (m³/m³).
        wilting_point_m3_m3: Volumetric permanent wilting point (m³/m³).
        available_water_capacity_m3_m3: Optional explicit AWC (m³/m³).
        soil_ph: Soil pH value.
        electrical_conductivity_ds_m: EC in dS/m.
        as_of_time: Reference evaluation timestamp.
        dynamic_stale_days: Freshness threshold for dynamic moisture readings (defaults to 3d).
        static_stale_days: Freshness threshold for static texture/AWC (defaults to 365d).

    Returns:
        Validated SoilFeatures object.
    """
    max_dyn_stale = (
        dynamic_stale_days if dynamic_stale_days is not None
        else default_freshness_config.dynamic_soil_moisture_stale_days
    )
    max_static_stale = (
        static_stale_days if static_stale_days is not None
        else default_freshness_config.static_soil_stale_days
    )

    # Derive AWC if not provided but FC and WP are known
    awc = available_water_capacity_m3_m3
    if awc is None and field_capacity_m3_m3 is not None and wilting_point_m3_m3 is not None:
        awc = float(field_capacity_m3_m3 - wilting_point_m3_m3)

    # Freshness evaluation
    is_stale = False
    age_days = 0.0
    if as_of_time is not None:
        age_days = (as_of_time - observed_at).total_seconds() / 86400.0
        # If dynamic sensor moisture is present, use dynamic threshold; otherwise use static threshold
        threshold = max_dyn_stale if soil_moisture_m3_m3 is not None else max_static_stale
        if age_days > threshold:
            is_stale = True

    # Quality status
    if is_stale:
        q_status = DataQualityStatus.STALE
        q_note = f"Soil evidence age ({age_days:.1f}d) exceeds freshness threshold."
    elif soil_moisture_m3_m3 is not None or (field_capacity_m3_m3 is not None and wilting_point_m3_m3 is not None):
        q_status = DataQualityStatus.GOOD
        q_note = "Valid soil evidence with required hydraulic or moisture properties."
    elif soil_texture is not None or soil_ph is not None:
        q_status = DataQualityStatus.PARTIAL
        q_note = "Partial soil context available; quantitative moisture or hydraulic properties missing."
    else:
        q_status = DataQualityStatus.INSUFFICIENT
        q_note = "Missing all quantitative soil moisture and hydraulic parameters."

    return SoilFeatures(
        source_provider=source_provider,
        provenance_type=provenance_type,
        observed_at=observed_at,
        depth_min_cm=depth_min_cm,
        depth_max_cm=depth_max_cm,
        soil_moisture_m3_m3=soil_moisture_m3_m3,
        soil_texture=soil_texture,
        field_capacity_m3_m3=field_capacity_m3_m3,
        wilting_point_m3_m3=wilting_point_m3_m3,
        available_water_capacity_m3_m3=awc,
        soil_ph=soil_ph,
        ph_method=ph_method,
        electrical_conductivity_ds_m=electrical_conductivity_ds_m,
        ec_method=ec_method,
        moisture_sensor_type=moisture_sensor_type,
        quality_status=q_status,
        quality_note=q_note,
        is_stale=is_stale,
    )

