"""Configuration settings for the intelligence module.

Enforces documented assumptions and ensures scientific thresholds
(such as minimum valid pixel fractions) are explicit, configurable,
and recorded with results.
"""

from pydantic import BaseModel, Field


class GeospatialConfig(BaseModel):
    """Configuration parameters for geospatial and raster processing."""

    default_crs: str = Field(
        default="EPSG:4326",
        description="Default geographic coordinate reference system for API boundaries (WGS84)."
    )

    min_valid_pixel_fraction: float = Field(
        default=0.60,
        ge=0.0,
        le=1.0,
        description=(
            "Provisional minimum valid (clear, non-NoData) pixel fraction required "
            "to declare zonal raster statistics reliable. Configurable per evaluation run."
        )
    )

    min_pixel_count: int = Field(
        default=3,
        ge=1,
        description=(
            "Absolute minimum count of valid pixels required within a zone geometry "
            "to compute statistical metrics like median and mean."
        )
    )

    containment_tolerance_m2: float = Field(
        default=1.0,
        ge=0.0,
        description=(
            "Allowable tolerance in square meters when checking whether a zone polygon "
            "is fully contained within a farm boundary, to account for numerical rounding."
        )
    )

    ndvi_clip_min: float = Field(
        default=-1.0,
        description="Theoretical lower bound for NDVI index."
    )

    ndvi_clip_max: float = Field(
        default=1.0,
        description="Theoretical upper bound for NDVI index."
    )

    min_pixel_overlap_fraction: float = Field(
        default=1e-5,
        ge=0.0,
        le=0.5,
        description=(
            "Scale-invariant minimum fraction of pixel area that must overlap a geometry "
            "to be counted as intersecting. Prevents false positive boundary-only 1D edge touches "
            "across both geographic (degrees) and projected (meters) coordinate systems."
        )
    )


# Default global instance
default_geospatial_config = GeospatialConfig()


class FeatureFreshnessConfig(BaseModel):
    """Configuration for data freshness policies across multimodal domains.

    Per DATA_SOURCES.md, freshness policies must vary by domain:
    satellite revisit frequency is lower than weather, and static soil properties
    have multi-month or annual validity.

    PROVISIONAL POLICY NOTICE:
    These freshness thresholds represent initial operational application policies,
    NOT universal scientific constants. They are configurable per region, crop cycle,
    and deployment environment. Every evaluation records whether provisional settings
    were applied.
    """
    is_provisional: bool = Field(
        default=True,
        description="Explicitly marks thresholds as provisional operational application policies, not validated universal scientific constants."
    )
    satellite_stale_days: float = Field(
        default=14.0,
        ge=1.0,
        description="Maximum age in days before an optical satellite scene is flagged as stale."
    )
    weather_stale_hours: float = Field(
        default=48.0,
        ge=1.0,
        description="Maximum age in hours before historical/recent weather observations are flagged as stale."
    )
    dynamic_soil_moisture_stale_days: float = Field(
        default=3.0,
        ge=0.1,
        description="Maximum age in days before high-frequency soil moisture sensor readings are flagged as stale."
    )
    static_soil_stale_days: float = Field(
        default=365.0,
        ge=1.0,
        description="Maximum age in days before static soil properties (texture, AWC, pH) are flagged as stale."
    )
    crop_growth_stage_stale_days: float = Field(
        default=30.0,
        ge=1.0,
        description="Maximum age in days before an in-field crop growth stage inspection is flagged as stale."
    )
    temporal_alignment_warning_days: float = Field(
        default=5.0,
        ge=0.5,
        description="Maximum difference in days between satellite and weather observations before triggering a temporal misalignment caveat."
    )


default_freshness_config = FeatureFreshnessConfig()

