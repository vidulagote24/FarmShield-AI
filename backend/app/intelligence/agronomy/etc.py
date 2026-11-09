"""Crop Evapotranspiration (ETc) Calculation Module.

Calculates standard crop evapotranspiration under non-stress conditions
per FAO-56 Chapter 6:
    ETc = Kc * ET0

And adjusted crop evapotranspiration under soil water stress per FAO-56 Chapter 8:
    ETc,adj = Ks * ETc = Ks * Kc * ET0

Where:
    ETc: Standard crop evapotranspiration under disease-free, well-watered conditions (mm/day)
    ETc,adj: Actual / adjusted crop evapotranspiration under soil water stress (mm/day)
    Kc: Crop coefficient (dimensionless)
    ET0: Reference evapotranspiration (mm/day)
    Ks: Water-stress reduction coefficient (0.0 <= Ks <= 1.0)

Agronomic & Safety Rules:
1. Purely Deterministic: Multiplies verified Kc by verified ET0.
2. Scientific Disclaimer: Clearly disclaims that ETc is a calculated crop water requirement,
   NOT an in-field lysimeter or eddy covariance flux observation.
3. Separation of Potential vs Actual: Retains standard non-stressed ETc as a distinct
   baseline alongside adjusted ETc,adj.
4. Single vs Dual Crop Coefficient Limitations:
   The single crop coefficient method combines soil evaporation (Ke) and plant transpiration
   (Kcb) into a single coefficient Kc. It does not account for rapid day-to-day evaporation
   swings from wet topsoil independently of root-zone transpiration.
"""

from typing import Any, List, Optional, Union
from pydantic import BaseModel, Field

from backend.app.intelligence.agronomy.crop_coefficient import CropCoefficientResult
from backend.app.intelligence.agronomy.et0 import ET0CalculationResult
from backend.app.intelligence.types import DataQualityStatus


class CropETResult(BaseModel):
    """Structured result of crop evapotranspiration calculation."""

    etc_mm_day: float = Field(..., ge=0.0, description="Standard non-stressed crop evapotranspiration in mm/day")
    etc_adj_mm_day: Optional[float] = Field(default=None, ge=0.0, description="Adjusted crop evapotranspiration under stress ETc,adj in mm/day")
    water_stress_coefficient_ks: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Water stress coefficient Ks applied")
    et0_mm_day: float = Field(..., ge=0.0, description="Reference evapotranspiration in mm/day")
    kc: float = Field(..., ge=0.0, description="Crop coefficient Kc applied")
    crop_type: Optional[str] = Field(default=None, description="Crop species evaluated")
    growth_stage: Optional[str] = Field(default=None, description="Crop growth stage")
    depletion_fraction_p: Optional[float] = Field(default=None, description="Allowable depletion fraction p")
    effective_rooting_depth_m: Optional[float] = Field(default=None, description="Effective rooting depth Zr in meters")
    calculation_formula: str = Field(default="ETc = Kc * ET0", description="Applied calculation equation")
    scientific_disclaimer: str = Field(
        default=(
            "Calculated potential crop evapotranspiration under standard conditions "
            "per FAO-56 methodology. This is an agronomic water requirement estimate, NOT a direct "
            "in-situ physical measurement."
        ),
        description="Mandatory scientific disclaimer"
    )
    quality_status: DataQualityStatus = Field(default=DataQualityStatus.GOOD, description="Synthesized calculation quality")
    quality_notes: List[str] = Field(default_factory=list, description="Quality caveats or input provenance notes")


def calculate_adjusted_crop_evapotranspiration(
    etc_mm_day: float,
    ks: float,
) -> float:
    """Calculate adjusted crop evapotranspiration under soil water stress (FAO-56 Eq. 80).

    ETc,adj = Ks * ETc

    Args:
        etc_mm_day: Standard non-stressed crop evapotranspiration (mm/day).
        ks: FAO-56 water stress coefficient (0.0 <= Ks <= 1.0).

    Returns:
        Adjusted crop evapotranspiration in mm/day.

    Raises:
        ValueError: If etc_mm_day is negative or ks is out of bounds.
    """
    if etc_mm_day < 0.0:
        raise ValueError(f"ETc cannot be negative: {etc_mm_day} mm/day.")
    if ks < 0.0 or ks > 1.0:
        raise ValueError(f"Water stress coefficient Ks must be in [0.0, 1.0], got {ks}.")

    return round(float(ks) * float(etc_mm_day), 3)


def calculate_crop_evapotranspiration(
    et0: Union[float, ET0CalculationResult],
    crop_coefficient: Union[float, CropCoefficientResult],
    ks: Optional[float] = None,
) -> CropETResult:
    """Calculate standard crop evapotranspiration ETc = Kc * ET0 and optional adjusted ETc,adj = Ks * ETc.

    Args:
        et0: Reference evapotranspiration in mm/day, either as float or ET0CalculationResult.
        crop_coefficient: Crop coefficient Kc, either as float or CropCoefficientResult.
        ks: Optional water-stress coefficient Ks in [0.0, 1.0]. If provided, calculates ETc,adj.

    Returns:
        CropETResult containing ETc, optional ETc,adj, input parameters, and scientific disclaimers.

    Raises:
        ValueError: If ET0 < 0 or Kc < 0.1 or inputs are invalid.
    """
    quality_notes: List[str] = []
    q_status = DataQualityStatus.GOOD

    # 1. Unpack ET0
    if isinstance(et0, ET0CalculationResult):
        et0_val = et0.et0_mm_day
        if et0.quality_status != DataQualityStatus.GOOD:
            q_status = et0.quality_status
            quality_notes.extend(et0.quality_notes)
    elif isinstance(et0, (int, float)):
        et0_val = float(et0)
    else:
        raise ValueError(f"Invalid type for et0: {type(et0)}. Must be float or ET0CalculationResult.")

    if et0_val < 0.0:
        raise ValueError(f"Reference evapotranspiration ET0 cannot be negative: {et0_val} mm/day.")

    # 2. Unpack Crop Coefficient
    crop_name = None
    stage = None
    p_val = None
    zr_val = None

    if isinstance(crop_coefficient, CropCoefficientResult):
        kc_val = crop_coefficient.kc
        crop_name = crop_coefficient.crop_type
        stage = crop_coefficient.growth_stage
        p_val = crop_coefficient.depletion_fraction_p
        zr_val = crop_coefficient.effective_rooting_depth_m
        quality_notes.extend(crop_coefficient.assumptions)
        quality_notes.extend(crop_coefficient.validation_warnings)
        if kc_val < 0.0:
            raise ValueError(f"Crop coefficient Kc cannot be negative: {kc_val}")
        if kc_val < 0.1 or kc_val > 2.0:
            quality_notes.append(
                f"Warning: Applied Kc ({kc_val:.3f}) falls outside standard [0.1, 2.0] validation range."
            )
    elif isinstance(crop_coefficient, (int, float)):
        kc_val = float(crop_coefficient)
        if kc_val < 0.1 or kc_val > 2.0:
            raise ValueError(f"Crop coefficient Kc out of agronomic bounds [0.1, 2.0]: {kc_val}")
    else:
        raise ValueError(
            f"Invalid type for crop_coefficient: {type(crop_coefficient)}. "
            f"Must be float or CropCoefficientResult."
        )

    # 3. Deterministic calculation: ETc = Kc * ET0
    etc_val = kc_val * et0_val
    formula = "ETc = Kc * ET0"

    # 4. Optional Water Stress Adjustment
    etc_adj = None
    if ks is not None:
        if ks < 0.0 or ks > 1.0:
            raise ValueError(f"Water stress coefficient Ks must be in [0.0, 1.0], got {ks}.")
        etc_adj = calculate_adjusted_crop_evapotranspiration(etc_val, ks)
        formula = "ETc = Kc * ET0; ETc,adj = Ks * ETc"
        quality_notes.append(
            f"Applied water stress coefficient Ks = {ks:.3f}; adjusted ETc,adj = {etc_adj:.3f} mm/day."
        )

    return CropETResult(
        etc_mm_day=round(etc_val, 3),
        etc_adj_mm_day=etc_adj,
        water_stress_coefficient_ks=round(ks, 4) if ks is not None else None,
        et0_mm_day=round(et0_val, 3),
        kc=round(kc_val, 3),
        crop_type=crop_name,
        growth_stage=stage,
        depletion_fraction_p=p_val,
        effective_rooting_depth_m=zr_val,
        calculation_formula=formula,
        quality_status=q_status,
        quality_notes=quality_notes,
    )
