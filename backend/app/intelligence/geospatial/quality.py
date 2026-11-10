"""Spatial data quality assessment rules.

Evaluates valid-pixel coverage, cloud contamination, and spatial overlap
against configurable scientific thresholds.
"""

from typing import Optional, Tuple
from backend.app.intelligence.types import SpatialQualityStatus


def assess_spatial_quality(
    total_pixels: int,
    valid_pixels: int,
    valid_fraction: float,
    min_valid_fraction_threshold: float = 0.60,
    min_pixel_count_threshold: int = 3,
    has_cloud_contamination: bool = False,
) -> Tuple[SpatialQualityStatus, Optional[str]]:
    """Assess the spatial observation quality of a zone raster intersection.

    Enforces that:
    1. Zero intersecting pixels -> NO_SPATIAL_OVERLAP.
    2. Zero valid pixels -> INSUFFICIENT_COVERAGE.
    3. Below configurable coverage threshold -> INSUFFICIENT_COVERAGE / CLOUD_CONTAMINATED.
    4. Sufficient clear pixels -> GOOD (or SUSPECT if minor noise).

    Args:
        total_pixels: Count of raster pixels falling within zone polygon.
        valid_pixels: Count of unmasked, non-NoData pixels.
        valid_fraction: Ratio of valid to total pixels.
        min_valid_fraction_threshold: Minimum acceptable valid pixel fraction (e.g. 0.60).
        min_pixel_count_threshold: Minimum absolute count of valid pixels required.
        has_cloud_contamination: Flag indicating whether masked pixels were caused by clouds/shadows.

    Returns:
        Tuple of (SpatialQualityStatus, explanation_note).
    """
    if total_pixels <= 0:
        return (
            SpatialQualityStatus.NO_SPATIAL_OVERLAP,
            "Zone geometry does not spatially intersect the raster extent."
        )

    if valid_pixels <= 0:
        note = (
            "All pixels inside the zone are invalid or masked (e.g., dense cloud cover or NoData)."
            if has_cloud_contamination else
            "Zone contains zero usable pixels due to missing or invalid data."
        )
        return SpatialQualityStatus.INSUFFICIENT_COVERAGE, note

    if valid_pixels < min_pixel_count_threshold:
        return (
            SpatialQualityStatus.INSUFFICIENT_COVERAGE,
            f"Only {valid_pixels} valid pixels found inside zone, below absolute minimum threshold of {min_pixel_count_threshold}."
        )

    if valid_fraction < min_valid_fraction_threshold:
        status = (
            SpatialQualityStatus.CLOUD_CONTAMINATED
            if has_cloud_contamination else
            SpatialQualityStatus.INSUFFICIENT_COVERAGE
        )
        note = (
            f"Valid pixel fraction ({valid_fraction:.1%}) is below configured threshold "
            f"({min_valid_fraction_threshold:.1%}). Statistics are withheld to prevent misleading recommendations."
        )
        return status, note

    # High quality clear observation
    return SpatialQualityStatus.GOOD, None

