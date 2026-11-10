"""Zone-level multimodal crop and water stress assessment service.

Integrates independent indicators from water-balance, satellite vegetation,
meteorology, and soil physics into a structured, traceable ZoneStressAssessment.

Scientific and Agronomic Restrictions (per AGENTS.md, AI_SPEC.md):
- Preserves independent stress dimensions across domains; does NOT force
  multimodal evidence into an arbitrary single composite index.
- A zone with insufficient evidence in one domain MUST NOT automatically be
  classified as healthy.
- Continuous measurements, discrete boundary crossings, and reason codes are
  fully preserved for downstream decision rules and explanations.
- Missing, stale, and suspect inputs are explicitly documented in metadata.
- Employs deterministic Evidence Synthesis / Status Aggregation hierarchy.
  No priority ranking, action codes, or irrigation recommendations are generated
  in this module (Phase 5).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

from backend.app.intelligence.agronomy.water_balance import WaterBalanceResult
from backend.app.intelligence.config import (
    FeatureFreshnessConfig,
    default_freshness_config,
)
from backend.app.intelligence.features.soil import SoilFeatures
from backend.app.intelligence.features.vegetation import ZoneVegetationFeatures
from backend.app.intelligence.features.weather import WeatherFeatures
from backend.app.intelligence.stress.indicators import (
    CropStressThresholds,
    SoilConditionIndicators,
    VegetationHistoricalBaseline,
    VegetationStressIndicators,
    WaterStressIndicators,
    WeatherStressIndicators,
    calculate_soil_condition_indicators,
    calculate_vegetation_stress_indicators,
    calculate_water_stress_indicators,
    calculate_weather_stress_indicators,
)
from backend.app.intelligence.stress.scoring import (
    DomainStressEvaluation,
    StressReasonCode,
    evaluate_soil_stress_domain,
    evaluate_vegetation_stress_domain,
    evaluate_water_stress_domain,
    evaluate_weather_stress_domain,
    synthesize_overall_stress_status,
)
from backend.app.intelligence.types import DataQualityStatus, ProvenanceType, StressStatus


class ZoneStressAssessment(BaseModel):
    """Structured multimodal zone-level crop and water stress assessment."""

    model_config = ConfigDict(populate_by_name=True)

    zone_id: str = Field(..., description="Unique management zone identifier")
    farm_id: Optional[str] = Field(default=None, description="Unique farm identifier")
    assessed_at: datetime = Field(..., description="Assessment execution UTC timestamp")
    method_version: str = Field(default="0.4.0", description="Stress assessment algorithm version")

    # Overall synthesized assessment
    status: StressStatus = Field(..., description="Synthesized zone condition status: healthy, monitor, attention, high_stress, insufficient_data")
    data_quality_status: DataQualityStatus = Field(..., description="Synthesized data quality classification")
    water_stress_severity: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Continuous water-stress severity (1.0 - Ks); strictly None if water balance is missing or uncalibrated"
    )

    def __init__(self, **data: Any) -> None:
        if "stress_score" in data and "water_stress_severity" not in data:
            data["water_stress_severity"] = data.pop("stress_score")
        super().__init__(**data)

    @property
    def stress_score(self) -> Optional[float]:
        """Backward-compatibility property returning continuous water-stress severity (1.0 - Ks)."""
        return self.water_stress_severity

    # Independent Domain Assessments (keeps separate stress dimensions visible)
    domain_assessments: Dict[str, DomainStressEvaluation] = Field(
        default_factory=dict,
        description="Independent evaluations for water, vegetation, weather, and soil domains"
    )

    # Detailed Indicators by Domain
    water_indicators: Optional[WaterStressIndicators] = Field(default=None, description="Root-zone water balance indicators")
    vegetation_indicators: Optional[VegetationStressIndicators] = Field(default=None, description="Satellite canopy vegetation indicators")
    weather_indicators: Optional[WeatherStressIndicators] = Field(default=None, description="Atmospheric evaporative demand and weather indicators")
    soil_indicators: Optional[SoilConditionIndicators] = Field(default=None, description="Soil physicochemical and hydraulic indicators")

    # Evidence, Limitations & Audit Metadata
    evidence_summary: Dict[str, Any] = Field(default_factory=dict, description="Structured key-value summary of evaluated metrics")
    missing_evidence: List[str] = Field(default_factory=list, description="Itemized list of missing data inputs")
    stale_evidence: List[str] = Field(default_factory=list, description="Itemized list of inputs exceeding freshness thresholds")
    suspect_evidence: List[str] = Field(default_factory=list, description="Itemized list of suspect or contaminated inputs")
    reason_codes: List[StressReasonCode] = Field(default_factory=list, description="Machine-readable diagnostic reason codes")
    uncertainty_and_limitations: List[str] = Field(default_factory=list, description="Agronomic limitations and scientific caveats")


def assess_zone_stress(
    zone_id: str,
    farm_id: Optional[str] = None,
    water_balance: Optional[WaterBalanceResult] = None,
    vegetation_features: Optional[ZoneVegetationFeatures] = None,
    weather_features: Optional[WeatherFeatures] = None,
    soil_features: Optional[SoilFeatures] = None,
    historical_vegetation_baseline: Optional[VegetationHistoricalBaseline] = None,
    crop_stage_thresholds: Optional[CropStressThresholds] = None,
    crop_type: Optional[str] = None,
    growth_stage: Optional[str] = None,
    material_decline_threshold: float = -0.12,
    min_clear_observation_fraction: float = 0.60,
    max_cloud_shadow_fraction: float = 0.20,
    cloud_shadow_fraction: Optional[float] = None,
    cast_shadow_fraction: Optional[float] = None,
    processing_baseline: Optional[str] = None,
    sodium_adsorption_ratio_sar: Optional[float] = None,
    exchangeable_sodium_pct_esp: Optional[float] = None,
    crop_salinity_tolerance_ece: Optional[float] = None,
    in_situ_soil_moisture: Optional[float] = None,
    moisture_provenance: Optional[ProvenanceType] = None,
    moisture_depth_cm: Optional[Tuple[float, float]] = None,
    consecutive_dry_days: Optional[int] = None,
    sustained_high_temp_days: Optional[int] = None,
    freshness_config: FeatureFreshnessConfig = default_freshness_config,
    as_of_time: Optional[datetime] = None,
) -> ZoneStressAssessment:
    """Build a comprehensive, deterministic ZoneStressAssessment across multimodal inputs.

    Performs deterministic Evidence Synthesis / Status Aggregation across four independent
    domains without forcing an arbitrary composite numerical score.

    Args:
        zone_id: Management zone identifier.
        farm_id: Optional farm identifier.
        water_balance: Phase 3 daily root-zone water balance result.
        vegetation_features: Phase 2 optical satellite vegetation features.
        weather_features: Phase 2 meteorological feature set.
        soil_features: Phase 2 soil context and measurements.
        historical_vegetation_baseline: Validated baseline for vegetation anomaly detection.
        crop_stage_thresholds: Documented crop- and stage-specific stress thresholds.
        crop_type: Optional crop species for baseline matching.
        growth_stage: Optional phenological growth stage for baseline matching.
        material_decline_threshold: Configurable operational threshold for NDVI material decline (default -0.12).
        min_clear_observation_fraction: Configurable clear-sky observation fraction policy (default 0.60).
        max_cloud_shadow_fraction: Configurable cloud/shadow limit policy (default 0.20).
        sodium_adsorption_ratio_sar: Independent chemical SAR measurement for sodicity diagnosis.
        exchangeable_sodium_pct_esp: Independent chemical ESP (%) measurement for sodicity diagnosis.
        crop_salinity_tolerance_ece: Saturated paste ECe threshold for specific crop yield decline.
        in_situ_soil_moisture: Independent physical soil moisture sensor reading.
        moisture_provenance: Provenance of in-situ soil moisture.
        moisture_depth_cm: Depth range of in-situ soil moisture.
        consecutive_dry_days: Count of days without rain.
        sustained_high_temp_days: Consecutive days above critical temperature threshold.
        freshness_config: Freshness thresholds across domains.
        as_of_time: Reference UTC timestamp (defaults to current UTC).

    Returns:
        Structured ZoneStressAssessment.
    """
    now_utc = as_of_time or datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    missing_items: List[str] = []
    stale_items: List[str] = []
    suspect_items: List[str] = []
    limitations: List[str] = []

    # 1. Extract Water Indicators & Evaluate Domain
    water_ind = calculate_water_stress_indicators(
        water_balance=water_balance,
        in_situ_soil_moisture=in_situ_soil_moisture,
        moisture_provenance=moisture_provenance,
        moisture_depth_cm=moisture_depth_cm,
        freshness_config=freshness_config,
        as_of_time=now_utc,
    )
    water_eval = evaluate_water_stress_domain(water_ind)
    limitations.extend(water_ind.scientific_caveats)
    if water_ind.quality_status == DataQualityStatus.INSUFFICIENT:
        missing_items.append("Water Balance: Daily root-zone water balance model output is missing or incomplete.")
    if water_ind.is_stale:
        stale_items.append("Water Balance: Observations exceed freshness policy.")

    # 2. Extract Vegetation Indicators & Evaluate Domain
    veg_ind = calculate_vegetation_stress_indicators(
        vegetation_features=vegetation_features,
        baseline=historical_vegetation_baseline,
        crop_type=crop_type,
        growth_stage=growth_stage,
        material_decline_threshold=material_decline_threshold,
        min_clear_observation_fraction=min_clear_observation_fraction,
        max_cloud_shadow_fraction=max_cloud_shadow_fraction,
        cloud_shadow_fraction=cloud_shadow_fraction,
        cast_shadow_fraction=cast_shadow_fraction,
        processing_baseline=processing_baseline,
        freshness_config=freshness_config,
        as_of_time=now_utc,
    )
    veg_eval = evaluate_vegetation_stress_domain(veg_ind)
    limitations.extend(veg_ind.scientific_caveats)
    if veg_ind.quality_status == DataQualityStatus.INSUFFICIENT:
        missing_items.append("Vegetation: Satellite optical features or historical baseline missing.")
    if veg_ind.is_stale:
        stale_items.append("Vegetation: Satellite scene exceeds freshness policy.")
    if veg_ind.is_suspect:
        suspect_items.append("Vegetation: SCL cloud/shadow contamination or low coverage detected.")

    # 3. Extract Weather Indicators & Evaluate Domain
    weath_ind = calculate_weather_stress_indicators(
        weather_features=weather_features,
        crop_stage_thresholds=crop_stage_thresholds,
        consecutive_dry_days=consecutive_dry_days,
        sustained_high_temp_days=sustained_high_temp_days,
        freshness_config=freshness_config,
        as_of_time=now_utc,
    )
    weath_eval = evaluate_weather_stress_domain(weath_ind)
    limitations.extend(weath_ind.scientific_caveats)
    if weath_ind.quality_status == DataQualityStatus.INSUFFICIENT:
        missing_items.append("Weather: Meteorological observation features missing.")
    if weath_ind.is_stale:
        stale_items.append("Weather: Meteorological records exceed freshness policy.")

    # 4. Extract Soil Indicators & Evaluate Domain
    soil_ind = calculate_soil_condition_indicators(
        soil_features=soil_features,
        sodium_adsorption_ratio_sar=sodium_adsorption_ratio_sar,
        exchangeable_sodium_pct_esp=exchangeable_sodium_pct_esp,
        crop_salinity_tolerance_ece=crop_salinity_tolerance_ece,
        freshness_config=freshness_config,
        as_of_time=now_utc,
    )
    soil_eval = evaluate_soil_stress_domain(soil_ind)
    limitations.extend(soil_ind.scientific_caveats)
    if soil_ind.quality_status == DataQualityStatus.INSUFFICIENT:
        missing_items.append("Soil: Soil physicochemical and hydraulic property measurements missing.")
    if soil_ind.is_stale:
        stale_items.append("Soil: Soil property record exceeds freshness policy.")

    # 5. Synthesize Multimodal Zone Assessment (Evidence Synthesis / Status Aggregation)
    domain_evals: Dict[str, DomainStressEvaluation] = {
        "water": water_eval,
        "vegetation": veg_eval,
        "weather": weath_eval,
        "soil": soil_eval,
    }

    overall_status, overall_quality, all_reasons = synthesize_overall_stress_status(domain_evals)

    # Clean and deduplicate limitations and reasons
    unique_limitations = list(dict.fromkeys(limitations))
    unique_reasons = list(dict.fromkeys(all_reasons))

    # Evidence Summary dictionary
    evidence_sum: Dict[str, Any] = {
        "water": {
            "depletion_mm": water_ind.depletion_mm,
            "total_available_water_mm": water_ind.total_available_water_mm,
            "readily_available_water_mm": water_ind.readily_available_water_mm,
            "water_stress_coefficient_ks": water_ind.water_stress_coefficient_ks,
            "stress_deficit_mm": water_ind.stress_deficit_mm,
            "is_depletion_exceeding_raw": water_ind.is_depletion_exceeding_raw,
            "is_wilting_point_reached": water_ind.is_wilting_point_reached,
            "modelled_soil_moisture_m3_m3": water_ind.modelled_root_zone_moisture_m3_m3,
            "measured_soil_moisture_m3_m3": water_ind.measured_soil_moisture_m3_m3,
            "status": water_eval.status.value,
        },
        "vegetation": {
            "ndvi_median": veg_ind.ndvi_median,
            "ndmi_median": veg_ind.ndmi_median,
            "vegetation_coverage_fraction": veg_ind.vegetation_coverage_fraction,
            "clear_observation_fraction": veg_ind.clear_observation_fraction,
            "cloud_shadow_fraction": veg_ind.cloud_shadow_fraction,
            "cast_shadow_fraction": veg_ind.cast_shadow_fraction,
            "scl_2_class_number": veg_ind.scl_2_class_number,
            "scl_2_fraction": veg_ind.scl_2_fraction,
            "scl_2_original_label": veg_ind.scl_2_original_label,
            "scl_2_semantic_interpretation": veg_ind.scl_2_semantic_interpretation,
            "scl_3_class_number": veg_ind.scl_3_class_number,
            "scl_3_fraction": veg_ind.scl_3_fraction,
            "scl_3_original_label": veg_ind.scl_3_original_label,
            "scl_3_semantic_interpretation": veg_ind.scl_3_semantic_interpretation,
            "scl_class_2_label": veg_ind.scl_class_2_label,
            "processing_baseline": veg_ind.processing_baseline,
            "ndvi_anomaly": veg_ind.ndvi_anomaly,
            "z_score": veg_ind.z_score,
            "is_material_vegetation_decline": veg_ind.is_material_vegetation_decline,
            "is_statistically_significant_anomaly": veg_ind.is_statistically_significant_anomaly,
            "is_statistically_significant_decline": veg_ind.is_statistically_significant_decline,
            "statistical_test_details": veg_ind.statistical_test_details,
            "has_valid_baseline": veg_ind.has_valid_baseline,
            "status": veg_eval.status.value,
        },
        "weather": {
            "temperature_max_c": weath_ind.temperature_max_c,
            "temperature_mean_c": weath_ind.temperature_mean_c,
            "vapor_pressure_deficit_kpa": weath_ind.vapor_pressure_deficit_kpa,
            "vpd_calculation_method": weath_ind.vpd_calculation_method.value if weath_ind.vpd_calculation_method else None,
            "vpd_equation_citation": weath_ind.vpd_equation_citation,
            "is_high_vpd_stress": weath_ind.is_high_vpd_stress,
            "is_prolonged_heat_stress": weath_ind.is_prolonged_heat_stress,
            "is_extended_dry_spell": weath_ind.is_extended_dry_spell,
            "is_frost_risk": weath_ind.is_frost_risk,
            "status": weath_eval.status.value,
        },
        "soil": {
            "electrical_conductivity_ds_m": soil_ind.electrical_conductivity_ds_m,
            "ec_method": soil_ind.ec_method,
            "salinity_hazard_level": soil_ind.salinity_hazard_level,
            "crop_salinity_tolerance_ece": soil_ind.crop_salinity_tolerance_ece,
            "soil_ph": soil_ind.soil_ph,
            "ph_classification": soil_ind.ph_classification,
            "sodium_adsorption_ratio_sar": soil_ind.sodium_adsorption_ratio_sar,
            "exchangeable_sodium_pct_esp": soil_ind.exchangeable_sodium_pct_esp,
            "is_sodic_hazard": soil_ind.is_sodic_hazard,
            "available_water_capacity_m3_m3": soil_ind.available_water_capacity_m3_m3,
            "has_low_water_storage_capacity": soil_ind.has_low_water_storage_capacity,
            "has_low_awc_limitation": soil_ind.has_low_awc_limitation,
            "status": soil_eval.status.value,
        },
    }

    # Documented water-stress severity (1.0 - Ks) or None
    severity_val = water_eval.continuous_severity

    return ZoneStressAssessment(
        zone_id=zone_id,
        farm_id=farm_id,
        assessed_at=now_utc,
        method_version="0.4.0",
        status=overall_status,
        data_quality_status=overall_quality,
        water_stress_severity=severity_val,
        domain_assessments=domain_evals,
        water_indicators=water_ind,
        vegetation_indicators=veg_ind,
        weather_indicators=weath_ind,
        soil_indicators=soil_ind,
        evidence_summary=evidence_sum,
        missing_evidence=missing_items,
        stale_evidence=stale_items,
        suspect_evidence=suspect_items,
        reason_codes=unique_reasons,
        uncertainty_and_limitations=unique_limitations,
    )

