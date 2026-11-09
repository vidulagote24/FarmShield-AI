"""Crop context feature extraction and metadata validation.

Encapsulates crop species, variety, phenological growth stage, planting date,
and rooting depth metadata provided by farmer records or agronomist inspections.

Scientific and Agronomic Restrictions (per AGENTS.md, AI_SPEC.md, DATA_SOURCES.md):
1. Crop identity MUST NOT be inferred from satellite vegetation classification alone.
   Optical satellite reflectance cannot reliably distinguish crop species from weeds or natural flora.
2. Crop coefficients (Kc), evapotranspiration (ETc), and irrigation volume requirements
   belong to Phase 3 and MUST NOT be implemented in this feature module.
3. Missing crop variety or rooting depth metadata MUST remain None and must not be fabricated.
"""

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator

from backend.app.intelligence.config import default_freshness_config
from backend.app.intelligence.types import DataQualityStatus, ProvenanceType

STANDARD_CROP_CAVEATS: List[str] = [
    "Crop identity MUST be supplied by farmer records, farm registration, or agronomist inspection; it cannot be inferred from satellite imagery.",
    "Crop coefficients (Kc) and irrigation requirements are calculated in downstream agronomic water-balance models (Phase 3).",
    "Growth stage estimations based strictly on calendar days require in-field validation for accurate scheduling.",
]


class CropFeatures(BaseModel):
    """Structured crop context features for a management zone or farm."""

    crop_type: str = Field(
        ...,
        description="Canonical crop name or identifier (e.g. 'wheat', 'cotton', 'soybean', 'sugarcane')"
    )
    variety: Optional[str] = Field(
        default=None,
        description="Cultivar or variety name if known (e.g. 'HD-2967', 'BT-Cotton')"
    )
    planting_date: Optional[date] = Field(
        default=None,
        description="Date of sowing or crop emergence"
    )
    days_after_sowing: Optional[int] = Field(
        default=None,
        ge=0,
        description="Elapsed calendar days from planting date to observation date"
    )
    growth_stage: Optional[str] = Field(
        default=None,
        description="Phenological stage (e.g., 'initial', 'development', 'mid_season', 'late_season', 'harvest')"
    )
    growth_stage_source: Optional[str] = Field(
        default=None,
        description="Source of growth stage: 'farmer_reported', 'agronomist_inspected', 'calendar_estimated', or 'unknown'"
    )
    rooting_depth_m: Optional[float] = Field(
        default=None,
        ge=0.05,
        le=5.0,
        description="Effective crop rooting depth in meters (only if supplied by agronomic measurement or farm record)"
    )

    observed_at: datetime = Field(
        ...,
        description="UTC timestamp of the crop record or field inspection"
    )
    source_provider: str = Field(
        default="Farmer Record",
        description="Entity or mechanism providing the crop information"
    )
    provenance_type: ProvenanceType = Field(
        default=ProvenanceType.FARMER_ENTERED,
        description="Provenance classification: farmer_entered, sensor_measured, or provider_modelled"
    )
    quality_status: DataQualityStatus = Field(
        ...,
        description="Quality and completeness rating of crop metadata"
    )
    quality_note: Optional[str] = Field(
        default=None,
        description="Quality audit rationale or caveats"
    )
    is_stale: bool = Field(
        default=False,
        description="Whether crop inspection date exceeds freshness threshold"
    )
    scientific_caveats: List[str] = Field(
        default_factory=lambda: STANDARD_CROP_CAVEATS.copy(),
        description="Mandatory scientific restrictions and caveats"
    )

    @model_validator(mode="after")
    def validate_crop_dates(self) -> "CropFeatures":
        """Validate that planting date does not fall after the observation timestamp."""
        if self.planting_date is not None:
            obs_date = self.observed_at.date()
            if self.planting_date > obs_date:
                raise ValueError(
                    f"Physically impossible crop dates: planting_date ({self.planting_date}) "
                    f"is after observed_at date ({obs_date})"
                )
        return self


def create_crop_features(
    crop_type: str,
    observed_at: datetime,
    variety: Optional[str] = None,
    planting_date: Optional[date] = None,
    growth_stage: Optional[str] = None,
    growth_stage_source: Optional[str] = None,
    rooting_depth_m: Optional[float] = None,
    source_provider: str = "Farmer Record",
    provenance_type: ProvenanceType = ProvenanceType.FARMER_ENTERED,
    as_of_time: Optional[datetime] = None,
    stale_days: Optional[float] = None,
) -> CropFeatures:
    """Construct and validate a structured CropFeatures instance.

    Computes days_after_sowing deterministically if planting_date is available.

    Args:
        crop_type: Canonical crop species name.
        observed_at: Date and time of crop context inspection or report.
        variety: Optional crop variety name.
        planting_date: Sowing/emergence date.
        growth_stage: Phenological stage label.
        growth_stage_source: Origin of growth stage determination.
        rooting_depth_m: Optional rooting depth in meters.
        source_provider: Provider name.
        provenance_type: Provenance classification.
        as_of_time: Evaluation reference timestamp for staleness checking.
        stale_days: Freshness threshold in days.

    Returns:
        Validated CropFeatures object.
    """
    if not crop_type or not crop_type.strip():
        raise ValueError("crop_type cannot be empty or blank.")

    canonical_crop = crop_type.strip().lower()

    # Calculate days after sowing
    das: Optional[int] = None
    if planting_date is not None:
        obs_date = observed_at.date()
        delta = (obs_date - planting_date).days
        if delta < 0:
            raise ValueError(
                f"Planting date {planting_date} cannot be in the future relative to observation date {obs_date}."
            )
        das = int(delta)

    # Freshness evaluation
    max_stale_days = (
        stale_days if stale_days is not None
        else default_freshness_config.crop_growth_stage_stale_days
    )
    is_stale = False
    age_days = 0.0
    if as_of_time is not None:
        age_days = (as_of_time - observed_at).total_seconds() / 86400.0
        if age_days > max_stale_days:
            is_stale = True

    # Quality status
    if is_stale:
        q_status = DataQualityStatus.STALE
        q_note = f"Crop record age ({age_days:.1f}d) exceeds freshness threshold ({max_stale_days}d)."
    elif growth_stage is not None and planting_date is not None:
        q_status = DataQualityStatus.GOOD
        q_note = "Complete crop context with verified planting date and growth stage."
    elif growth_stage is not None or planting_date is not None:
        q_status = DataQualityStatus.PARTIAL
        q_note = "Partial crop context; either planting date or growth stage is missing."
    else:
        q_status = DataQualityStatus.PARTIAL
        q_note = "Crop type is known, but phenological stage and sowing date are unrecorded."

    return CropFeatures(
        crop_type=canonical_crop,
        variety=variety,
        planting_date=planting_date,
        days_after_sowing=das,
        growth_stage=growth_stage,
        growth_stage_source=growth_stage_source,
        rooting_depth_m=rooting_depth_m,
        observed_at=observed_at,
        source_provider=source_provider,
        provenance_type=provenance_type,
        quality_status=q_status,
        quality_note=q_note,
        is_stale=is_stale,
    )

