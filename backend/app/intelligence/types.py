"""Data contracts and domain types for the FarmShield AI Intelligence module.

These models and enums represent clean domain concepts independent of
direct ORM or HTTP transport concerns, matching docs/DATA_MODEL.md
and docs/API_CONTRACTS.md.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class SpatialQualityStatus(str, Enum):
    """Quality classification of a zone-level spatial or raster observation."""
    GOOD = "good"
    SUSPECT = "suspect"
    CLOUD_CONTAMINATED = "cloud_contaminated"
    INSUFFICIENT_COVERAGE = "insufficient_coverage"
    NO_SPATIAL_OVERLAP = "no_spatial_overlap"
    INVALID_GEOMETRY = "invalid_geometry"


class StressStatus(str, Enum):
    """Zone condition assessment status per AI_SPEC.md."""
    HEALTHY = "healthy"
    MONITOR = "monitor"
    ATTENTION = "attention"
    HIGH_STRESS = "high_stress"
    INSUFFICIENT_DATA = "insufficient_data"


class ActionCode(str, Enum):
    """Advisory action codes per AI_SPEC.md and API_CONTRACTS.md."""
    IRRIGATE = "irrigate"
    MONITOR = "monitor"
    DELAY_AND_REASSESS = "delay_and_reassess"
    INSPECT = "inspect"
    NO_ACTION_INDICATED = "no_action_indicated"
    INSUFFICIENT_DATA = "insufficient_data"


class PriorityLevel(str, Enum):
    """Urgency level of a recommendation."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ProvenanceType(str, Enum):
    """Source provenance classification matching docs/DATA_MODEL.md."""
    SENSOR_MEASURED = "sensor_measured"
    PROVIDER_MODELLED = "provider_modelled"
    SATELLITE_DERIVED = "satellite_derived"
    FARMER_ENTERED = "farmer_entered"
    LABORATORY_ANALYZED = "laboratory_analyzed"
    CALCULATED = "calculated"
    SIMULATED = "simulated"


class DataQualityStatus(str, Enum):
    """Data quality and validity classification matching docs/DATA_MODEL.md and DATA_SOURCES.md."""
    GOOD = "good"
    PARTIAL = "partial"
    SUSPECT = "suspect"
    CLOUD_CONTAMINATED = "cloud_contaminated"
    STALE = "stale"
    MISSING = "missing"
    INSUFFICIENT = "insufficient"
    SIMULATED = "simulated"


class MeasurementHeightProvenance(str, Enum):
    """Provenance classification for meteorological sensor measurement heights."""
    PROVIDER_REPORTED = "provider_reported"       # Formally reported in data payload/metadata by external provider
    SENSOR_MEASURED = "sensor_measured"           # Directly recorded physical installation height of in-field sensor
    CONVENTION_ASSUMED = "convention_assumed"     # Inferred from standard meteorological convention (e.g. 10m wind / 2m temp)
    UNKNOWN = "unknown"                           # Measurement height is unknown or missing from source metadata


class SolarIrradianceType(str, Enum):
    """Classification of solar radiation irradiance input mode."""
    INTERVAL_MEAN = "interval_mean"     # Time-averaged flux over preceding interval (e.g., Open-Meteo, ECMWF)
    INSTANTANEOUS = "instantaneous"     # Spot / point-in-time flux sample (e.g., instantaneous pyranometer reading)


class WeatherWindowType(str, Enum):
    """Temporal window classification for weather features."""
    INSTANTANEOUS = "instantaneous"
    HOURLY = "hourly"
    DAILY_SUMMARY = "daily_summary"
    WINDOW_24H = "window_24h"
    WINDOW_48H = "window_48h"
    WINDOW_7D = "window_7d"
    WINDOW_30D = "window_30d"                 # Strictly 30 elapsed days (720 hours)
    APPROXIMATE_30D = "approximate_30d"       # Provider-reported approximate 30-day period (28 to 31.5 days)
    MONTHLY = "monthly"                       # Standard calendar-month aggregation aligned to calendar boundaries
    FORECAST_WINDOW = "forecast_window"


class SoilTextureClass(str, Enum):
    """Standard USDA soil texture classification."""
    SAND = "sand"
    LOAMY_SAND = "loamy_sand"
    SANDY_LOAM = "sandy_loam"
    LOAM = "loam"
    SILT_LOAM = "silt_loam"
    SILT = "silt"
    SANDY_CLAY_LOAM = "sandy_clay_loam"
    CLAY_LOAM = "clay_loam"
    SILTY_CLAY_LOAM = "silty_clay_loam"
    SANDY_CLAY = "sandy_clay"
    SILTY_CLAY = "silty_clay"
    CLAY = "clay"
    UNKNOWN = "unknown"


class BoundingBox(BaseModel):
    """Spatial bounding box in a specified CRS (default EPSG:4326)."""
    min_x: float = Field(..., description="Minimum X / Longitude")
    min_y: float = Field(..., description="Minimum Y / Latitude")
    max_x: float = Field(..., description="Maximum X / Longitude")
    max_y: float = Field(..., description="Maximum Y / Latitude")
    crs: str = Field(default="EPSG:4326", description="Coordinate Reference System")


class GeometryValidationResult(BaseModel):
    """Result of polygon geometry validation and metric measurements."""
    is_valid: bool = Field(..., description="Whether geometry is topologically valid")
    error_message: Optional[str] = Field(default=None, description="Detailed explanation if invalid")
    is_empty: bool = Field(default=False, description="Whether geometry contains no coordinates")
    geometry_type: Optional[str] = Field(default=None, description="Polygon or MultiPolygon")
    area_m2: Optional[float] = Field(default=None, description="Geodesic surface area in square meters")
    area_ha: Optional[float] = Field(default=None, description="Geodesic surface area in hectares")
    bounds: Optional[BoundingBox] = Field(default=None, description="Bounding box in EPSG:4326")


class RasterMetadata(BaseModel):
    """Metadata describing a 2D raster grid and its spatial georeferencing."""
    scene_id: str = Field(..., description="Unique scene or acquisition identifier")
    acquisition_time: Optional[datetime] = Field(default=None, description="UTC timestamp of scene acquisition")
    crs: str = Field(default="EPSG:4326", description="Coordinate Reference System of the raster coordinates")
    resolution_m: float = Field(..., description="Nominal pixel resolution in meters")
    bounds: BoundingBox = Field(..., description="Spatial extent of the raster grid")
    rows: int = Field(..., description="Number of rows in the raster array")
    cols: int = Field(..., description="Number of columns in the raster array")
    nodata_value: Optional[float] = Field(default=None, description="Value denoting invalid/missing pixels")
    processing_version: str = Field(default="0.1.0", description="Processing version applied to the raster")


class ZoneRasterStats(BaseModel):
    """Aggregated zonal statistics derived from an intersecting raster."""
    zone_id: Optional[str] = Field(default=None, description="Zone identifier")
    index_name: str = Field(..., description="Name of the index (e.g. NDVI)")
    mean: Optional[float] = Field(default=None, description="Mean of valid pixels inside zone")
    median: Optional[float] = Field(default=None, description="Median of valid pixels inside zone")
    min: Optional[float] = Field(default=None, description="Minimum valid pixel value")
    max: Optional[float] = Field(default=None, description="Maximum valid pixel value")
    std: Optional[float] = Field(default=None, description="Standard deviation of valid pixels")
    total_pixels_in_geometry: int = Field(..., description="Total raster pixels intersecting the geometry")
    valid_pixel_count: int = Field(..., description="Number of unmasked, non-NoData pixels inside zone")
    valid_pixel_fraction: float = Field(..., description="Ratio of valid pixels to total intersecting pixels")
    min_valid_fraction_threshold: float = Field(..., description="Threshold configured for acceptable coverage")
    quality_status: SpatialQualityStatus = Field(..., description="Spatial quality evaluation")
    quality_note: Optional[str] = Field(default=None, description="Explanation of quality flags or caveats")

