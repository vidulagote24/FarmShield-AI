"""Multimodal crop and water stress indicators.

Extracts deterministic, scientifically traceable stress indicators across four
independent domains:
1. Root-Zone Water Balance & Depletion (Phase 3)
2. Satellite Canopy Vegetation & Moisture Indices (Phase 2)
3. Weather & Atmospheric Evaporative Demand (Phase 2)
4. Soil Physicochemical & Hydraulic Conditions (Phase 2)

Scientific and Agronomic Restrictions (per AGENTS.md, AI_SPEC.md, DATA_SOURCES.md):
- Root-zone soil moisture is modelled via daily water-balance accounting. Field sensor
  observations must never be conflated with gridded or water-balance estimates.
- Spectral vegetation indices (NDVI, NDMI) reflect canopy greenness and leaf hydration;
  they are NOT direct measurements of root-zone soil moisture or confirmed drought diagnoses.
- Universal NDVI/NDMI drought thresholds are scientifically rejected. Vegetation anomalies
  require an explicit, validated historical baseline for comparison.
- Two-observation endpoint changes represent interval rates and MUST NOT be labelled
  as statistically established trends.
- Single-reading instantaneous high temperatures do NOT constitute proof of prolonged heat stress.
- Soil electrical conductivity (EC) from different extraction ratios (e.g. 1:5 extract vs
  saturated paste ECe) are NOT interchangeable without texture-dependent conversion.
- Salinity and soil reaction (pH) concerns represent osmotic and chemical constraints,
  distinct from hydraulic water depletion.
- Missing evidence MUST remain None and report INSUFFICIENT data; missing evidence must
  never be treated as healthy conditions.
"""

from datetime import datetime, timezone
from enum import Enum
import math
import re
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field

from backend.app.intelligence.agronomy.water_balance import (
    SoilWaterCapacities,
    WaterBalanceResult,
)
from backend.app.intelligence.config import (
    FeatureFreshnessConfig,
    default_freshness_config,
)
from backend.app.intelligence.features.soil import SoilFeatures
from backend.app.intelligence.features.vegetation import ZoneVegetationFeatures
from backend.app.intelligence.features.weather import WeatherFeatures
from backend.app.intelligence.types import (
    DataQualityStatus,
    ProvenanceType,
    WeatherWindowType,
)

# Standard literature citations for thresholds
CITATION_FAO56 = "FAO Irrigation and Drainage Paper 56 (Allen et al., 1998)"
CITATION_FAO39 = "FAO Soils Bulletin 39: Salt-affected soils and their management (1988)"
CITATION_USDA60 = "USDA Agriculture Handbook 60: Diagnosis and Improvement of Saline and Alkali Soils (Richards, 1954)"
CITATION_HEAT_STRESS_WHEAT = "Prasad et al. (2008): Impact of High Temperature Stress on Floret Fertility and Grain Yield of Wheat (cv. Karl 92, controlled growth chambers, 32°C daytime max)"
CITATION_HEAT_STRESS_COTTON = "Craufurd & Wheeler (2009): Temperature Stress and Flowering Time of Annual Crops (cotton flowering, 38°C experimental threshold)"
CITATION_HEAT_STRESS = CITATION_HEAT_STRESS_WHEAT
CITATION_VPD_DEMAND = "FAO-56 Chapter 3; Grossiord et al. (2020): Plant responses to rising vapor pressure deficit (operational demand warning, not universal tissue necrosis)"
CITATION_VPD_FAO56_PAIRED = "FAO-56 Eq. 11 (Tetens psychrometric definition from simultaneous T and RH)"
CITATION_VPD_FAO56_RH_MAX_MIN = "FAO-56 Eq. 12 & Eq. 17 (Daily actual vapour pressure from RHmax and RHmin)"
CITATION_VPD_FAO56_RH_MEAN = "FAO-56 Eq. 12 & Eq. 19 (Daily mean-RH approximation; does NOT cite Eq. 17)"
CITATION_VPD_DIURNAL_PROXY = "Diurnal proxy estimation (provisional midday peak demand from Tmax and daily mean RH; non-simultaneous)"


class HypothesisTestConvention(str, Enum):
    """Statistical hypothesis testing convention for formal vegetation anomaly inference."""
    ONE_SIDED_LOWER = "one_sided_lower"  # H1: mu_new < mu_0 (depressed canopy greenness, t <= -t_{0.95, df})
    TWO_SIDED = "two_sided"              # H1: mu_new != mu_0 (bidirectional greenness departure, |t| >= t_{0.975, df})


# Exact Student's t critical values for alpha = 0.05
# t_0.95: One-sided lower tail critical value (95th percentile, upper 5% single tail)
STUDENT_T_0_95_CRITICAL_VALUES: Dict[int, float] = {
    1: 6.314, 2: 2.920, 3: 2.353, 4: 2.132, 5: 2.015,
    6: 1.943, 7: 1.895, 8: 1.860, 9: 1.833, 10: 1.812,
    11: 1.796, 12: 1.782, 13: 1.771, 14: 1.761, 15: 1.753,
    16: 1.746, 17: 1.740, 18: 1.734, 19: 1.729, 20: 1.725,
    21: 1.721, 22: 1.717, 23: 1.714, 24: 1.711, 25: 1.708,
    26: 1.706, 27: 1.703, 28: 1.701, 29: 1.699, 30: 1.697,
}

# t_0.975: Two-sided critical value (97.5th percentile, alpha/2 = 0.025 per tail)
STUDENT_T_0_975_CRITICAL_VALUES: Dict[int, float] = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
    6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
    11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
    16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
    21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060,
    26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042,
}


def get_student_t_critical_value(
    degrees_of_freedom: int,
    alpha: float = 0.05,
    two_sided: bool = True,
) -> float:
    """Retrieve or compute Student's t distribution critical value at alpha=0.05.

    Conventions:
    - One-sided lower tail (two_sided=False, alpha=0.05): uses 0.95 t quantile (t_0.95).
    - Two-sided (two_sided=True, alpha=0.05): uses 0.975 t quantile (t_0.975, alpha/2 = 0.025 per tail).

    Uses exact tabulated quantiles for df <= 30; uses high-order Cornish-Fisher expansion for df > 30.
    """
    if degrees_of_freedom < 1:
        raise ValueError(f"Degrees of freedom must be >= 1, got {degrees_of_freedom}")

    if two_sided:
        if degrees_of_freedom in STUDENT_T_0_975_CRITICAL_VALUES:
            return STUDENT_T_0_975_CRITICAL_VALUES[degrees_of_freedom]
        z = 1.959964
    else:
        if degrees_of_freedom in STUDENT_T_0_95_CRITICAL_VALUES:
            return STUDENT_T_0_95_CRITICAL_VALUES[degrees_of_freedom]
        z = 1.644853

    # High-order Cornish-Fisher asymptotic expansion for df > 30
    term1 = (z**3 + z) / (4.0 * degrees_of_freedom)
    term2 = (5.0 * z**5 + 16.0 * z**3 + 3.0 * z) / (96.0 * (degrees_of_freedom**2))
    return round(z + term1 + term2, 3)


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


class VegetationHistoricalBaseline(BaseModel):
    """Historical baseline for vegetation anomaly detection.

    Enforces that satellite anomaly calculations require a documented,
    scientifically comparable historical reference for the crop and stage.
    """
    crop_type: Optional[str] = Field(default=None, description="Crop species associated with baseline")
    growth_stage: Optional[str] = Field(default=None, description="Phenological stage associated with baseline (e.g. 'flowering')")
    baseline_ndvi: float = Field(..., ge=-1.0, le=1.0, description="Expected baseline median/mean NDVI")
    baseline_ndmi: Optional[float] = Field(default=None, ge=-1.0, le=1.0, description="Expected baseline median NDMI")
    baseline_std: Optional[float] = Field(default=None, ge=0.0, description="Historical sample standard deviation s of NDVI")
    sample_size_years: Optional[int] = Field(default=None, ge=1, description="Number of historical years/cycles in baseline (N)")
    min_sample_size: int = Field(default=10, description="Minimum historical samples/cycles required for formal statistical hypothesis testing")
    min_sample_size_formal_test: int = Field(default=10, description="Operational minimum sample size policy for formal hypothesis testing (df >= 9)")
    degrees_of_freedom: Optional[int] = Field(default=None, description="Degrees of freedom (N - 1) for hypothesis testing")
    hypothesis_test_convention: HypothesisTestConvention = Field(
        default=HypothesisTestConvention.TWO_SIDED,
        description="Hypothesis testing convention: 'two_sided' (t_0.975) or 'one_sided_lower' (t_0.95)"
    )
    distribution_assumed: str = Field(default="normal", description="Assumed distribution of historical stage medians")
    is_statistically_robust: bool = Field(default=False, description="Whether baseline has documented variance and sufficient sample size (N >= 10) to support formal statistical hypothesis testing")
    is_valid: bool = Field(default=True, description="Whether baseline is scientifically comparable and validated")
    baseline_source: str = Field(..., description="Source of baseline (e.g. '10-year zone median', 'regional phenology curve')")

    def model_post_init(self, __context: Any) -> None:
        """Derive degrees of freedom and statistical robustness."""
        if self.sample_size_years is not None:
            self.degrees_of_freedom = max(0, self.sample_size_years - 1)

        threshold_n = min(self.min_sample_size, self.min_sample_size_formal_test)
        if (
            self.baseline_std is not None
            and self.baseline_std > 0.0
            and self.sample_size_years is not None
            and self.sample_size_years >= threshold_n
            and (self.degrees_of_freedom is not None and self.degrees_of_freedom >= 1)
        ):
            self.is_statistically_robust = True
        else:
            self.is_statistically_robust = False


class CropStressThresholds(BaseModel):
    """Documented crop- and stage-specific meteorological and edaphic stress thresholds.

    Controlled-environment experimental thresholds must not be generalized into
    universal production thresholds without regional cultivar calibration.
    """
    crop_type: str = Field(..., description="Target crop name (e.g. 'wheat', 'cotton')")
    growth_stage: Optional[str] = Field(default=None, description="Phenological growth stage (e.g. 'flowering', 'grain_filling')")
    critical_temperature_max_c: float = Field(
        default=35.0,
        description="Critical daily maximum temperature (°C) causing transpirational/reproductive stress"
    )
    critical_heat_duration_days: int = Field(
        default=2,
        ge=1,
        description="Minimum consecutive days above critical temperature to confirm prolonged heat stress"
    )
    source_cultivar: Optional[str] = Field(default=None, description="Cultivar or genotype tested in cited literature (e.g. cv. 'Karl 92')")
    experimental_conditions: Optional[str] = Field(default=None, description="Testing environment in source literature (e.g. 'controlled growth chamber', 'field shelter')")
    is_threshold_provisional: bool = Field(default=True, description="Marks threshold as provisional; controlled experimental results cannot be generalized as universal production thresholds")

    critical_vpd_kpa: float = Field(
        default=2.2,
        ge=0.5,
        description="Vapour-pressure deficit threshold (kPa) for high atmospheric evaporative demand warning (not universal crop damage)"
    )
    is_vpd_provisional: bool = Field(default=True, description="Marks VPD threshold as provisional operational warning, not universal tissue damage")

    frost_threshold_c: float = Field(
        default=2.0,
        description="Minimum temperature (°C) triggering frost or chilling hazard"
    )
    salinity_tolerance_ece_ds_m: float = Field(
        default=4.0,
        ge=0.0,
        description="Saturated paste ECe threshold (dS/m) where crop yield reduction begins for target crop (FAO-29/39)"
    )
    threshold_source: str = Field(
        default="FAO-56 / Agronomic Literature",
        description="Authoritative literature citation for these thresholds"
    )


# ==============================================================================
# 1. WATER STRESS INDICATORS
# ==============================================================================

class WaterStressIndicators(BaseModel):
    """Interpretable water-stress indicators derived from Phase 3 root-zone water balance."""

    # Continuous metrics
    depletion_mm: Optional[float] = Field(default=None, description="Root-zone water depletion Dr in mm")
    depletion_fraction_taw: Optional[float] = Field(default=None, description="Fraction of TAW depleted (Dr / TAW)")
    raw_depletion_fraction_p: Optional[float] = Field(default=None, description="Readily available fraction p (RAW / TAW)")
    stress_deficit_mm: Optional[float] = Field(default=None, description="Depletion in excess of RAW: max(0, Dr - RAW) in mm")
    water_stress_coefficient_ks: Optional[float] = Field(default=None, description="FAO-56 water stress coefficient Ks in [0.0, 1.0]")
    standard_etc_mm: Optional[float] = Field(default=None, description="Standard crop evapotranspiration ETc in mm")
    adjusted_etc_mm: Optional[float] = Field(default=None, description="Water-stress adjusted crop evapotranspiration ETc,adj in mm")
    transpiration_reduction_pct: Optional[float] = Field(default=None, description="Relative transpiration reduction: (1.0 - Ks) * 100%")

    # Hydraulic reference capacities
    total_available_water_mm: Optional[float] = Field(default=None, description="Total available water TAW in mm")
    readily_available_water_mm: Optional[float] = Field(default=None, description="Readily available water RAW in mm")
    field_capacity_m3_m3: Optional[float] = Field(default=None, description="Volumetric moisture at Field Capacity")
    wilting_point_m3_m3: Optional[float] = Field(default=None, description="Volumetric moisture at Wilting Point")
    available_water_capacity_m3_m3: Optional[float] = Field(default=None, description="AWC = FC - WP")
    effective_rooting_depth_m: Optional[float] = Field(default=None, description="Effective rooting depth Zr in meters")

    # Discrete boundary states
    is_depletion_exceeding_raw: Optional[bool] = Field(default=None, description="Whether Dr > RAW (Ks < 1.0, active water stress)")
    is_approaching_raw: Optional[bool] = Field(default=None, description="Whether Dr >= 0.8 * RAW and Dr <= RAW (warning zone)")
    is_wilting_point_reached: Optional[bool] = Field(default=None, description="Whether Dr >= TAW (Ks = 0.0, severe water stress)")
    is_soil_at_or_above_fc: Optional[bool] = Field(default=None, description="Whether Dr <= 0.0 (soil at or wetter than Field Capacity)")

    # Measured vs Modelled Moisture distinction
    modelled_root_zone_moisture_m3_m3: Optional[float] = Field(
        default=None,
        description="Modelled volumetric moisture derived from daily water balance (m³/m³)"
    )
    measured_soil_moisture_m3_m3: Optional[float] = Field(
        default=None,
        description="In-situ sensor or laboratory measured volumetric moisture (m³/m³)"
    )
    measured_moisture_provenance: Optional[ProvenanceType] = Field(
        default=None,
        description="Provenance of in-situ soil moisture if measured"
    )
    measured_moisture_depth_cm: Optional[Tuple[float, float]] = Field(
        default=None,
        description="Depth range (min, max) in cm of in-situ moisture measurement"
    )

    # Provenance and quality
    is_provisional_empirical: bool = Field(default=False, description="Whether water balance relied on provisional empirical methods")
    quality_status: DataQualityStatus = Field(default=DataQualityStatus.GOOD, description="Quality status of water balance evidence")
    is_stale: bool = Field(default=False, description="Whether water balance evidence exceeds freshness threshold")
    audit_trail: List[str] = Field(default_factory=list, description="Step-by-step indicator audit notes")
    scientific_caveats: List[str] = Field(default_factory=list, description="Agronomic limitations and warnings")


def calculate_water_stress_indicators(
    water_balance: Optional[WaterBalanceResult],
    in_situ_soil_moisture: Optional[float] = None,
    moisture_provenance: Optional[ProvenanceType] = None,
    moisture_depth_cm: Optional[Tuple[float, float]] = None,
    freshness_config: FeatureFreshnessConfig = default_freshness_config,
    as_of_time: Optional[datetime] = None,
) -> WaterStressIndicators:
    """Extract interpretable water stress indicators from Phase 3 root-zone water balance.

    Preserves continuous Ks and depletion, identifies RAW and Wilting Point threshold crossings,
    and strictly separates modelled water-balance depletion from in-situ soil moisture measurements.
    """
    caveats = [
        "Water stress indicators are derived from deterministic FAO-56 daily water-balance accounting.",
        "Modelled root-zone depletion is an agronomic water-budget estimate and must not be presented as a physical field sensor reading.",
        "In-situ sensor readings, when available, reflect local sensor placement and depth; they are not inferred from satellite NDVI or NDMI.",
    ]

    # Handle missing or insufficient water balance
    if water_balance is None or water_balance.quality_status == DataQualityStatus.INSUFFICIENT or water_balance.final_depletion_mm is None:
        return WaterStressIndicators(
            measured_soil_moisture_m3_m3=in_situ_soil_moisture,
            measured_moisture_provenance=moisture_provenance,
            measured_moisture_depth_cm=moisture_depth_cm,
            quality_status=DataQualityStatus.INSUFFICIENT,
            audit_trail=[
                "Aborted: Water balance evidence is missing, incomplete, or marked INSUFFICIENT. "
                "Water stress cannot be evaluated without an initial soil moisture state and soil hydraulic properties."
            ],
            scientific_caveats=caveats,
        )

    audit: List[str] = []
    dr = water_balance.final_depletion_mm
    caps = water_balance.soil_capacities
    taw = caps.total_available_water_mm if caps else (water_balance.total_available_water_mm or 0.0)
    raw = caps.readily_available_water_mm if caps else (water_balance.readily_available_water_mm or 0.0)
    p_frac = caps.depletion_fraction_p if caps else (raw / taw if taw > 0 else 0.5)

    # Continuous metrics
    depletion_frac_taw = round(dr / taw, 4) if taw > 0 else None
    stress_deficit = round(max(0.0, dr - raw), 2)
    ks = water_balance.water_stress_coefficient_ks
    transpiration_red = round((1.0 - ks) * 100.0, 1)

    # Boundary states
    exceeds_raw = dr > raw
    approaching_raw = (dr >= 0.8 * raw) and (dr <= raw)
    wilting_point = dr >= taw
    at_or_above_fc = dr <= 0.0

    audit.append(f"Root-zone depletion Dr = {dr:.2f} mm (TAW = {taw:.2f} mm, RAW = {raw:.2f} mm).")
    audit.append(f"FAO-56 water stress coefficient Ks = {ks:.3f} (Transpiration reduction: {transpiration_red:.1f}%).")

    if wilting_point:
        audit.append(f"CRITICAL BOUNDARY: Depletion Dr ({dr:.2f} mm) >= TAW ({taw:.2f} mm). Permanent Wilting Point reached; plant transpiration ceases (Ks = 0.0).")
    elif exceeds_raw:
        audit.append(f"STRESS THRESHOLD CROSSED: Depletion Dr ({dr:.2f} mm) > RAW ({raw:.2f} mm). Soil water stress active; deficit = {stress_deficit:.2f} mm.")
    elif approaching_raw:
        audit.append(f"WARNING BOUNDARY: Depletion Dr ({dr:.2f} mm) is approaching RAW ({raw:.2f} mm) (Dr >= 80% RAW).")
    elif at_or_above_fc:
        audit.append(f"Soil is at or wetter than Field Capacity (Dr = {dr:.2f} mm <= 0.0 mm). No water stress (Ks = 1.0).")
    else:
        audit.append(f"Soil moisture is in the readily available range (Dr = {dr:.2f} mm <= RAW). No water stress (Ks = 1.0).")

    if in_situ_soil_moisture is not None:
        audit.append(
            f"Independent in-situ soil moisture sensor reading: {in_situ_soil_moisture:.3f} m³/m³ "
            f"(Provenance: {moisture_provenance.value if moisture_provenance else 'unknown'}, Depth: {moisture_depth_cm})."
        )

    return WaterStressIndicators(
        depletion_mm=round(dr, 2),
        depletion_fraction_taw=depletion_frac_taw,
        raw_depletion_fraction_p=round(p_frac, 3),
        stress_deficit_mm=stress_deficit,
        water_stress_coefficient_ks=round(ks, 3),
        standard_etc_mm=round(water_balance.crop_evapotranspiration_mm, 2),
        adjusted_etc_mm=round(water_balance.adjusted_crop_evapotranspiration_mm, 2),
        transpiration_reduction_pct=transpiration_red,
        total_available_water_mm=round(taw, 2),
        readily_available_water_mm=round(raw, 2),
        field_capacity_m3_m3=caps.field_capacity_m3_m3 if caps else None,
        wilting_point_m3_m3=caps.wilting_point_m3_m3 if caps else None,
        available_water_capacity_m3_m3=caps.available_water_capacity_m3_m3 if caps else None,
        effective_rooting_depth_m=caps.effective_rooting_depth_m if caps else None,
        is_depletion_exceeding_raw=exceeds_raw,
        is_approaching_raw=approaching_raw,
        is_wilting_point_reached=wilting_point,
        is_soil_at_or_above_fc=at_or_above_fc,
        modelled_root_zone_moisture_m3_m3=round(water_balance.root_zone_moisture_m3_m3, 4) if water_balance.root_zone_moisture_m3_m3 is not None else None,
        measured_soil_moisture_m3_m3=round(in_situ_soil_moisture, 4) if in_situ_soil_moisture is not None else None,
        measured_moisture_provenance=moisture_provenance,
        measured_moisture_depth_cm=moisture_depth_cm,
        is_provisional_empirical=water_balance.is_provisional_empirical,
        quality_status=water_balance.quality_status,
        audit_trail=audit,
        scientific_caveats=caveats,
    )


# ==============================================================================
# 2. VEGETATION STRESS INDICATORS
# ==============================================================================

class VegetationStressIndicators(BaseModel):
    """Interpretable vegetation stress indicators derived from Sentinel-2 optical features."""

    # Spectral Indices
    ndvi_mean: Optional[float] = Field(default=None, description="Zonal mean NDVI of valid vegetation pixels")
    ndvi_median: Optional[float] = Field(default=None, description="Zonal median NDVI of valid vegetation pixels")
    ndvi_std: Optional[float] = Field(default=None, description="Standard deviation of zonal NDVI")
    ndvi_p10: Optional[float] = Field(default=None, description="10th percentile NDVI")
    ndvi_p90: Optional[float] = Field(default=None, description="90th percentile NDVI")
    ndmi_median: Optional[float] = Field(default=None, description="Zonal median NDMI (canopy leaf-water indicator)")
    ndmi_mean: Optional[float] = Field(default=None, description="Zonal mean NDMI")

    # Coverage and Quality (Provisional Configurable Policies)
    vegetation_coverage_fraction: Optional[float] = Field(default=None, description="Fraction of zone classified as SCL 4 Vegetation")
    clear_observation_fraction: Optional[float] = Field(default=None, description="Fraction of zone clear of clouds and shadows")
    cloud_fraction: Optional[float] = Field(default=None, description="Fraction of zone obscured by clouds/cirrus (SCL 8, 9, 10)")
    cloud_shadow_fraction: Optional[float] = Field(default=None, description="Fraction of zone covered by cloud shadow (SCL Class 3)")
    cast_shadow_fraction: Optional[float] = Field(default=None, description="Fraction of zone covered by cast shadow / dark features (SCL Class 2)")
    scl_2_class_number: int = Field(default=2, description="Actual SCL class number (2)")
    scl_2_fraction: Optional[float] = Field(default=None, description="Fraction of zone occupied by SCL Class 2")
    scl_2_original_label: Optional[str] = Field(
        default=None,
        description="Official Copernicus PSD label for SCL Class 2: 'DARK_AREA_PIXELS' (< PB 04.00), 'DARK_FEATURES' (PB 04.00-05.10), 'CAST_SHADOW' (>= PB 05.11)"
    )
    scl_2_semantic_interpretation: Optional[str] = Field(
        default=None,
        description="Baseline-aware semantic interpretation: dark surface features / topographic shadow / cast shadow"
    )
    scl_class_2_label: Optional[str] = Field(
        default=None,
        description="Official Copernicus Sentinel-2 PSD nomenclature for SCL Class 2 based on processing baseline"
    )
    scl_3_class_number: int = Field(default=3, description="Actual SCL class number (3)")
    scl_3_fraction: Optional[float] = Field(default=None, description="Fraction of zone occupied by SCL Class 3 (exclusively cloud shadow)")
    scl_3_original_label: str = Field(default="CLOUD_SHADOW", description="Official Copernicus PSD label for SCL Class 3 (exclusively CLOUD_SHADOW)")
    scl_3_semantic_interpretation: str = Field(
        default="Cloud shadow cast on surface (exclusively cloud shadow; NOT cast/topographic shadow)",
        description="Semantic interpretation of SCL Class 3"
    )
    processing_baseline: Optional[str] = Field(
        default=None,
        description="ESA Processing Baseline (e.g. '02.14', '04.00', '05.11') preserved in diagnostics"
    )
    is_quality_threshold_provisional: bool = Field(default=True, description="Marks 60% clear and 20% cloud/shadow screening as provisional configurable policy, not official Sentinel-2 standard")

    # Baseline & Anomaly Interpretation
    has_valid_baseline: bool = Field(default=False, description="Whether a validated historical baseline was supplied")
    baseline_ndvi: Optional[float] = Field(default=None, description="Historical reference NDVI for this crop and stage")
    ndvi_anomaly: Optional[float] = Field(default=None, description="Deviation from baseline: NDVI_obs - NDVI_baseline")
    ndvi_anomaly_ratio: Optional[float] = Field(default=None, description="Ratio to baseline: NDVI_obs / NDVI_baseline")
    z_score: Optional[float] = Field(default=None, description="Standardized deviation: (NDVI - baseline_mean) / baseline_std when variance is documented")
    is_material_vegetation_decline: Optional[bool] = Field(
        default=None,
        description="Whether negative difference exceeds provisional operational threshold (e.g. <= -0.12 or ratio < 0.85)"
    )
    is_statistically_significant_anomaly: Optional[bool] = Field(
        default=None,
        description="Whether deviation achieves formal statistical significance under hypothesis test with adequate N and df (abs(t_stat) >= t_crit for two-sided; t_stat <= -t_crit for lower tail)"
    )
    is_statistically_significant_decline: Optional[bool] = Field(
        default=None,
        description="Whether negative deviation achieves formal statistical significance below baseline (t_stat <= -t_crit)"
    )
    statistical_test_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Formal statistical hypothesis testing metadata (H0, method, df, assumed distribution)"
    )
    is_canopy_anomaly_detected: Optional[bool] = Field(
        default=None,
        description="Material decline or threshold-exceeded canopy anomaly (retained for backward compatibility)"
    )
    material_decline_threshold: float = Field(default=-0.12, description="Provisional operational threshold for material NDVI drop")
    is_threshold_provisional: bool = Field(default=True, description="Marks -0.12 threshold as provisional operational policy, not a universal constant")

    # Multi-temporal endpoint rate (strictly NOT a trend)
    ndvi_change_rate_per_day: Optional[float] = Field(
        default=None,
        description="Two-observation endpoint change rate per day (strictly NOT a statistical trend)"
    )

    # Provenance and quality
    observed_at: Optional[datetime] = Field(default=None, description="Scene acquisition UTC timestamp")
    scene_id: Optional[str] = Field(default=None, description="Sentinel-2 scene identifier")
    quality_status: DataQualityStatus = Field(default=DataQualityStatus.GOOD, description="Satellite evidence quality")
    is_stale: bool = Field(default=False, description="Whether satellite observation exceeds freshness threshold")
    is_suspect: bool = Field(default=False, description="Whether SCL contamination or insufficient coverage marks observation as suspect")
    audit_trail: List[str] = Field(default_factory=list, description="Vegetation indicator audit log")
    scientific_caveats: List[str] = Field(default_factory=list, description="Vegetation index limitations and caveats")


def calculate_vegetation_stress_indicators(
    vegetation_features: Optional[ZoneVegetationFeatures],
    baseline: Optional[VegetationHistoricalBaseline] = None,
    crop_type: Optional[str] = None,
    growth_stage: Optional[str] = None,
    crop_stage: Optional[str] = None,
    hypothesis_test_convention: Optional[Union[HypothesisTestConvention, str]] = None,
    material_decline_threshold: float = -0.12,
    min_clear_observation_fraction: float = 0.60,
    max_cloud_shadow_fraction: float = 0.20,
    cloud_shadow_fraction: Optional[float] = None,
    cast_shadow_fraction: Optional[float] = None,
    processing_baseline: Optional[str] = None,
    freshness_config: FeatureFreshnessConfig = default_freshness_config,
    as_of_time: Optional[datetime] = None,
) -> VegetationStressIndicators:
    """Extract interpretable vegetation stress indicators from Phase 2 optical satellite features.

    Enforces that NDVI/NDMI are treated as canopy spectral indicators rather than direct soil moisture
    measurements, requires an explicit historical baseline with phenological matching for anomaly detection,
    distinguishes material decline from formal statistical significance, and screens for cloud vs cast shadow
    contamination with processing-baseline-aware SCL class resolution.
    """
    caveats = [
        "NDVI and NDMI are spectral greenness and canopy leaf-water indicators; they are NOT direct measurements of root-zone soil moisture.",
        "Vegetation indices reflect integrated crop health, canopy density, nutrient status, and atmospheric conditions; a decrease in NDVI is not an automatic drought diagnosis.",
        "Universal NDVI drought thresholds are scientifically invalid because baseline greenness varies by crop type, cultivar, planting density, and growth stage.",
        "A fixed NDVI difference (e.g. -0.12) represents a provisional operational threshold for material decline, NOT proof of statistical significance.",
        "Clear coverage (>= 60%) and cloud/shadow (<= 20%) screening thresholds are configurable application policies, not official Sentinel-2 mission standards.",
        "SCL Class 2 corresponds to DARK_AREA_PIXELS (pre-PB 04.00), DARK_FEATURES (PB 04.00-05.10), or CAST_SHADOW (PB 05.11+); it is NOT cloud shadow.",
        "SCL Class 3 corresponds to CLOUD_SHADOW; it is NOT cast or topographic shadow.",
        "Observations from different crop growth stages are not interchangeable; baseline comparison requires phenological alignment.",
        "Two-observation endpoint change rates represent interval rate of change and must NOT be interpreted as statistically established trends.",
    ]

    if vegetation_features is None:
        return VegetationStressIndicators(
            quality_status=DataQualityStatus.INSUFFICIENT,
            audit_trail=["Aborted: No satellite vegetation features supplied. Vegetation stress cannot be assessed."],
            scientific_caveats=caveats,
        )

    audit: List[str] = []
    audit.append(f"Evaluating Sentinel-2 scene {vegetation_features.scene_id} acquired at {vegetation_features.observed_at.isoformat()}.")

    # Resolve SCL Class 2 nomenclature based on processing baseline
    pb = processing_baseline or getattr(vegetation_features, "processing_baseline", None)
    if pb is None and vegetation_features.scene_id:
        match = re.search(r"_N(\d{2})(\d{2})_", vegetation_features.scene_id)
        if match:
            pb = f"{match.group(1)}.{match.group(2)}"

    scl_2_label, norm_pb, scl_2_sem = resolve_scl_class_2_semantics(pb)
    if norm_pb is not None:
        audit.append(
            f"Sentinel-2 SCL Processing Baseline: {norm_pb}. "
            f"Class 2 Nomenclature: '{scl_2_label}'. Semantic Interpretation: '{scl_2_sem}'. "
            "Class 3 Nomenclature: 'CLOUD_SHADOW' (exclusively cloud shadow; NOT cast/topographic shadow)."
        )
    else:
        audit.append(
            "Sentinel-2 SCL Processing Baseline: unavailable/unspecified. "
            f"Class 2 Nomenclature: '{scl_2_label}' (explicitly ambiguous legacy category). "
            f"Semantic Interpretation: '{scl_2_sem}'. "
            "Class 3 Nomenclature: 'CLOUD_SHADOW' (exclusively cloud shadow; NOT cast/topographic shadow)."
        )

    # Evaluate SCL contamination:
    # SCL 3 is strictly Cloud Shadow
    # SCL 2 is Cast Shadow / Dark Features / Dark Area Pixels
    clear_frac = getattr(vegetation_features, "valid_observation_fraction", None)
    if clear_frac is None:
        clear_frac = getattr(vegetation_features, "clear_observation_fraction", None)

    cloud_val = getattr(vegetation_features, "cloud_fraction", None) or 0.0
    cloud_shadow_val = (
        cloud_shadow_fraction
        if cloud_shadow_fraction is not None
        else getattr(vegetation_features, "scl_3_fraction", None)
        or getattr(vegetation_features, "scl_3_cloud_shadow_fraction", None)
        or getattr(vegetation_features, "shadow_fraction", None)
        or 0.0
    )
    cast_shadow_val = (
        cast_shadow_fraction
        if cast_shadow_fraction is not None
        else getattr(vegetation_features, "scl_2_fraction", None)
        or getattr(vegetation_features, "scl_2_cast_shadow_fraction", None)
        or getattr(vegetation_features, "cast_shadow_fraction", None)
        or 0.0
    )

    if cloud_shadow_val > 0.0 or cast_shadow_val > 0.0:
        audit.append(
            f"Shadow breakdown: SCL 2 ({scl_2_label}) = {cast_shadow_val:.2%}, "
            f"SCL 3 (CLOUD_SHADOW) = {cloud_shadow_val:.2%}."
        )

    # Total obscuring fraction: cloud + cloud shadow (SCL 3) + cast shadow / dark features (SCL 2)
    obscuring_frac = cloud_val + cloud_shadow_val + cast_shadow_val

    veg_cov = vegetation_features.vegetation_coverage_fraction
    is_suspect = False
    quality = vegetation_features.quality_status

    if obscuring_frac > max_cloud_shadow_fraction or (clear_frac is not None and clear_frac < min_clear_observation_fraction):
        is_suspect = True
        quality = DataQualityStatus.CLOUD_CONTAMINATED
        suppression_reason = (
            f"clear coverage ({clear_frac:.2%}) < configurable threshold ({min_clear_observation_fraction:.2%})"
            if clear_frac is not None and clear_frac < min_clear_observation_fraction
            else f"cloud/shadow obscuration ({obscuring_frac:.2%}) > configurable threshold ({max_cloud_shadow_fraction:.2%})"
        )
        audit.append(
            f"SCL CONTAMINATION WARNING (PROVISIONAL QUALITY SCREENING): Observation suppressed due to {suppression_reason}. "
            "Thresholds represent configurable application policy, not official Sentinel-2 mission standard."
        )
    elif veg_cov is not None and veg_cov < 0.10:
        is_suspect = True
        quality = DataQualityStatus.SUSPECT
        audit.append(
            f"LOW VEGETATION COVER WARNING: SCL Vegetation fraction ({veg_cov:.2f}) is below 10%. "
            "Canopy indices may reflect bare soil background rather than crop health."
        )

    # Evaluate Freshness
    now_utc = as_of_time or datetime.now(timezone.utc)
    obs_time = vegetation_features.observed_at
    if obs_time.tzinfo is None:
        obs_time = obs_time.replace(tzinfo=timezone.utc)
    age_days = (now_utc - obs_time).total_seconds() / 86400.0
    is_stale = age_days > freshness_config.satellite_stale_days
    if is_stale:
        audit.append(f"STALE EVIDENCE: Satellite scene is {age_days:.1f} days old (freshness policy: {freshness_config.satellite_stale_days:.1f} days).")
        if quality == DataQualityStatus.GOOD:
            quality = DataQualityStatus.STALE

    # Anomaly Detection vs Valid Historical Baseline with Phenological Alignment
    has_valid_baseline = False
    base_ndvi: Optional[float] = None
    ndvi_anomaly: Optional[float] = None
    ndvi_ratio: Optional[float] = None
    z_score_val: Optional[float] = None
    is_material_decline: Optional[bool] = None
    is_stat_sig: Optional[bool] = None
    is_stat_decline: Optional[bool] = None
    stat_details: Dict[str, Any] = {}

    if baseline is not None and baseline.is_valid:
        pheno_mismatch = False
        if crop_type is not None and baseline.crop_type is not None:
            if crop_type.strip().lower() != baseline.crop_type.strip().lower():
                pheno_mismatch = True
                audit.append(
                    f"CROP TYPE MISMATCH: Requested crop ('{crop_type}') does not match "
                    f"historical baseline crop ('{baseline.crop_type}'). Cross-crop baseline comparison rejected."
                )
        effective_stage = growth_stage or crop_stage
        if effective_stage is not None and baseline.growth_stage is not None:
            if effective_stage.strip().lower() != baseline.growth_stage.strip().lower():
                pheno_mismatch = True
                audit.append(
                    f"PHENOLOGICAL STAGE MISMATCH: Observed stage ('{effective_stage}') does not match "
                    f"baseline stage ('{baseline.growth_stage}'). Observations from different phenological stages "
                    "are not interchangeable; baseline comparison withheld."
                )

        if pheno_mismatch:
            has_valid_baseline = False
            audit.append("Historical baseline comparison aborted due to crop/stage mismatch.")
        elif vegetation_features.ndvi_median is not None:
            has_valid_baseline = True
            base_ndvi = baseline.baseline_ndvi
            diff = vegetation_features.ndvi_median - base_ndvi
            ndvi_anomaly = round(diff, 4)
            ndvi_ratio = round(vegetation_features.ndvi_median / base_ndvi, 4) if base_ndvi > 0 else None

            # Descriptive Standardized Anomaly (z-score)
            if baseline.baseline_std is not None and baseline.baseline_std > 0.0:
                z = diff / baseline.baseline_std
                z_score_val = round(z, 2)
            else:
                z_score_val = None

            n_samples = baseline.sample_size_years
            df = baseline.degrees_of_freedom or ((n_samples - 1) if n_samples is not None else None)

            # Determine hypothesis testing convention
            conv = hypothesis_test_convention or getattr(baseline, "hypothesis_test_convention", HypothesisTestConvention.TWO_SIDED)
            if isinstance(conv, str):
                conv = HypothesisTestConvention(conv)

            # Formal Student's t Prediction Interval for a single new observation:
            # - Sample standard deviation s is used when variance is estimated from historical records.
            # - Degrees of freedom equal N - 1.
            # - Standard error of prediction is s * sqrt(1 + 1/N).
            # - Selected alternative hypothesis is explicitly documented.
            # - One-sided lower tail alpha=0.05 uses the 0.95 t quantile (t_0.95).
            # - Two-sided alpha=0.05 uses the 0.975 t quantile (t_0.975).
            # - Operational sample size policy: N >= 10 is an operational policy to prevent
            #   excessive estimation error on s^2, not a universal mathematical theorem.
            # - If assumptions are not adequately supported, statistical significance remains None.
            if (
                baseline.is_statistically_robust
                and n_samples is not None
                and n_samples >= 10
                and baseline.baseline_std is not None
                and baseline.baseline_std > 0.0
                and df is not None
                and df >= 1
            ):
                s = baseline.baseline_std
                se_pred = s * math.sqrt(1.0 + 1.0 / n_samples)
                t_stat = diff / se_pred

                is_two_sided = (conv == HypothesisTestConvention.TWO_SIDED)
                t_crit = get_student_t_critical_value(df, alpha=0.05, two_sided=is_two_sided)

                if is_two_sided:
                    alt_hyp = "H1: Current canopy greenness deviates significantly from historical stage baseline (mu_new != mu_0, two-sided)"
                    quantile_str = "t_0.975"
                    is_stat_sig = (abs(t_stat) >= t_crit)
                    is_stat_decline = (t_stat <= -t_crit)
                else:
                    alt_hyp = "H1: Current canopy greenness is significantly depressed below historical stage baseline (mu_new < mu_0, one-sided lower tail)"
                    quantile_str = "t_0.95"
                    is_stat_sig = (t_stat <= -t_crit)
                    is_stat_decline = is_stat_sig

                stat_details = {
                    "null_hypothesis": "H0: Current canopy greenness is drawn from historical stage distribution (mu_new = mu_0)",
                    "alternative_hypothesis": alt_hyp,
                    "test_convention": conv.value,
                    "statistical_method": "Student's t prediction interval for new single observation",
                    "sample_size_N": n_samples,
                    "degrees_of_freedom": df,
                    "sample_standard_deviation_s": round(s, 4),
                    "prediction_standard_error_se": round(se_pred, 4),
                    "t_statistic": round(t_stat, 3),
                    "t_critical_alpha_0_05": round(t_crit, 3),
                    "quantile_used": quantile_str,
                    "alpha": 0.05,
                    "assumed_distribution": baseline.distribution_assumed,
                    "temporal_independence": "Annual inter-season observations at matched phenological stage",
                    "operational_minimum_sample_policy": (
                        "N >= 10 (df >= 9) operational threshold applied per project policy to mitigate "
                        "excessive sampling variance on s^2; this represents an operational risk-control policy, "
                        "not a universal mathematical theorem."
                    ),
                    "is_statistically_significant_anomaly": is_stat_sig,
                    "is_statistically_significant_decline": is_stat_decline,
                }

                if is_stat_sig:
                    if t_stat < 0.0:
                        audit.append(
                            f"STATISTICALLY SIGNIFICANT VEGETATION DECLINE CONFIRMED: Student's t = {t_stat:.3f} <= -{t_crit:.3f} "
                            f"({conv.value} alpha = 0.05 using {quantile_str} quantile, df = {df}, N = {n_samples}). "
                            f"Alternative hypothesis: '{alt_hyp}'. "
                            f"Prediction SE = s * sqrt(1 + 1/N) = {se_pred:.4f} (sample std s = {s:.4f}). "
                            f"Distributional assumption: {baseline.distribution_assumed}. "
                            "Temporal assumption: annual inter-cycle independence at matched phenological stage."
                        )
                    else:
                        audit.append(
                            f"STATISTICALLY SIGNIFICANT POSITIVE ANOMALY (CANOPY GREENING) DETECTED: Student's t = +{t_stat:.3f} >= +{t_crit:.3f} "
                            f"({conv.value} alpha = 0.05 using {quantile_str} quantile, df = {df}, N = {n_samples}). "
                            f"Alternative hypothesis: '{alt_hyp}'. "
                            f"Prediction SE = s * sqrt(1 + 1/N) = {se_pred:.4f} (sample std s = {s:.4f}). "
                            f"Distributional assumption: {baseline.distribution_assumed}. "
                            "Temporal assumption: annual inter-cycle independence at matched phenological stage."
                        )
                else:
                    audit.append(
                        f"Formal hypothesis test: vegetation anomaly not statistically significant "
                        f"(t = {t_stat:.3f}, critical bound = {t_crit:.3f}, {conv.value} alpha = 0.05 using {quantile_str}, df = {df})."
                    )
            else:
                is_stat_sig = None
                is_stat_decline = None
                if baseline.baseline_std is None or baseline.baseline_std <= 0.0:
                    audit.append(
                        "Statistical significance is NOT claimed: baseline lacks documented variance (std). "
                        "Standard deviation is required to scale deviation. Evaluating strictly as provisional material threshold decline."
                    )
                elif n_samples is not None and n_samples < 10:
                    audit.append(
                        f"DESCRIPTIVE STANDARDIZED ANOMALY ONLY (z = {z_score_val if z_score_val is not None else 'N/A'}): "
                        f"Formal statistical hypothesis testing suppressed due to small historical sample size (N = {n_samples} < 10, df = {df if df is not None else 'N/A'}). "
                        "Sample standard deviation from N < 10 has excessive sampling variance on s^2; claiming statistical significance from z <= -2 is scientifically invalid. "
                        "Note: N >= 10 is an operational minimum-sample policy to ensure robust variance estimation."
                    )
                else:
                    audit.append(
                        "Statistical significance is NOT claimed: baseline lacks documented variance (std) "
                        "or adequate historical sample size. Evaluating strictly as provisional material threshold decline."
                    )

            # Material Vegetation Decline Check (Configurable Operational Policy Threshold)
            if diff <= material_decline_threshold or (ndvi_ratio is not None and ndvi_ratio < 0.85):
                is_material_decline = True
                audit.append(
                    f"MATERIAL VEGETATION DECLINE DETECTED (CANOPY ANOMALY DETECTED): Observed median NDVI ({vegetation_features.ndvi_median:.3f}) "
                    f"deviates from historical baseline ({base_ndvi:.3f}) by {ndvi_anomaly:.3f} <= threshold ({material_decline_threshold:.2f}) "
                    f"(ratio: {ndvi_ratio:.2f}). Note: This represents an operational policy threshold, not a validated universal constant."
                )
            else:
                is_material_decline = False
                audit.append(
                    f"Vegetation greenness consistent with baseline: Observed median NDVI ({vegetation_features.ndvi_median:.3f}) "
                    f"vs baseline ({base_ndvi:.3f}), anomaly = {ndvi_anomaly:+.3f}."
                )
    else:
        audit.append(
            "No validated historical baseline provided for this crop/stage. Anomaly calculation is withheld (None). "
            "Universal drought thresholds are rejected per agronomic integrity rules."
        )

    rate_per_day = getattr(vegetation_features, "ndvi_change_rate_per_day", None)
    if rate_per_day is not None:
        audit.append(
            f"Multi-temporal two-observation change rate: {rate_per_day:+.4f}/day. "
            "(Interval rate of change; NOT a statistical trend)."
        )

    return VegetationStressIndicators(
        ndvi_mean=vegetation_features.ndvi_mean,
        ndvi_median=vegetation_features.ndvi_median,
        ndvi_std=vegetation_features.ndvi_std,
        ndvi_p10=vegetation_features.ndvi_p10,
        ndvi_p90=vegetation_features.ndvi_p90,
        ndmi_median=vegetation_features.ndmi_median,
        ndmi_mean=vegetation_features.ndmi_mean,
        vegetation_coverage_fraction=veg_cov,
        clear_observation_fraction=clear_frac,
        cloud_fraction=round(cloud_val, 4) if cloud_val > 0 else None,
        cloud_shadow_fraction=round(cloud_shadow_val, 4) if cloud_shadow_val > 0 else None,
        cast_shadow_fraction=round(cast_shadow_val, 4) if cast_shadow_val > 0 else None,
        scl_2_class_number=2,
        scl_2_fraction=round(cast_shadow_val, 4) if cast_shadow_val > 0 else None,
        scl_2_original_label=scl_2_label,
        scl_2_semantic_interpretation=scl_2_sem,
        scl_class_2_label=scl_2_label,
        scl_3_class_number=3,
        scl_3_fraction=round(cloud_shadow_val, 4) if cloud_shadow_val > 0 else None,
        scl_3_original_label="CLOUD_SHADOW",
        scl_3_semantic_interpretation="Cloud shadow cast on surface (exclusively cloud shadow; NOT cast/topographic shadow)",
        processing_baseline=norm_pb,
        is_quality_threshold_provisional=True,
        has_valid_baseline=has_valid_baseline,
        baseline_ndvi=base_ndvi,
        ndvi_anomaly=ndvi_anomaly,
        ndvi_anomaly_ratio=ndvi_ratio,
        z_score=z_score_val,
        is_material_vegetation_decline=is_material_decline,
        is_statistically_significant_anomaly=is_stat_sig,
        is_statistically_significant_decline=is_stat_decline,
        statistical_test_details=stat_details,
        is_canopy_anomaly_detected=is_material_decline,
        material_decline_threshold=material_decline_threshold,
        is_threshold_provisional=True,
        ndvi_change_rate_per_day=rate_per_day,
        observed_at=vegetation_features.observed_at,
        scene_id=vegetation_features.scene_id,
        quality_status=quality,
        is_stale=is_stale,
        is_suspect=is_suspect,
        audit_trail=audit,
        scientific_caveats=caveats,
    )


# ==============================================================================
# 3. WEATHER STRESS INDICATORS & VPD FORMULAE
# ==============================================================================

class VPDCalculationMethod(str, Enum):
    """Authoritative methodology for Vapour-Pressure Deficit (VPD) calculation."""
    PAIRED_INSTANTANEOUS = "PAIRED_INSTANTANEOUS"  # Simultaneous T and RH observation (psychrometric definition, FAO-56 Eq. 11)
    FAO56_RH_MAX_MIN = "FAO56_RH_MAX_MIN"          # Daily summary with Tmax, Tmin, RHmax, RHmin (FAO-56 Eq. 12, 17)
    FAO56_MEAN_RH_APPROX = "FAO56_MEAN_RH_APPROX"  # Daily summary with Tmax, Tmin, RHmean (FAO-56 Eq. 12, 19)
    DIURNAL_PROXY = "DIURNAL_PROXY"                # Peak demand proxy from Tmax and daily mean RH (provisional, non-simultaneous)


def calculate_saturation_vapor_pressure(temperature_c: float) -> float:
    """Calculate saturation vapour pressure e0(T) in kPa using Tetens formula (FAO-56 Eq. 11).

    Formula (FAO-56 Eq. 11):
        e0(T) = 0.6108 * exp((17.27 * T) / (T + 237.3))
    """
    return 0.6108 * math.exp((17.27 * temperature_c) / (temperature_c + 237.3))


def calculate_vapor_pressure_deficit_paired(
    temperature_c: float,
    relative_humidity_pct: float,
) -> Tuple[float, str]:
    """Calculate atmospheric VPD in kPa from simultaneous air temperature and relative humidity.

    Formula:
        e0(T) = 0.6108 * exp((17.27 * T) / (T + 237.3))  [FAO-56 Eq. 11]
        ea = e0(T) * (RH / 100.0)
        VPD = max(0.0, e0(T) - ea)
    Citation: FAO-56 Eq. 11 (Tetens psychrometric definition from simultaneous T and RH).
    """
    if relative_humidity_pct < 0.0 or relative_humidity_pct > 100.0:
        raise ValueError(f"Relative humidity must be in [0, 100], got {relative_humidity_pct}%")
    es = calculate_saturation_vapor_pressure(temperature_c)
    ea = es * (relative_humidity_pct / 100.0)
    vpd = max(0.0, es - ea)
    citation = CITATION_VPD_FAO56_PAIRED
    return round(vpd, 3), citation


def calculate_vapor_pressure_deficit_fao56_rh_max_min(
    t_max_c: float,
    t_min_c: float,
    rh_max_pct: float,
    rh_min_pct: float,
) -> Tuple[float, str]:
    """Calculate daily VPD in kPa from daily Tmax, Tmin, RHmax, RHmin (FAO-56 Eq. 12 & Eq. 17).

    Formula:
        es = (e0(Tmax) + e0(Tmin)) / 2  [FAO-56 Eq. 12]
        ea = (e0(Tmin) * (RHmax / 100) + e0(Tmax) * (RHmin / 100)) / 2  [FAO-56 Eq. 17]
        VPD = max(0.0, es - ea)
    Citation: FAO-56 Eq. 12 & Eq. 17 (Daily actual vapour pressure from RHmax and RHmin).
    """
    for rh_val, name in [(rh_max_pct, "RHmax"), (rh_min_pct, "RHmin")]:
        if rh_val < 0.0 or rh_val > 100.0:
            raise ValueError(f"{name} must be in [0, 100], got {rh_val}%")
    e0_max = calculate_saturation_vapor_pressure(t_max_c)
    e0_min = calculate_saturation_vapor_pressure(t_min_c)
    es = (e0_max + e0_min) / 2.0
    ea = (e0_min * (rh_max_pct / 100.0) + e0_max * (rh_min_pct / 100.0)) / 2.0
    vpd = max(0.0, es - ea)
    citation = CITATION_VPD_FAO56_RH_MAX_MIN
    return round(vpd, 3), citation


def calculate_vapor_pressure_deficit_fao56_mean_rh(
    t_max_c: float,
    t_min_c: float,
    rh_mean_pct: float,
) -> Tuple[float, str]:
    """Calculate daily VPD in kPa from daily Tmax, Tmin and RHmean (FAO-56 Eq. 12 & Eq. 19).

    Formula:
        es = (e0(Tmax) + e0(Tmin)) / 2  [FAO-56 Eq. 12]
        ea = es * (RHmean / 100)  [FAO-56 Eq. 19 approximation]
        VPD = max(0.0, es - ea) = es * (1 - RHmean / 100)
    Note: Does NOT cite or use Equation 17 because RHmax/RHmin are unavailable.
    Citation: FAO-56 Eq. 12 & Eq. 19 (Daily mean-RH approximation; does NOT cite Eq. 17).
    """
    if rh_mean_pct < 0.0 or rh_mean_pct > 100.0:
        raise ValueError(f"RHmean must be in [0, 100], got {rh_mean_pct}%")
    e0_max = calculate_saturation_vapor_pressure(t_max_c)
    e0_min = calculate_saturation_vapor_pressure(t_min_c)
    es = (e0_max + e0_min) / 2.0
    ea = es * (rh_mean_pct / 100.0)
    vpd = max(0.0, es - ea)
    citation = CITATION_VPD_FAO56_RH_MEAN
    return round(vpd, 3), citation


def calculate_vapor_pressure_deficit_diurnal_proxy(
    t_max_c: float,
    rh_mean_pct: float,
) -> Tuple[float, str]:
    """Calculate provisional midday peak VPD proxy from Tmax and daily mean RH.

    Formula:
        e0(Tmax) = 0.6108 * exp((17.27 * Tmax) / (Tmax + 237.3))  [FAO-56 Eq. 11]
        ea_est = e0(Tmax) * (RHmean / 100.0)
        VPD_proxy = max(0.0, e0(Tmax) - ea_est)
    Note: Tmax and RHmean are not simultaneous; represents a provisional operational proxy.
    Citation: Diurnal proxy estimation (provisional midday peak demand from Tmax and daily mean RH; non-simultaneous).
    """
    if rh_mean_pct < 0.0 or rh_mean_pct > 100.0:
        raise ValueError(f"RHmean must be in [0, 100], got {rh_mean_pct}%")
    es = calculate_saturation_vapor_pressure(t_max_c)
    ea = es * (rh_mean_pct / 100.0)
    vpd = max(0.0, es - ea)
    citation = CITATION_VPD_DIURNAL_PROXY
    return round(vpd, 3), citation


def calculate_vapor_pressure_deficit(
    temperature_c: float,
    relative_humidity_pct: float,
) -> float:
    """Calculate atmospheric Vapour-Pressure Deficit (VPD) in kPa using Tetens psychrometric formula (FAO-56 Eq. 11).

    Backward-compatible wrapper for calculate_vapor_pressure_deficit_paired.
    """
    vpd, _ = calculate_vapor_pressure_deficit_paired(temperature_c, relative_humidity_pct)
    return vpd


class WeatherStressIndicators(BaseModel):
    """Interpretable weather and atmospheric evaporative demand stress indicators."""

    temperature_max_c: Optional[float] = Field(default=None, description="Maximum air temperature in window (°C)")
    temperature_min_c: Optional[float] = Field(default=None, description="Minimum air temperature in window (°C)")
    temperature_mean_c: Optional[float] = Field(default=None, description="Mean air temperature in window (°C)")
    relative_humidity_mean_pct: Optional[float] = Field(default=None, description="Mean relative humidity (%)")

    vapor_pressure_deficit_kpa: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Atmospheric Vapour-Pressure Deficit (VPD) in kPa (FAO-56 psychrometric formula)"
    )
    vpd_calculation_method: Optional[VPDCalculationMethod] = Field(
        default=None,
        description="Exact method used for VPD calculation: PAIRED_INSTANTANEOUS, FAO56_RH_MAX_MIN, FAO56_MEAN_RH_APPROX, or DIURNAL_PROXY"
    )
    vpd_equation_citation: Optional[str] = Field(
        default=None,
        description="Authoritative equation citation for VPD calculation"
    )
    is_high_vpd_stress: Optional[bool] = Field(
        default=None,
        description="Whether atmospheric demand VPD exceeds operational warning threshold (e.g. > 2.2 kPa)"
    )
    is_vpd_provisional: bool = Field(
        default=True,
        description="Marks VPD threshold as provisional operational warning, not a universal crop damage threshold"
    )

    accumulated_precipitation_mm: Optional[float] = Field(default=None, description="Accumulated rainfall in window (mm)")
    consecutive_dry_days: Optional[int] = Field(default=None, ge=0, description="Count of consecutive days without significant rainfall")
    is_extended_dry_spell: Optional[bool] = Field(default=None, description="Whether extended dry spell condition is active")

    heat_exposure_hours: Optional[float] = Field(default=None, description="Cumulative hours above critical heat threshold in window")
    sustained_high_temp_days: Optional[int] = Field(default=None, description="Consecutive days where Tmax >= critical threshold")
    is_prolonged_heat_stress: Optional[bool] = Field(
        default=None,
        description="Whether sustained multi-day heat stress threshold is crossed"
    )
    is_heat_threshold_provisional: bool = Field(
        default=True,
        description="Marks heat threshold as provisional experimental baseline, not a universal production threshold"
    )
    source_cultivar: Optional[str] = Field(default=None, description="Cultivar or genotype tested in cited literature")
    experimental_conditions: Optional[str] = Field(default=None, description="Controlled growth chamber vs field conditions")

    is_frost_risk: Optional[bool] = Field(
        default=None,
        description="Whether minimum temperature indicates frost/chilling risk (<= 2.0 °C)"
    )

    window_type: Optional[WeatherWindowType] = Field(default=None, description="Weather evaluation window type")
    is_forecast: bool = Field(default=False, description="Whether weather evidence is forecast rather than observed")
    critical_temperature_threshold_c: Optional[float] = Field(default=None, description="Critical temperature threshold used")
    threshold_source: str = Field(default="FAO-56 / Agronomic Literature", description="Literature citation for thresholds")

    observed_at: Optional[datetime] = Field(default=None, description="Weather observation UTC timestamp")
    quality_status: DataQualityStatus = Field(default=DataQualityStatus.GOOD, description="Weather evidence quality")
    is_stale: bool = Field(default=False, description="Whether weather evidence exceeds freshness threshold")
    audit_trail: List[str] = Field(default_factory=list, description="Weather indicator audit notes")
    scientific_caveats: List[str] = Field(default_factory=list, description="Atmospheric indicator caveats")


def calculate_weather_stress_indicators(
    weather_features: Optional[WeatherFeatures],
    crop_stage_thresholds: Optional[CropStressThresholds] = None,
    consecutive_dry_days: Optional[int] = None,
    sustained_high_temp_days: Optional[int] = None,
    freshness_config: FeatureFreshnessConfig = default_freshness_config,
    as_of_time: Optional[datetime] = None,
) -> WeatherStressIndicators:
    """Extract interpretable atmospheric and meteorological stress indicators.

    Evaluates Vapour-Pressure Deficit (VPD) as an operational evaporative demand warning,
    prolonged heat stress (requiring sustained multi-day exposure), extended dry spells,
    and frost risk. Distinguishes elevated temperature from confirmed crop damage.
    """
    caveats = [
        "Atmospheric demand (VPD) and ambient temperature represent atmospheric drivers, not canopy temperature directly.",
        "A VPD threshold of 2.2 kPa is an operational high-atmospheric-demand warning indicating increased evaporative pull and physiological stomatal regulation, NOT a universal crop injury threshold.",
        "Crop heat thresholds (e.g. wheat 32°C, cotton 38°C) are provisional baselines derived from specific cultivar studies in controlled environments; they cannot be generalized as universal production thresholds without field calibration.",
        "Elevated temperature exposure does not equal confirmed crop damage; actual canopy temperature and transpirational cooling govern physiological outcome.",
        "Prolonged heat stress requires sustained multi-day exposure; single-hour peak readings do not constitute confirmed prolonged heat damage.",
        "Weather observations must be distinguished between historical reanalysis/sensors and NWP forecasts.",
    ]

    if weather_features is None:
        return WeatherStressIndicators(
            quality_status=DataQualityStatus.INSUFFICIENT,
            audit_trail=["Aborted: No meteorological feature evidence supplied."],
            scientific_caveats=caveats,
        )

    audit: List[str] = []
    t_max = weather_features.temperature_max_c
    t_min = weather_features.temperature_min_c
    t_mean = weather_features.temperature_mean_c
    rh_mean = weather_features.relative_humidity_mean_pct
    precip = weather_features.precipitation_mm

    # Freshness evaluation
    now_utc = as_of_time or datetime.now(timezone.utc)
    obs_time = weather_features.observed_at
    if obs_time.tzinfo is None:
        obs_time = obs_time.replace(tzinfo=timezone.utc)
    age_hours = (now_utc - obs_time).total_seconds() / 3600.0
    is_stale = age_hours > freshness_config.weather_stale_hours
    quality = weather_features.quality_status
    if is_stale:
        audit.append(f"STALE EVIDENCE: Weather data is {age_hours:.1f} hours old (threshold: {freshness_config.weather_stale_hours:.1f} h).")
        if quality == DataQualityStatus.GOOD:
            quality = DataQualityStatus.STALE

    # Establish documented thresholds
    source_cv: Optional[str] = None
    exp_cond: Optional[str] = None
    if crop_stage_thresholds is not None:
        t_crit = crop_stage_thresholds.critical_temperature_max_c
        vpd_crit = crop_stage_thresholds.critical_vpd_kpa
        frost_crit = crop_stage_thresholds.frost_threshold_c
        min_heat_days = crop_stage_thresholds.critical_heat_duration_days
        source_cv = crop_stage_thresholds.source_cultivar
        exp_cond = crop_stage_thresholds.experimental_conditions
        thresh_src = f"{crop_stage_thresholds.crop_type} ({crop_stage_thresholds.growth_stage or 'all stages'}): {crop_stage_thresholds.threshold_source}"
    else:
        t_crit = 35.0  # Conservative general agronomic threshold
        vpd_crit = 2.2  # FAO-56 / Grossiord et al. 2020 operational warning
        frost_crit = 2.0
        min_heat_days = 2
        thresh_src = f"Conservative Agronomic Default ({CITATION_HEAT_STRESS_WHEAT}; {CITATION_VPD_DEMAND})"

    # 1. Vapour-Pressure Deficit (VPD)
    vpd: Optional[float] = None
    vpd_method: Optional[VPDCalculationMethod] = None
    vpd_citation: Optional[str] = None
    is_high_vpd: Optional[bool] = None

    rh_max = getattr(weather_features, "relative_humidity_max_pct", None)
    rh_min = getattr(weather_features, "relative_humidity_min_pct", None)

    if t_max is not None and t_min is not None and rh_max is not None and rh_min is not None:
        vpd, vpd_citation = calculate_vapor_pressure_deficit_fao56_rh_max_min(t_max, t_min, rh_max, rh_min)
        vpd_method = VPDCalculationMethod.FAO56_RH_MAX_MIN
        audit.append(
            f"Calculated daily VPD = {vpd:.2f} kPa via FAO-56 Eq. 12 & Eq. 17 using Tmax ({t_max:.1f}°C), "
            f"Tmin ({t_min:.1f}°C), RHmax ({rh_max:.1f}%), RHmin ({rh_min:.1f}%)."
        )
    elif t_max is not None and t_min is not None and rh_mean is not None:
        vpd, vpd_citation = calculate_vapor_pressure_deficit_fao56_mean_rh(t_max, t_min, rh_mean)
        vpd_method = VPDCalculationMethod.FAO56_MEAN_RH_APPROX
        audit.append(
            f"Calculated daily VPD = {vpd:.2f} kPa via FAO-56 Eq. 12 & Eq. 19 (Mean-RH approximation; does NOT cite Eq. 17) "
            f"using Tmax ({t_max:.1f}°C), Tmin ({t_min:.1f}°C), RHmean ({rh_mean:.1f}%)."
        )
    elif t_mean is not None and rh_mean is not None:
        vpd, vpd_citation = calculate_vapor_pressure_deficit_paired(t_mean, rh_mean)
        vpd_method = VPDCalculationMethod.PAIRED_INSTANTANEOUS
        audit.append(
            f"Calculated atmospheric VPD = {vpd:.2f} kPa via FAO-56 Eq. 11 psychrometric formula "
            f"from simultaneous mean T ({t_mean:.1f}°C) and RH ({rh_mean:.1f}%)."
        )
    elif t_max is not None and rh_mean is not None:
        vpd, vpd_citation = calculate_vapor_pressure_deficit_diurnal_proxy(t_max, rh_mean)
        vpd_method = VPDCalculationMethod.DIURNAL_PROXY
        audit.append(
            f"Estimated peak daytime atmospheric VPD = {vpd:.2f} kPa via diurnal proxy from Tmax ({t_max:.1f}°C) "
            f"and daily mean RH ({rh_mean:.1f}%). (Provisional midday proxy; non-simultaneous)."
        )

    if vpd is not None:
        is_high_vpd = vpd >= vpd_crit
        if is_high_vpd:
            audit.append(
                f"HIGH ATMOSPHERIC DEMAND WARNING: Atmospheric VPD ({vpd:.2f} kPa) >= operational warning threshold ({vpd_crit:.2f} kPa). "
                "Represents elevated evaporative demand and physiological stomatal regulation, NOT a universal crop damage threshold."
            )

    # 2. Prolonged Heat Stress vs Instantaneous Reading
    is_prolonged_heat = False
    window_type = weather_features.window_type
    is_forecast = (window_type == WeatherWindowType.FORECAST_WINDOW)

    if t_max is not None:
        if t_max >= t_crit:
            if sustained_high_temp_days is not None and sustained_high_temp_days >= min_heat_days:
                is_prolonged_heat = True
                audit.append(
                    f"PROLONGED HEAT STRESS CONFIRMED: Daily Tmax ({t_max:.1f}°C) has exceeded provisional threshold {t_crit:.1f}°C "
                    f"for {sustained_high_temp_days} consecutive days (required: >={min_heat_days} days). "
                    f"Source: {thresh_src} (Cultivar: {source_cv or 'unspecified'}, Condition: {exp_cond or 'provisional baseline'}). "
                    "Note: Confirmed exposure does not guarantee crop damage if canopy transpirational cooling is maintained."
                )
            elif window_type in (WeatherWindowType.WINDOW_48H, WeatherWindowType.WINDOW_7D) and t_mean is not None and t_mean >= 30.0:
                is_prolonged_heat = True
                audit.append(
                    f"PROLONGED HEAT EXPOSURE CONFIRMED: Multi-day window ({window_type.value}) exhibits sustained high mean temp ({t_mean:.1f}°C) "
                    f"and peak Tmax ({t_max:.1f}°C >= provisional threshold {t_crit:.1f}°C)."
                )
            else:
                is_prolonged_heat = False
                audit.append(
                    f"ELEVATED TEMPERATURE DETECTED: Elevated temperature exposure: Tmax reached {t_max:.1f}°C (provisional threshold: {t_crit:.1f}°C), "
                    "but sustained multi-day duration threshold is not confirmed. An isolated single peak does not constitute prolonged heat stress."
                )
        else:
            is_prolonged_heat = False
            audit.append(f"Maximum temperature ({t_max:.1f}°C) is below critical threshold ({t_crit:.1f}°C).")

    # 3. Frost / Chilling Hazard
    is_frost = False
    if t_min is not None:
        if t_min <= frost_crit:
            is_frost = True
            audit.append(f"FROST/CHILLING RISK: Minimum temperature ({t_min:.1f}°C) <= frost threshold ({frost_crit:.1f}°C).")

    # 4. Extended Dry Spell
    is_dry_spell = False
    if consecutive_dry_days is not None:
        if consecutive_dry_days >= 7 and (precip is None or precip < 2.0):
            is_dry_spell = True
            audit.append(f"EXTENDED DRY SPELL: {consecutive_dry_days} consecutive dry days with minimal precipitation ({precip or 0.0:.1f} mm).")
    elif window_type == WeatherWindowType.WINDOW_7D and precip is not None and precip < 2.0:
        is_dry_spell = True
        audit.append(f"EXTENDED DRY SPELL: 7-day precipitation is negligible ({precip:.1f} mm).")

    return WeatherStressIndicators(
        temperature_max_c=t_max,
        temperature_min_c=t_min,
        temperature_mean_c=t_mean,
        relative_humidity_mean_pct=rh_mean,
        vapor_pressure_deficit_kpa=vpd,
        vpd_calculation_method=vpd_method,
        vpd_equation_citation=vpd_citation,
        is_high_vpd_stress=is_high_vpd,
        is_vpd_provisional=True,
        accumulated_precipitation_mm=precip,
        consecutive_dry_days=consecutive_dry_days,
        is_extended_dry_spell=is_dry_spell,
        sustained_high_temp_days=sustained_high_temp_days,
        is_prolonged_heat_stress=is_prolonged_heat,
        is_heat_threshold_provisional=True,
        source_cultivar=source_cv,
        experimental_conditions=exp_cond,
        is_frost_risk=is_frost,
        window_type=window_type,
        is_forecast=is_forecast,
        critical_temperature_threshold_c=t_crit,
        threshold_source=thresh_src,
        observed_at=weather_features.observed_at,
        quality_status=quality,
        is_stale=is_stale,
        audit_trail=audit,
        scientific_caveats=caveats,
    )


# ==============================================================================
# 4. SOIL CONDITION INDICATORS
# ==============================================================================

class SoilConditionIndicators(BaseModel):
    """Interpretable soil condition, salinity, and hydraulic limitation indicators."""

    soil_moisture_m3_m3: Optional[float] = Field(default=None, description="In-situ measured volumetric soil moisture (m³/m³)")
    moisture_depth_min_cm: Optional[float] = Field(default=None, description="Top measurement depth (cm)")
    moisture_depth_max_cm: Optional[float] = Field(default=None, description="Bottom measurement depth (cm)")
    moisture_sensor_type: Optional[str] = Field(default=None, description="In-situ sensor technology (capacitance, TDR, etc.)")
    moisture_provenance: Optional[ProvenanceType] = Field(default=None, description="Provenance of moisture measurement")

    electrical_conductivity_ds_m: Optional[float] = Field(default=None, ge=0.0, description="Soil electrical conductivity (dS/m)")
    ec_method: Optional[str] = Field(default=None, description="Analytical extraction method for EC (e.g. saturated_paste_extract_ECe, 1:5_extract)")
    salinity_hazard_level: Optional[str] = Field(
        default=None,
        description="General soil salinity classification: 'none', 'slight', 'moderate', 'severe' (USDA Handbook 60, not universal crop injury)"
    )
    is_salinity_stress: Optional[bool] = Field(default=None, description="Whether soil salinity poses general or crop-specific hazard")
    crop_salinity_tolerance_ece: Optional[float] = Field(default=None, description="Documented crop-specific ECe threshold if supplied")

    soil_ph: Optional[float] = Field(default=None, ge=3.0, le=11.0, description="Soil pH in water suspension")
    ph_method: Optional[str] = Field(default=None, description="Analytical pH method (e.g. 1:2.5_water, 1:5_water)")
    ph_classification: Optional[str] = Field(
        default=None,
        description="Soil reaction classification: 'strongly_acidic', 'moderately_acidic', 'neutral_optimal', 'moderately_alkaline', 'strongly_alkaline'"
    )
    is_ph_stress: Optional[bool] = Field(default=None, description="Whether soil pH falls outside optimal crop growth range")

    # Sodicity Evidence (Kept strictly distinct from pH/Alkalinity)
    sodium_adsorption_ratio_sar: Optional[float] = Field(default=None, ge=0.0, description="Sodium Adsorption Ratio SAR")
    exchangeable_sodium_pct_esp: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="Exchangeable Sodium Percentage ESP (%)")
    is_sodic_hazard: Optional[bool] = Field(
        default=None,
        description="Whether soil exhibits confirmed sodic hazard (SAR >= 13 or ESP >= 15%). Strictly None if sodium evidence is missing."
    )

    available_water_capacity_m3_m3: Optional[float] = Field(default=None, description="Available Water Capacity AWC (m³/m³)")
    has_low_water_storage_capacity: Optional[bool] = Field(
        default=None,
        description="Available Water Capacity AWC < 0.08 m³/m³ indicates a low soil water-storage constraint, NOT proof of active water stress."
    )
    has_low_awc_limitation: Optional[bool] = Field(
        default=None,
        description="Retained for backward compatibility: identical to has_low_water_storage_capacity."
    )
    hydraulic_limitations: List[str] = Field(default_factory=list, description="Identified hydraulic constraints")

    quality_status: DataQualityStatus = Field(default=DataQualityStatus.GOOD, description="Soil evidence quality")
    is_stale: bool = Field(default=False, description="Whether soil observation exceeds freshness policy")
    audit_trail: List[str] = Field(default_factory=list, description="Soil indicator audit log")
    scientific_caveats: List[str] = Field(default_factory=list, description="Soil indicator caveats")


def calculate_soil_condition_indicators(
    soil_features: Optional[SoilFeatures],
    sodium_adsorption_ratio_sar: Optional[float] = None,
    exchangeable_sodium_pct_esp: Optional[float] = None,
    crop_salinity_tolerance_ece: Optional[float] = None,
    freshness_config: FeatureFreshnessConfig = default_freshness_config,
    as_of_time: Optional[datetime] = None,
) -> SoilConditionIndicators:
    """Extract interpretable soil condition, salinity, pH, sodicity, and hydraulic indicators.

    Strictly preserves laboratory extraction method provenance (e.g. ECe saturated paste vs 1:5 extract),
    distinguishes general salinity from crop-specific injury thresholds, separates alkalinity (pH) from
    sodicity (SAR/ESP), and documents low AWC as a storage constraint rather than proof of active water stress.
    """
    caveats = [
        "Soil electrical conductivity (EC) extraction methods are NOT directly interchangeable: EC1:5 values cannot be directly compared to standard ECe saturated paste thresholds without texture-specific conversion.",
        "An ECe >= 4.0 dS/m indicates a general soil salinity classification (USDA Handbook 60), NOT a universal crop injury threshold. Crop-specific tolerance varies widely.",
        "High soil pH (> 8.5) indicates strong alkalinity but does NOT diagnose sodicity; sodicity requires independent chemical evidence (SAR >= 13 or ESP >= 15%).",
        "Available Water Capacity (AWC < 0.08 m³/m³) indicates low soil water-storage capacity, NOT proof of active water stress. Soil texture cannot be inferred from AWC alone.",
        "Soil salinity and reaction (pH) represent physicochemical and osmotic soil health properties, distinct from hydraulic root-zone water depletion.",
        "Missing soil measurements MUST remain None and not be populated with synthetic regional defaults.",
    ]

    if soil_features is None:
        return SoilConditionIndicators(
            quality_status=DataQualityStatus.INSUFFICIENT,
            audit_trail=["Aborted: No soil feature evidence supplied."],
            scientific_caveats=caveats,
        )

    audit: List[str] = []
    hydraulic_limits: List[str] = []

    # 1. Freshness check
    now_utc = as_of_time or datetime.now(timezone.utc)
    obs_time = soil_features.observed_at
    if obs_time.tzinfo is None:
        obs_time = obs_time.replace(tzinfo=timezone.utc)
    age_days = (now_utc - obs_time).total_seconds() / 86400.0

    # Differentiate static (pH, EC, texture) from dynamic soil moisture freshness
    is_stale = False
    if soil_features.soil_moisture_m3_m3 is not None:
        is_stale = age_days > freshness_config.dynamic_soil_moisture_stale_days
    else:
        is_stale = age_days > freshness_config.static_soil_stale_days

    quality = soil_features.quality_status
    if is_stale:
        audit.append(f"STALE EVIDENCE: Soil record is {age_days:.1f} days old.")
        if quality == DataQualityStatus.GOOD:
            quality = DataQualityStatus.STALE

    # 2. Electrical Conductivity (Salinity) & Method Provenance
    ec = soil_features.electrical_conductivity_ds_m
    ec_method = (soil_features.ec_method or "").lower()
    salinity_hazard: Optional[str] = None
    is_salinity_stress: Optional[bool] = None

    if ec is not None:
        # Check extraction method provenance
        is_paste_ece = any(term in ec_method for term in ["paste", "ece", "saturated"])
        is_dilute_extract = any(term in ec_method for term in ["1:5", "1:2.5"])

        if is_paste_ece:
            # Standard USDA Handbook 60 / FAO-39 ECe general classifications
            if ec < 2.0:
                salinity_hazard = "none"
                is_salinity_stress = False
                audit.append(f"Soil ECe = {ec:.2f} dS/m (saturated paste): Non-saline; negligible crop impact.")
            elif ec < 4.0:
                salinity_hazard = "slight"
                is_salinity_stress = True
                audit.append(f"Soil ECe = {ec:.2f} dS/m (saturated paste): Slightly saline; sensitive crops may experience slight yield restriction.")
            elif ec < 8.0:
                salinity_hazard = "moderate"
                is_salinity_stress = True
                audit.append(f"Soil ECe = {ec:.2f} dS/m (saturated paste): Moderately saline (USDA Handbook 60 general classification). Crop injury depends on specific crop tolerance.")
            else:
                salinity_hazard = "severe"
                is_salinity_stress = True
                audit.append(f"Soil ECe = {ec:.2f} dS/m (saturated paste): Severely saline; only highly tolerant crops produce satisfactory yields.")

            # Crop-specific tolerance evaluation if configured
            if crop_salinity_tolerance_ece is not None:
                if ec >= crop_salinity_tolerance_ece:
                    is_salinity_stress = True
                    audit.append(
                        f"CROP-SPECIFIC SALINITY HAZARD: ECe ({ec:.2f} dS/m) exceeds documented crop tolerance ({crop_salinity_tolerance_ece:.2f} dS/m)."
                    )
                else:
                    audit.append(
                        f"Crop-specific salinity check: ECe ({ec:.2f} dS/m) is within documented crop tolerance ({crop_salinity_tolerance_ece:.2f} dS/m)."
                    )
        elif is_dilute_extract:
            salinity_hazard = None
            is_salinity_stress = None
            audit.append(
                f"METHOD PROVENANCE RESTRICTION: EC reported as {ec:.2f} dS/m via dilute extract ({soil_features.ec_method}). "
                "Dilute 1:5 or 1:2.5 extract EC CANNOT be directly compared against FAO/USDA ECe thresholds without soil-texture conversion. "
                "Salinity hazard classification is withheld."
            )
        else:
            salinity_hazard = None
            is_salinity_stress = None
            audit.append(
                f"EC reported as {ec:.2f} dS/m with unconfirmed method ({soil_features.ec_method}). "
                "Standard ECe thresholds cannot be safely applied."
            )
    else:
        audit.append("No soil electrical conductivity (EC) measurement provided.")

    # 3. Soil pH (Acidity / Alkalinity) & Sodicity Separation
    ph = soil_features.soil_ph
    ph_class: Optional[str] = None
    is_ph_stress: Optional[bool] = None

    if ph is not None:
        if ph < 5.5:
            ph_class = "strongly_acidic"
            is_ph_stress = True
            audit.append(f"Soil pH = {ph:.2f}: Strongly acidic (risk of aluminum/manganese toxicity, reduced P availability).")
        elif ph < 6.5:
            ph_class = "moderately_acidic"
            is_ph_stress = False
            audit.append(f"Soil pH = {ph:.2f}: Moderately acidic; acceptable for most field crops.")
        elif ph <= 7.8:
            ph_class = "neutral_optimal"
            is_ph_stress = False
            audit.append(f"Soil pH = {ph:.2f}: Neutral to optimal range for nutrient availability.")
        elif ph <= 8.5:
            ph_class = "moderately_alkaline"
            is_ph_stress = False
            audit.append(f"Soil pH = {ph:.2f}: Moderately alkaline; calcareous soil, potential micronutrient (Fe/Zn) tie-up.")
        else:
            ph_class = "strongly_alkaline"
            is_ph_stress = True
            audit.append(
                f"Soil pH = {ph:.2f}: Strongly alkaline / high pH hazard (potential micronutrient tie-up and carbonate dominance). "
                "Note: Sodicity is NOT diagnosed from pH alone; independent SAR or ESP evidence is required."
            )
    else:
        audit.append("No soil pH measurement provided.")

    # 4. Sodicity Evaluation (SAR / ESP)
    sar = sodium_adsorption_ratio_sar if sodium_adsorption_ratio_sar is not None else getattr(soil_features, "sodium_adsorption_ratio_sar", None)
    esp = exchangeable_sodium_pct_esp if exchangeable_sodium_pct_esp is not None else getattr(soil_features, "exchangeable_sodium_pct_esp", None)
    is_sodic: Optional[bool] = None

    if sar is not None and sar >= 13.0:
        is_sodic = True
        audit.append(f"SODIC HAZARD CONFIRMED: Sodium Adsorption Ratio SAR = {sar:.1f} >= 13.0 (USDA Handbook 60). Structural dispersion risk.")
    elif esp is not None and esp >= 15.0:
        is_sodic = True
        audit.append(f"SODIC HAZARD CONFIRMED: Exchangeable Sodium Percentage ESP = {esp:.1f}% >= 15.0% (USDA Handbook 60). Structural dispersion risk.")
    elif sar is not None or esp is not None:
        is_sodic = False
        audit.append(f"No sodic hazard detected from sodium analysis (SAR = {sar}, ESP = {esp}%).")
    else:
        is_sodic = None
        audit.append("Sodicity is unassessed: no SAR or ESP measurement provided. High pH alone does NOT constitute a diagnosis of sodicity.")

    # 5. Hydraulic & Storage Limitations
    awc = soil_features.available_water_capacity_m3_m3
    low_storage = False
    if awc is not None:
        if awc < 0.08:
            low_storage = True
            hydraulic_limits.append(f"Low Available Water Capacity constraint: low soil water-storage capacity (AWC = {awc:.3f} m³/m³ < 0.08).")
            audit.append(
                f"Soil constraint: Low water-storage capacity (AWC = {awc:.3f} m³/m³ < 0.08). "
                "Note: This represents a physical water-storage capacity limitation, NOT proof of active water stress. "
                "Soil texture cannot be inferred from AWC alone (requires particle size analysis)."
            )
        else:
            audit.append(f"Soil Available Water Capacity AWC = {awc:.3f} m³/m³ (Adequate water storage capacity).")

    return SoilConditionIndicators(
        soil_moisture_m3_m3=soil_features.soil_moisture_m3_m3,
        moisture_depth_min_cm=soil_features.depth_min_cm,
        moisture_depth_max_cm=soil_features.depth_max_cm,
        moisture_sensor_type=soil_features.moisture_sensor_type,
        moisture_provenance=soil_features.provenance_type,
        electrical_conductivity_ds_m=ec,
        ec_method=soil_features.ec_method,
        salinity_hazard_level=salinity_hazard,
        is_salinity_stress=is_salinity_stress,
        crop_salinity_tolerance_ece=crop_salinity_tolerance_ece,
        soil_ph=ph,
        ph_method=soil_features.ph_method,
        ph_classification=ph_class,
        is_ph_stress=is_ph_stress,
        sodium_adsorption_ratio_sar=sar,
        exchangeable_sodium_pct_esp=esp,
        is_sodic_hazard=is_sodic,
        available_water_capacity_m3_m3=awc,
        has_low_water_storage_capacity=low_storage,
        has_low_awc_limitation=low_storage,
        hydraulic_limitations=hydraulic_limits,
        quality_status=quality,
        is_stale=is_stale,
        audit_trail=audit,
        scientific_caveats=caveats,
    )
