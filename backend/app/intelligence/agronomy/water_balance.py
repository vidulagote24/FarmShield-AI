"""Root-Zone Soil-Water Balance Module.

Implements FAO-56 Chapter 8 transparent daily soil-water accounting in the crop root zone:
    TAW = 1000 * (theta_FC - theta_WP) * Zr
    RAW = p * TAW
    Ks = 1.0 when Dr <= RAW; Ks = (TAW - Dr) / (TAW - RAW) when Dr > RAW
    ETc,adj = Ks * ETc
    Dr,t = Dr,t-1 - P_inf - It + ETc,adj,t + DPt

Where:
    TAW: Total available water in the crop root zone (mm)
    RAW: Readily available water without water stress (mm)
    theta_FC: Volumetric moisture content at field capacity (-33 kPa) (m³/m³)
    theta_WP: Volumetric moisture content at permanent wilting point (-1500 kPa) (m³/m³)
    Zr: Effective crop rooting depth (m)
    p: Soil water depletion fraction for no stress (dimensionless, 0.1 - 0.8)
    Ks: FAO-56 water-stress coefficient (dimensionless, 0.0 <= Ks <= 1.0)
    ETc: Standard potential crop evapotranspiration under non-stressed conditions (mm)
    ETc,adj: Actual / adjusted crop evapotranspiration under soil water deficit (mm)
    Dr: Root-zone soil water depletion (mm, 0 <= Dr <= TAW)
    P_inf: Infiltrated precipitation entering root zone (mm)
    I: Net irrigation applied (mm)
    DP: Deep percolation loss beyond the root zone (mm)

Mutually Exclusive Rainfall Accounting Modes:
1. Physical Mass-Balance Mode:
   - Inputs: gross_precipitation_mm, surface_runoff_mm (validated 0 <= RO <= P_gross), applied_irrigation_mm, ETc.
   - Infiltrated rainfall: P_inf = gross_precipitation_mm - surface_runoff_mm.
   - Deep percolation is dynamically computed strictly from root-zone storage overflow beyond field capacity (Dr < 0).
   - Empirical effective-rainfall losses are NOT deducted again (prevents double-counting).
   - Missing surface runoff is strictly rejected (never silently assumed to be zero).

2. Empirical Rainfall Mode:
   - Inputs: effective_rainfall_mm (or daily empirical EffectiveRainfallResult), applied_irrigation_mm, ETc.
   - Surface runoff is NOT deducted again because empirical formulas (e.g. FAO dependable daily)
     already account for surface runoff and initial abstractions.
   - Monthly USDA-SCS effective rainfall is strictly kept separate and cannot be consumed directly
     by the daily soil-water balance without an independently justified temporal-disaggregation method.

Scientific & Agronomic Rules:
1. No Silent Imputation: Never assumes default soil moisture or hydraulic properties.
   Missing soil characteristics or initial depletion returns an explicit INSUFFICIENT result.
2. Bounded Physical State: Depletion Dr is strictly bounded: 0 <= Dr <= TAW.
   Excess water above field capacity (Dr < 0) becomes deep percolation (DP) and resets Dr = 0.
3. Stress Detection & Transpiration Reduction:
   When Dr > RAW, the crop enters the water-stress zone and actual transpiration decreases
   per FAO-56 Eq. 84: Ks = (TAW - Dr) / (TAW - RAW). Standard non-stressed ETc is retained
   alongside ETc,adj.
4. Single Crop Coefficient Limitations:
   The single crop coefficient approach does not separate topsoil evaporation (Ke) from
   crop transpiration (Kcb). Under high wetting frequency with depleted root zone, or dry
   topsoil with saturated subsoil, single-Kc stress estimation represents a daily average.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from backend.app.intelligence.types import DataQualityStatus, ProvenanceType


class WaterBalanceRainfallMode(str, Enum):
    """Mutually exclusive rainfall accounting modes for root-zone water balance."""
    PHYSICAL = "physical_mass_balance"
    EMPIRICAL = "empirical_effective_rainfall"


class SoilWaterCapacities(BaseModel):
    """Hydraulic water-holding capacities of the crop root zone."""

    field_capacity_m3_m3: float = Field(..., ge=0.05, le=0.60, description="Volumetric moisture at Field Capacity (-33 kPa)")
    wilting_point_m3_m3: float = Field(..., ge=0.01, le=0.45, description="Volumetric moisture at Permanent Wilting Point (-1500 kPa)")
    available_water_capacity_m3_m3: float = Field(..., ge=0.02, le=0.40, description="AWC = theta_FC - theta_WP (m³/m³)")
    effective_rooting_depth_m: float = Field(..., ge=0.1, le=3.0, description="Effective crop rooting depth Zr in meters")
    depletion_fraction_p: float = Field(..., ge=0.1, le=0.8, description="Allowable soil water depletion fraction p")
    depletion_fraction_p_table: float = Field(..., ge=0.1, le=0.8, description="Baseline Table 22 depletion fraction (ETc ~ 5 mm/day)")
    is_p_adjusted: bool = Field(default=False, description="Whether depletion fraction was adjusted for daily non-stressed ETc")
    total_available_water_mm: float = Field(..., ge=1.0, description="Total available water TAW in mm")
    readily_available_water_mm: float = Field(..., ge=0.5, description="Readily available water RAW in mm")


class WaterBalanceResult(BaseModel):
    """Structured result of daily root-zone soil-water balance accounting."""

    rainfall_mode: WaterBalanceRainfallMode = Field(default=WaterBalanceRainfallMode.PHYSICAL, description="Active rainfall accounting mode")
    soil_capacities: Optional[SoilWaterCapacities] = Field(default=None, description="Root-zone soil water capacities")
    initial_depletion_mm: Optional[float] = Field(default=None, description="Root-zone depletion at start of interval in mm")

    gross_precipitation_mm: Optional[float] = Field(default=None, ge=0.0, description="Gross rainfall input in mm (physical mode)")
    surface_runoff_mm: Optional[float] = Field(default=None, ge=0.0, description="Surface runoff loss in mm (physical mode)")
    infiltrated_precipitation_mm: float = Field(default=0.0, ge=0.0, description="Precipitation infiltrating into root zone in mm")
    effective_rainfall_mm: Optional[float] = Field(default=None, ge=0.0, description="Effective rainfall input in mm (empirical mode)")
    applied_irrigation_mm: float = Field(default=0.0, ge=0.0, description="Irrigation depth applied during interval in mm")

    crop_evapotranspiration_mm: float = Field(default=0.0, ge=0.0, description="Standard non-stressed crop evapotranspiration ETc in mm")
    adjusted_crop_evapotranspiration_mm: float = Field(default=0.0, ge=0.0, description="Adjusted crop evapotranspiration ETc,adj under water stress in mm")
    water_stress_coefficient_ks: float = Field(default=1.0, ge=0.0, le=1.0, description="FAO-56 water stress coefficient Ks (0.0 <= Ks <= 1.0)")

    deep_percolation_mm: float = Field(default=0.0, ge=0.0, description="Water lost to deep drainage below root zone in mm")
    final_depletion_mm: Optional[float] = Field(default=None, description="Updated root-zone depletion Dr at end of interval in mm")
    root_zone_moisture_m3_m3: Optional[float] = Field(default=None, description="Equivalent volumetric soil moisture in m³/m³")

    total_available_water_mm: Optional[float] = Field(default=None, ge=0.0, description="Total available water TAW in mm")
    readily_available_water_mm: Optional[float] = Field(default=None, ge=0.0, description="Readily available water RAW in mm")
    is_in_stress_zone: bool = Field(default=False, description="Whether final depletion Dr exceeds RAW (Dr > RAW)")
    stress_deficit_mm: float = Field(default=0.0, ge=0.0, description="Depletion in excess of RAW (Dr - RAW) in mm")
    is_provisional_empirical: bool = Field(default=False, description="Whether calculation incorporated provisional empirical methods")
    effective_rainfall_method: Optional[str] = Field(default=None, description="Estimation methodology of effective rainfall if applied")
    effective_rainfall_provenance: Optional[ProvenanceType] = Field(default=None, description="Provenance classification of effective rainfall")

    quality_status: DataQualityStatus = Field(default=DataQualityStatus.GOOD, description="Calculation quality assessment")
    audit_trail: List[str] = Field(default_factory=list, description="Step-by-step physical accounting log")


def calculate_water_stress_coefficient(
    depletion_mm: float,
    readily_available_water_mm: float,
    total_available_water_mm: float,
) -> float:
    """Calculate FAO-56 water stress coefficient Ks (FAO-56 Chapter 8, Eq. 84).

    Formula:
        Ks = 1.0                                when Dr <= RAW
        Ks = (TAW - Dr) / (TAW - RAW)           when Dr > RAW

    Bounds:
        0.0 <= Ks <= 1.0

    Agronomic Edge Cases:
        - If Dr <= RAW: Ks = 1.0 (no water stress, potential transpiration).
        - If Dr >= TAW: Ks = 0.0 (wilting point reached, transpiration ceases).
        - If Dr < 0.0: Ks = 1.0 (soil wetter than field capacity).
        - If TAW <= RAW (or TAW - RAW < 1e-6): Ks = 0.0 if Dr >= TAW else 1.0.

    Args:
        depletion_mm: Current root-zone soil water depletion Dr in mm.
        readily_available_water_mm: Readily available water RAW in mm.
        total_available_water_mm: Total available water TAW in mm.

    Returns:
        Water-stress coefficient Ks bounded in [0.0, 1.0].
    """
    dr = float(depletion_mm)
    raw = float(readily_available_water_mm)
    taw = float(total_available_water_mm)

    if taw <= 0.0:
        raise ValueError(f"Total available water TAW must be positive: {taw} mm.")
    if raw < 0.0:
        raise ValueError(f"Readily available water RAW cannot be negative: {raw} mm.")

    # Physical clamping: RAW cannot exceed TAW
    if raw > taw:
        raw = taw

    if dr >= taw:
        return 0.0

    if dr <= raw:
        return 1.0

    denom = taw - raw
    if denom <= 1e-6:
        return 0.0 if dr >= taw else 1.0

    ks = (taw - dr) / denom
    return max(0.0, min(1.0, float(ks)))


def calculate_soil_water_capacities(
    field_capacity_m3_m3: float,
    wilting_point_m3_m3: float,
    rooting_depth_m: float,
    depletion_fraction_p: float = 0.50,
    etc_mm_day: Optional[float] = None,
    adjust_p_for_etc: bool = True,
) -> SoilWaterCapacities:
    """Derive TAW and RAW from soil hydraulic limits, rooting depth, and optional non-stressed ETc adjustment.

    TAW = 1000 * (theta_FC - theta_WP) * Zr
    p_adj = p_table + 0.04 * (5.0 - ETc) (if etc_mm_day provided and adjust_p_for_etc is True)
    RAW = p * TAW

    Args:
        field_capacity_m3_m3: Field capacity in m³/m³.
        wilting_point_m3_m3: Permanent wilting point in m³/m³.
        rooting_depth_m: Effective rooting depth Zr in meters.
        depletion_fraction_p: Baseline Table 22 depletion fraction without stress (default 0.50).
        etc_mm_day: Optional non-stressed ETc rate in mm/day for climatic adjustment of p.
        adjust_p_for_etc: Whether to apply FAO-56 Table 22 climatic adjustment to p.

    Returns:
        SoilWaterCapacities object.

    Raises:
        ValueError: If hydraulic parameters are physically inconsistent (WP >= FC).
    """
    if wilting_point_m3_m3 >= field_capacity_m3_m3:
        raise ValueError(
            f"Physically impossible soil hydraulics: Wilting Point ({wilting_point_m3_m3:.3f}) "
            f">= Field Capacity ({field_capacity_m3_m3:.3f})."
        )

    if rooting_depth_m <= 0.05 or rooting_depth_m > 5.0:
        raise ValueError(f"Rooting depth Zr out of physical bounds: {rooting_depth_m} m.")

    if depletion_fraction_p <= 0.05 or depletion_fraction_p > 0.90:
        raise ValueError(f"Depletion fraction p out of agronomic bounds: {depletion_fraction_p}.")

    awc = field_capacity_m3_m3 - wilting_point_m3_m3
    taw = 1000.0 * awc * rooting_depth_m

    p_table = float(depletion_fraction_p)
    p_final = p_table
    is_p_adj = False

    if etc_mm_day is not None and adjust_p_for_etc:
        if etc_mm_day < 0.0:
            raise ValueError(f"ETc cannot be negative: {etc_mm_day} mm/day.")
        p_raw = p_table + 0.04 * (5.0 - float(etc_mm_day))
        p_final = max(0.10, min(0.80, round(p_raw, 4)))
        is_p_adj = True

    raw = p_final * taw

    return SoilWaterCapacities(
        field_capacity_m3_m3=round(field_capacity_m3_m3, 4),
        wilting_point_m3_m3=round(wilting_point_m3_m3, 4),
        available_water_capacity_m3_m3=round(awc, 4),
        effective_rooting_depth_m=round(rooting_depth_m, 3),
        depletion_fraction_p=round(p_final, 3),
        depletion_fraction_p_table=round(p_table, 3),
        is_p_adjusted=is_p_adj,
        total_available_water_mm=round(taw, 2),
        readily_available_water_mm=round(raw, 2),
    )


def initial_depletion_from_moisture(
    soil_moisture_m3_m3: float,
    capacities: SoilWaterCapacities,
) -> Tuple[float, List[str]]:
    """Convert in-situ volumetric soil moisture into root-zone depletion Dr.

    Dr = 1000 * (theta_FC - theta) * Zr

    Args:
        soil_moisture_m3_m3: Measured volumetric water content in m³/m³.
        capacities: SoilWaterCapacities object.

    Returns:
        Tuple of (depletion_mm, audit_notes).
    """
    notes = []
    fc = capacities.field_capacity_m3_m3
    wp = capacities.wilting_point_m3_m3
    zr = capacities.effective_rooting_depth_m
    taw = capacities.total_available_water_mm

    if soil_moisture_m3_m3 > fc:
        dr = 0.0
        notes.append(f"Measured soil moisture ({soil_moisture_m3_m3:.3f}) > FC ({fc:.3f}): soil at saturation; Dr set to 0.0 mm.")
    elif soil_moisture_m3_m3 < wp:
        dr = taw
        notes.append(f"Measured soil moisture ({soil_moisture_m3_m3:.3f}) < WP ({wp:.3f}): severe drought deficit beyond wilting point; Dr capped at TAW ({taw:.1f} mm).")
    else:
        dr = 1000.0 * (fc - soil_moisture_m3_m3) * zr
        notes.append(f"Computed initial Dr = {dr:.1f} mm from in-situ soil moisture ({soil_moisture_m3_m3:.3f} m³/m³).")

    return max(0.0, min(taw, float(dr))), notes


def update_root_zone_water_balance(
    etc_mm: float,
    gross_precipitation_mm: Optional[float] = None,
    surface_runoff_mm: Optional[float] = None,
    effective_rainfall_mm: Optional[float] = None,
    rainfall_result: Optional[Any] = None,
    soil_capacities: Optional[SoilWaterCapacities] = None,
    initial_depletion_mm: Optional[float] = None,
    applied_irrigation_mm: float = 0.0,
    soil_moisture_m3_m3: Optional[float] = None,
    apply_water_stress_adjustment: bool = True,
    allow_provisional_method: bool = False,
    effective_rainfall_method: Optional[Any] = None,
    effective_rainfall_provenance: Optional[ProvenanceType] = None,
    is_provisional_empirical: Optional[bool] = None,
) -> WaterBalanceResult:
    """Update root-zone water balance over a daily interval per FAO-56 Chapter 8.

    Enforces two mutually exclusive rainfall modes:
    1. Physical Mass-Balance Mode (gross_precipitation_mm is provided):
       - Requires validated surface_runoff_mm with 0 <= RO <= gross_precipitation_mm.
       - Infiltrated water: P_inf = gross_precipitation_mm - surface_runoff_mm.
       - Deep percolation is calculated strictly from storage overflow beyond field capacity (Dr < 0).
       - Empirical effective-rainfall losses are not deducted again.

    2. Empirical Rainfall Mode (effective_rainfall_mm or daily rainfall_result is provided):
       - Applied directly as root-zone infiltration P_inf = effective_rainfall_mm.
       - Disallows separate surface_runoff_mm (prevents double-counting).
       - Monthly USDA-SCS effective rainfall cannot be consumed directly without temporal disaggregation.

    Args:
        etc_mm: Standard non-stressed crop evapotranspiration ETc during interval in mm (>= 0).
        gross_precipitation_mm: Gross rainfall in mm for physical mass balance mode.
        surface_runoff_mm: Surface runoff in mm (physical mode only; 0 <= RO <= P_gross).
        effective_rainfall_mm: Infiltrating rainfall Peff in mm for empirical mode (>= 0).
        rainfall_result: Optional EffectiveRainfallResult.
        soil_capacities: Optional SoilWaterCapacities.
        initial_depletion_mm: Explicit initial depletion Dr,0 in mm.
        applied_irrigation_mm: Irrigation applied during interval in mm (>= 0).
        soil_moisture_m3_m3: Optional in-situ volumetric soil moisture in m³/m³.
        apply_water_stress_adjustment: Whether to reduce ETc using FAO-56 Ks when Dr > RAW (default True).
        allow_provisional_method: Explicit opt-in flag required when consuming provisional daily rainfall.

    Returns:
        WaterBalanceResult with updated depletion and mass balance breakdown.

    Raises:
        ValueError: If mode inputs are mixed, runoff is invalid/missing, or parameters are out of bounds.
    """
    audit: List[str] = []

    # 1. Validation of essential soil context
    if soil_capacities is None:
        return WaterBalanceResult(
            quality_status=DataQualityStatus.INSUFFICIENT,
            audit_trail=["Aborted: Missing soil hydraulic properties (FC, WP, or rooting depth)."],
        )

    # 2. Validation of initial moisture state
    dr_start: float
    if initial_depletion_mm is not None:
        if initial_depletion_mm < 0.0:
            raise ValueError(f"Initial depletion cannot be negative: {initial_depletion_mm} mm.")
        dr_start = min(soil_capacities.total_available_water_mm, float(initial_depletion_mm))
        audit.append(f"Starting with configured initial depletion Dr,0 = {dr_start:.2f} mm.")
    elif soil_moisture_m3_m3 is not None:
        dr_start, init_notes = initial_depletion_from_moisture(soil_moisture_m3_m3, soil_capacities)
        audit.extend(init_notes)
    else:
        return WaterBalanceResult(
            soil_capacities=soil_capacities,
            quality_status=DataQualityStatus.INSUFFICIENT,
            audit_trail=[
                "Aborted: No initial soil moisture or depletion evidence provided. "
                "Water balance cannot be computed without an initial state."
            ],
        )

    # 3. Input validation
    if etc_mm < 0.0:
        raise ValueError(f"Crop evapotranspiration cannot be negative: {etc_mm} mm.")
    if applied_irrigation_mm < 0.0:
        raise ValueError(f"Applied irrigation cannot be negative: {applied_irrigation_mm} mm.")

    # 4. Handle rainfall_result if provided
    is_provisional = False
    eff_method_str: Optional[str] = None
    eff_prov: Optional[ProvenanceType] = effective_rainfall_provenance

    if rainfall_result is not None:
        if getattr(rainfall_result, "quality_status", None) == DataQualityStatus.INSUFFICIENT or getattr(rainfall_result, "effective_rainfall_mm", None) is None:
            return WaterBalanceResult(
                soil_capacities=soil_capacities,
                quality_status=DataQualityStatus.INSUFFICIENT,
                is_provisional_empirical=getattr(rainfall_result, "is_provisional_empirical", False),
                effective_rainfall_method=getattr(getattr(rainfall_result, "method", None), "value", str(getattr(rainfall_result, "method", None))),
                effective_rainfall_provenance=getattr(rainfall_result, "provenance_type", None),
                audit_trail=[
                    "Aborted: Input rainfall_result has INSUFFICIENT quality or missing effective rainfall (None). "
                    "Downstream water balance cannot interpret missing rainfall evidence as zero."
                ],
            )

        method_obj = getattr(rainfall_result, "method", None)
        method_str = getattr(method_obj, "value", str(method_obj)).lower()
        eff_method_str = getattr(method_obj, "value", str(method_obj)) if method_obj else None
        eff_prov = getattr(rainfall_result, "provenance_type", None) or eff_prov

        if "usda_scs" in method_str:
            raise ValueError(
                "Monthly USDA-SCS effective rainfall cannot be consumed directly by the daily "
                "soil-water balance without an independently justified temporal-disaggregation method."
            )
        if getattr(rainfall_result, "is_provisional_empirical", False):
            is_provisional = True

        if effective_rainfall_mm is not None:
            raise ValueError("Pass either effective_rainfall_mm or rainfall_result, not both.")
        effective_rainfall_mm = getattr(rainfall_result, "effective_rainfall_mm", None)

    elif effective_rainfall_mm is not None:
        # Scalar input route: require explicit method and provenance for scientific traceability
        if effective_rainfall_method is None:
            raise ValueError(
                "When effective_rainfall_mm is passed directly as a scalar, an explicit "
                "effective_rainfall_method is required for scientific traceability and safety."
            )
        if effective_rainfall_provenance is None:
            raise ValueError(
                "When effective_rainfall_mm is passed directly as a scalar, an explicit "
                "effective_rainfall_provenance is required."
            )
        prov_val = getattr(effective_rainfall_provenance, "value", str(effective_rainfall_provenance)).lower()
        if prov_val in {"unknown", "none", ""}:
            raise ValueError(
                f"effective_rainfall_provenance cannot be '{effective_rainfall_provenance}'; "
                "known, valid provenance is required."
            )

        method_str = getattr(effective_rainfall_method, "value", str(effective_rainfall_method)).lower()
        eff_method_str = getattr(effective_rainfall_method, "value", str(effective_rainfall_method))
        eff_prov = effective_rainfall_provenance

        if "usda_scs" in method_str:
            raise ValueError(
                "Monthly USDA-SCS effective rainfall cannot be consumed directly by the daily "
                "soil-water balance without an independently justified temporal-disaggregation method."
            )

        is_method_provisional = ("fao_dependable" in method_str)
        if is_method_provisional:
            if is_provisional_empirical is False:
                raise ValueError(
                    f"Conflicting provisional configuration: effective_rainfall_method '{eff_method_str}' "
                    "is inherently provisional empirical, but is_provisional_empirical was set to False. "
                    "Provisional status cannot be overridden."
                )
            is_provisional = True
        else:
            is_provisional = bool(is_provisional_empirical)

    # Validate provisional method gating across all input routes
    if is_provisional:
        if not allow_provisional_method:
            raise ValueError(
                "The effective rainfall input is derived from or marked as the provisional daily method and is gated. "
                "Set allow_provisional_method=True on update_root_zone_water_balance to explicitly opt in for research use."
            )
        audit.append(
            "NOTE: Using PROVISIONAL empirical daily effective rainfall method (FAO dependable daily approximation). "
            "Results are uncalibrated and intended for sensitivity analysis only."
        )

    # 5. Enforce mutually exclusive rainfall modes
    if gross_precipitation_mm is not None and effective_rainfall_mm is not None:
        raise ValueError(
            "Mutually exclusive rainfall modes: pass either gross_precipitation_mm (Physical mass-balance mode) "
            "or effective_rainfall_mm (Empirical rainfall mode), but not both."
        )

    rainfall_mode: WaterBalanceRainfallMode
    p_infiltrating: float
    p_gross_out: Optional[float] = None
    p_ro_out: Optional[float] = None
    p_eff_out: Optional[float] = None

    if gross_precipitation_mm is not None:
        # --- Physical Mass-Balance Mode ---
        rainfall_mode = WaterBalanceRainfallMode.PHYSICAL
        p_gross = float(gross_precipitation_mm)
        if p_gross < 0.0:
            raise ValueError(f"Gross precipitation cannot be negative: {p_gross} mm.")

        # Require explicit, non-None surface runoff in physical mode
        if surface_runoff_mm is None:
            raise ValueError(
                "Physical mass-balance mode requires an explicit, validated surface_runoff_mm. "
                "Missing runoff cannot be silently assumed to be zero."
            )

        p_ro = float(surface_runoff_mm)
        if p_ro < 0.0:
            raise ValueError(f"Surface runoff cannot be negative: {p_ro} mm.")
        if p_ro > p_gross:
            raise ValueError(
                f"Surface runoff ({p_ro:.2f} mm) cannot exceed gross precipitation ({p_gross:.2f} mm)."
            )

        p_infiltrating = p_gross - p_ro
        p_gross_out = p_gross
        p_ro_out = p_ro
        audit.append(
            f"Physical mass-balance mode: Gross P ({p_gross:.2f} mm) - Runoff RO ({p_ro:.2f} mm) "
            f"= Net infiltrated rainfall ({p_infiltrating:.2f} mm). Empirical losses not deducted."
        )

    else:
        # --- Empirical Effective Rainfall Mode ---
        rainfall_mode = WaterBalanceRainfallMode.EMPIRICAL
        if surface_runoff_mm is not None:
            raise ValueError(
                "Cannot supply surface_runoff_mm in Empirical rainfall mode. "
                "Empirical effective rainfall (P_eff) already accounts for runoff losses; "
                "deducting runoff again would double-count losses."
            )

        p_eff = float(effective_rainfall_mm) if effective_rainfall_mm is not None else 0.0
        if p_eff < 0.0:
            raise ValueError(f"Effective rainfall cannot be negative: {p_eff} mm.")

        p_infiltrating = p_eff
        p_eff_out = p_eff
        audit.append(
            f"Empirical rainfall mode: Peff ({p_eff:.2f} mm) applied directly as net root-zone infiltration. "
            "Runoff and canopy abstractions are assumed already deducted by empirical model; "
            "deep percolation DP only drains water exceeding TAW."
        )

    taw = soil_capacities.total_available_water_mm
    raw = soil_capacities.readily_available_water_mm
    fc = soil_capacities.field_capacity_m3_m3
    zr = soil_capacities.effective_rooting_depth_m

    # 6. Pre-Transpiration Soil Deficit
    water_added = p_infiltrating + applied_irrigation_mm
    dr_pre = dr_start - water_added
    audit.append(
        f"Pre-ET depletion: Dr,start ({dr_start:.2f}) - Infiltration ({p_infiltrating:.2f}) - "
        f"Irrig ({applied_irrigation_mm:.2f}) = Dr,pre ({dr_pre:.2f} mm)."
    )

    # 7. Water-Stress Coefficient Ks (FAO-56 Eq. 84)
    # Evaluated from the pre-transpiration deficit after effective water inputs for the day
    dr_for_ks = max(0.0, min(taw, dr_pre))
    ks = calculate_water_stress_coefficient(
        depletion_mm=dr_for_ks,
        readily_available_water_mm=raw,
        total_available_water_mm=taw,
    )

    if apply_water_stress_adjustment:
        etc_effective = round(ks * etc_mm, 3)
        if ks < 1.0:
            audit.append(
                f"Water stress active: Dr,pre ({dr_for_ks:.2f} mm) > RAW ({raw:.2f} mm). "
                f"Ks = {ks:.3f}; standard ETc ({etc_mm:.2f} mm) reduced to ETc,adj ({etc_effective:.2f} mm)."
            )
        else:
            audit.append(
                f"No water stress: Dr,pre ({dr_for_ks:.2f} mm) <= RAW ({raw:.2f} mm). "
                f"Ks = 1.000; ETc transpires at full potential ({etc_effective:.2f} mm)."
            )
    else:
        etc_effective = etc_mm
        audit.append(f"Stress adjustment disabled: using unadjusted ETc ({etc_mm:.2f} mm). Ks={ks:.3f}.")

    # 8. Daily Mass Balance Accounting & Drainage
    dr_raw = dr_pre + etc_effective

    if dr_raw < 0.0:
        deep_percolation = -dr_raw
        dr_final = 0.0
        audit.append(
            f"Deep percolation occurred: {deep_percolation:.2f} mm drained below root zone beyond Field Capacity; "
            f"Dr reset to 0.0 mm (FC)."
        )
    else:
        deep_percolation = 0.0
        if dr_raw > taw:
            dr_final = taw
            audit.append(f"Depletion reached maximum capacity TAW ({taw:.2f} mm); soil at permanent wilting point.")
        else:
            dr_final = dr_raw

    # 9. Volumetric moisture equivalent
    theta_final = fc - (dr_final / (1000.0 * zr))

    # 10. Final Stress Evaluation at End of Day
    is_stressed = dr_final > raw
    stress_deficit = max(0.0, dr_final - raw)

    return WaterBalanceResult(
        rainfall_mode=rainfall_mode,
        soil_capacities=soil_capacities,
        initial_depletion_mm=round(dr_start, 2),
        gross_precipitation_mm=round(p_gross_out, 2) if p_gross_out is not None else None,
        surface_runoff_mm=round(p_ro_out, 2) if p_ro_out is not None else None,
        infiltrated_precipitation_mm=round(p_infiltrating, 2),
        effective_rainfall_mm=round(p_eff_out, 2) if p_eff_out is not None else None,
        applied_irrigation_mm=round(applied_irrigation_mm, 2),
        crop_evapotranspiration_mm=round(etc_mm, 2),
        adjusted_crop_evapotranspiration_mm=round(etc_effective, 2),
        water_stress_coefficient_ks=round(ks, 4),
        deep_percolation_mm=round(deep_percolation, 2),
        final_depletion_mm=round(dr_final, 2),
        root_zone_moisture_m3_m3=round(theta_final, 4),
        total_available_water_mm=round(taw, 2),
        readily_available_water_mm=round(raw, 2),
        is_in_stress_zone=is_stressed,
        stress_deficit_mm=round(stress_deficit, 2),
        is_provisional_empirical=is_provisional,
        effective_rainfall_method=eff_method_str,
        effective_rainfall_provenance=eff_prov,
        quality_status=DataQualityStatus.GOOD,
        audit_trail=audit,
    )
