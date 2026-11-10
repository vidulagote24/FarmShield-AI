"""Crop coefficient (Kc) determination and phenological stage interpolation.

Implements FAO-56 Table 12 crop coefficients and Table 22 allowable soil water
depletion fractions for standard agricultural crops.

Scientific Foundation & Baselines:
1. Standard Subhumid Reference Baseline:
   FAO-56 Table 12 crop coefficients represent standard subhumid reference conditions:
   - Minimum relative humidity (RHmin) ≈ 45%
   - Mean wind speed at 2 m height (u2) ≈ 2.0 m/s
   - Under well-watered, disease-free, high-yield agricultural management.

2. Climatic Adjustment for Mid-Season and Late-Season (FAO-56 Eqs. 62 & 65):
   In arid, hot, or windy climates (e.g. Maharashtra pre-monsoon dry season), Kc_mid
   and Kc_end increase due to increased canopy advective roughness.
   Adjustment formula:
       Kc_adj = Kc_tab + [0.04 * (u2 - 2.0) - 0.004 * (RHmin - 45.0)] * (h / 3.0)^0.3
   Where:
       u2: Mean daily wind speed at 2 m (m/s), applicable range 1.0 <= u2 <= 6.0 m/s
       RHmin: Mean daily minimum relative humidity (%), applicable range 20.0 <= RHmin <= 80.0%
       h: Mean plant height during the stage (m), applicable range 0.1 <= h <= 10.0 m
   - Mid-season adjustment applies representative mid-season inputs for Kc_mid >= 0.45.
   - Late-season adjustment applies representative late-season inputs for Kc_end > 0.45.
   - Calculated coefficients are NOT silently clipped to arbitrary [0.1, 2.0] bounds.
     If a calculated result falls outside [0.1, 2.0], the raw value is preserved and
     flagged for agronomist review.
   - If required climatic inputs are missing, coefficients explicitly remain unadjusted Table 12 baselines.

3. Initial Stage (Kc_ini) Wetting Frequency Dependence:
   FAO-56 Figures 29 and 30 emphasize that Kc_ini is primarily governed by topsoil
   wetting frequency (irrigation/rain recurrence interval) and evaporative demand (ET0).
   Table 12 values represent typical 3–7 day wetting frequencies on medium soils.

4. Allowable Depletion Fraction (p) Climatic Sensitivity (FAO-56 Table 22 Footnote):
   Table 22 values are tabulated for standard non-stressed ETc ≈ 5.0 mm/day.
   Climatic adjustment:
       p_adj = p_table + 0.04 * (5.0 - ETc)
   Constrained to the documented FAO range: 0.10 <= p_adj <= 0.80.
   Under high evaporative demand (ETc > 5 mm/day), crops experience water stress earlier
   (lower allowable depletion fraction).

Agronomic & Safety Rules:
1. No Silent Guessing: Unknown crop types are NEVER assigned assumed default values.
   Attempting to evaluate an unregistered crop without an explicit override raises ValueError.
2. Transparent Traceability: Every calculated Kc records its source reference,
   growth stage, baseline Kc, climate adjustment delta, and depletion fraction audit.
3. Calculated vs Measured: Disclaims that Kc is an empirical tabular/model parameter,
   NOT an in-situ physiological canopy measurement.
"""

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class CropAgronomicParameters(BaseModel):
    """Agronomic parameters for a specific crop species per FAO-56 Table 12 & Table 22."""

    crop_type: str = Field(..., description="Canonical lowercase crop identifier (e.g. 'wheat')")
    display_name: str = Field(..., description="Common readable name")
    scientific_name: Optional[str] = Field(default=None, description="Botanical binomial")
    kc_ini: float = Field(..., ge=0.1, le=1.5, description="Baseline Kc at initial stage (Table 12)")
    kc_mid: float = Field(..., ge=0.2, le=1.8, description="Baseline Kc at mid-season stage (Table 12)")
    kc_end: float = Field(..., ge=0.1, le=1.5, description="Baseline Kc at late season / harvest (Table 12)")
    stage_lengths_days: Dict[str, int] = Field(
        ...,
        description="Typical phenological stage durations in days (initial, development, mid_season, late_season)"
    )
    depletion_fraction_p: float = Field(
        ...,
        ge=0.1,
        le=0.8,
        description="Baseline soil water depletion fraction for no stress at ETc ~ 5 mm/day (Table 22)"
    )
    max_rooting_depth_m: float = Field(
        ...,
        ge=0.2,
        le=3.0,
        description="Standard maximum effective rooting depth Zr in meters"
    )
    plant_height_m: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Typical full canopy plant height h in meters (FAO-56 Table 12)"
    )
    reference: str = Field(default="FAO-56 Table 12 & Table 22", description="Agronomic literature reference")


class CropCoefficientResult(BaseModel):
    """Result of crop coefficient determination with stage context, climate adjustment, and assumptions."""

    crop_type: str = Field(..., description="Evaluated crop identifier")
    growth_stage: str = Field(..., description="Evaluated growth stage: initial, development, mid_season, late_season, harvest")
    kc: float = Field(..., ge=0.0, description="Evaluated crop coefficient Kc (adjusted or baseline, unclipped)")
    kc_table_baseline: float = Field(..., ge=0.0, description="Standard FAO-56 Table 12 unadjusted baseline Kc")
    is_climate_adjusted: bool = Field(default=False, description="Whether FAO-56 Eqs. 62/65 climatic adjustment was applied")
    climate_adjustment_delta: float = Field(default=0.0, description="Delta added to baseline Kc from climatic adjustment")
    plant_height_m: Optional[float] = Field(default=None, description="Plant height h used for climatic adjustment")

    is_out_of_validation_range: bool = Field(default=False, description="Whether adjusted Kc falls outside standard [0.1, 2.0] validation range")
    validation_warnings: List[str] = Field(default_factory=list, description="Validation warnings for out-of-range results")

    depletion_fraction_p: float = Field(..., ge=0.1, le=0.8, description="Allowable soil water depletion fraction p")
    depletion_fraction_p_table: float = Field(..., ge=0.1, le=0.8, description="Table 22 baseline depletion fraction (ETc ~ 5 mm/day)")
    is_p_adjusted: bool = Field(default=False, description="Whether Table 22 depletion fraction was adjusted for non-stressed ETc")
    etc_mm_day_for_p_adj: Optional[float] = Field(default=None, description="Non-stressed ETc rate used for adjusting p")

    effective_rooting_depth_m: float = Field(..., ge=0.1, le=3.0, description="Effective crop rooting depth Zr in meters")
    is_interpolated: bool = Field(..., description="Whether Kc was linearly interpolated across phenological stage days")
    source_reference: str = Field(..., description="Literature or configuration source of Kc")
    assumptions: List[str] = Field(default_factory=list, description="Agronomic assumptions applied")


# --- FAO-56 Table 12 & Table 22 Database for Representative Regional Crops ---

FAO56_CROP_DATABASE: Dict[str, CropAgronomicParameters] = {
    "wheat": CropAgronomicParameters(
        crop_type="wheat",
        display_name="Wheat (Spring / Winter)",
        scientific_name="Triticum aestivum",
        kc_ini=0.30,
        kc_mid=1.15,
        kc_end=0.25,
        stage_lengths_days={"initial": 20, "development": 30, "mid_season": 40, "late_season": 30},
        depletion_fraction_p=0.55,
        max_rooting_depth_m=1.2,
        plant_height_m=1.0,
        reference="FAO-56 Table 12 & Table 22",
    ),
    "cotton": CropAgronomicParameters(
        crop_type="cotton",
        display_name="Cotton",
        scientific_name="Gossypium hirsutum",
        kc_ini=0.35,
        kc_mid=1.20,
        kc_end=0.60,
        stage_lengths_days={"initial": 30, "development": 50, "mid_season": 55, "late_season": 45},
        depletion_fraction_p=0.65,
        max_rooting_depth_m=1.4,
        plant_height_m=1.2,
        reference="FAO-56 Table 12 & Table 22",
    ),
    "soybean": CropAgronomicParameters(
        crop_type="soybean",
        display_name="Soybean",
        scientific_name="Glycine max",
        kc_ini=0.40,
        kc_mid=1.15,
        kc_end=0.50,
        stage_lengths_days={"initial": 20, "development": 30, "mid_season": 50, "late_season": 25},
        depletion_fraction_p=0.50,
        max_rooting_depth_m=1.0,
        plant_height_m=0.6,
        reference="FAO-56 Table 12 & Table 22",
    ),
    "maize": CropAgronomicParameters(
        crop_type="maize",
        display_name="Maize / Corn",
        scientific_name="Zea mays",
        kc_ini=0.30,
        kc_mid=1.20,
        kc_end=0.35,
        stage_lengths_days={"initial": 25, "development": 40, "mid_season": 45, "late_season": 30},
        depletion_fraction_p=0.55,
        max_rooting_depth_m=1.2,
        plant_height_m=2.0,
        reference="FAO-56 Table 12 & Table 22",
    ),
    "sugarcane": CropAgronomicParameters(
        crop_type="sugarcane",
        display_name="Sugarcane",
        scientific_name="Saccharum officinarum",
        kc_ini=0.40,
        kc_mid=1.25,
        kc_end=0.75,
        stage_lengths_days={"initial": 35, "development": 60, "mid_season": 180, "late_season": 90},
        depletion_fraction_p=0.65,
        max_rooting_depth_m=1.5,
        plant_height_m=3.0,
        reference="FAO-56 Table 12 & Table 22",
    ),
    "tomato": CropAgronomicParameters(
        crop_type="tomato",
        display_name="Tomato",
        scientific_name="Solanum lycopersicum",
        kc_ini=0.60,
        kc_mid=1.15,
        kc_end=0.80,
        stage_lengths_days={"initial": 30, "development": 40, "mid_season": 45, "late_season": 30},
        depletion_fraction_p=0.40,
        max_rooting_depth_m=1.0,
        plant_height_m=0.6,
        reference="FAO-56 Table 12 & Table 22",
    ),
    "onion": CropAgronomicParameters(
        crop_type="onion",
        display_name="Onion (Dry)",
        scientific_name="Allium cepa",
        kc_ini=0.70,
        kc_mid=1.05,
        kc_end=0.75,
        stage_lengths_days={"initial": 20, "development": 35, "mid_season": 70, "late_season": 25},
        depletion_fraction_p=0.30,
        max_rooting_depth_m=0.6,
        plant_height_m=0.4,
        reference="FAO-56 Table 12 & Table 22",
    ),
    "groundnut": CropAgronomicParameters(
        crop_type="groundnut",
        display_name="Groundnut / Peanut",
        scientific_name="Arachis hypogaea",
        kc_ini=0.40,
        kc_mid=1.15,
        kc_end=0.60,
        stage_lengths_days={"initial": 25, "development": 35, "mid_season": 45, "late_season": 25},
        depletion_fraction_p=0.50,
        max_rooting_depth_m=0.8,
        plant_height_m=0.4,
        reference="FAO-56 Table 12 & Table 22",
    ),
    "chickpea": CropAgronomicParameters(
        crop_type="chickpea",
        display_name="Chickpea / Gram",
        scientific_name="Cicer arietinum",
        kc_ini=0.40,
        kc_mid=1.00,
        kc_end=0.35,
        stage_lengths_days={"initial": 20, "development": 30, "mid_season": 40, "late_season": 25},
        depletion_fraction_p=0.50,
        max_rooting_depth_m=0.9,
        plant_height_m=0.4,
        reference="FAO-56 Table 12 & Table 22",
    ),
    "sorghum": CropAgronomicParameters(
        crop_type="sorghum",
        display_name="Sorghum / Jowar",
        scientific_name="Sorghum bicolor",
        kc_ini=0.30,
        kc_mid=1.05,
        kc_end=0.55,
        stage_lengths_days={"initial": 20, "development": 35, "mid_season": 45, "late_season": 30},
        depletion_fraction_p=0.55,
        max_rooting_depth_m=1.2,
        plant_height_m=1.5,
        reference="FAO-56 Table 12 & Table 22",
    ),
}


def adjust_depletion_fraction_p(
    p_table: float,
    etc_mm_day: float,
    clip_min: float = 0.10,
    clip_max: float = 0.80,
) -> float:
    """Adjust FAO-56 Table 22 depletion fraction p for daily evaporative demand ETc.

    Formula (FAO-56 Table 22 footnote, p. 162):
        p_adj = p_table + 0.04 * (5.0 - ETc)
    Constrained to [0.10, 0.80].

    Note:
        ETc must be the standard non-stressed crop evapotranspiration, NOT the
        stress-adjusted ETc,adj, because p defines the threshold where water stress
        begins under standard evaporative demand.

    Args:
        p_table: Table 22 baseline depletion fraction for ETc ~ 5 mm/day.
        etc_mm_day: Non-stressed crop evapotranspiration in mm/day.
        clip_min: Minimum allowable fraction (default 0.10).
        clip_max: Maximum allowable fraction (default 0.80).

    Returns:
        Climatically adjusted depletion fraction p.

    Raises:
        ValueError: If etc_mm_day is negative or p_table is invalid.
    """
    if etc_mm_day < 0.0:
        raise ValueError(f"ETc cannot be negative: {etc_mm_day} mm/day.")
    if p_table < 0.05 or p_table > 0.95:
        raise ValueError(f"p_table out of physical bounds: {p_table}.")

    p_raw = p_table + 0.04 * (5.0 - float(etc_mm_day))
    return max(clip_min, min(clip_max, round(p_raw, 4)))


def calculate_climatic_kc_adjustment(
    kc_baseline: float,
    wind_speed_2m_ms: float,
    rh_min_pct: float,
    plant_height_m: float,
) -> Tuple[float, float, bool, List[str]]:
    """Calculate FAO-56 Eqs. 62 & 65 climatic adjustment for Kc_mid or Kc_end.

    Formula:
        delta = [0.04 * (u2 - 2.0) - 0.004 * (RHmin - 45.0)] * (h / 3.0)^0.3
        kc_adj = kc_baseline + delta

    Validation Ranges (FAO-56 pp. 122, 128):
        - u2: 1.0 to 6.0 m/s
        - RHmin: 20.0 to 80.0%
        - h: 0.1 to 10.0 m

    No Silent Clipping:
        If kc_adj falls outside [0.1, 2.0], the raw value is preserved and
        is_out_of_range is set to True with explanatory warning messages.

    Args:
        kc_baseline: FAO-56 Table 12 baseline Kc.
        wind_speed_2m_ms: Mean daily wind speed at 2 m (m/s).
        rh_min_pct: Mean daily minimum relative humidity (%).
        plant_height_m: Crop height h in meters.

    Returns:
        Tuple of (kc_adj, delta, is_out_of_range, validation_warnings).

    Raises:
        ValueError: If inputs fall outside applicable FAO-56 ranges.
    """
    u2 = float(wind_speed_2m_ms)
    rh_min = float(rh_min_pct)
    h = float(plant_height_m)

    if u2 < 1.0 or u2 > 6.0:
        raise ValueError(
            f"Wind speed u2 ({u2:.2f} m/s) is outside applicable FAO-56 adjustment range [1.0, 6.0] m/s."
        )
    if rh_min < 20.0 or rh_min > 80.0:
        raise ValueError(
            f"Minimum relative humidity RHmin ({rh_min:.1f}%) is outside applicable FAO-56 adjustment range [20.0, 80.0]%."
        )
    if h < 0.1 or h > 10.0:
        raise ValueError(
            f"Plant height h ({h:.2f} m) is outside applicable FAO-56 range [0.1, 10.0] m."
        )

    delta = (0.04 * (u2 - 2.0) - 0.004 * (rh_min - 45.0)) * ((h / 3.0) ** 0.3)
    kc_adj = kc_baseline + delta

    warnings: List[str] = []
    is_out = False
    if kc_adj < 0.1 or kc_adj > 2.0:
        is_out = True
        warnings.append(
            f"Climatically adjusted Kc ({kc_adj:.3f}) falls outside standard FAO validation range [0.1, 2.0]. "
            "Raw unclipped value preserved for agronomist review."
        )

    return round(kc_adj, 4), round(delta, 4), is_out, warnings


def get_crop_coefficient(
    crop_type: str,
    growth_stage: Optional[str] = None,
    days_after_sowing: Optional[int] = None,
    days_in_stage: Optional[int] = None,
    custom_kc: Optional[float] = None,
    custom_rooting_depth_m: Optional[float] = None,
    custom_depletion_fraction_p: Optional[float] = None,
    # General / fallback climatic inputs:
    wind_speed_2m_ms: Optional[float] = None,
    rh_min_pct: Optional[float] = None,
    plant_height_m: Optional[float] = None,
    # Stage-specific representative climatic inputs:
    wind_speed_2m_mid_ms: Optional[float] = None,
    rh_min_mid_pct: Optional[float] = None,
    plant_height_mid_m: Optional[float] = None,
    wind_speed_2m_end_ms: Optional[float] = None,
    rh_min_end_pct: Optional[float] = None,
    plant_height_end_m: Optional[float] = None,
    # Depletion fraction input:
    etc_mm_day: Optional[float] = None,
    adjust_p_for_etc: bool = True,
    apply_climate_adjustment: bool = True,
) -> CropCoefficientResult:
    """Determine crop coefficient Kc, depletion fraction p, and rooting depth Zr.

    Supports:
    1. Explicit custom Kc overrides (e.g. from agronomist inspection).
    2. Phenological stage lookups ('initial', 'development', 'mid_season', 'late_season', 'harvest').
    3. Calendar day interpolation across growth stages when sowing date is known.
    4. FAO-56 Eqs. 62 & 65 climatic adjustments with stage-specific representative inputs.
    5. FAO-56 Table 22 climatic adjustment for depletion fraction p using non-stressed ETc.

    Args:
        crop_type: Canonical crop identifier.
        growth_stage: Optional phenological stage name.
        days_after_sowing: Optional elapsed days from planting.
        days_in_stage: Optional days elapsed within current stage.
        custom_kc: Optional user-supplied Kc override.
        custom_rooting_depth_m: Optional user-supplied rooting depth override in meters.
        custom_depletion_fraction_p: Optional user-supplied depletion fraction p.
        wind_speed_2m_ms: Optional general mean daily wind speed at 2 m in m/s.
        rh_min_pct: Optional general mean daily minimum RH in %.
        plant_height_m: Optional crop height override in meters.
        wind_speed_2m_mid_ms: Representative mid-season wind speed at 2 m in m/s.
        rh_min_mid_pct: Representative mid-season minimum RH in %.
        plant_height_mid_m: Representative mid-season plant height in meters.
        wind_speed_2m_end_ms: Representative late-season wind speed at 2 m in m/s.
        rh_min_end_pct: Representative late-season minimum RH in %.
        plant_height_end_m: Representative late-season plant height in meters.
        etc_mm_day: Optional non-stressed ETc rate in mm/day for adjusting depletion fraction p.
        adjust_p_for_etc: Whether to apply FAO-56 Table 22 climatic adjustment to p (default True).
        apply_climate_adjustment: Whether to apply FAO-56 Eqs. 62/65 climatic adjustment to Kc (default True).

    Returns:
        CropCoefficientResult with verified parameters, adjustments, and audit trail.

    Raises:
        ValueError: If crop is unknown and no custom Kc is provided, or parameters are invalid.
    """
    canonical_type = crop_type.strip().lower()

    # 1. Custom override path
    if custom_kc is not None:
        if custom_kc < 0.1 or custom_kc > 2.0:
            raise ValueError(f"Custom Kc out of physical agronomic bounds [0.1, 2.0]: {custom_kc}")
        p_val = custom_depletion_fraction_p or 0.50
        zr_val = custom_rooting_depth_m or 1.0
        return CropCoefficientResult(
            crop_type=canonical_type,
            growth_stage=growth_stage or "user_specified",
            kc=round(custom_kc, 3),
            kc_table_baseline=round(custom_kc, 3),
            is_climate_adjusted=False,
            climate_adjustment_delta=0.0,
            plant_height_m=plant_height_m,
            is_out_of_validation_range=False,
            validation_warnings=[],
            depletion_fraction_p=round(p_val, 2),
            depletion_fraction_p_table=round(p_val, 2),
            is_p_adjusted=False,
            etc_mm_day_for_p_adj=None,
            effective_rooting_depth_m=round(zr_val, 2),
            is_interpolated=False,
            source_reference="User / Agronomist Custom Override",
            assumptions=["Kc explicitly configured by user/agronomist without FAO-56 tabular lookup."],
        )

    # 2. Tabular lookup
    if canonical_type not in FAO56_CROP_DATABASE:
        available = ", ".join(sorted(FAO56_CROP_DATABASE.keys()))
        raise ValueError(
            f"Unknown crop type '{crop_type}'. FAO-56 crop coefficient cannot be inferred. "
            f"Supported crops: [{available}]. Provide an explicit custom_kc or register crop parameters."
        )

    crop_params = FAO56_CROP_DATABASE[canonical_type]
    stage_lengths = crop_params.stage_lengths_days

    # Determine stage from days_after_sowing if growth_stage is unspecified
    active_stage = (growth_stage or "").strip().lower()

    if not active_stage and days_after_sowing is not None:
        l_ini = stage_lengths["initial"]
        l_dev = stage_lengths["development"]
        l_mid = stage_lengths["mid_season"]
        l_late = stage_lengths["late_season"]

        if days_after_sowing <= l_ini:
            active_stage = "initial"
            days_in_stage = days_after_sowing
        elif days_after_sowing <= l_ini + l_dev:
            active_stage = "development"
            days_in_stage = days_after_sowing - l_ini
        elif days_after_sowing <= l_ini + l_dev + l_mid:
            active_stage = "mid_season"
            days_in_stage = days_after_sowing - (l_ini + l_dev)
        else:
            active_stage = "late_season"
            days_in_stage = days_after_sowing - (l_ini + l_dev + l_mid)

    if not active_stage:
        active_stage = "mid_season"  # Documented fallback assumption
        stage_assumed = True
    else:
        stage_assumed = False

    # 3. Compute baseline stage Kc and stage interpolation
    assumptions: List[str] = [
        "FAO-56 Table 12 standard subhumid reference conditions (u2=2 m/s, RHmin=45%)."
    ]
    if stage_assumed:
        assumptions.append("Growth stage unspecified: assumed mid-season stage with peak Kc.")

    is_interpolated = False
    if active_stage in {"initial", "ini"}:
        kc_base = crop_params.kc_ini
        zr_val = 0.3 * crop_params.max_rooting_depth_m
        assumptions.append(
            "Initial stage Kc_ini reflects standard 3-7 day wetting frequency on medium soil (FAO-56 Fig. 29/30)."
        )

    elif active_stage in {"development", "dev"}:
        total_dev_days = stage_lengths.get("development", 30)
        if days_in_stage is not None and total_dev_days > 0:
            frac = max(0.0, min(1.0, days_in_stage / total_dev_days))
            kc_base = crop_params.kc_ini + frac * (crop_params.kc_mid - crop_params.kc_ini)
            zr_val = (0.3 + 0.7 * frac) * crop_params.max_rooting_depth_m
            is_interpolated = True
            assumptions.append(f"Linearly interpolated development Kc ({frac * 100:.0f}% stage completion).")
        else:
            kc_base = (crop_params.kc_ini + crop_params.kc_mid) / 2.0
            zr_val = 0.65 * crop_params.max_rooting_depth_m
            assumptions.append("Development stage duration elapsed unknown: applied arithmetic mean of Kc_ini and Kc_mid.")

    elif active_stage in {"mid_season", "mid"}:
        kc_base = crop_params.kc_mid
        zr_val = crop_params.max_rooting_depth_m

    elif active_stage in {"late_season", "late"}:
        total_late_days = stage_lengths.get("late_season", 30)
        if days_in_stage is not None and total_late_days > 0:
            frac = max(0.0, min(1.0, days_in_stage / total_late_days))
            kc_base = crop_params.kc_mid - frac * (crop_params.kc_mid - crop_params.kc_end)
            zr_val = crop_params.max_rooting_depth_m
            is_interpolated = True
            assumptions.append(f"Linearly interpolated late-season Kc ({frac * 100:.0f}% stage completion).")
        else:
            kc_base = (crop_params.kc_mid + crop_params.kc_end) / 2.0
            zr_val = crop_params.max_rooting_depth_m
            assumptions.append("Late-season stage duration elapsed unknown: applied arithmetic mean of Kc_mid and Kc_end.")

    elif active_stage in {"harvest", "end"}:
        kc_base = crop_params.kc_end
        zr_val = crop_params.max_rooting_depth_m

    else:
        raise ValueError(
            f"Unrecognized growth stage '{growth_stage}'. "
            f"Must be one of: ['initial', 'development', 'mid_season', 'late_season', 'harvest']."
        )

    # 4. Climatic Adjustment (FAO-56 Eqs. 62 & 65) with representative stage inputs
    is_climate_adj = False
    delta_kc = 0.0
    final_kc = kc_base
    is_out_of_range = False
    validation_warnings: List[str] = []
    h_plant = plant_height_m if plant_height_m is not None else crop_params.plant_height_m

    if apply_climate_adjustment and active_stage in {"mid_season", "mid", "late_season", "late", "harvest", "end"}:
        can_adjust = False
        stage_u2: Optional[float] = None
        stage_rh: Optional[float] = None
        stage_h: float = h_plant

        if active_stage in {"mid_season", "mid"}:
            if kc_base >= 0.45:
                can_adjust = True
                stage_u2 = wind_speed_2m_mid_ms if wind_speed_2m_mid_ms is not None else wind_speed_2m_ms
                stage_rh = rh_min_mid_pct if rh_min_mid_pct is not None else rh_min_pct
                stage_h = plant_height_mid_m if plant_height_mid_m is not None else h_plant

        elif active_stage in {"late_season", "late", "harvest", "end"}:
            if kc_base > 0.45:
                can_adjust = True
                stage_u2 = wind_speed_2m_end_ms if wind_speed_2m_end_ms is not None else wind_speed_2m_ms
                stage_rh = rh_min_end_pct if rh_min_end_pct is not None else rh_min_pct
                stage_h = plant_height_end_m if plant_height_end_m is not None else h_plant

        if can_adjust:
            if stage_u2 is not None and stage_rh is not None:
                final_kc, delta_kc, is_out_of_range, validation_warnings = calculate_climatic_kc_adjustment(
                    kc_baseline=kc_base,
                    wind_speed_2m_ms=stage_u2,
                    rh_min_pct=stage_rh,
                    plant_height_m=stage_h,
                )
                is_climate_adj = abs(delta_kc) > 1e-4
                if is_climate_adj:
                    assumptions.append(
                        f"Climatically adjusted Kc (delta={delta_kc:+.3f}) using FAO-56 Eq. 62/65 "
                        f"(u2={stage_u2:.1f} m/s, RHmin={stage_rh:.1f}%, h={stage_h:.1f} m)."
                    )
                else:
                    assumptions.append(
                        "Climatic inputs match subhumid reference baseline (u2=2.0 m/s, RHmin=45%): Kc delta is 0.00."
                    )
            else:
                assumptions.append(
                    "Climatic adjustment inputs (u2, RHmin) not provided: Kc remains standard unadjusted Table 12 baseline."
                )

    # 5. Depletion Fraction Adjustment (FAO-56 Table 22) using non-stressed ETc
    p_table_base = crop_params.depletion_fraction_p
    p_final = custom_depletion_fraction_p if custom_depletion_fraction_p is not None else p_table_base
    is_p_adj = False

    if custom_depletion_fraction_p is None and etc_mm_day is not None and adjust_p_for_etc:
        p_final = adjust_depletion_fraction_p(p_table=p_table_base, etc_mm_day=etc_mm_day)
        is_p_adj = True
        assumptions.append(
            f"Adjusted depletion fraction p from Table 22 baseline ({p_table_base:.2f}) to {p_final:.2f} "
            f"for non-stressed ETc = {etc_mm_day:.2f} mm/day (FAO-56 Table 22 footnote)."
        )
    elif custom_depletion_fraction_p is None:
        assumptions.append(
            f"Depletion fraction p ({p_table_base:.2f}) remains unadjusted Table 22 baseline for ETc ~ 5 mm/day."
        )

    # Overrides for depth if supplied
    final_zr = custom_rooting_depth_m if custom_rooting_depth_m is not None else zr_val

    return CropCoefficientResult(
        crop_type=canonical_type,
        growth_stage=active_stage,
        kc=round(final_kc, 3),
        kc_table_baseline=round(kc_base, 3),
        is_climate_adjusted=is_climate_adj,
        climate_adjustment_delta=round(delta_kc, 3),
        plant_height_m=round(h_plant, 2),
        is_out_of_validation_range=is_out_of_range,
        validation_warnings=validation_warnings,
        depletion_fraction_p=round(p_final, 3),
        depletion_fraction_p_table=round(p_table_base, 3),
        is_p_adjusted=is_p_adj,
        etc_mm_day_for_p_adj=round(etc_mm_day, 2) if etc_mm_day is not None else None,
        effective_rooting_depth_m=round(max(0.1, final_zr), 2),
        is_interpolated=is_interpolated,
        source_reference=crop_params.reference,
        assumptions=assumptions,
    )
