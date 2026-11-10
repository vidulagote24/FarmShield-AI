"""Deterministic domain-level stress evaluation and reason-code scoring.

Evaluates independent stress dimensions across water, vegetation, weather,
and soil domains without forcing them into an arbitrary composite numerical score.

Scientific and Agronomic Restrictions (per AGENTS.md, AI_SPEC.md):
- Independent stress dimensions MUST remain visible; do not force all domains
  into a single composite index that obscures which factor is driving stress.
- A zone with insufficient evidence in one domain MUST NOT automatically be
  classified as healthy.
- Continuous severity metrics (such as 1.0 - Ks for water stress) must be
  preserved alongside categorical statuses.
- Reason codes must be stable, machine-readable, and traceable to explicit inputs.
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from backend.app.intelligence.stress.indicators import (
    SoilConditionIndicators,
    VegetationStressIndicators,
    WaterStressIndicators,
    WeatherStressIndicators,
)
from backend.app.intelligence.types import DataQualityStatus, StressStatus


class StressReasonCode(str, Enum):
    """Stable, machine-readable reason codes explaining zone stress assessments."""

    # Water Domain Reason Codes
    WATER_DEPLETION_NORMAL = "WATER_DEPLETION_NORMAL"
    WATER_DEPLETION_APPROACHING_RAW = "WATER_DEPLETION_APPROACHING_RAW"
    WATER_DEPLETION_EXCEEDS_RAW = "WATER_DEPLETION_EXCEEDS_RAW"
    SEVERE_DEPLETION_AT_WILTING_POINT = "SEVERE_DEPLETION_AT_WILTING_POINT"
    WATER_STRESS_KS_REDUCED = "WATER_STRESS_KS_REDUCED"
    WATER_BALANCE_INSUFFICIENT = "WATER_BALANCE_INSUFFICIENT"
    WATER_BALANCE_STALE = "WATER_BALANCE_STALE"

    # Vegetation Domain Reason Codes
    VEGETATION_CANOPY_HEALTHY = "VEGETATION_CANOPY_HEALTHY"
    VEGETATION_ANOMALY_NEGATIVE = "VEGETATION_ANOMALY_NEGATIVE"
    VEGETATION_ANOMALY_POSITIVE = "VEGETATION_ANOMALY_POSITIVE"
    VEGETATION_MATERIAL_DECLINE = "VEGETATION_MATERIAL_DECLINE"
    VEGETATION_STATISTICAL_ANOMALY = "VEGETATION_STATISTICAL_ANOMALY"
    VEGETATION_STATISTICAL_DECLINE = "VEGETATION_STATISTICAL_DECLINE"
    VEGETATION_MOISTURE_INDEX_LOW = "VEGETATION_MOISTURE_INDEX_LOW"
    VEGETATION_BASELINE_MISSING = "VEGETATION_BASELINE_MISSING"
    VEGETATION_PHENOLOGY_MISMATCH = "VEGETATION_PHENOLOGY_MISMATCH"
    VEGETATION_SCL_CONTAMINATED = "VEGETATION_SCL_CONTAMINATED"
    VEGETATION_CLOUD_SHADOW_CONTAMINATED = "VEGETATION_CLOUD_SHADOW_CONTAMINATED"
    VEGETATION_CAST_SHADOW_CONTAMINATED = "VEGETATION_CAST_SHADOW_CONTAMINATED"
    VEGETATION_COVERAGE_INSUFFICIENT = "VEGETATION_COVERAGE_INSUFFICIENT"
    VEGETATION_EVIDENCE_STALE = "VEGETATION_EVIDENCE_STALE"
    VEGETATION_EVIDENCE_INSUFFICIENT = "VEGETATION_EVIDENCE_INSUFFICIENT"

    # Weather Domain Reason Codes
    WEATHER_CONDITIONS_FAVORABLE = "WEATHER_CONDITIONS_FAVORABLE"
    WEATHER_HEAT_STRESS_PROLONGED = "WEATHER_HEAT_STRESS_PROLONGED"
    WEATHER_HIGH_VAPOR_PRESSURE_DEFICIT = "WEATHER_HIGH_VAPOR_PRESSURE_DEFICIT"
    WEATHER_EXTENDED_DRY_SPELL = "WEATHER_EXTENDED_DRY_SPELL"
    WEATHER_FROST_RISK = "WEATHER_FROST_RISK"
    WEATHER_EVIDENCE_INSUFFICIENT = "WEATHER_EVIDENCE_INSUFFICIENT"
    WEATHER_EVIDENCE_STALE = "WEATHER_EVIDENCE_STALE"

    # Soil Domain Reason Codes
    SOIL_CONDITIONS_OPTIMAL = "SOIL_CONDITIONS_OPTIMAL"
    SOIL_SALINITY_ELEVATED = "SOIL_SALINITY_ELEVATED"
    SOIL_SALINITY_SEVERE = "SOIL_SALINITY_SEVERE"
    SOIL_PH_ALKALINE = "SOIL_PH_ALKALINE"
    SOIL_PH_ACIDIC = "SOIL_PH_ACIDIC"
    SOIL_SODIC_HAZARD = "SOIL_SODIC_HAZARD"
    SOIL_METHOD_NOT_STANDARDIZED = "SOIL_METHOD_NOT_STANDARDIZED"
    SOIL_AWC_LOW = "SOIL_AWC_LOW"
    SOIL_EVIDENCE_INSUFFICIENT = "SOIL_EVIDENCE_INSUFFICIENT"
    SOIL_EVIDENCE_STALE = "SOIL_EVIDENCE_STALE"


class DomainStressEvaluation(BaseModel):
    """Stress evaluation for an individual agronomic domain."""

    domain: str = Field(..., description="Domain name: 'water', 'vegetation', 'weather', or 'soil'")
    status: StressStatus = Field(..., description="Domain status: healthy, monitor, attention, high_stress, insufficient_data")
    stress_detected: Optional[bool] = Field(default=None, description="Whether active stress is detected (None if insufficient/suspect)")
    quality_status: DataQualityStatus = Field(default=DataQualityStatus.GOOD, description="Domain data quality")
    is_stale: bool = Field(default=False, description="Whether evidence is stale")
    is_suspect: bool = Field(default=False, description="Whether evidence is suspect or contaminated")
    continuous_severity: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Domain continuous stress severity metric (e.g. 1.0 - Ks for water; None if inapplicable)"
    )
    reason_codes: List[StressReasonCode] = Field(default_factory=list, description="Machine-readable reason codes")
    evidence_notes: List[str] = Field(default_factory=list, description="Transparent domain evidence notes")


# ==============================================================================
# 1. WATER DOMAIN SCORING
# ==============================================================================

def evaluate_water_stress_domain(indicators: WaterStressIndicators) -> DomainStressEvaluation:
    """Evaluate water stress status from root-zone water balance indicators."""
    reasons: List[StressReasonCode] = []
    notes: List[str] = []

    # Check for insufficient data
    if indicators.quality_status == DataQualityStatus.INSUFFICIENT or indicators.depletion_mm is None:
        reasons.append(StressReasonCode.WATER_BALANCE_INSUFFICIENT)
        notes.append("Water balance evidence is missing, incomplete, or marked INSUFFICIENT.")
        return DomainStressEvaluation(
            domain="water",
            status=StressStatus.INSUFFICIENT_DATA,
            stress_detected=None,
            quality_status=DataQualityStatus.INSUFFICIENT,
            is_stale=indicators.is_stale,
            is_suspect=False,
            continuous_severity=None,
            reason_codes=reasons,
            evidence_notes=notes,
        )

    ks = indicators.water_stress_coefficient_ks if indicators.water_stress_coefficient_ks is not None else 1.0
    dr = indicators.depletion_mm
    raw = indicators.readily_available_water_mm or 0.0
    taw = indicators.total_available_water_mm or 0.0
    continuous_sev = round(max(0.0, min(1.0, 1.0 - ks)), 3)

    if indicators.is_stale:
        reasons.append(StressReasonCode.WATER_BALANCE_STALE)
        notes.append("Water balance evidence is stale.")

    # 1. Severe stress: Wilting point reached (Dr >= TAW or Ks == 0.0)
    if indicators.is_wilting_point_reached or dr >= taw:
        status = StressStatus.HIGH_STRESS
        stress_detected = True
        reasons.append(StressReasonCode.SEVERE_DEPLETION_AT_WILTING_POINT)
        reasons.append(StressReasonCode.WATER_STRESS_KS_REDUCED)
        notes.append(f"Severe water stress: Depletion Dr ({dr:.1f} mm) >= TAW ({taw:.1f} mm). Ks = 0.00.")

    # 2. Stress threshold crossed: Dr > RAW (0.0 < Ks < 1.0)
    elif indicators.is_depletion_exceeding_raw or dr > raw:
        stress_detected = True
        reasons.append(StressReasonCode.WATER_DEPLETION_EXCEEDS_RAW)
        reasons.append(StressReasonCode.WATER_STRESS_KS_REDUCED)
        if ks < 0.50:
            status = StressStatus.HIGH_STRESS
            notes.append(f"High water stress: Depletion Dr ({dr:.1f} mm) > RAW ({raw:.1f} mm), Ks = {ks:.2f} (< 0.50).")
        else:
            status = StressStatus.ATTENTION
            notes.append(f"Water stress active: Depletion Dr ({dr:.1f} mm) > RAW ({raw:.1f} mm), Ks = {ks:.2f}.")

    # 3. Warning band: 80% RAW <= Dr <= RAW (Ks == 1.0)
    elif indicators.is_approaching_raw:
        status = StressStatus.MONITOR
        stress_detected = False
        reasons.append(StressReasonCode.WATER_DEPLETION_APPROACHING_RAW)
        notes.append(f"Water depletion ({dr:.1f} mm) is approaching RAW ({raw:.1f} mm). Plant transpiration is currently non-stressed (Ks = 1.00).")

    # 4. Healthy: Dr < 80% RAW
    else:
        status = StressStatus.HEALTHY
        stress_detected = False
        reasons.append(StressReasonCode.WATER_DEPLETION_NORMAL)
        notes.append(f"Root-zone water content is well within readily available limits (Dr = {dr:.1f} mm, RAW = {raw:.1f} mm, Ks = 1.00).")

    return DomainStressEvaluation(
        domain="water",
        status=status,
        stress_detected=stress_detected,
        quality_status=indicators.quality_status,
        is_stale=indicators.is_stale,
        is_suspect=False,
        continuous_severity=continuous_sev,
        reason_codes=reasons,
        evidence_notes=notes,
    )


# ==============================================================================
# 2. VEGETATION DOMAIN SCORING
# ==============================================================================

def evaluate_vegetation_stress_domain(indicators: VegetationStressIndicators) -> DomainStressEvaluation:
    """Evaluate vegetation canopy stress status from Sentinel-2 optical features."""
    reasons: List[StressReasonCode] = []
    notes: List[str] = []

    # 1. Missing evidence completely
    if indicators.quality_status == DataQualityStatus.INSUFFICIENT or indicators.ndvi_median is None:
        reasons.append(StressReasonCode.VEGETATION_EVIDENCE_INSUFFICIENT)
        notes.append("No satellite vegetation features available.")
        return DomainStressEvaluation(
            domain="vegetation",
            status=StressStatus.INSUFFICIENT_DATA,
            stress_detected=None,
            quality_status=DataQualityStatus.INSUFFICIENT,
            is_stale=indicators.is_stale,
            is_suspect=indicators.is_suspect,
            continuous_severity=None,
            reason_codes=reasons,
            evidence_notes=notes,
        )

    # 2. Cloud / SCL contamination or suspect coverage
    if indicators.is_suspect or indicators.quality_status in (DataQualityStatus.CLOUD_CONTAMINATED, DataQualityStatus.SUSPECT):
        reasons.append(StressReasonCode.VEGETATION_SCL_CONTAMINATED)
        if indicators.cloud_shadow_fraction is not None and indicators.cloud_shadow_fraction > 0.02:
            reasons.append(StressReasonCode.VEGETATION_CLOUD_SHADOW_CONTAMINATED)
            notes.append(f"Observation affected by cloud shadow (SCL Class 3 = {indicators.cloud_shadow_fraction:.2%}).")
        if indicators.cast_shadow_fraction is not None and indicators.cast_shadow_fraction > 0.02:
            reasons.append(StressReasonCode.VEGETATION_CAST_SHADOW_CONTAMINATED)
            scl2_lbl = indicators.scl_class_2_label or "SCL Class 2"
            notes.append(f"Observation affected by {scl2_lbl} (SCL Class 2 = {indicators.cast_shadow_fraction:.2%}).")
        notes.append("Satellite pass is cloud/shadow contaminated or has suspect coverage; stress classification withheld.")
        return DomainStressEvaluation(
            domain="vegetation",
            status=StressStatus.INSUFFICIENT_DATA,
            stress_detected=None,
            quality_status=indicators.quality_status,
            is_stale=indicators.is_stale,
            is_suspect=True,
            continuous_severity=None,
            reason_codes=reasons,
            evidence_notes=notes,
        )

    if indicators.is_stale:
        reasons.append(StressReasonCode.VEGETATION_EVIDENCE_STALE)
        notes.append("Satellite observation is stale.")

    # 3. Missing historical baseline or phenological mismatch
    if not indicators.has_valid_baseline or indicators.ndvi_anomaly is None:
        reasons.append(StressReasonCode.VEGETATION_BASELINE_MISSING)
        if any("PHENOLOGICAL STAGE MISMATCH" in note or "CROP TYPE MISMATCH" in note for note in indicators.audit_trail):
            reasons.append(StressReasonCode.VEGETATION_PHENOLOGY_MISMATCH)
            notes.append("Phenological stage or crop species mismatch between observation and historical baseline.")
        else:
            notes.append("No historical baseline available for anomaly detection. Universal thresholds rejected per agronomic integrity.")
        return DomainStressEvaluation(
            domain="vegetation",
            status=StressStatus.INSUFFICIENT_DATA,
            stress_detected=None,
            quality_status=indicators.quality_status,
            is_stale=indicators.is_stale,
            is_suspect=False,
            continuous_severity=None,
            reason_codes=reasons,
            evidence_notes=notes,
        )

    # 4. Anomaly evaluation with valid baseline
    anomaly = indicators.ndvi_anomaly
    base_ndvi = indicators.baseline_ndvi or 0.5
    cont_sev = round(max(0.0, min(1.0, -anomaly / base_ndvi)), 3) if base_ndvi > 0 else 0.0

    # Distinguish statistically significant anomaly vs material vegetation decline
    is_mat_decline = indicators.is_material_vegetation_decline
    if is_mat_decline is None and anomaly is not None:
        thresh = getattr(indicators, "material_decline_threshold", -0.12)
        is_mat_decline = (anomaly <= thresh)

    t_stat_val = indicators.statistical_test_details.get("t_statistic")
    t_crit_val = indicators.statistical_test_details.get("t_critical_alpha_0_05")

    if indicators.is_statistically_significant_anomaly:
        reasons.append(StressReasonCode.VEGETATION_STATISTICAL_ANOMALY)
        stat_decline = indicators.is_statistically_significant_decline
        if stat_decline is None:
            stat_decline = (anomaly is not None and anomaly < 0.0)

        if stat_decline:
            reasons.append(StressReasonCode.VEGETATION_STATISTICAL_DECLINE)
            if StressReasonCode.VEGETATION_ANOMALY_NEGATIVE not in reasons:
                reasons.append(StressReasonCode.VEGETATION_ANOMALY_NEGATIVE)
            status = StressStatus.ATTENTION
            stress_detected = True
            notes.append(
                f"Statistically significant lower vegetation decline confirmed: Student's t = {t_stat_val} <= -{t_crit_val} "
                f"(baseline NDVI: {base_ndvi:.3f}, anomaly: {anomaly:+.3f} if anomaly is not None else 'N/A')."
            )
        else:
            reasons.append(StressReasonCode.VEGETATION_ANOMALY_POSITIVE)
            status = StressStatus.HEALTHY
            stress_detected = False
            notes.append(
                f"Statistically significant positive canopy greenness anomaly detected: Student's t = {t_stat_val} >= +{t_crit_val} "
                f"(baseline NDVI: {base_ndvi:.3f}, anomaly: {anomaly:+.3f} if anomaly is not None else 'N/A')."
            )
    if is_mat_decline:
        reasons.append(StressReasonCode.VEGETATION_MATERIAL_DECLINE)
        if StressReasonCode.VEGETATION_ANOMALY_NEGATIVE not in reasons:
            reasons.append(StressReasonCode.VEGETATION_ANOMALY_NEGATIVE)
        if not indicators.is_statistically_significant_anomaly:
            status = StressStatus.ATTENTION if anomaly < -0.15 else StressStatus.MONITOR
            stress_detected = True
        notes.append(
            f"Material vegetation decline: median NDVI dropped {abs(anomaly):.3f} below historical baseline "
            f"(threshold: {getattr(indicators, 'material_decline_threshold', -0.12):.2f}). Evaluated as operational policy threshold."
        )
    elif not indicators.is_statistically_significant_anomaly:
        if anomaly < -0.08:
            status = StressStatus.MONITOR
            stress_detected = False
            reasons.append(StressReasonCode.VEGETATION_ANOMALY_NEGATIVE)
            notes.append(f"Moderate greenness dip: median NDVI dropped {abs(anomaly):.3f} below baseline.")
        else:
            status = StressStatus.HEALTHY
            stress_detected = False
            reasons.append(StressReasonCode.VEGETATION_CANOPY_HEALTHY)
            notes.append(f"Canopy greenness is consistent with historical baseline (anomaly = {anomaly:+.3f}).")

    return DomainStressEvaluation(
        domain="vegetation",
        status=status,
        stress_detected=stress_detected,
        quality_status=indicators.quality_status,
        is_stale=indicators.is_stale,
        is_suspect=indicators.is_suspect,
        continuous_severity=cont_sev,
        reason_codes=reasons,
        evidence_notes=notes,
    )


# ==============================================================================
# 3. WEATHER DOMAIN SCORING
# ==============================================================================

def evaluate_weather_stress_domain(indicators: WeatherStressIndicators) -> DomainStressEvaluation:
    """Evaluate weather and evaporative demand stress status."""
    reasons: List[StressReasonCode] = []
    notes: List[str] = []

    if indicators.quality_status == DataQualityStatus.INSUFFICIENT or (
        indicators.temperature_max_c is None and indicators.temperature_mean_c is None
    ):
        reasons.append(StressReasonCode.WEATHER_EVIDENCE_INSUFFICIENT)
        notes.append("No meteorological feature evidence available.")
        return DomainStressEvaluation(
            domain="weather",
            status=StressStatus.INSUFFICIENT_DATA,
            stress_detected=None,
            quality_status=DataQualityStatus.INSUFFICIENT,
            is_stale=indicators.is_stale,
            is_suspect=False,
            continuous_severity=None,
            reason_codes=reasons,
            evidence_notes=notes,
        )

    if indicators.is_stale:
        reasons.append(StressReasonCode.WEATHER_EVIDENCE_STALE)
        notes.append("Weather observations are stale.")

    # High stress conditions
    if indicators.is_prolonged_heat_stress:
        status = StressStatus.HIGH_STRESS
        stress_detected = True
        reasons.append(StressReasonCode.WEATHER_HEAT_STRESS_PROLONGED)
        notes.append(f"Prolonged heat stress: Tmax exceeded {indicators.critical_temperature_threshold_c}°C over sustained exposure.")
    elif indicators.is_frost_risk:
        status = StressStatus.ATTENTION
        stress_detected = True
        reasons.append(StressReasonCode.WEATHER_FROST_RISK)
        notes.append(f"Frost hazard: Minimum temperature reached {indicators.temperature_min_c}°C.")
    elif indicators.is_high_vpd_stress and indicators.is_extended_dry_spell:
        status = StressStatus.ATTENTION
        stress_detected = True
        reasons.append(StressReasonCode.WEATHER_HIGH_VAPOR_PRESSURE_DEFICIT)
        reasons.append(StressReasonCode.WEATHER_EXTENDED_DRY_SPELL)
        notes.append(f"Combined atmospheric stress: High VPD ({indicators.vapor_pressure_deficit_kpa:.2f} kPa) and extended dry spell.")
    elif indicators.is_high_vpd_stress:
        status = StressStatus.MONITOR
        stress_detected = True
        reasons.append(StressReasonCode.WEATHER_HIGH_VAPOR_PRESSURE_DEFICIT)
        notes.append(f"High atmospheric evaporative demand: VPD = {indicators.vapor_pressure_deficit_kpa:.2f} kPa.")
    elif indicators.is_extended_dry_spell:
        status = StressStatus.MONITOR
        stress_detected = True
        reasons.append(StressReasonCode.WEATHER_EXTENDED_DRY_SPELL)
        notes.append("Extended dry spell detected (negligible precipitation across evaluation window).")
    else:
        status = StressStatus.HEALTHY
        stress_detected = False
        reasons.append(StressReasonCode.WEATHER_CONDITIONS_FAVORABLE)
        notes.append("Weather and atmospheric demand within normal agronomic ranges.")

    return DomainStressEvaluation(
        domain="weather",
        status=status,
        stress_detected=stress_detected,
        quality_status=indicators.quality_status,
        is_stale=indicators.is_stale,
        is_suspect=False,
        continuous_severity=None,
        reason_codes=reasons,
        evidence_notes=notes,
    )


# ==============================================================================
# 4. SOIL DOMAIN SCORING
# ==============================================================================

def evaluate_soil_stress_domain(indicators: SoilConditionIndicators) -> DomainStressEvaluation:
    """Evaluate soil physicochemical, salinity, and hydraulic limitation status."""
    reasons: List[StressReasonCode] = []
    notes: List[str] = []

    if indicators.quality_status == DataQualityStatus.INSUFFICIENT or (
        indicators.electrical_conductivity_ds_m is None
        and indicators.soil_ph is None
        and indicators.available_water_capacity_m3_m3 is None
    ):
        reasons.append(StressReasonCode.SOIL_EVIDENCE_INSUFFICIENT)
        notes.append("No soil physicochemical or hydraulic property evidence available.")
        return DomainStressEvaluation(
            domain="soil",
            status=StressStatus.INSUFFICIENT_DATA,
            stress_detected=None,
            quality_status=DataQualityStatus.INSUFFICIENT,
            is_stale=indicators.is_stale,
            is_suspect=False,
            continuous_severity=None,
            reason_codes=reasons,
            evidence_notes=notes,
        )

    if indicators.is_stale:
        reasons.append(StressReasonCode.SOIL_EVIDENCE_STALE)
        notes.append("Soil evidence exceeds freshness policy.")

    # Analytical method check for EC
    if indicators.electrical_conductivity_ds_m is not None and indicators.salinity_hazard_level is None:
        reasons.append(StressReasonCode.SOIL_METHOD_NOT_STANDARDIZED)
        notes.append(f"EC measured via dilute extract ({indicators.ec_method}); not evaluated against standard ECe thresholds.")

    # Salinity, pH, and sodicity conditions are evaluated distinctly
    is_severe_salinity = indicators.salinity_hazard_level == "severe"
    is_mod_salinity = indicators.salinity_hazard_level in ("slight", "moderate") or (
        indicators.crop_salinity_tolerance_ece is not None
        and indicators.electrical_conductivity_ds_m is not None
        and indicators.electrical_conductivity_ds_m >= indicators.crop_salinity_tolerance_ece
    )
    is_ph_extreme = indicators.ph_classification in ("strongly_acidic", "strongly_alkaline", "strongly_alkaline_sodic")
    is_sodic = indicators.is_sodic_hazard is True

    # Assign specific reason codes and notes for all detected conditions
    if is_severe_salinity:
        reasons.append(StressReasonCode.SOIL_SALINITY_SEVERE)
        notes.append(f"Severe soil salinity hazard (ECe = {indicators.electrical_conductivity_ds_m:.2f} dS/m).")

    if is_mod_salinity and not is_severe_salinity:
        reasons.append(StressReasonCode.SOIL_SALINITY_ELEVATED)
        notes.append(f"Elevated soil salinity: ECe = {indicators.electrical_conductivity_ds_m:.2f} dS/m (tolerance/threshold exceeded).")

    if is_sodic:
        reasons.append(StressReasonCode.SOIL_SODIC_HAZARD)
        notes.append(
            f"Confirmed sodic hazard (SAR = {indicators.sodium_adsorption_ratio_sar}, "
            f"ESP = {indicators.exchangeable_sodium_pct_esp}%). Soil structural dispersion risk."
        )

    if is_ph_extreme:
        if indicators.ph_classification in ("strongly_alkaline", "strongly_alkaline_sodic"):
            reasons.append(StressReasonCode.SOIL_PH_ALKALINE)
            notes.append(f"Strongly alkaline / high pH soil (pH = {indicators.soil_ph:.2f}). (Sodicity not inferred from pH alone).")
        else:
            reasons.append(StressReasonCode.SOIL_PH_ACIDIC)
            notes.append(f"Strongly acidic soil (pH = {indicators.soil_ph:.2f}).")

    if indicators.has_low_water_storage_capacity or indicators.has_low_awc_limitation:
        reasons.append(StressReasonCode.SOIL_AWC_LOW)
        notes.append(
            f"Low soil water-storage capacity constraint (AWC = {indicators.available_water_capacity_m3_m3:.3f} m³/m³ < 0.08). "
            "Physical storage constraint; NOT proof of active water stress."
        )

    # Determine status based on most severe condition
    if is_severe_salinity or (is_sodic and is_severe_salinity):
        status = StressStatus.HIGH_STRESS
        stress_detected = True
    elif is_ph_extreme or is_sodic:
        status = StressStatus.ATTENTION
        stress_detected = True
    elif is_mod_salinity or indicators.has_low_water_storage_capacity or indicators.has_low_awc_limitation:
        status = StressStatus.MONITOR
        stress_detected = True
    else:
        status = StressStatus.HEALTHY
        stress_detected = False
        reasons.append(StressReasonCode.SOIL_CONDITIONS_OPTIMAL)
        notes.append("Soil physicochemical properties within optimal agronomic ranges.")

    return DomainStressEvaluation(
        domain="soil",
        status=status,
        stress_detected=stress_detected,
        quality_status=indicators.quality_status,
        is_stale=indicators.is_stale,
        is_suspect=False,
        continuous_severity=None,
        reason_codes=reasons,
        evidence_notes=notes,
    )


# ==============================================================================
# 5. EVIDENCE SYNTHESIS / STATUS AGGREGATION
# ==============================================================================

def synthesize_overall_stress_status(
    domain_evaluations: Dict[str, DomainStressEvaluation],
) -> Tuple[StressStatus, DataQualityStatus, List[StressReasonCode]]:
    """Synthesize multimodal zone status without forcing a false composite numerical score.

    Deterministic Evidence Synthesis / Status Aggregation Hierarchy:
    1. If any domain exhibits HIGH_STRESS -> Overall status is HIGH_STRESS.
    2. If any domain exhibits ATTENTION -> Overall status is ATTENTION.
    3. If any domain exhibits MONITOR -> Overall status is MONITOR.
    4. If the critical water domain is INSUFFICIENT_DATA, the zone CANNOT be classified
       as HEALTHY; it must be classified as INSUFFICIENT_DATA.
    5. Only when the primary water domain is verified HEALTHY and no other domain exhibits
       stress, can the zone be declared HEALTHY.

    Note: This is strictly an evidence synthesis and status aggregation module. No priority
    ranking, action codes, or irrigation recommendations are generated here (Phase 5).
    """
    water_eval = domain_evaluations.get("water")
    all_evals = list(domain_evaluations.values())

    # Aggregate reason codes
    all_reasons: List[StressReasonCode] = []
    for ev in all_evals:
        all_reasons.extend(ev.reason_codes)

    # Determine overall quality
    qualities = [ev.quality_status for ev in all_evals]
    if all(q == DataQualityStatus.INSUFFICIENT for q in qualities):
        overall_quality = DataQualityStatus.INSUFFICIENT
    elif any(q == DataQualityStatus.INSUFFICIENT for q in qualities):
        overall_quality = DataQualityStatus.PARTIAL
    elif any(q in (DataQualityStatus.SUSPECT, DataQualityStatus.CLOUD_CONTAMINATED) for q in qualities):
        overall_quality = DataQualityStatus.SUSPECT
    elif any(q == DataQualityStatus.STALE for q in qualities):
        overall_quality = DataQualityStatus.STALE
    else:
        overall_quality = DataQualityStatus.GOOD

    # Check for active stress hierarchy
    has_high_stress = any(ev.status == StressStatus.HIGH_STRESS for ev in all_evals)
    has_attention = any(ev.status == StressStatus.ATTENTION for ev in all_evals)
    has_monitor = any(ev.status == StressStatus.MONITOR for ev in all_evals)

    if has_high_stress:
        return StressStatus.HIGH_STRESS, overall_quality, all_reasons

    if has_attention:
        return StressStatus.ATTENTION, overall_quality, all_reasons

    if has_monitor:
        return StressStatus.MONITOR, overall_quality, all_reasons

    # No domain shows active stress.
    # CRITICAL RULE: A zone with missing/insufficient water balance CANNOT be classified as HEALTHY.
    if water_eval is None or water_eval.status == StressStatus.INSUFFICIENT_DATA:
        return StressStatus.INSUFFICIENT_DATA, overall_quality, all_reasons

    # If all available domains are HEALTHY (or non-water domains are missing with water proven healthy)
    if water_eval.status == StressStatus.HEALTHY:
        return StressStatus.HEALTHY, overall_quality, all_reasons

    return StressStatus.INSUFFICIENT_DATA, overall_quality, all_reasons
