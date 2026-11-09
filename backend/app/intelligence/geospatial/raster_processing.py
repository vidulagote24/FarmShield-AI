"""Raster data representation, georeferencing, NoData masking, and cloud filtering.

Provides a clean container for 2D raster grids with explicit georeferencing metadata,
pixel-to-coordinate mapping, NoData identification, and quality mask filtering.
"""

from typing import Optional, Set, Tuple, Union
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from affine import Affine

from backend.app.intelligence.types import BoundingBox, RasterMetadata


class GeoRasterGrid:
    """A 2D raster grid with georeferenced spatial metadata and affine transform."""

    def __init__(self, data: np.ndarray, metadata: RasterMetadata):
        """Initialize GeoRasterGrid.

        Args:
            data: 2D numpy array with dimensions matching (metadata.rows, metadata.cols).
            metadata: RasterMetadata describing spatial bounds, CRS, resolution, and timestamps.

        Raises:
            ValueError: If data is not 2D or dimensions do not match metadata.
        """
        if data.ndim != 2:
            raise ValueError(f"Raster data must be 2-dimensional (rows, cols), got ndim={data.ndim}")

        if data.shape != (metadata.rows, metadata.cols):
            raise ValueError(
                f"Data shape {data.shape} does not match metadata dimensions "
                f"({metadata.rows}, {metadata.cols})"
            )

        self.data = data
        self.metadata = metadata

    @property
    def rows(self) -> int:
        return self.metadata.rows

    @property
    def cols(self) -> int:
        return self.metadata.cols

    @property
    def bounds(self) -> BoundingBox:
        return self.metadata.bounds

    @property
    def pixel_width(self) -> float:
        """Width of a single pixel in coordinate units (degrees or meters)."""
        return (self.bounds.max_x - self.bounds.min_x) / self.cols

    @property
    def pixel_height(self) -> float:
        """Height of a single pixel in coordinate units (degrees or meters)."""
        return (self.bounds.max_y - self.bounds.min_y) / self.rows

    @property
    def transform(self) -> Affine:
        """Affine transformation mapping pixel coordinates (col, row) to CRS (x, y)."""
        return from_bounds(
            self.bounds.min_x,
            self.bounds.min_y,
            self.bounds.max_x,
            self.bounds.max_y,
            self.cols,
            self.rows,
        )

    @property
    def pixel_area(self) -> float:
        """Area of a single pixel cell in squared CRS coordinate units.

        Calculated using the full 2D affine transformation determinant:
            |a * e - b * d|

        CRS Unit Warning:
        - The resulting value is strictly in the squared units of the raster's CRS:
          * Projected CRS (e.g., UTM EPSG:32643): area in square metres (m^2).
          * Geographic CRS (e.g., WGS84 EPSG:4326): area in square degrees (deg^2).
        - DO NOT treat or label EPSG:4326 pixel_area as square metres. Degree area varies with
          latitude and cannot be used directly as a metric ground area measurement.
        - For metric farm or parcel ground area, use calculate_geodesic_area_m2() or projected CRS.

        For north-up, axis-aligned grids (b = 0, d = 0), this evaluates exactly
        to pixel_width * pixel_height in coordinate units squared.
        """
        t = self.transform
        return abs(t.a * t.e - t.b * t.d)

    def validate_axis_aligned(self) -> None:
        """Verify that the raster is north-up and axis-aligned (zero rotation and skew).

        Raises:
            ValueError: If the affine transform has non-zero rotation or shear coefficients.
        """
        t = self.transform
        if abs(t.b) > 1e-9 or abs(t.d) > 1e-9:
            raise ValueError(
                f"Unsupported rotated or sheared grid: affine coefficients b={t.b}, d={t.d} are non-zero. "
                "FarmShield AI currently assumes north-up, axis-aligned grids."
            )

    def coord_to_pixel(self, x: float, y: float) -> Tuple[int, int]:
        """Convert a continuous spatial coordinate (x, y) to discrete grid indices (row, col)."""
        col = int((x - self.bounds.min_x) / self.pixel_width)
        row = int((self.bounds.max_y - y) / self.pixel_height)
        return row, col

    def pixel_to_coord(self, row: int, col: int) -> Tuple[float, float]:
        """Return the center continuous coordinate (x, y) of a given pixel (row, col)."""
        x = self.bounds.min_x + (col + 0.5) * self.pixel_width
        y = self.bounds.max_y - (row + 0.5) * self.pixel_height
        return x, y

    def get_pixel_bounds(self, row: int, col: int) -> Tuple[float, float, float, float]:
        """Return the bounding box (minx, miny, maxx, maxy) of a specific pixel cell."""
        minx = self.bounds.min_x + col * self.pixel_width
        maxx = minx + self.pixel_width
        maxy = self.bounds.max_y - row * self.pixel_height
        miny = maxy - self.pixel_height
        return minx, miny, maxx, maxy

    @classmethod
    def from_geotiff(cls, filepath: str, band_idx: int = 1, scene_id: Optional[str] = None) -> "GeoRasterGrid":
        """Read a single band from a GeoTIFF file into a GeoRasterGrid.

        Args:
            filepath: Path to the GeoTIFF file.
            band_idx: 1-based band index (default 1).
            scene_id: Optional scene identifier (defaults to filename).

        Returns:
            GeoRasterGrid populated from GeoTIFF raster data and metadata.
        """
        with rasterio.open(filepath) as src:
            t = src.transform
            if abs(t.b) > 1e-9 or abs(t.d) > 1e-9:
                raise ValueError(
                    f"Unsupported rotated or sheared raster in '{filepath}': "
                    f"affine coefficients b={t.b}, d={t.d} are non-zero. "
                    "FarmShield AI currently requires north-up, axis-aligned grids."
                )
            data = src.read(band_idx).astype(np.float32)
            crs_str = src.crs.to_string() if src.crs else "EPSG:4326"
            b = src.bounds
            bounds = BoundingBox(
                min_x=b.left,
                min_y=b.bottom,
                max_x=b.right,
                max_y=b.top,
                crs=crs_str,
            )
            # Resolution in coordinate units or meters
            res_m = float(src.res[0])
            nodata_val = float(src.nodata) if src.nodata is not None else None

            meta = RasterMetadata(
                scene_id=scene_id or filepath.split("/")[-1],
                crs=crs_str,
                resolution_m=res_m,
                bounds=bounds,
                rows=src.height,
                cols=src.width,
                nodata_value=nodata_val,
            )
            return cls(data, meta)

    def to_geotiff(self, filepath: str) -> None:
        """Write the GeoRasterGrid array and spatial metadata to a GeoTIFF file.

        Args:
            filepath: Destination path for the GeoTIFF.
        """
        nodata = self.metadata.nodata_value if self.metadata.nodata_value is not None else -9999.0
        # Replace NaN with explicit nodata for writing
        write_data = np.where(np.isnan(self.data), nodata, self.data).astype(np.float32)

        with rasterio.open(
            filepath,
            "w",
            driver="GTiff",
            height=self.rows,
            width=self.cols,
            count=1,
            dtype="float32",
            crs=self.metadata.crs,
            transform=self.transform,
            nodata=nodata,
        ) as dst:
            dst.write(write_data, 1)


def create_valid_mask(
    data: np.ndarray,
    nodata_value: Optional[float] = None,
    cloud_mask: Optional[np.ndarray] = None,
    scl_layer: Optional[np.ndarray] = None,
    usable_scl_classes: Optional[Set[int]] = None,
    vegetation_only: bool = True,
    crop_vegetation_only: Optional[bool] = None,
) -> np.ndarray:
    """Create a unified boolean mask indicating which pixels are valid and usable.

    True = valid, usable pixel for the target analysis.
    False = cloudy, shadow, invalid, NoData, or non-target land-cover pixel.

    Critical SCL separation:
    - If vegetation_only=True: Only Class 4 (Vegetation) is accepted. Note that SCL Class 4
      identifies general green vegetation (not specifically agricultural crops). Bare soil (Class 5)
      and water (Class 6) are masked out so they cannot depress or distort vegetation indices.
    - If vegetation_only=False: Classes {4, 5, 6} are accepted (general clear-sky surface quality).
    - If usable_scl_classes is explicitly passed: Exactly that set of classes is accepted.

    Args:
        data: 2D numpy array of raster values.
        nodata_value: Optional value denoting missing/NoData pixels.
        cloud_mask: Optional 2D boolean array (True = clear, False = cloudy/shadow).
        scl_layer: Optional 2D array of Sentinel-2 Scene Classification Layer (SCL) codes.
        usable_scl_classes: Optional explicit set of allowed integer SCL classes.
        vegetation_only: When usable_scl_classes is None, whether to restrict to Class 4.
        crop_vegetation_only: Deprecated alias for vegetation_only (maintained for backward compatibility).

    Returns:
        2D boolean array where True indicates usable pixel.
    """
    if crop_vegetation_only is not None:
        vegetation_only = crop_vegetation_only

    valid = np.isfinite(data)

    # Check explicit NoData value
    if nodata_value is not None:
        if np.isnan(nodata_value):
            valid = valid & (~np.isnan(data))
        else:
            valid = valid & (data != nodata_value)

    # Check external cloud mask if provided
    if cloud_mask is not None:
        if cloud_mask.shape != data.shape:
            raise ValueError(f"Cloud mask shape {cloud_mask.shape} does not match data {data.shape}")
        valid = valid & cloud_mask.astype(bool)

    # Check Sentinel-2 Scene Classification Layer (SCL)
    if scl_layer is not None:
        if scl_layer.shape != data.shape:
            raise ValueError(f"SCL layer shape {scl_layer.shape} does not match data {data.shape}")
        if usable_scl_classes is not None:
            allowed = usable_scl_classes
        elif vegetation_only:
            allowed = {4}  # General vegetation
        else:
            allowed = {4, 5, 6}  # General clear ground/water observation

        usable_scl = np.isin(scl_layer, list(allowed))
        valid = valid & usable_scl

    return valid

