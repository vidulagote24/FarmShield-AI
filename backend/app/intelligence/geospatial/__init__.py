"""Geospatial processing subpackage for FarmShield AI.

Provides geometry validation, geodesic metric calculation, CRS transformation,
raster handling, Sentinel-2 radiometric calibration, NDVI/NDMI spectral calculations,
multi-resolution grid alignment, quality masking, and zonal aggregation.
"""

from .geometry import (
    calculate_geodesic_area_m2,
    calculate_geodesic_area_ha,
    validate_polygon_geometry,
    check_zone_contained_in_farm,
    transform_geometry_crs,
)
from .indices import calculate_ndvi, calculate_ndmi
from .reflectance import (
    S2ReflectanceMode,
    S2CalibrationMetadata,
    CalibratedReflectanceResult,
    calibrate_sentinel2_reflectance,
    calibrate_sentinel2_reflectance_with_diagnostics,
)
from .raster_processing import GeoRasterGrid, create_valid_mask
from .grid_alignment import (
    ResamplingMethod,
    validate_raster_alignment,
    resample_raster_to_target,
    resample_scl_to_10m,
    compute_zone_scl_breakdown,
    ZoneSCLBreakdown,
    calculate_aligned_ndmi,
    SCL_VEGETATION_CLASSES,
    SCL_CROP_VEGETATION_CLASSES,
    SCL_BARE_SOIL_CLASSES,
    SCL_WATER_CLASSES,
    SCL_CLEAR_OBSERVATION_CLASSES,
    SCL_CONTAMINATION_CLASSES,
    SCL_USABLE_FOR_VEGETATION,
    SCL_EXCLUDED_FOR_VEGETATION,
    SCL_CLASS_DESCRIPTIONS,
    resolve_scl_class_2_semantics,
    resolve_scl_class_2_label,
)
from .zone_aggregation import aggregate_raster_for_zone
from .quality import assess_spatial_quality

__all__ = [
    "calculate_geodesic_area_m2",
    "calculate_geodesic_area_ha",
    "validate_polygon_geometry",
    "check_zone_contained_in_farm",
    "transform_geometry_crs",
    "calculate_ndvi",
    "calculate_ndmi",
    "S2ReflectanceMode",
    "S2CalibrationMetadata",
    "CalibratedReflectanceResult",
    "calibrate_sentinel2_reflectance",
    "calibrate_sentinel2_reflectance_with_diagnostics",
    "GeoRasterGrid",
    "create_valid_mask",
    "ResamplingMethod",
    "validate_raster_alignment",
    "resample_raster_to_target",
    "resample_scl_to_10m",
    "compute_zone_scl_breakdown",
    "ZoneSCLBreakdown",
    "calculate_aligned_ndmi",
    "SCL_VEGETATION_CLASSES",
    "SCL_CROP_VEGETATION_CLASSES",
    "SCL_BARE_SOIL_CLASSES",
    "SCL_WATER_CLASSES",
    "SCL_CLEAR_OBSERVATION_CLASSES",
    "SCL_CONTAMINATION_CLASSES",
    "SCL_USABLE_FOR_VEGETATION",
    "SCL_EXCLUDED_FOR_VEGETATION",
    "SCL_CLASS_DESCRIPTIONS",
    "resolve_scl_class_2_semantics",
    "resolve_scl_class_2_label",
    "aggregate_raster_for_zone",
    "assess_spatial_quality",
]
