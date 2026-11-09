"""Irrigation Requirement Calculation Module.

Calculates net refill depth to field capacity, strategy-gated net irrigation depth,
and gross irrigation requirements in depth (mm) and volume (m³) accounting for
irrigation system application efficiency:
    Net Refill to Field Capacity (mm) = max(0, Dr)
    Gross Irrigation Depth (mm) = Net Irrigation Depth (mm) / Application Efficiency
    Volume (m³) = Depth (mm) * Area (m²) / 1000 = Depth (mm) * (Area_ha * 10000) / 1000

Agronomic & Safety Rules (per AGENTS.md, AI_SPEC.md):
1. Net Refill Semantics: max(0, Dr) physically represents the water required to restore
   the root-zone deficit back to Field Capacity (Dr = 0).
2. Separation of Trigger Policy and Refill Depth: Management strategy and Management-Allowed
   Depletion (MAD) govern WHEN irrigation is triggered, while refill depth governs the physical
   soil water deficit.
3. Gross >= Net: Since application efficiency eta in (0, 1], gross irrigation is
   never smaller than net irrigation (I_gross >= I_net).
4. Efficiency Must Be Explicit: eta must be explicitly provided or sourced from
   documented agronomic system references (e.g. drip: 0.90, sprinkler: 0.75, furrow: 0.60).
5. Strict Volume Gating: Volume (m³) is calculated ONLY when the actual zone area
   in hectares is known and positive. If area is unrecorded, volume remains strictly None.
6. Scope Boundary: This module calculates deterministic water physics requirements;
   it DOES NOT produce farmer-facing decision codes or advisory rules (reserved for Phase 4).
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.intelligence.agronomy.water_balance import WaterBalanceResult
from backend.app.intelligence.types import DataQualityStatus, ProvenanceType


class IrrigationMethodEfficiency(float, Enum):
    """Documented typical application efficiencies by irrigation method (FAO-24 / FAO-56)."""
    DRIP = 0.90
    MICRO_SPRINKLER = 0.85
    CENTER_PIVOT = 0.80
    SOLID_SET_SPRINKLER = 0.75
    FURROW_SURFACE = 0.60
    BASIN_FLOOD = 0.50
    DEFAULT_GOOD_PRACTICE = 0.85


class IrrigationManagementStrategy(str, Enum):
    """Irrigation scheduling objective."""
    REFILL_TO_FIELD_CAPACITY = "refill_to_field_capacity"
    IRRIGATE_WHEN_STRESSED = "irrigate_when_stressed"


class IrrigationRequirementResult(BaseModel):
    """Structured calculation result for net refill, net irrigation, and gross requirements."""

    net_refill_to_field_capacity_mm: float = Field(
        ...,
        ge=0.0,
        description="Physical net water depth needed to refill the root zone back to Field Capacity (max(0, Dr))"
    )
    net_irrigation_depth_mm: float = Field(
        ...,
        ge=0.0,
        description="Net water depth required under applied management strategy (mm)"
    )
    gross_irrigation_depth_mm: float = Field(
        ...,
        ge=0.0,
        description="Gross water depth applied accounting for system efficiency in mm"
    )
    application_efficiency: float = Field(
        ...,
        gt=0.0,
        le=1.0,
        description="Irrigation system application efficiency fraction"
    )
    efficiency_source: str = Field(..., description="Source of efficiency parameter (system method or explicit user input)")
    management_strategy: IrrigationManagementStrategy = Field(..., description="Irrigation scheduling strategy applied")
    is_irrigation_needed: bool = Field(..., description="Whether positive irrigation application is triggered under strategy")
    management_allowed_depletion_mm: Optional[float] = Field(default=None, description="MAD trigger threshold in mm")

    # Volumetric Requirements (Only populated when area is known)
    area_ha: Optional[float] = Field(default=None, ge=0.0, description="Evaluated zone/field area in hectares")
    net_irrigation_volume_m3: Optional[float] = Field(default=None, ge=0.0, description="Net irrigation volume in m³")
    gross_irrigation_volume_m3: Optional[float] = Field(default=None, ge=0.0, description="Gross irrigation volume in m³")
    is_provisional_empirical: bool = Field(default=False, description="Whether requirement was calculated from provisional water balance")
    effective_rainfall_method: Optional[str] = Field(default=None, description="Effective rainfall method inherited from water balance")
    effective_rainfall_provenance: Optional[ProvenanceType] = Field(default=None, description="Provenance of effective rainfall inherited from water balance")

    quality_status: DataQualityStatus = Field(default=DataQualityStatus.GOOD, description="Quality classification")
    audit_notes: List[str] = Field(default_factory=list, description="Audit log of calculation steps")


def calculate_irrigation_requirement(
    water_balance: WaterBalanceResult,
    application_efficiency: Optional[float] = None,
    irrigation_method: Optional[str] = None,
    area_ha: Optional[float] = None,
    strategy: IrrigationManagementStrategy = IrrigationManagementStrategy.REFILL_TO_FIELD_CAPACITY,
    management_allowed_depletion_fraction: Optional[float] = None,
) -> IrrigationRequirementResult:
    """Calculate net refill depth, net irrigation depth, and gross depth/volume requirements.

    Args:
        water_balance: WaterBalanceResult containing current root-zone depletion.
        application_efficiency: Explicit efficiency fraction in (0.0, 1.0].
        irrigation_method: Method name to look up documented default efficiency if not provided.
        area_ha: Optional zone area in hectares for volumetric conversion.
        strategy: IrrigationManagementStrategy determining trigger condition.
        management_allowed_depletion_fraction: Optional MAD fraction of TAW (e.g. 0.50).
            If provided, overrides RAW as the trigger threshold.

    Returns:
        IrrigationRequirementResult with depths, volumes, and audit trail.

    Raises:
        ValueError: If efficiency is out of bounds or water balance is invalid.
    """
    audit: List[str] = []

    # 1. Check water balance quality
    is_provisional = getattr(water_balance, "is_provisional_empirical", False)
    if is_provisional:
        audit.append(
            "NOTE: Water balance was evaluated using a PROVISIONAL empirical method. "
            "Downstream irrigation requirements are indicative only and intended for sensitivity analysis."
        )
    if getattr(water_balance, "effective_rainfall_method", None):
        audit.append(f"Water balance effective rainfall method: {water_balance.effective_rainfall_method}.")

    if water_balance.quality_status == DataQualityStatus.INSUFFICIENT or water_balance.final_depletion_mm is None:
        return IrrigationRequirementResult(
            net_refill_to_field_capacity_mm=0.0,
            net_irrigation_depth_mm=0.0,
            gross_irrigation_depth_mm=0.0,
            application_efficiency=0.85,
            efficiency_source="Not evaluated (insufficient water balance)",
            management_strategy=strategy,
            is_irrigation_needed=False,
            is_provisional_empirical=is_provisional,
            effective_rainfall_method=getattr(water_balance, "effective_rainfall_method", None),
            effective_rainfall_provenance=getattr(water_balance, "effective_rainfall_provenance", None),
            quality_status=DataQualityStatus.INSUFFICIENT,
            audit_notes=["Aborted: Input water balance is incomplete or insufficient."],
        )

    # 2. Determine Application Efficiency
    eff: float
    eff_source: str
    if application_efficiency is not None:
        if application_efficiency <= 0.0 or application_efficiency > 1.0:
            raise ValueError(
                f"Application efficiency must be strictly in (0.0, 1.0], got {application_efficiency}."
            )
        eff = float(application_efficiency)
        eff_source = f"Explicit user/configuration parameter ({eff:.2f})"
    elif irrigation_method:
        method_key = irrigation_method.strip().upper()
        if hasattr(IrrigationMethodEfficiency, method_key):
            eff = getattr(IrrigationMethodEfficiency, method_key).value
            eff_source = f"FAO documented default for '{irrigation_method}' system ({eff:.2f})"
        else:
            eff = IrrigationMethodEfficiency.DEFAULT_GOOD_PRACTICE.value
            eff_source = f"Default good practice fallback for unknown method '{irrigation_method}' ({eff:.2f})"
            audit.append(f"Unrecognized irrigation method '{irrigation_method}'; applied default efficiency {eff:.2f}.")
    else:
        eff = IrrigationMethodEfficiency.DEFAULT_GOOD_PRACTICE.value
        eff_source = f"Standard documented good practice default ({eff:.2f})"

    # 3. Derive Net Refill Depth to Field Capacity
    dr = water_balance.final_depletion_mm
    soil_caps = water_balance.soil_capacities
    taw = soil_caps.total_available_water_mm if soil_caps else (water_balance.total_available_water_mm or 0.0)
    raw = soil_caps.readily_available_water_mm if soil_caps else (water_balance.readily_available_water_mm or 0.0)

    # Physical refill-to-field-capacity depth
    net_refill_fc = max(0.0, dr)
    audit.append(f"Physical net refill to Field Capacity: max(0, Dr) = {net_refill_fc:.2f} mm.")

    # Determine Trigger Threshold
    mad_mm: Optional[float] = None
    if management_allowed_depletion_fraction is not None:
        if management_allowed_depletion_fraction <= 0.0 or management_allowed_depletion_fraction > 1.0:
            raise ValueError(
                f"MAD fraction must be in (0.0, 1.0], got {management_allowed_depletion_fraction}."
            )
        mad_mm = round(management_allowed_depletion_fraction * taw, 2)
        trigger_threshold = mad_mm
        threshold_name = f"MAD ({management_allowed_depletion_fraction:.2f} * TAW = {mad_mm:.2f} mm)"
    else:
        trigger_threshold = raw
        threshold_name = f"RAW ({raw:.2f} mm)"

    # 4. Evaluate Irrigation Trigger Strategy
    if strategy == IrrigationManagementStrategy.REFILL_TO_FIELD_CAPACITY:
        net_depth = net_refill_fc
        is_needed = net_depth > 0.5  # Practical agronomic threshold (ignore micro-millimeter noise)
        audit.append(f"Strategy: Refill to Field Capacity. Net irrigation depth = {net_depth:.2f} mm.")

    elif strategy == IrrigationManagementStrategy.IRRIGATE_WHEN_STRESSED:
        if dr > trigger_threshold:
            net_depth = net_refill_fc  # Refill back to FC once trigger threshold is crossed
            is_needed = True
            audit.append(
                f"Strategy: Depletion ({dr:.2f} mm) > {threshold_name}. Triggered net irrigation of {net_depth:.2f} mm."
            )
        else:
            net_depth = 0.0
            is_needed = False
            audit.append(
                f"Strategy: Depletion ({dr:.2f} mm) <= {threshold_name}. No irrigation triggered today."
            )

    else:
        raise ValueError(f"Unsupported irrigation management strategy: {strategy}")

    # 5. Derive Gross Irrigation Depth
    gross_depth = net_depth / eff
    audit.append(
        f"Gross depth = Net ({net_depth:.2f} mm) / Efficiency ({eff:.2f}) = {gross_depth:.2f} mm."
    )

    # 6. Volumetric Conversion (Gated strictly by known area)
    net_vol: Optional[float] = None
    gross_vol: Optional[float] = None

    if area_ha is not None and area_ha > 0.0:
        area_m2 = area_ha * 10000.0
        # Volume (m³) = Depth (mm) * Area (m²) / 1000
        net_vol = (net_depth * area_m2) / 1000.0
        gross_vol = (gross_depth * area_m2) / 1000.0
        audit.append(
            f"Volumetric conversion for area {area_ha:.2f} ha: "
            f"Net volume = {net_vol:.1f} m³, Gross volume = {gross_vol:.1f} m³."
        )
    else:
        audit.append("Zone area is unknown or zero: volumetric requirements withheld.")

    return IrrigationRequirementResult(
        net_refill_to_field_capacity_mm=round(net_refill_fc, 2),
        net_irrigation_depth_mm=round(net_depth, 2),
        gross_irrigation_depth_mm=round(gross_depth, 2),
        application_efficiency=round(eff, 3),
        efficiency_source=eff_source,
        management_strategy=strategy,
        is_irrigation_needed=is_needed,
        management_allowed_depletion_mm=mad_mm,
        area_ha=round(area_ha, 3) if area_ha is not None else None,
        net_irrigation_volume_m3=round(net_vol, 2) if net_vol is not None else None,
        gross_irrigation_volume_m3=round(gross_vol, 2) if gross_vol is not None else None,
        is_provisional_empirical=is_provisional,
        effective_rainfall_method=getattr(water_balance, "effective_rainfall_method", None),
        effective_rainfall_provenance=getattr(water_balance, "effective_rainfall_provenance", None),
        quality_status=water_balance.quality_status,
        audit_notes=audit,
    )
