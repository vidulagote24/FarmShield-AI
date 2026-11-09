"""Raster grid alignment, multi-resolution harmonization, and SCL class semantics.

Methodological and scientific principles:
1. SCL Classification Semantics:
   - Class 4 (Vegetation): Identifies general photosynthetically active green vegetation
     (e.g., natural vegetation, trees, shrubs, weeds, and agricultural crops).
     Note on agronomic interpretation: SCL Class 4 detects general vegetation spectral
     signatures; it does NOT distinguish agricultural crops from surrounding trees, weeds,
     or natural grass, nor does it uniquely identify crop canopy. Farm parcel boundaries and
     cropping metadata must be combined with SCL to isolate agricultural fields.
     Only Class 4 is accepted when computing vegetation-health indices (NDVI/NDMI).
   - Class 5 (Not-vegetated / bare soil): Represents fallow ground, roads, and bare soil.
     Must NOT be combined into vegetation-health statistics, as bare soil severely depresses NDVI.
   - Class 6 (Water): Represents farm ponds, irrigation channels, or standing flood water.
     Must NOT be combined into vegetation-health statistics, as water has negative NDVI.
   - Clear Observation vs Vegetation:
     Classes {4, 5, 6} represent clear-sky observations of the Earth's surface (free of clouds/shadows),
     whereas only Class {4} isolates green vegetation.
   - Processing Baseline Evolution for Class 2:
     * Pre-PB 04.00: Designated as DARK_AREA_PIXELS (legacy grouping of dark targets and shadows).
     * PB 04.00 through PB 05.10: Retained official label DARK_FEATURES. However, from PB 04.00,
       shadows were separated from dark surface features such as dark soils and burned areas, which
       were assigned to SCL Class 7 (Unclassified). Class 2's underlying computation remained unchanged
       from PB 04.00 until its PB 05.11 rename to CAST_SHADOW.
     * PB 05.11 onwards: Formally renamed to CAST_SHADOW to reflect that it exclusively represents
       shadows cast by topography or tall structures.
     * Modern Class 2 strictly represents cast shadows, NOT dark soils (which belong to
       Class 5 NOT_VEGETATED) nor burned areas / dark features (which belong to Class 7
       UNCLASSIFIED). It is treated as an excluded contamination class.
   - Contamination Classes:
     0 (NoData), 1 (Defective), 2 (Cast Shadow / Dark Features / Dark Area), 3 (Cloud Shadows),
     7 (Unclassified), 8 (Medium Cloud), 9 (High Cloud), 10 (Cirrus), 11 (Snow).

2. Raster Resampling Methods:
   - Nearest-Neighbor: Required for categorical data (e.g. SCL). Preserves discrete integer
     class labels without introducing unphysical interpolated values (e.g. 4.5).
   - Spatial Area Averaging: Used when downsampling continuous reflectance (e.g. 10 m NIR
     to 20 m SWIR1). Computes the arithmetic mean reflectance factor across the 2x2 footprint,
     avoiding point-sampling aliasing. Does not imply physical radiant energy flux conservation.
   - Bilinear: Used for continuous spatial interpolation onto finer grids.
   - Native-Grid Calculation: Whenever possible, compute multi-band indices on native detector
     resolutions (e.g. using Band 8A at 20 m with Band 11 at 20 m for NDMI).

3. Grid Alignment Assumptions:
   - Coordinate reference systems must be identical.
   - Pixel boundaries must align within spatial tolerance (1e-4).
   - Rasters are assumed to be north-up and axis-aligned. Rotated grids are not supported.
"""

from enum import Enum
from typing import Dict, Optional, Set, Tuple
import numpy as np
from pydantic import BaseModel, Field
from pyproj import CRS
import rasterio
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject
from shapely.geometry import Polygon, MultiPolygon, box

from backend.app.intelligence.geospatial.indices import calculate_ndmi
from backend.app.intelligence.geospatial.raster_processing import GeoRasterGrid
from backend.app.intelligence.types import BoundingBox, RasterMetadata


# Copernicus Sentinel-2 Scene Classification Layer (SCL) class dictionary
SCL_CLASS_DESCRIPTIONS: Dict[int, str] = {
    0: "NO_DATA (Missing observation or detector dead zone)",
    1: "SATURATED_OR_DEFECTIVE (Sensor saturation or corrupted pixel)",
    2: "DARK_FEATURES / CAST_SHADOW / DARK_AREA_PIXELS (Class 2: pre-PB 04.00 DARK_AREA_PIXELS; PB 04.00-05.10 DARK_FEATURES where dark soils/burned areas separated to Class 7 and Class 2 computed cast shadows; PB 05.11+ CAST_SHADOW; excluded from clear surface observations; NOT cloud shadow)",
    3: "CLOUD_SHADOWS (Class 3: Cloud shadow on surface; NOT cast/topographic shadow)",
    4: "VEGETATION (General green vegetation; does not distinguish crop from natural vegetation/trees)",
    5: "NOT_VEGETATED (Valid bare soil, rocks, fallow fields)",
    6: "WATER (Open surface water / irrigation ponds)",
    7: "UNCLASSIFIED (Low confidence classification; ambiguous)",
    8: "CLOUD_MEDIUM_PROBABILITY (Medium probability opaque cloud)",
    9: "CLOUD_HIGH_PROBABILITY (Dense opaque cloud)",
    10: "THIN_CIRRUS (Semi-transparent cirrus cloud contaminating reflectance)",
    11: "SNOW (Snow or ice cover)",
}

# 1. Clear-sky surface observation classes (ground/water visible, free of cloud/shadow)
SCL_CLEAR_OBSERVATION_CLASSES: Set[int] = {4, 5, 6}

# 2. General green vegetation only (isolates vegetation from bare soil and water)
# Note: Identifies general vegetation; does not uniquely identify agricultural crop canopy.
SCL_VEGETATION_CLASSES: Set[int] = {4}

# 3. Bare soil only
SCL_BARE_SOIL_CLASSES: Set[int] = {5}

# 4. Surface water only
SCL_WATER_CLASSES: Set[int] = {6}

# 5. Contamination / excluded classes
SCL_CONTAMINATION_CLASSES: Set[int] = {0, 1, 2, 3, 7, 8, 9, 10, 11}

# Backward compatibility aliases
SCL_CROP_VEGETATION_CLASSES = SCL_VEGETATION_CLASSES
SCL_USABLE_FOR_VEGETATION = SCL_VEGETATION_CLASSES
SCL_EXCLUDED_FOR_VEGETATION = SCL_CONTAMINATION_CLASSES


def resolve_scl_class_2_semantics(
    processing_baseline: Optional[str],
) -> Tuple[str, Optional[str], str]:
    """Determine official Copernicus Sentinel-2 PSD nomenclature and semantic interpretation for SCL Class 2.

    Copernicus Sentinel-2 Product Specification Document (PSD) evolution:
    - Pre-PB 04.00 (< 04.00): 'DARK_AREA_PIXELS'
      Semantic: 'Legacy dark surface features and general topographic/cast shadows (pre-PB 04.00; NOT exclusively cast shadow; never cloud shadow)'
    - PB 04.00 to PB 05.10 [04.00, 05.10]: 'DARK_FEATURES'
      Semantic: 'Topographic and obstacle cast shadows under official label DARK_FEATURES (PB 04.00–05.10; dark soils and burned areas were separated to Class 7; computation unchanged through PB 05.11 rename to CAST_SHADOW; NOT cloud shadow)'
    - PB 05.11 onwards (>= 05.11): 'CAST_SHADOW'
      Semantic: 'Topographic and obstacle cast shadow (PB 05.11+; exclusively cast/topographic shadow, distinct from cloud shadow)'
    - Baseline missing / unavailable: 'DARK_FEATURES_OR_CAST_SHADOW_UNSPECIFIED_BASELINE'
      Semantic: 'Ambiguous legacy classification: dark features or cast shadow with unspecified baseline (NOT cloud shadow)'

    Returns:
        Tuple of (scl_2_label, normalized_pb_string_or_None, semantic_interpretation).
    """
    if processing_baseline is None or not str(processing_baseline).strip():
        return (
            "DARK_FEATURES_OR_CAST_SHADOW_UNSPECIFIED_BASELINE",
            None,
            "Ambiguous legacy classification: dark features or cast shadow with unspecified baseline (NOT cloud shadow)",
        )

    pb_str = str(processing_baseline).strip()
    cleaned = pb_str.lstrip("Nn").strip()
    try:
        parts = cleaned.split(".")
        if len(parts) >= 2:
            major = int(parts[0])
            minor = int(parts[1][:2])
            val = major + minor / 100.0
        else:
            val = float(cleaned)
    except (ValueError, IndexError):
        return (
            "DARK_FEATURES_OR_CAST_SHADOW_UNSPECIFIED_BASELINE",
            pb_str,
            "Ambiguous legacy classification: dark features or cast shadow with unparseable baseline (NOT cloud shadow)",
        )

    if val < 4.0:
        return (
            "DARK_AREA_PIXELS",
            pb_str,
            "Legacy dark surface features and general topographic/cast shadows (pre-PB 04.00; NOT exclusively cast shadow; never cloud shadow)",
        )
    elif val <= 5.10:
        return (
            "DARK_FEATURES",
            pb_str,
            "Topographic and obstacle cast shadows under official label DARK_FEATURES (PB 04.00–05.10; dark soils and burned areas were separated to Class 7; computation unchanged through PB 05.11 rename to CAST_SHADOW; NOT cloud shadow)",
        )
    else:
        return (
            "CAST_SHADOW",
            pb_str,
            "Topographic and obstacle cast shadow (PB 05.11+; exclusively cast/topographic shadow, distinct from cloud shadow)",
        )


def resolve_scl_class_2_label(processing_baseline: Optional[str]) -> Tuple[str, Optional[str]]:
    """Determine official Copernicus Sentinel-2 PSD nomenclature for SCL Class 2 based on processing baseline.

    Backward compatibility wrapper returning (scl_2_label, normalized_pb).
    """
    lbl, norm_pb, _ = resolve_scl_class_2_semantics(processing_baseline)
    return lbl, norm_pb


class ZoneSCLBreakdown(BaseModel):
    """Detailed breakdown of SCL surface classification across a management zone.

    Preserves both:
    1. Pixel-count-weighted fractions (vegetation_fraction, bare_soil_fraction, etc.)
       where each pixel with overlap > min_overlap counts as 1.0.
    2. Fractional intersection-area-weighted fractions (vegetation_area_fraction, etc.)
       accounting for exact geometric clipping of boundary pixels by the zone polygon.

    Mutually exclusive coverage classes (summing to 1.0 within float precision):
    - Vegetation: SCL 4
    - Bare Soil: SCL 5
    - Water: SCL 6
    - Shadow / Dark Features: SCL 2 (Dark area pixels / dark features / cast shadow depending on baseline), SCL 3 (Cloud shadow)
    - Cloud: SCL 8 (Medium prob), SCL 9 (High prob), SCL 10 (Thin cirrus)
    - Snow/Ice: SCL 11
    - Other/Invalid: SCL 0 (NoData), SCL 1 (Defective), SCL 7 (Unclassified)
    """
    total_pixels: int = Field(..., description="Total classified pixels intersecting the zone geometry")
    vegetation_pixels: int = Field(..., description="Count of Class 4 (Vegetation) pixels")
    vegetation_fraction: float = Field(..., description="Pixel-count fraction of zone occupied by vegetation (SCL 4)")
    bare_soil_pixels: int = Field(..., description="Count of Class 5 (Bare soil) pixels")
    bare_soil_fraction: float = Field(..., description="Pixel-count fraction of zone occupied by bare soil (SCL 5)")
    water_pixels: int = Field(..., description="Count of Class 6 (Water) pixels")
    water_fraction: float = Field(..., description="Pixel-count fraction of zone occupied by open water (SCL 6)")
    cloud_shadow_pixels: int = Field(..., description="Count of Class 2 and Class 3 pixels")
    cloud_shadow_fraction: float = Field(..., description="Pixel-count fraction under SCL 2 and SCL 3")

    # Baseline-Aware SCL Class 2 Fields
    scl_2_pixels: int = Field(default=0, description="Count of SCL Class 2 pixels (actual class number 2)")
    scl_2_fraction: float = Field(default=0.0, description="Fraction of zone occupied by SCL Class 2")
    scl_2_class_number: int = Field(default=2, description="Actual SCL class number (2)")
    scl_2_original_class_label: Optional[str] = Field(
        default=None,
        description="Official Copernicus Sentinel-2 PSD class label: 'DARK_AREA_PIXELS' (< PB 04.00), 'DARK_FEATURES' (PB 04.00-05.10), or 'CAST_SHADOW' (>= PB 05.11)"
    )
    scl_2_semantic_interpretation: Optional[str] = Field(
        default=None,
        description="Baseline-aware semantic interpretation: dark surface features / topographic shadow / cast shadow"
    )
    # Backward compatibility aliases for SCL 2
    scl_2_cast_shadow_pixels: int = Field(default=0, description="Count of SCL Class 2 pixels (backward compatibility alias; note pre-PB 04.00 DARK_AREA_PIXELS is not exclusively cast shadow)")
    scl_2_cast_shadow_fraction: float = Field(default=0.0, description="Fraction of zone occupied by SCL Class 2 (backward compatibility alias)")

    # Baseline-Aware SCL Class 3 Fields (Exclusively Cloud Shadow across all baselines)
    scl_3_pixels: int = Field(default=0, description="Count of SCL Class 3 (Cloud shadow) pixels")
    scl_3_fraction: float = Field(default=0.0, description="Fraction of zone occupied by SCL Class 3 (Cloud shadow)")
    scl_3_class_number: int = Field(default=3, description="Actual SCL class number (3)")
    scl_3_original_class_label: str = Field(default="CLOUD_SHADOW", description="Official Copernicus PSD label for Class 3 (exclusively CLOUD_SHADOW across all baselines)")
    scl_3_semantic_interpretation: str = Field(
        default="Cloud shadow cast on surface (exclusively cloud shadow; NOT cast/topographic shadow)",
        description="Semantic interpretation of SCL Class 3"
    )
    # Backward compatibility aliases for SCL 3
    scl_3_cloud_shadow_pixels: int = Field(default=0, description="Count of SCL Class 3 (Cloud shadow)")
    scl_3_cloud_shadow_fraction: float = Field(default=0.0, description="Fraction of zone occupied by SCL Class 3 (Cloud shadow)")

    processing_baseline: Optional[str] = Field(default=None, description="Copernicus Sentinel-2 Processing Baseline (e.g. '02.14', '04.00', '05.11')")

    cloud_pixels: int = Field(..., description="Count of Class 8, 9, 10 (Cloud/cirrus) pixels")
    cloud_fraction: float = Field(..., description="Pixel-count fraction under clouds/cirrus (SCL 8, 9, 10)")
    snow_ice_pixels: int = Field(default=0, description="Count of Class 11 (Snow/Ice) pixels")
    snow_ice_fraction: float = Field(default=0.0, description="Pixel-count fraction covered by snow/ice (SCL 11)")
    other_pixels: int = Field(..., description="Count of Class 0 (NoData), 1 (Defective), 7 (Unclassified), or invalid pixels")
    other_fraction: float = Field(..., description="Pixel-count fraction unclassified, defective, or NoData")

    # Physical Zone Boundary Intersection-Area-Weighted Coverage
    total_intersected_area: Optional[float] = Field(
        default=None,
        description="Total geodesic/projected intersection area of all valid pixels clipped to zone polygon in CRS units squared"
    )
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
    cloud_shadow_area_fraction: Optional[float] = Field(
        default=None,
        description="Actual intersection-area-weighted fraction of zone covered by shadow"
    )
    cloud_area_fraction: Optional[float] = Field(
        default=None,
        description="Actual intersection-area-weighted fraction of zone covered by cloud/cirrus"
    )
    snow_ice_area_fraction: Optional[float] = Field(
        default=None,
        description="Actual intersection-area-weighted fraction of zone covered by snow/ice"
    )
    other_area_fraction: Optional[float] = Field(
        default=None,
        description="Actual intersection-area-weighted fraction unclassified or defective"
    )
    weighting_method: str = Field(
        default="pixel_count",
        description="Primary weighting method used in default fraction fields ('pixel_count')"
    )

    @property
    def other_invalid_fraction(self) -> float:
        """Alias for other_fraction for contract consistency."""
        return self.other_fraction


class ResamplingMethod(str, Enum):
    NEAREST = "nearest"
    BILINEAR = "bilinear"
    AVERAGE = "average"


def validate_raster_alignment(
    raster_a: GeoRasterGrid,
    raster_b: GeoRasterGrid,
    tolerance: float = 1e-4,
) -> Tuple[bool, Optional[str]]:
    """Verify that two rasters occupy an identical spatial grid.

    Checks:
    - CRS equivalence
    - Bounding box coordinates within numerical tolerance
    - Grid dimensions (rows, cols)
    - Pixel resolution (width, height)

    Args:
        raster_a: First GeoRasterGrid.
        raster_b: Second GeoRasterGrid.
        tolerance: Coordinate comparison tolerance in CRS units.

    Returns:
        Tuple of (is_aligned: bool, failure_reason: Optional[str]).
    """
    # 1. CRS check
    try:
        crs_a = CRS(raster_a.metadata.crs)
        crs_b = CRS(raster_b.metadata.crs)
        if crs_a != crs_b:
            return False, f"CRS mismatch: {crs_a.to_string()} vs {crs_b.to_string()}"
    except Exception as exc:
        return False, f"Invalid CRS: {str(exc)}"

    # 2. Dimensions check
    if raster_a.rows != raster_b.rows or raster_a.cols != raster_b.cols:
        return False, (
            f"Dimension mismatch: Raster A is ({raster_a.rows}, {raster_a.cols}) "
            f"vs Raster B ({raster_b.rows}, {raster_b.cols})"
        )

    # 3. Bounds check
    b_a = raster_a.bounds
    b_b = raster_b.bounds
    if (
        abs(b_a.min_x - b_b.min_x) > tolerance or
        abs(b_a.min_y - b_b.min_y) > tolerance or
        abs(b_a.max_x - b_b.max_x) > tolerance or
        abs(b_a.max_y - b_b.max_y) > tolerance
    ):
        return False, (
            f"Spatial bounds mismatch: A=[{b_a.min_x:.5f}, {b_a.min_y:.5f}, {b_a.max_x:.5f}, {b_a.max_y:.5f}] "
            f"vs B=[{b_b.min_x:.5f}, {b_b.min_y:.5f}, {b_b.max_x:.5f}, {b_b.max_y:.5f}]"
        )

    # 4. Pixel resolution check
    if (
        abs(raster_a.pixel_width - raster_b.pixel_width) > tolerance or
        abs(raster_a.pixel_height - raster_b.pixel_height) > tolerance
    ):
        return False, (
            f"Pixel size mismatch: A=({raster_a.pixel_width:.6f}, {raster_a.pixel_height:.6f}) "
            f"vs B=({raster_b.pixel_width:.6f}, {raster_b.pixel_height:.6f})"
        )

    return True, None


def resample_raster_to_target(
    source_raster: GeoRasterGrid,
    target_grid: GeoRasterGrid,
    method: ResamplingMethod = ResamplingMethod.BILINEAR,
    nodata_value: Optional[float] = None,
) -> GeoRasterGrid:
    """Resample a source GeoRasterGrid onto the exact spatial grid of a target GeoRasterGrid.

    Uses rasterio.warp.reproject to ensure mathematically robust coordinate transformation.

    Resampling guidelines:
    - Categorical data (e.g. SCL): MUST use NEAREST to prevent creating synthetic fractional classes.
    - Continuous downsampling (e.g. 10 m to 20 m): MUST use AVERAGE (spatial area mean of footprint).
    - Continuous interpolation (e.g. 20 m to 10 m): Use BILINEAR.

    Args:
        source_raster: GeoRasterGrid to be resampled.
        target_grid: GeoRasterGrid defining the destination bounding box, dimensions, and CRS.
        method: ResamplingMethod (NEAREST, BILINEAR, or AVERAGE).
        nodata_value: Optional explicit NoData value for unmapped destination pixels.

    Returns:
        New GeoRasterGrid aligned with target_grid.
    """
    resampling_map = {
        ResamplingMethod.NEAREST: Resampling.nearest,
        ResamplingMethod.BILINEAR: Resampling.bilinear,
        ResamplingMethod.AVERAGE: Resampling.average,
    }
    rio_resampling = resampling_map[method]

    src_transform = from_bounds(
        source_raster.bounds.min_x,
        source_raster.bounds.min_y,
        source_raster.bounds.max_x,
        source_raster.bounds.max_y,
        source_raster.cols,
        source_raster.rows,
    )

    dst_transform = from_bounds(
        target_grid.bounds.min_x,
        target_grid.bounds.min_y,
        target_grid.bounds.max_x,
        target_grid.bounds.max_y,
        target_grid.cols,
        target_grid.rows,
    )

    dst_data = np.full((target_grid.rows, target_grid.cols), np.nan, dtype=np.float32)

    effective_nodata = (
        nodata_value if nodata_value is not None else source_raster.metadata.nodata_value
    )

    reproject(
        source=source_raster.data.astype(np.float32),
        destination=dst_data,
        src_transform=src_transform,
        src_crs=source_raster.metadata.crs,
        dst_transform=dst_transform,
        dst_crs=target_grid.metadata.crs,
        src_nodata=effective_nodata,
        dst_nodata=effective_nodata,
        resampling=rio_resampling,
    )

    meta = RasterMetadata(
        scene_id=source_raster.metadata.scene_id,
        acquisition_time=source_raster.metadata.acquisition_time,
        crs=target_grid.metadata.crs,
        resolution_m=target_grid.metadata.resolution_m,
        bounds=target_grid.bounds,
        rows=target_grid.rows,
        cols=target_grid.cols,
        nodata_value=effective_nodata,
        processing_version=source_raster.metadata.processing_version,
    )

    return GeoRasterGrid(dst_data, meta)


def resample_scl_to_10m(
    scl_20m: GeoRasterGrid,
    target_10m: GeoRasterGrid,
) -> GeoRasterGrid:
    """Resample Sentinel-2 20 m Scene Classification Layer (SCL) onto a 10 m analysis grid.

    Enforces categorical integrity: strictly uses NEAREST-NEIGHBOR resampling to prevent
    interpolated fractional class values.
    """
    return resample_raster_to_target(
        source_raster=scl_20m,
        target_grid=target_10m,
        method=ResamplingMethod.NEAREST,
        nodata_value=0.0,
    )


def compute_zone_scl_breakdown(
    scl_raster: GeoRasterGrid,
    zone_geom: Polygon,
    processing_baseline: Optional[str] = None,
) -> ZoneSCLBreakdown:
    """Compute explicit SCL land cover and quality class breakdown across a zone polygon.

    Ensures every SCL class is accounted for in mutually exclusive categories:
    - SCL 4: Vegetation
    - SCL 5: Bare Soil / Non-vegetated
    - SCL 6: Water
    - SCL 2, 3: Shadow (Cast shadow and cloud shadow)
    - SCL 8, 9, 10: Cloud (Medium probability, high probability, thin cirrus)
    - SCL 11: Snow / Ice
    - SCL 0, 1, 7 and unclassified: Other / Invalid (NoData, defective, unclassified)

    Computes both:
    1. Pixel-count-weighted fractions (each intersecting pixel with overlap > min_overlap counts as 1.0).
    2. Actual intersection-area-weighted fractions (accounting for fractional pixel overlap at polygon boundary).

    Guarantees all mutually exclusive class fractions sum to 1.0 within floating point tolerance.
    """
    min_overlap = (scl_raster.pixel_width * scl_raster.pixel_height) * 1e-5

    z_minx, z_miny, z_maxx, z_maxy = zone_geom.bounds
    r_bounds = scl_raster.bounds

    col_min = max(0, int(np.floor((z_minx - r_bounds.min_x) / scl_raster.pixel_width)))
    col_max = min(scl_raster.cols - 1, int(np.ceil((z_maxx - r_bounds.min_x) / scl_raster.pixel_width)))
    row_min = max(0, int(np.floor((r_bounds.max_y - z_maxy) / scl_raster.pixel_height)))
    row_max = min(scl_raster.rows - 1, int(np.ceil((r_bounds.max_y - z_miny) / scl_raster.pixel_height)))

    pixel_counts = {c: 0 for c in range(12)}
    pixel_areas = {c: 0.0 for c in range(12)}
    extra_other_count = 0
    extra_other_area = 0.0

    total_pixels = 0
    total_area = 0.0

    for r in range(row_min, row_max + 1):
        for c in range(col_min, col_max + 1):
            p_minx, p_miny, p_maxx, p_maxy = scl_raster.get_pixel_bounds(r, c)
            pixel_polygon = box(p_minx, p_miny, p_maxx, p_maxy)

            if pixel_polygon.intersects(zone_geom):
                overlap = pixel_polygon.intersection(zone_geom)
                if not overlap.is_empty and overlap.area > min_overlap:
                    val = scl_raster.data[r, c]
                    if np.isfinite(val):
                        c_idx = int(round(val))
                        ov_area = float(overlap.area)
                        total_pixels += 1
                        total_area += ov_area
                        if 0 <= c_idx <= 11:
                            pixel_counts[c_idx] += 1
                            pixel_areas[c_idx] += ov_area
                        else:
                            extra_other_count += 1
                            extra_other_area += ov_area

    if total_pixels == 0:
        return ZoneSCLBreakdown(
            total_pixels=0,
            vegetation_pixels=0,
            vegetation_fraction=0.0,
            bare_soil_pixels=0,
            bare_soil_fraction=0.0,
            water_pixels=0,
            water_fraction=0.0,
            cloud_shadow_pixels=0,
            cloud_shadow_fraction=0.0,
            cloud_pixels=0,
            cloud_fraction=0.0,
            snow_ice_pixels=0,
            snow_ice_fraction=0.0,
            other_pixels=0,
            other_fraction=0.0,
            total_intersected_area=0.0,
            vegetation_area_fraction=0.0,
            bare_soil_area_fraction=0.0,
            water_area_fraction=0.0,
            cloud_shadow_area_fraction=0.0,
            cloud_area_fraction=0.0,
            snow_ice_area_fraction=0.0,
            other_area_fraction=0.0,
            weighting_method="pixel_count",
        )

    veg_count = pixel_counts[4]
    veg_area = pixel_areas[4]

    soil_count = pixel_counts[5]
    soil_area = pixel_areas[5]

    water_count = pixel_counts[6]
    water_area = pixel_areas[6]

    shadow_count = pixel_counts[2] + pixel_counts[3]
    shadow_area = pixel_areas[2] + pixel_areas[3]

    scl_2_count = pixel_counts[2]
    scl_3_count = pixel_counts[3]

    cloud_count = pixel_counts[8] + pixel_counts[9] + pixel_counts[10]
    cloud_area = pixel_areas[8] + pixel_areas[9] + pixel_areas[10]

    snow_count = pixel_counts[11]
    snow_area = pixel_areas[11]

    other_count = pixel_counts[0] + pixel_counts[1] + pixel_counts[7] + extra_other_count
    other_area = pixel_areas[0] + pixel_areas[1] + pixel_areas[7] + extra_other_area

    return ZoneSCLBreakdown(
        total_pixels=total_pixels,
        vegetation_pixels=veg_count,
        vegetation_fraction=float(veg_count / total_pixels),
        bare_soil_pixels=soil_count,
        bare_soil_fraction=float(soil_count / total_pixels),
        water_pixels=water_count,
        water_fraction=float(water_count / total_pixels),
        cloud_shadow_pixels=shadow_count,
        cloud_shadow_fraction=float(shadow_count / total_pixels),
        scl_2_pixels=scl_2_count,
        scl_2_fraction=float(scl_2_count / total_pixels),
        scl_2_class_number=2,
        scl_2_original_class_label=resolve_scl_class_2_semantics(processing_baseline)[0],
        scl_2_semantic_interpretation=resolve_scl_class_2_semantics(processing_baseline)[2],
        scl_2_cast_shadow_pixels=scl_2_count,
        scl_2_cast_shadow_fraction=float(scl_2_count / total_pixels),
        scl_3_pixels=scl_3_count,
        scl_3_fraction=float(scl_3_count / total_pixels),
        scl_3_class_number=3,
        scl_3_original_class_label="CLOUD_SHADOW",
        scl_3_semantic_interpretation="Cloud shadow cast on surface (exclusively cloud shadow; NOT cast/topographic shadow)",
        scl_3_cloud_shadow_pixels=scl_3_count,
        scl_3_cloud_shadow_fraction=float(scl_3_count / total_pixels),
        processing_baseline=resolve_scl_class_2_semantics(processing_baseline)[1],
        cloud_pixels=cloud_count,
        cloud_fraction=float(cloud_count / total_pixels),
        snow_ice_pixels=snow_count,
        snow_ice_fraction=float(snow_count / total_pixels),
        other_pixels=other_count,
        other_fraction=float(other_count / total_pixels),
        total_intersected_area=float(total_area),
        vegetation_area_fraction=float(veg_area / total_area) if total_area > 0 else 0.0,
        bare_soil_area_fraction=float(soil_area / total_area) if total_area > 0 else 0.0,
        water_area_fraction=float(water_area / total_area) if total_area > 0 else 0.0,
        cloud_shadow_area_fraction=float(shadow_area / total_area) if total_area > 0 else 0.0,
        cloud_area_fraction=float(cloud_area / total_area) if total_area > 0 else 0.0,
        snow_ice_area_fraction=float(snow_area / total_area) if total_area > 0 else 0.0,
        other_area_fraction=float(other_area / total_area) if total_area > 0 else 0.0,
        weighting_method="pixel_count",
    )


def calculate_aligned_ndmi(
    nir_raster: GeoRasterGrid,
    swir_raster: GeoRasterGrid,
    use_native_20m: bool = True,
) -> GeoRasterGrid:
    """Calculate NDMI ensuring rigorous spatial grid alignment between NIR and SWIR1 bands.

    NDMI = (NIR - SWIR1) / (NIR + SWIR1)

    Approaches supported:
    1. Native 20 m alignment (Recommended):
       If NIR is Band 8A (20 m) and SWIR is Band 11 (20 m), both are already natively
       aligned at 20 m, avoiding resampling artifacts.
    2. Resampled alignment:
       If NIR is Band 8 (10 m), it is downsampled onto the 20 m SWIR1 grid using
       spatial area averaging (mean pixel aggregation across the 2x2 footprint),
       avoiding point-sample aliasing.

    Args:
        nir_raster: GeoRasterGrid of NIR band (B8 or B8A).
        swir_raster: GeoRasterGrid of SWIR1 band (B11, nominally 20 m).
        use_native_20m: If True and resolutions differ, downsamples 10 m NIR to 20 m SWIR1 grid.

    Returns:
        GeoRasterGrid of NDMI values.
    """
    is_aligned, reason = validate_raster_alignment(nir_raster, swir_raster)

    if not is_aligned:
        if use_native_20m:
            # Resample 10 m NIR to 20 m SWIR1 grid using AREA AVERAGE
            aligned_nir = resample_raster_to_target(
                source_raster=nir_raster,
                target_grid=swir_raster,
                method=ResamplingMethod.AVERAGE,
            )
            aligned_swir = swir_raster
            base_meta = swir_raster.metadata
        else:
            # Resample 20 m SWIR1 to 10 m NIR grid using BILINEAR
            aligned_swir = resample_raster_to_target(
                source_raster=swir_raster,
                target_grid=nir_raster,
                method=ResamplingMethod.BILINEAR,
            )
            aligned_nir = nir_raster
            base_meta = nir_raster.metadata
    else:
        aligned_nir = nir_raster
        aligned_swir = swir_raster
        base_meta = swir_raster.metadata

    ndmi_data = calculate_ndmi(aligned_nir.data, aligned_swir.data)

    out_meta = RasterMetadata(
        scene_id=base_meta.scene_id,
        acquisition_time=base_meta.acquisition_time,
        crs=base_meta.crs,
        resolution_m=base_meta.resolution_m,
        bounds=base_meta.bounds,
        rows=base_meta.rows,
        cols=base_meta.cols,
        nodata_value=np.nan,
        processing_version=base_meta.processing_version,
    )
    return GeoRasterGrid(ndmi_data, out_meta)
