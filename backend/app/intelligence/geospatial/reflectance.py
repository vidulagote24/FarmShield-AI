"""Source-aware radiometric calibration and surface reflectance normalization for Sentinel-2.

Official References and Standards:
1. Copernicus Data Space S2 L2A Radiometric Offset:
   https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html
   - From Processing Baseline (PB) 04.00 (deployed January 25, 2022), ESA introduced a radiometric
     offset of BOA_ADD_OFFSET = -1000 to prevent truncation of negative surface reflectances.
     Formula:
         Surface_Reflectance = (DN + BOA_ADD_OFFSET) / QUANTIFICATION_VALUE
                             = (DN - 1000) / 10000.0
   - Prior to PB 04.00, BOA_ADD_OFFSET = 0 (or omitted):
         Surface_Reflectance = DN / 10000.0
   - In raw L2A products, DN = 0 is strictly designated as NoData (outside swath / detector boundary).

2. Google Earth Engine Harmonized Surface Reflectance:
   https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED
   - GEE harmonizes PB >= 04.00 with older scenes by applying the offset shift on ingestion,
     so Harmonized SR has BOA_ADD_OFFSET = 0 and scale = 0.0001 (divide by 10000.0).

3. Reflectance Validity Policy:
   - Reflectance over vegetation and typical soils is normally 0.0 to 1.0.
   - Very bright soils, dry salt pans, steep sun-facing terrain, or specular reflection can
     legitimately exceed 1.0 (up to ~1.4 - 1.6). Blanket clamping to 1.0 distorts indices.
     The upper threshold `max_plausible_reflectance` is configurable (default 2.0).
   - Small negative reflectances down to negative_tolerance (default -0.05) are caused by
     atmospheric over-correction over very dark targets/water in radiative transfer models (Sen2Cor).
     Handling is configurable:
     * clamp_small_negatives=True (default): Clamps [-0.05, 0.0] to 0.0.
     * allow_negative_reflectance=True: Preserves exact negative values down to tolerance.
     * clamp=False and allow=False: Masks all negative values (< 0.0) as invalid (NaN).
"""

from enum import Enum
from typing import Any, Dict, Optional, Tuple
import numpy as np
from pydantic import BaseModel, ConfigDict, Field


class S2ReflectanceMode(str, Enum):
    """Supported Sentinel-2 radiometric input modes."""
    HARMONIZED_SR = "harmonized_sr"  # Pre-harmonized integer SR (e.g. GEE S2_SR_HARMONIZED, scale=10000)
    RAW_L2A_DN = "raw_l2a_dn"        # Raw ESA L2A integer DN with BOA_ADD_OFFSET (DN=0 is NoData)
    NORMALIZED_FLOAT = "normalized_float"  # Already normalized float surface reflectance [0.0, 2.0]


class S2CalibrationMetadata(BaseModel):
    """Metadata governing Sentinel-2 radiometric conversion."""
    mode: S2ReflectanceMode = Field(..., description="Radiometric input format")
    processing_baseline: Optional[str] = Field(
        default=None,
        description="ESA Processing Baseline (e.g., '04.00', '05.09', '02.14')"
    )
    boa_add_offset: Optional[float] = Field(
        default=None,
        description="Radiometric offset in DN (e.g., -1000.0 for PB >= 04.00, 0.0 for PB < 04.00)"
    )
    quantification_value: float = Field(
        default=10000.0,
        gt=0.0,
        description="Scaling divisor (standard S2 is 10000.0)"
    )
    nodata_dn: int = Field(
        default=0,
        description="Digital number denoting NoData in raw products"
    )
    max_plausible_reflectance: float = Field(
        default=2.0,
        description="Configurable upper bound; values above this are masked as sensor artifacts"
    )
    negative_tolerance: float = Field(
        default=-0.05,
        description="Tolerance for small negative values from atmospheric over-correction"
    )
    clamp_small_negatives: bool = Field(
        default=True,
        description="If True, small negative values within tolerance are clamped to 0.0"
    )
    allow_negative_reflectance: bool = Field(
        default=False,
        description="If True, exact negative reflectances within tolerance are preserved without clamping"
    )


class CalibratedReflectanceResult(BaseModel):
    """Detailed result container preserving calibrated array and diagnostic metadata."""
    data: Any = Field(..., description="2D numpy array of calibrated float32 reflectance")
    metadata: S2CalibrationMetadata = Field(..., description="Calibration metadata used")
    applied_offset: float = Field(..., description="Exact offset applied in DN")
    applied_scale: float = Field(..., description="Exact divisor applied")
    nodata_pixel_count: int = Field(..., description="Pixels masked due to NoData flag")
    valid_pixel_count: int = Field(..., description="Valid usable pixels")
    clamped_negative_count: int = Field(..., description="Pixels clamped from small negative to 0.0")
    severely_negative_count: int = Field(..., description="Pixels masked due to severe negative values")
    exceeded_max_count: int = Field(..., description="Pixels masked due to exceeding max_plausible_reflectance")

    model_config = ConfigDict(arbitrary_types_allowed=True)


def calibrate_sentinel2_reflectance_with_diagnostics(
    array: np.ndarray,
    metadata: S2CalibrationMetadata,
) -> CalibratedReflectanceResult:
    """Calibrate Sentinel-2 array into surface reflectance and return detailed diagnostic record."""
    if array.ndim != 2:
        raise ValueError(f"Expected 2D band array, got ndim={array.ndim}")

    if array.size == 0:
        raise ValueError("Cannot calibrate empty array.")

    # Guard against applying raw offset twice to float data
    if metadata.mode == S2ReflectanceMode.RAW_L2A_DN:
        if np.issubdtype(array.dtype, np.floating):
            finite_vals = array[np.isfinite(array)]
            if finite_vals.size > 0 and np.nanmax(finite_vals) <= 2.5 and np.nanmin(finite_vals) >= -0.5:
                raise ValueError(
                    "Input array appears to already contain normalized float reflectance "
                    f"(max={np.nanmax(finite_vals):.3f}). Applying RAW_L2A_DN offset (-1000) "
                    "would cause unphysical double-correction."
                )

    out = np.full(array.shape, np.nan, dtype=np.float32)

    nodata_count = 0
    clamped_count = 0
    severe_neg_count = 0
    exceeded_max_count = 0

    if metadata.mode == S2ReflectanceMode.NORMALIZED_FLOAT:
        arr_f = array.astype(np.float64, copy=True)
        valid = np.isfinite(arr_f)
        nodata_count = int(np.sum(~valid))

        # Check negative values
        if metadata.allow_negative_reflectance:
            # Keep negative values down to tolerance
            in_bounds_neg = valid & (arr_f < 0.0) & (arr_f >= metadata.negative_tolerance)
            # do not clamp
        elif metadata.clamp_small_negatives:
            small_neg = valid & (arr_f < 0.0) & (arr_f >= metadata.negative_tolerance)
            clamped_count = int(np.sum(small_neg))
            arr_f[small_neg] = 0.0
        else:
            # Mask all negatives
            all_neg = valid & (arr_f < 0.0)
            severe_neg_count += int(np.sum(all_neg))
            arr_f[all_neg] = np.nan

        # Severely negative mask
        severely_neg = valid & (arr_f < metadata.negative_tolerance)
        severe_neg_count += int(np.sum(severely_neg))
        arr_f[severely_neg] = np.nan

        # Maximum plausible threshold check
        too_high = valid & (arr_f > metadata.max_plausible_reflectance)
        exceeded_max_count = int(np.sum(too_high))
        arr_f[too_high] = np.nan

        usable = np.isfinite(arr_f)
        out[usable] = arr_f[usable].astype(np.float32)
        valid_count = int(np.sum(usable))

        return CalibratedReflectanceResult(
            data=out,
            metadata=metadata,
            applied_offset=0.0,
            applied_scale=1.0,
            nodata_pixel_count=nodata_count,
            valid_pixel_count=valid_count,
            clamped_negative_count=clamped_count,
            severely_negative_count=severe_neg_count,
            exceeded_max_count=exceeded_max_count,
        )

    elif metadata.mode == S2ReflectanceMode.HARMONIZED_SR:
        arr_f = array.astype(np.float64, copy=True)
        nodata_mask = (array == metadata.nodata_dn) | (~np.isfinite(arr_f))
        nodata_count = int(np.sum(nodata_mask))

        valid_dn = ~nodata_mask
        sr = arr_f[valid_dn] / metadata.quantification_value

        if metadata.allow_negative_reflectance:
            pass
        elif metadata.clamp_small_negatives:
            small_neg = (sr < 0.0) & (sr >= metadata.negative_tolerance)
            clamped_count = int(np.sum(small_neg))
            sr[small_neg] = 0.0
        else:
            all_neg = sr < 0.0
            severe_neg_count += int(np.sum(all_neg))
            sr[all_neg] = np.nan

        severely_neg = sr < metadata.negative_tolerance
        severe_neg_count += int(np.sum(severely_neg))
        sr[severely_neg] = np.nan

        too_high = sr > metadata.max_plausible_reflectance
        exceeded_max_count = int(np.sum(too_high))
        sr[too_high] = np.nan

        usable = np.isfinite(sr)
        temp = np.full(sr.shape, np.nan, dtype=np.float32)
        temp[usable] = sr[usable].astype(np.float32)
        out[valid_dn] = temp
        valid_count = int(np.sum(usable))

        return CalibratedReflectanceResult(
            data=out,
            metadata=metadata,
            applied_offset=0.0,
            applied_scale=metadata.quantification_value,
            nodata_pixel_count=nodata_count,
            valid_pixel_count=valid_count,
            clamped_negative_count=clamped_count,
            severely_negative_count=severe_neg_count,
            exceeded_max_count=exceeded_max_count,
        )

    elif metadata.mode == S2ReflectanceMode.RAW_L2A_DN:
        if metadata.boa_add_offset is None:
            if metadata.processing_baseline is not None:
                try:
                    pb_num = float(metadata.processing_baseline[:5])
                    offset = -1000.0 if pb_num >= 4.0 else 0.0
                except ValueError:
                    raise ValueError(
                        f"Unknown processing_baseline format: '{metadata.processing_baseline}'. "
                        "Explicit boa_add_offset is required to avoid guessing."
                    )
            else:
                raise ValueError(
                    "RAW_L2A_DN requires explicit boa_add_offset or processing_baseline. "
                    "Cannot silently infer radiometric offset."
                )
        else:
            offset = float(metadata.boa_add_offset)

        arr_f = array.astype(np.float64, copy=True)
        nodata_mask = (array == metadata.nodata_dn) | (~np.isfinite(arr_f))
        nodata_count = int(np.sum(nodata_mask))

        valid_dn = ~nodata_mask
        sr = (arr_f[valid_dn] + offset) / metadata.quantification_value

        if metadata.allow_negative_reflectance:
            pass
        elif metadata.clamp_small_negatives:
            small_neg = (sr < 0.0) & (sr >= metadata.negative_tolerance)
            clamped_count = int(np.sum(small_neg))
            sr[small_neg] = 0.0
        else:
            all_neg = sr < 0.0
            severe_neg_count += int(np.sum(all_neg))
            sr[all_neg] = np.nan

        severely_neg = sr < metadata.negative_tolerance
        severe_neg_count += int(np.sum(severely_neg))
        sr[severely_neg] = np.nan

        too_high = sr > metadata.max_plausible_reflectance
        exceeded_max_count = int(np.sum(too_high))
        sr[too_high] = np.nan

        usable = np.isfinite(sr)
        temp = np.full(sr.shape, np.nan, dtype=np.float32)
        temp[usable] = sr[usable].astype(np.float32)
        out[valid_dn] = temp
        valid_count = int(np.sum(usable))

        return CalibratedReflectanceResult(
            data=out,
            metadata=metadata,
            applied_offset=offset,
            applied_scale=metadata.quantification_value,
            nodata_pixel_count=nodata_count,
            valid_pixel_count=valid_count,
            clamped_negative_count=clamped_count,
            severely_negative_count=severe_neg_count,
            exceeded_max_count=exceeded_max_count,
        )

    else:
        raise ValueError(f"Unsupported reflectance mode: {metadata.mode}")


def calibrate_sentinel2_reflectance(
    array: np.ndarray,
    metadata: S2CalibrationMetadata,
) -> np.ndarray:
    """Convert raw or harmonized Sentinel-2 band arrays into true surface reflectance float32.

    Returns the 2D float32 array directly for clean integration with downstream index calculations.
    """
    res = calibrate_sentinel2_reflectance_with_diagnostics(array, metadata)
    return res.data
