"""Vegetation feature extraction from normalized satellite evidence.

Transforms Sentinel-2 surface reflectance products (NDVI, NDMI, SCL) into
structured, quality-evaluated, and scientifically defensible zone-level features.

Scientific and Agronomic Restrictions (per AGENTS.md, AI_SPEC.md, DATA_SOURCES.md):
1. NDVI is a spectral greenness indicator and NOT a direct measurement of crop yield,
   biomass, or root-zone soil moisture.
2. NDMI (Normalized Difference Moisture Index) reflects canopy leaf-water content and
   hydration state; it is NOT a direct measurement of root-zone soil moisture.
3. Sentinel-2 SCL Class 4 identifies general green vegetation (crops, trees, weeds, grass);
   it does NOT uniquely identify agricultural crop canopy.
4. Bare soil (SCL 5) and surface water (SCL 6) are strictly isolated and excluded from
   vegetation canopy statistics to prevent false drought or crop failure alarms.
5. Temporal trends CANNOT and MUST NOT be manufactured from a single satellite observation.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
from pydantic import BaseModel, Field
from shapely.geometry import Polygon, MultiPolygon

from backend.app.intelligence.config import (
    GeospatialConfig,
    default_freshness_config,
    default_geospatial_config,
)
from backend.app.intelligence.geospatial.grid_alignment import (
    SCL_CLEAR_OBSERVATION_CLASSES,
    SCL_VEGETATION_CLASSES,
    ZoneSCLBreakdown,
    compute_zone_scl_breakdown,
)
from backend.app.intelligence.geospatial.raster_processing import GeoRasterGrid, create_valid_mask
from backend.app.intelligence.geospatial.zone_aggregation import aggregate_raster_for_zone
from backend.app.intelligence.types import (
    DataQualityStatus,
    ProvenanceType,
    SpatialQualityStatus,
    ZoneRasterStats,
)


class ZoneVegetationFeatures(BaseModel):
    """Structured zone-level vegetation features with provenance and quality metadata."""

    zone_id: Optional[str] = Field(default=None, description="Zone identifier")
    scene_id: str = Field(..., description="Satellite scene identifier (e.g., S2A_MSIL2A_...)")
    source_provider: str = Field(
        default="Copernicus Sentinel-2 L2A",
        description="Satellite data source provider"
    )
    observed_at: datetime = Field(..., description="Scene acquisition UTC timestamp")
    retrieved_at: Optional[datetime] = Field(default=None, description="Data ingestion/retrieval timestamp")
    provenance_type: ProvenanceType = Field(
        default=ProvenanceType.SATELLITE_DERIVED,
        description="Data provenance type"
    )

    # NDVI Statistics (strictly over valid vegetation pixels)
    ndvi_mean: Optional[float] = Field(
        default=None,
        description="Zonal mean NDVI of valid vegetation pixels (dimensionless, [-1.0, 1.0])"
    )
    ndvi_median: Optional[float] = Field(
        default=None,
        description="Zonal median NDVI of valid vegetation pixels"
    )
    ndvi_min: Optional[float] = Field(default=None, description="Zonal minimum NDVI")
    ndvi_max: Optional[float] = Field(default=None, description="Zonal maximum NDVI")
    ndvi_std: Optional[float] = Field(default=None, description="Zonal standard deviation of NDVI")
    ndvi_p10: Optional[float] = Field(default=None, description="10th percentile NDVI (robust lower bound)")
    ndvi_p25: Optional[float] = Field(default=None, description="25th percentile NDVI (lower quartile)")
    ndvi_p75: Optional[float] = Field(default=None, description="75th percentile NDVI (upper quartile)")
    ndvi_p90: Optional[float] = Field(default=None, description="90th percentile NDVI (robust upper bound)")

    # NDMI Statistics (Canopy-water-related spectral indicator)
    ndmi_mean: Optional[float] = Field(
        default=None,
        description="Zonal mean NDMI (canopy moisture spectral indicator, [-1.0, 1.0])"
    )
    ndmi_median: Optional[float] = Field(
        default=None,
        description="Zonal median NDMI"
    )
    ndmi_std: Optional[float] = Field(default=None, description="Zonal standard deviation of NDMI")

    # Land Cover & Coverage Breakdown (from SCL)
    vegetation_coverage_fraction: Optional[float] = Field(
        default=None,
        description="Fraction of zone occupied by SCL Class 4 (Vegetation)"
    )
    bare_soil_fraction: Optional[float] = Field(
        default=None,
        description="Fraction of zone occupied by SCL Class 5 (Bare Soil)"
    )
    water_fraction: Optional[float] = Field(
        default=None,
        description="Fraction of zone occupied by SCL Class 6 (Water)"
    )
    cloud_fraction: Optional[float] = Field(
        default=None,
        description="Fraction of zone covered by clouds/cirrus (SCL 8, 9, 10)"
    )
    shadow_fraction: Optional[float] = Field(
        default=None,
        description="Fraction of zone covered by shadows (SCL 2, 3)"
    )
    snow_ice_fraction: Optional[float] = Field(
        default=None,
        description="Fraction of zone covered by snow/ice (SCL 11)"
    )
    other_invalid_fraction: Optional[float] = Field(
        default=None,
        description="Fraction of zone unclassified, defective, or NoData (SCL 0, 1, 7)"
    )
    coverage_weighting_method: str = Field(
        default="pixel_count",
        description="Primary weighting method used in fraction fields: 'pixel_count' or 'intersection_area'"
    )

    # Actual Intersection-Area-Weighted Coverage (accounts for fractional boundary pixels)
    vegetation_area_fraction: Optional[float] = Field(
        default=None,
        description="Actual intersection-area-weighted fraction of zone occupied by vegetation"
    )
    bare_soil_area_fraction: Optional[float] = Field(
        default=None,
        description="Actual intersection-area-weighted fraction of zone occupied by bare soil"
    )
    water_area_fraction: Optional[float] = Field(
        default=None,
        description="Actual intersection-area-weighted fraction of zone occupied by water"
    )
    cloud_area_fraction: Optional[float] = Field(
        default=None,
        description="Actual intersection-area-weighted fraction of zone covered by cloud/cirrus"
    )
    shadow_area_fraction: Optional[float] = Field(
        default=None,
        description="Actual intersection-area-weighted fraction of zone covered by shadow"
    )
    snow_ice_area_fraction: Optional[float] = Field(
        default=None,
        description="Actual intersection-area-weighted fraction of zone covered by snow/ice"
    )
    other_invalid_area_fraction: Optional[float] = Field(
        default=None,
        description="Actual intersection-area-weighted fraction unclassified or defective"
    )
    valid_observation_fraction: float = Field(
        ...,
        description="Fraction of clear-sky surface observation (free from cloud/shadow)"
    )
    total_pixels_in_geometry: int = Field(
        ...,
        description="Total raster pixels intersecting the zone geometry"
    )
    valid_vegetation_pixel_count: int = Field(
        ...,
        description="Count of usable, unmasked vegetation pixels used for statistics"
    )

    # Quality & Freshness Assessment
    quality_status: DataQualityStatus = Field(
        ...,
        description="Quality classification of vegetation evidence"
    )
    quality_note: Optional[str] = Field(
        default=None,
        description="Detailed rationale for quality rating or caveats"
    )
    is_stale: bool = Field(
        default=False,
        description="Whether the scene acquisition age exceeds freshness threshold"
    )
    scientific_caveats: List[str] = Field(
        default_factory=list,
        description="Mandatory scientific restrictions and caveats for downstream consumers"
    )


class VegetationTrendResult(BaseModel):
    """Two-observation endpoint change rate and multi-temporal tracking.

    IMPORTANT SCIENTIFIC LIMITATION:
    This calculation evaluates a two-point finite-difference rate of change between
    observation endpoints (delta_ndvi / delta_days). It MUST NOT be labeled or
    interpreted as a statistically established regression trend, seasonal phenology curve,
    or predictive growth model. A formal time-series trend requires dense multi-temporal
    observations and statistical significance testing.
    """

    zone_id: Optional[str] = Field(default=None, description="Zone identifier")
    start_time: datetime = Field(..., description="Earliest observation timestamp (UTC)")
    end_time: datetime = Field(..., description="Latest observation timestamp (UTC)")
    observation_count: int = Field(..., description="Number of distinct temporal observations evaluated")
    delta_ndvi_mean: float = Field(..., description="Change in mean NDVI (latest minus earliest)")
    delta_days: float = Field(..., description="Elapsed days between earliest and latest observations")
    ndvi_change_rate_per_day: float = Field(
        ...,
        description="Two-point finite-difference rate of NDVI change per day (delta_ndvi / delta_days)"
    )
    trend_direction: str = Field(..., description="'increasing', 'stable', or 'declining'")
    is_material_change: bool = Field(
        ...,
        description=(
            "Whether absolute NDVI change exceeds configured agronomic materiality threshold "
            "(|delta_ndvi_mean| >= materiality_threshold), indicating practical canopy change rather "
            "than sensor noise. NOTE: This is a deterministic threshold comparison, NOT a statistical significance test."
        )
    )
    min_temporal_separation_days: float = Field(
        default=1.0,
        description="Minimum temporal separation required between observations in days"
    )
    earliest_quality_status: DataQualityStatus = Field(
        ...,
        description="Data quality status of the earliest observation"
    )
    latest_quality_status: DataQualityStatus = Field(
        ...,
        description="Data quality status of the latest observation"
    )
    rate_method: str = Field(
        default="two_point_endpoint_finite_difference",
        description="Calculation method applied"
    )

    @property
    def is_significant(self) -> bool:
        """Backward-compatibility property alias for is_material_change."""
        return self.is_material_change

    @property
    def ndvi_rate_per_day(self) -> float:
        """Backward-compatibility property alias for ndvi_change_rate_per_day."""
        return self.ndvi_change_rate_per_day


STANDARD_VEGETATION_CAVEATS: List[str] = [
    "NDVI is a spectral greenness indicator and NOT a direct measurement of crop yield, biomass, or root-zone soil moisture.",
    "NDMI reflects canopy water content and vegetation hydration, NOT direct root-zone soil moisture.",
    "SCL Class 4 identifies general green vegetation and does not uniquely identify agricultural crop species or crop canopy.",
    "Bare soil and open water pixels are strictly excluded from vegetation index statistics to prevent false stress depression.",
    "Temporal trends require multi-temporal observations and cannot be inferred from a single scene.",
]


def extract_vegetation_features_for_zone(
    zone_geom: Union[Polygon, MultiPolygon, dict],
    ndvi_raster: GeoRasterGrid,
    ndmi_raster: Optional[GeoRasterGrid] = None,
    scl_raster: Optional[GeoRasterGrid] = None,
    zone_id: Optional[str] = None,
    as_of_time: Optional[datetime] = None,
    config: Optional[GeospatialConfig] = None,
    stale_days: Optional[float] = None,
) -> ZoneVegetationFeatures:
    """Extract structured, quality-aware vegetation features for a management zone.

    Args:
        zone_geom: Zone boundary geometry (Polygon, MultiPolygon, or GeoJSON dict).
        ndvi_raster: Pre-computed NDVI GeoRasterGrid.
        ndmi_raster: Optional pre-computed NDMI GeoRasterGrid.
        scl_raster: Optional Copernicus Sentinel-2 SCL GeoRasterGrid for land-cover classification.
        zone_id: Optional zone identifier.
        as_of_time: Evaluation reference timestamp for staleness checking.
        config: Optional geospatial configuration overrides.
        stale_days: Optional freshness threshold in days (defaults to config).

    Returns:
        ZoneVegetationFeatures populated with deterministic statistics and quality flags.
    """
    cfg = config or default_geospatial_config
    max_stale_days = stale_days if stale_days is not None else default_freshness_config.satellite_stale_days

    # Ensure zone_geom is a Shapely Polygon/MultiPolygon
    if isinstance(zone_geom, dict):
        poly_geom = Polygon(zone_geom["coordinates"][0])
    else:
        poly_geom = zone_geom

    # 1. Evaluate SCL breakdown if available
    scl_breakdown: Optional[ZoneSCLBreakdown] = None
    if scl_raster is not None:
        try:
            scl_breakdown = compute_zone_scl_breakdown(scl_raster, poly_geom)
        except Exception:
            scl_breakdown = None

    # 2. Extract vegetation mask
    # If SCL is available, isolate Class 4 (Vegetation); bare soil and water are masked out.
    valid_mask: Optional[np.ndarray] = None
    if scl_raster is not None:
        # Align SCL to NDVI dimensions if needed
        if scl_raster.data.shape == ndvi_raster.data.shape:
            valid_mask = create_valid_mask(
                ndvi_raster.data,
                nodata_value=ndvi_raster.metadata.nodata_value,
                scl_layer=scl_raster.data.astype(np.uint8),
                vegetation_only=True,
            )
        else:
            # Multi-resolution SCL: resample SCL nearest-neighbor to NDVI grid
            from backend.app.intelligence.geospatial.grid_alignment import resample_raster_to_target, ResamplingMethod
            aligned_scl = resample_raster_to_target(scl_raster, ndvi_raster, method=ResamplingMethod.NEAREST)
            valid_mask = create_valid_mask(
                ndvi_raster.data,
                nodata_value=ndvi_raster.metadata.nodata_value,
                scl_layer=aligned_scl.data.astype(np.uint8),
                vegetation_only=True,
            )

    # 3. Zonal aggregation for NDVI
    ndvi_stats: ZoneRasterStats = aggregate_raster_for_zone(
        zone_geom=zone_geom,
        raster=ndvi_raster,
        zone_id=zone_id,
        index_name="NDVI",
        valid_mask=valid_mask,
        config=cfg,
    )

    # 4. Extract valid pixel values for percentile calculation
    # Zonal aggregation gives mean, median, min, max, std. We compute percentiles (p10, p25, p75, p90)
    # directly from the intersecting valid pixels.
    p10, p25, p75, p90 = None, None, None, None
    if ndvi_stats.quality_status == SpatialQualityStatus.GOOD and ndvi_stats.valid_pixel_count >= cfg.min_pixel_count:
        # Collect valid pixel values inside zone polygon
        from shapely.geometry import box
        z_minx, z_miny, z_maxx, z_maxy = ndvi_raster.bounds.min_x, ndvi_raster.bounds.min_y, ndvi_raster.bounds.max_x, ndvi_raster.bounds.max_y
        poly_minx, poly_miny, poly_maxx, poly_maxy = (
            zone_geom.bounds if hasattr(zone_geom, "bounds") else Polygon(zone_geom["coordinates"][0]).bounds
        )
        r_bounds = ndvi_raster.bounds

        col_min = max(0, int(np.floor((poly_minx - r_bounds.min_x) / ndvi_raster.pixel_width)))
        col_max = min(ndvi_raster.cols - 1, int(np.ceil((poly_maxx - r_bounds.min_x) / ndvi_raster.pixel_width)))
        row_min = max(0, int(np.floor((r_bounds.max_y - poly_maxy) / ndvi_raster.pixel_height)))
        row_max = min(ndvi_raster.rows - 1, int(np.ceil((r_bounds.max_y - poly_miny) / ndvi_raster.pixel_height)))

        min_overlap = ndvi_raster.pixel_area * cfg.min_pixel_overlap_fraction
        poly = zone_geom if not isinstance(zone_geom, dict) else Polygon(zone_geom["coordinates"][0])

        valid_vals = []
        for r in range(row_min, row_max + 1):
            for c in range(col_min, col_max + 1):
                p_minx, p_miny, p_maxx, p_maxy = ndvi_raster.get_pixel_bounds(r, c)
                pix_box = box(p_minx, p_miny, p_maxx, p_maxy)
                if pix_box.intersects(poly):
                    ov = pix_box.intersection(poly)
                    if not ov.is_empty and ov.area > min_overlap:
                        val = ndvi_raster.data[r, c]
                        is_usable = (valid_mask[r, c] if valid_mask is not None else np.isfinite(val))
                        if is_usable and np.isfinite(val):
                            valid_vals.append(float(val))

        if len(valid_vals) >= cfg.min_pixel_count:
            # Documented Percentile Method:
            # Uses standard linear interpolation (NumPy default, Hyndman and Fan 1996 Type 7,
            # equivalent to Excel PERCENTILE.INC and R type 7).
            p10, p25, p75, p90 = [
                float(x) for x in np.percentile(valid_vals, [10, 25, 75, 90], method="linear")
            ]

    # 5. NDMI Aggregation if provided
    ndmi_mean, ndmi_median, ndmi_std = None, None, None
    if ndmi_raster is not None:
        ndmi_stats: ZoneRasterStats = aggregate_raster_for_zone(
            zone_geom=zone_geom,
            raster=ndmi_raster,
            zone_id=zone_id,
            index_name="NDMI",
            valid_mask=valid_mask,
            config=cfg,
        )
        if ndmi_stats.quality_status == SpatialQualityStatus.GOOD:
            ndmi_mean = ndmi_stats.mean
            ndmi_median = ndmi_stats.median
            ndmi_std = ndmi_stats.std

    # 6. Staleness evaluation
    observed_at = ndvi_raster.metadata.acquisition_time or datetime.now(timezone.utc)
    is_stale = False
    if as_of_time is not None:
        age_days = (as_of_time - observed_at).total_seconds() / 86400.0
        if age_days > max_stale_days:
            is_stale = True

    # 7. Quality status determination
    if ndvi_stats.quality_status == SpatialQualityStatus.GOOD:
        if is_stale:
            q_status = DataQualityStatus.STALE
            q_note = f"Observation is {age_days:.1f} days old (exceeds {max_stale_days}d freshness threshold)."
        else:
            q_status = DataQualityStatus.GOOD
            q_note = "Valid clear-sky vegetation observation with sufficient spatial coverage."
    elif ndvi_stats.quality_status == SpatialQualityStatus.CLOUD_CONTAMINATED:
        q_status = DataQualityStatus.CLOUD_CONTAMINATED
        q_note = ndvi_stats.quality_note or "Contaminated by cloud or shadow cover."
    elif ndvi_stats.quality_status == SpatialQualityStatus.INSUFFICIENT_COVERAGE:
        q_status = DataQualityStatus.PARTIAL
        q_note = ndvi_stats.quality_note or "Insufficient valid pixel coverage within zone boundary."
    else:
        q_status = DataQualityStatus.SUSPECT
        q_note = ndvi_stats.quality_note or "Spatial quality check failed."

    # 8. Fractions from SCL breakdown if available
    veg_frac = scl_breakdown.vegetation_fraction if scl_breakdown else None
    bare_soil_frac = scl_breakdown.bare_soil_fraction if scl_breakdown else None
    water_frac = scl_breakdown.water_fraction if scl_breakdown else None
    cloud_frac = scl_breakdown.cloud_fraction if scl_breakdown else None
    shadow_frac = scl_breakdown.cloud_shadow_fraction if scl_breakdown else None
    snow_ice_frac = scl_breakdown.snow_ice_fraction if scl_breakdown else None
    other_frac = scl_breakdown.other_fraction if scl_breakdown else None

    # Clear observation fraction (vegetation + bare soil + water)
    clear_obs_fraction = (
        (scl_breakdown.vegetation_pixels + scl_breakdown.bare_soil_pixels + scl_breakdown.water_pixels)
        / scl_breakdown.total_pixels
        if (scl_breakdown and scl_breakdown.total_pixels > 0)
        else ndvi_stats.valid_pixel_fraction
    )

    return ZoneVegetationFeatures(
        zone_id=zone_id,
        scene_id=ndvi_raster.metadata.scene_id,
        source_provider="Copernicus Sentinel-2 L2A",
        observed_at=observed_at,
        retrieved_at=None,
        provenance_type=ProvenanceType.SATELLITE_DERIVED,
        ndvi_mean=ndvi_stats.mean,
        ndvi_median=ndvi_stats.median,
        ndvi_min=ndvi_stats.min,
        ndvi_max=ndvi_stats.max,
        ndvi_std=ndvi_stats.std,
        ndvi_p10=p10,
        ndvi_p25=p25,
        ndvi_p75=p75,
        ndvi_p90=p90,
        ndmi_mean=ndmi_mean,
        ndmi_median=ndmi_median,
        ndmi_std=ndmi_std,
        vegetation_coverage_fraction=veg_frac,
        bare_soil_fraction=bare_soil_frac,
        water_fraction=water_frac,
        cloud_fraction=cloud_frac,
        shadow_fraction=shadow_frac,
        snow_ice_fraction=snow_ice_frac,
        other_invalid_fraction=other_frac,
        coverage_weighting_method=scl_breakdown.weighting_method if scl_breakdown else "pixel_count",
        vegetation_area_fraction=scl_breakdown.vegetation_area_fraction if scl_breakdown else None,
        bare_soil_area_fraction=scl_breakdown.bare_soil_area_fraction if scl_breakdown else None,
        water_area_fraction=scl_breakdown.water_area_fraction if scl_breakdown else None,
        cloud_area_fraction=scl_breakdown.cloud_area_fraction if scl_breakdown else None,
        shadow_area_fraction=scl_breakdown.cloud_shadow_area_fraction if scl_breakdown else None,
        snow_ice_area_fraction=scl_breakdown.snow_ice_area_fraction if scl_breakdown else None,
        other_invalid_area_fraction=scl_breakdown.other_area_fraction if scl_breakdown else None,
        valid_observation_fraction=clear_obs_fraction,
        total_pixels_in_geometry=ndvi_stats.total_pixels_in_geometry,
        valid_vegetation_pixel_count=ndvi_stats.valid_pixel_count,
        quality_status=q_status,
        quality_note=q_note,
        is_stale=is_stale,
        scientific_caveats=STANDARD_VEGETATION_CAVEATS.copy(),
    )


def compute_vegetation_trend(
    observations: List[ZoneVegetationFeatures],
    min_delta_days: float = 1.0,
    materiality_threshold: float = 0.05,
    significance_threshold: Optional[float] = None,
) -> Optional[VegetationTrendResult]:
    """Calculate multi-temporal vegetation change rate between distinct observation dates.

    Scientific guardrails and limitations:
    - Never manufactures a trend from a single observation.
    - Evaluates a two-point endpoint finite-difference change rate (delta_ndvi / delta_days).
      It is NOT a statistically fitted regression trend.
    - Requires at least 2 distinct observations with valid NDVI and separated by at least
      min_delta_days (defaults to 1.0 day to avoid sub-daily or identical-day noise).
    - Validates spatial comparability: all observations must belong to the same zone.
    - is_material_change evaluates whether the absolute change exceeds the agronomic
      materiality threshold; it does not claim statistical hypothesis significance.

    Args:
        observations: List of ZoneVegetationFeatures sorted or unsorted.
        min_delta_days: Minimum required separation in days between observations (documented: 1.0d).
        materiality_threshold: Absolute change in NDVI required to declare change materially significant.
        significance_threshold: Backward-compatibility alias for materiality_threshold.

    Returns:
        VegetationTrendResult if valid, comparable multi-temporal evidence exists, else None.
    """
    effective_thresh = significance_threshold if significance_threshold is not None else materiality_threshold

    # Filter for observations with valid mean NDVI and acceptable quality
    valid_obs = [
        obs for obs in observations
        if obs.ndvi_mean is not None and obs.quality_status in {DataQualityStatus.GOOD, DataQualityStatus.STALE}
    ]

    if len(valid_obs) < 2:
        return None

    # Check spatial comparability: all observations must belong to the same zone_id
    zone_ids = {obs.zone_id for obs in valid_obs if obs.zone_id is not None}
    if len(zone_ids) > 1:
        raise ValueError(
            f"Cannot calculate vegetation change rate across different zones: {zone_ids}"
        )

    # Sort chronologically
    sorted_obs = sorted(valid_obs, key=lambda x: x.observed_at)
    earliest = sorted_obs[0]
    latest = sorted_obs[-1]

    delta_seconds = (latest.observed_at - earliest.observed_at).total_seconds()
    delta_days = delta_seconds / 86400.0

    if delta_days < min_delta_days:
        return None

    delta_ndvi = latest.ndvi_mean - earliest.ndvi_mean
    rate_per_day = delta_ndvi / delta_days if delta_days > 0 else 0.0

    is_material = abs(delta_ndvi) >= effective_thresh

    if delta_ndvi > 0.02:
        direction = "increasing"
    elif delta_ndvi < -0.02:
        direction = "declining"
    else:
        direction = "stable"

    return VegetationTrendResult(
        zone_id=latest.zone_id,
        start_time=earliest.observed_at,
        end_time=latest.observed_at,
        observation_count=len(sorted_obs),
        delta_ndvi_mean=float(delta_ndvi),
        delta_days=float(delta_days),
        ndvi_change_rate_per_day=float(rate_per_day),
        trend_direction=direction,
        is_material_change=is_material,
        min_temporal_separation_days=float(min_delta_days),
        earliest_quality_status=earliest.quality_status,
        latest_quality_status=latest.quality_status,
        rate_method="two_point_endpoint_finite_difference",
    )
