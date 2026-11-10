"""Satellite spectral index calculations for FarmShield AI.

Scientific and methodological principles:
1. NDVI is computed strictly from Red and NIR surface reflectance:
      NDVI = (NIR - Red) / (NIR + Red)
2. Handle zero denominators, NaN inputs, and negative surface reflectance without crashing.
3. NDMI is distinct from NDWI:
   - NDMI (Normalized Difference Moisture Index) requires NIR (Sentinel-2 B8)
     and SWIR1 (Sentinel-2 B11): (NIR - SWIR1) / (NIR + SWIR1).
   - NDWI is ambiguous in literature: McFeeters (1996) uses (Green - NIR) / (Green + NIR)
     for open water delineation, whereas Gao (1996) uses (NIR - SWIR) for vegetation.
   - FarmShield AI explicitly avoids ambiguous "NDWI" designations and restricts NDMI
     to scenes where SWIR1 is available.
"""

from typing import Optional, Tuple, Union
import numpy as np


def calculate_ndvi(
    red: np.ndarray,
    nir: np.ndarray,
    scale_factor: Optional[float] = None,
    clip_range: Tuple[float, float] = (-1.0, 1.0),
) -> np.ndarray:
    """Calculate Normalized Difference Vegetation Index (NDVI) from Red and NIR reflectance arrays.

    Formula:
        NDVI = (NIR - Red) / (NIR + Red)

    Required bands (e.g. Sentinel-2 MSI):
        - Red: Band 4 (nominal central wavelength 665 nm, 10 m resolution)
        - NIR: Band 8 (nominal central wavelength 842 nm, 10 m resolution)

    Edge case handling:
        - Where (NIR + Red) == 0, returns np.nan (division-by-zero protection).
        - Where inputs are NaN, returns np.nan.
        - Negative reflectance values or invalid physical values are masked as np.nan.
        - Output is clipped to valid physical theoretical range [-1.0, 1.0].

    Args:
        red: 2D numpy array of Red surface reflectance.
        nir: 2D numpy array of Near-Infrared surface reflectance.
        scale_factor: Optional divisor if reflectance is stored as integers (e.g. 10000 for S2 SR).
                     If None and max value > 10.0, auto-detects 10000.0 scale factor.
        clip_range: Minimum and maximum allowed index values, default (-1.0, 1.0).

    Returns:
        2D numpy array of float32 NDVI values with NaN for invalid/uncomputable pixels.

    Raises:
        ValueError: If red and nir shapes do not match or arrays are empty.
    """
    if red.shape != nir.shape:
        raise ValueError(f"Array shapes must match: Red {red.shape} vs NIR {nir.shape}")

    if red.size == 0:
        raise ValueError("Cannot calculate NDVI on empty arrays.")

    # Convert to float64 for high numerical stability during calculation
    red_f = red.astype(np.float64, copy=True)
    nir_f = nir.astype(np.float64, copy=True)

    # Scale factor handling (Sentinel-2 L2A often scales reflectance by 10,000)
    if scale_factor is not None and scale_factor > 0:
        red_f = red_f / scale_factor
        nir_f = nir_f / scale_factor
    elif np.nanmax(nir_f) > 10.0 or np.nanmax(red_f) > 10.0:
        # Auto-detect standard 10,000 scaling for raw integer bands
        red_f = red_f / 10000.0
        nir_f = nir_f / 10000.0

    # Physical validity masking: reflectance cannot be negative
    invalid_physical = (red_f < 0.0) | (nir_f < 0.0) | np.isnan(red_f) | np.isnan(nir_f)

    numerator = nir_f - red_f
    denominator = nir_f + red_f

    # Create output array initialized to NaN
    ndvi = np.full(red.shape, np.nan, dtype=np.float32)

    # Valid computable pixels: non-zero denominator, physically valid, finite
    valid_mask = (~invalid_physical) & (denominator > 1e-7) & np.isfinite(denominator)

    # Compute index
    ndvi[valid_mask] = (numerator[valid_mask] / denominator[valid_mask]).astype(np.float32)

    # Apply clipping to theoretical range [-1.0, 1.0]
    min_val, max_val = clip_range
    np.clip(ndvi, min_val, max_val, out=ndvi)

    return ndvi


def calculate_ndmi(
    nir: np.ndarray,
    swir1: np.ndarray,
    scale_factor: Optional[float] = None,
    clip_range: Tuple[float, float] = (-1.0, 1.0),
) -> np.ndarray:
    """Calculate Normalized Difference Moisture Index (NDMI) from NIR and SWIR1 reflectance.

    Formula:
        NDMI = (NIR - SWIR1) / (NIR + SWIR1)

    Required bands (Sentinel-2 MSI):
        - NIR: Band 8 (central wavelength 842 nm, 10 m resolution)
        - SWIR1: Band 11 (central wavelength 1610 nm, 20 m resolution, resampled to match NIR)

    Note:
        NDMI reflects liquid water in crop canopies (Gao 1996).
        Do NOT call this function if SWIR1 band data is unavailable.
        NDMI is a vegetation moisture index and does NOT directly measure root-zone soil moisture.
    """
    if nir.shape != swir1.shape:
        raise ValueError(f"Array shapes must match: NIR {nir.shape} vs SWIR1 {swir1.shape}")

    if nir.size == 0:
        raise ValueError("Cannot calculate NDMI on empty arrays.")

    nir_f = nir.astype(np.float64, copy=True)
    swir_f = swir1.astype(np.float64, copy=True)

    if scale_factor is not None and scale_factor > 0:
        nir_f = nir_f / scale_factor
        swir_f = swir_f / scale_factor
    elif np.nanmax(nir_f) > 10.0 or np.nanmax(swir_f) > 10.0:
        nir_f = nir_f / 10000.0
        swir_f = swir_f / 10000.0

    invalid_physical = (nir_f < 0.0) | (swir_f < 0.0) | np.isnan(nir_f) | np.isnan(swir_f)
    numerator = nir_f - swir_f
    denominator = nir_f + swir_f

    ndmi = np.full(nir.shape, np.nan, dtype=np.float32)
    valid_mask = (~invalid_physical) & (denominator > 1e-7) & np.isfinite(denominator)

    ndmi[valid_mask] = (numerator[valid_mask] / denominator[valid_mask]).astype(np.float32)
    np.clip(ndmi, clip_range[0], clip_range[1], out=ndmi)

    return ndmi

