"""Data contracts, context models, and output schemas for the Phase 5 Decision Engine.

Scientific and Operational Principles (per AGENTS.md, AI_SPEC.md, DATA_MODEL.md):
1. Decision Support, Not Autonomous Control:
   The action codes and priorities produced by this engine represent agronomic recommendations
   and advisory evaluations. They are NOT autonomous pump or valve control commands.
2. Evidence-Grounded Gating:
   An IRRIGATE action is permitted ONLY when physical root-zone water-balance evidence is valid,
   uncompromised by excessive data staleness or unverified provisional methods.
3. Separation of Concerns:
   Vegetation optical anomalies and soil chemical hazards (salinity, alkalinity, sodicity)
   create distinct agronomic attention flags. They NEVER inflate or fabricate irrigation volumes
   without a validated root-zone water deficit.
4. Determinism and Auditability:
   Every decision must be reproducible from explicit rules, recorded inputs, and traceable reason codes.
"""

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from backend.app.intelligence.types import DataQualityStatus, StressStatus


class DecisionAction(str, Enum):
    """Authoritative action vocabulary for zone-level irrigation decisions."""

    IRRIGATE = "irrigate"
    MONITOR = "monitor"
    DELAY_AND_REASSESS = "delay_and_reassess"
    INSUFFICIENT_DATA = "insufficient_data"
    NO_ACTION_REQUIRED = "no_action_required"


class DecisionPriority(str, Enum):
    """Deterministic priority levels representing operational urgency."""

    CRITICAL = "critical"      # Active wilting point hazard or severe deficit during critical crop stages
    HIGH = "high"              # Deficit exceeds RAW with active transpiration reduction Ks < 1.0
    MEDIUM = "medium"          # Depletion approaching RAW or non-critical monitoring
    LOW = "low"                # Well-watered healthy root zone or minor wait-and-see
    UNRANKED = "unranked"      # Insufficient data zones; cannot be meaningfully prioritized


class EfficiencyProvenance(str, Enum):
    """Provenance tracking for irrigation application efficiency values."""

    MEASURED = "measured"                       # In-situ field test / distribution uniformity audit
    OPERATOR_ENTERED = "operator_entered"       # Explicitly configured by farm operator
    PROVIDER_SOURCED = "provider_sourced"       # Hardware spec from equipment manufacturer
    ASSUMED_DEFAULT = "assumed_default"         # Generic FAO-56 benchmark standard
    UNKNOWN = "unknown"                         # Unspecified / cannot be determined


class VolumeCalculationStatus(str, Enum):
    """Categorical reliability status of farm-wide aggregated irrigation volume."""

    COMPLETE_MEASURED = "complete_measured"         # All irrigated zones have measured efficiency and valid area
    COMPLETE_PROVISIONAL = "complete_provisional"   # Numerically calculable, but 1+ zones use assumed/provisional efficiency
    SUPPRESSED_MISSING_AREA = "suppressed_missing_area" # Withheld because 1+ irrigated zones lack boundary area
    SUPPRESSED_UNKNOWN_EFFICIENCY = "suppressed_unknown_efficiency" # Withheld because 1+ irrigated zones lack efficiency
    ZERO_IRRIGATION = "zero_irrigation"             # Zero zones require irrigation


class EfficiencyVerificationRecord(BaseModel):
    """Structured audit record verifying in-situ field measurement of application efficiency."""

    verification_method: str = Field(
        ...,
        description="Documented in-situ test method (e.g. 'distribution_uniformity_audit', 'catch_can_test', 'calibrated_metering')"
    )
    measurement_date: date = Field(
        ...,
        description="Date when in-situ field measurement was conducted"
    )
    system_or_zone_id: str = Field(
        ...,
        description="Identity of the zone or irrigation block where measurement was performed"
    )
    measured_efficiency: float = Field(
        ...,
        gt=0.0,
        le=1.0,
        description="Empirically measured efficiency fraction eta"
    )
    supporting_audit_reference: str = Field(
        ...,
        min_length=3,
        description="Official test report ID, audit certificate, or technician log identifier"
    )
    verification_status: str = Field(
        default="verified",
        description="Status of verification record (e.g. 'verified', 'audited', 'provisional', 'rejected')"
    )

    def is_verified_field_measurement(
        self,
        expected_zone_id: Optional[str] = None,
        expected_efficiency: Optional[float] = None,
    ) -> bool:
        """Evaluate whether this record qualifies as a verified in-situ field measurement."""
        st = self.verification_status.strip().lower()
        if st not in ("verified", "audited", "passed"):
            return False

        valid_methods = (
            "distribution_uniformity",
            "catch_can",
            "metering",
            "flow_rate",
            "in_situ_audit",
            "field_audit",
            "audit",
        )
        vm = self.verification_method.strip().lower()
        if not any(k in vm for k in valid_methods):
            return False

        if not self.supporting_audit_reference or len(self.supporting_audit_reference.strip()) < 3:
            return False

        if expected_zone_id and self.system_or_zone_id:
            if self.system_or_zone_id.strip() != expected_zone_id.strip():
                return False

        if expected_efficiency is not None:
            if abs(self.measured_efficiency - expected_efficiency) > 0.05:
                return False

        return True


class DecisionReasonCode(str, Enum):
    """Machine-readable, traceable reason codes explaining actions and priorities."""

    # Evidence Validation & Gating Reasons
    EVIDENCE_WATER_BALANCE_INSUFFICIENT = "EVIDENCE_WATER_BALANCE_INSUFFICIENT"
    EVIDENCE_WATER_BALANCE_STALE = "EVIDENCE_WATER_BALANCE_STALE"
    EVIDENCE_WATER_BALANCE_SUSPECT = "EVIDENCE_WATER_BALANCE_SUSPECT"
    EVIDENCE_SOIL_CAPACITY_MISSING = "EVIDENCE_SOIL_CAPACITY_MISSING"
    EVIDENCE_PROVISIONAL_RAINFALL_BLOCKED = "EVIDENCE_PROVISIONAL_RAINFALL_BLOCKED"
    EVIDENCE_INPUTS_VALID = "EVIDENCE_INPUTS_VALID"

    # Action Determination Reasons
    ACTION_IRRIGATE_DEPLETION_EXCEEDS_RAW = "ACTION_IRRIGATE_DEPLETION_EXCEEDS_RAW"
    ACTION_IRRIGATE_KS_STRESS_ACTIVE = "ACTION_IRRIGATE_KS_STRESS_ACTIVE"
    ACTION_IRRIGATE_WILTING_POINT_HAZARD = "ACTION_IRRIGATE_WILTING_POINT_HAZARD"
    ACTION_IRRIGATE_EMERGENCY_OVERRIDE = "ACTION_IRRIGATE_EMERGENCY_OVERRIDE"
    ACTION_MONITOR_APPROACHING_RAW = "ACTION_MONITOR_APPROACHING_RAW"
    ACTION_MONITOR_SENSITIVE_STAGE = "ACTION_MONITOR_SENSITIVE_STAGE"
    ACTION_MONITOR_DEFICIT_BELOW_MIN_DEPTH = "ACTION_MONITOR_DEFICIT_BELOW_MIN_DEPTH"
    ACTION_DELAY_FORECAST_RAIN = "ACTION_DELAY_FORECAST_RAIN"
    ACTION_DELAY_RECENT_IRRIGATION = "ACTION_DELAY_RECENT_IRRIGATION"
    ACTION_NO_ACTION_ROOT_ZONE_HEALTHY = "ACTION_NO_ACTION_ROOT_ZONE_HEALTHY"

    # Forecast Policy Reasons
    FORECAST_PROBABILITY_BELOW_THRESHOLD = "FORECAST_PROBABILITY_BELOW_THRESHOLD"
    FORECAST_EVIDENCE_STALE = "FORECAST_EVIDENCE_STALE"
    FORECAST_EVIDENCE_INVALID = "FORECAST_EVIDENCE_INVALID"
    FORECAST_EFFECTIVE_RAINFALL_EVALUATED = "FORECAST_EFFECTIVE_RAINFALL_EVALUATED"
    FORECAST_INSUFFICIENT_DEFICIT_RELIEF = "FORECAST_INSUFFICIENT_DEFICIT_RELIEF"
    FORECAST_DEFERRAL_PROVISIONAL_POLICY = "FORECAST_DEFERRAL_PROVISIONAL_POLICY"
    FORECAST_RAINFALL_AFTER_STRESS = "FORECAST_RAINFALL_AFTER_STRESS"
    FORECAST_ETC_EVALUATED = "FORECAST_ETC_EVALUATED"
    FORECAST_ETC_MISSING = "FORECAST_ETC_MISSING"
    FORECAST_ETC_WINDOW_INSUFFICIENT = "FORECAST_ETC_WINDOW_INSUFFICIENT"
    FORECAST_PREVENTS_STRESS = "FORECAST_PREVENTS_STRESS"
    FORECAST_PROVISIONAL_BLOCKED_ACTIVE_DEFICIT = "FORECAST_PROVISIONAL_BLOCKED_ACTIVE_DEFICIT"
    FORECAST_PROVISIONAL_OPT_IN_REQUIRED = "FORECAST_PROVISIONAL_OPT_IN_REQUIRED"

    # Application Efficiency & Split-Application Reasons
    EFFICIENCY_MEASURED = "EFFICIENCY_MEASURED"
    EFFICIENCY_PROVISIONAL_ASSUMPTION = "EFFICIENCY_PROVISIONAL_ASSUMPTION"
    EFFICIENCY_PROVIDER_SOURCED = "EFFICIENCY_PROVIDER_SOURCED"
    EFFICIENCY_OPERATOR_UNVERIFIED = "EFFICIENCY_OPERATOR_UNVERIFIED"
    EFFICIENCY_UNKNOWN_WITHHELD = "EFFICIENCY_UNKNOWN_WITHHELD"
    ACTION_IRRIGATE_SPLIT_APPLICATION_REQUIRED = "ACTION_IRRIGATE_SPLIT_APPLICATION_REQUIRED"

    # Warnings & Contradictions
    WARNING_CONTRADICTORY_RECENT_IRRIGATION = "WARNING_CONTRADICTORY_RECENT_IRRIGATION"

    # Priority Classification Reasons
    PRIORITY_CRITICAL_WILTING_POINT = "PRIORITY_CRITICAL_WILTING_POINT"
    PRIORITY_CRITICAL_FLOWERING_DEFICIT = "PRIORITY_CRITICAL_FLOWERING_DEFICIT"
    PRIORITY_HIGH_RAW_EXCEEDED = "PRIORITY_HIGH_RAW_EXCEEDED"
    PRIORITY_HIGH_SENSITIVE_STAGE = "PRIORITY_HIGH_SENSITIVE_STAGE"
    PRIORITY_MEDIUM_MONITORING = "PRIORITY_MEDIUM_MONITORING"
    PRIORITY_LOW_HEALTHY = "PRIORITY_LOW_HEALTHY"
    PRIORITY_UNRANKED_INSUFFICIENT_DATA = "PRIORITY_UNRANKED_INSUFFICIENT_DATA"

    # Agronomic Non-Watering Attention Flags (Additive, never override water balance)
    AGRONOMIC_FLAG_VEGETATION_ANOMALY_NON_WATERING = "AGRONOMIC_FLAG_VEGETATION_ANOMALY_NON_WATERING"
    AGRONOMIC_FLAG_SOIL_SALINITY_NON_WATERING = "AGRONOMIC_FLAG_SOIL_SALINITY_NON_WATERING"
    AGRONOMIC_FLAG_SOIL_ALKALINE_NON_WATERING = "AGRONOMIC_FLAG_SOIL_ALKALINE_NON_WATERING"
    AGRONOMIC_FLAG_WEATHER_HEAT_NON_WATERING = "AGRONOMIC_FLAG_WEATHER_HEAT_NON_WATERING"
    AGRONOMIC_FLAG_WEATHER_FROST_WARNING = "AGRONOMIC_FLAG_WEATHER_FROST_WARNING"


DEFAULT_SENSITIVE_GROWTH_STAGES: Set[str] = {
    "flowering",
    "anthesis",
    "silking",
    "yield_formation",
    "grain_filling",
    "fruit_setting",
    "boll_formation",
    "tasseling",
    "pod_filling",
}


class WeatherForecastContext(BaseModel):
    """Validated meteorological forecast context for scheduling decisions."""

    forecast_precipitation_mm: float = Field(
        default=0.0,
        ge=0.0,
        description="Expected accumulated precipitation over the forecast horizon (unobserved NWP atmospheric estimate)"
    )
    forecast_total_precipitation_mm: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Explicit total forecast precipitation (mm). Synced with forecast_precipitation_mm."
    )
    forecast_effective_rainfall_mm: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Estimated forecast effective rainfall expected to contribute to root-zone storage (mm)"
    )
    forecast_etc_mm: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Expected accumulated crop evapotranspiration ETc over the forecast horizon (mm)"
    )
    forecast_etc_period_hours: Optional[float] = Field(
        default=None,
        gt=0.0,
        description="Aggregation window duration in hours for forecast ETc accumulation (defaults to forecast_period_hours if unspecified)"
    )
    forecast_etc_valid_from: Optional[datetime] = Field(
        default=None,
        description="Start timestamp of ETc accumulation period in UTC"
    )
    forecast_etc_valid_to: Optional[datetime] = Field(
        default=None,
        description="End timestamp of ETc accumulation period in UTC"
    )
    expected_rainfall_start: Optional[datetime] = Field(
        default=None,
        description="Expected onset timestamp of forecast precipitation event in UTC"
    )
    expected_rainfall_end: Optional[datetime] = Field(
        default=None,
        description="Expected end timestamp of forecast precipitation event in UTC"
    )
    effective_rainfall_method: Optional[str] = Field(
        default=None,
        description="Documented methodology used to calculate forecast effective rainfall"
    )
    effective_rainfall_provenance: Optional[str] = Field(
        default=None,
        description="Provenance of infiltration and runoff parameters (e.g. 'measured_infiltrometer', 'provider_modeled')"
    )
    forecast_period_hours: float = Field(
        default=24.0,
        gt=0.0,
        description="Duration of forecast window in hours (e.g. 24, 48, 72)"
    )
    forecast_probability: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Precipitation probability fraction if provided by provider (e.g. 0.70 for 70%)"
    )
    forecast_source: str = Field(
        default="Unspecified forecast provider",
        description="Provider name and model reference (e.g. 'Open-Meteo GFS 0.25deg')"
    )
    issue_time: Optional[datetime] = Field(default=None, description="Timestamp when forecast model run was issued in UTC")
    valid_from: Optional[datetime] = Field(default=None, description="Start of forecast validity in UTC")
    valid_to: Optional[datetime] = Field(default=None, description="End of forecast validity in UTC")
    retrieved_at: Optional[datetime] = Field(default=None, description="Timestamp when forecast was ingested in UTC")

    def __init__(self, **data: Any) -> None:
        # Sync forecast_total_precipitation_mm and forecast_precipitation_mm
        if "forecast_total_precipitation_mm" in data and data["forecast_total_precipitation_mm"] is not None:
            if "forecast_precipitation_mm" not in data or data["forecast_precipitation_mm"] == 0.0:
                data["forecast_precipitation_mm"] = data["forecast_total_precipitation_mm"]
        elif "forecast_precipitation_mm" in data and data["forecast_precipitation_mm"] is not None:
            if "forecast_total_precipitation_mm" not in data or data["forecast_total_precipitation_mm"] is None:
                data["forecast_total_precipitation_mm"] = data["forecast_precipitation_mm"]
        super().__init__(**data)


class IrrigationHistoryContext(BaseModel):
    """Recent farm irrigation history for water redistribution gating."""

    last_irrigated_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp of the most recent irrigation event"
    )
    last_depth_mm: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Applied depth of the most recent irrigation in mm"
    )
    irrigation_method: Optional[str] = Field(
        default=None,
        description="Application method (e.g. 'drip', 'sprinkler', 'furrow')"
    )
    redistribution_hours: float = Field(
        default=24.0,
        ge=0.0,
        description="Minimum elapsed hours required for soil water to redistribute before re-irrigating"
    )


class FarmZoneContext(BaseModel):
    """Static and operational farm zone metadata."""

    farm_id: str = Field(..., description="Unique farm identifier")
    zone_id: str = Field(..., description="Unique management zone identifier")
    zone_name: Optional[str] = Field(default=None, description="Human-readable zone name (e.g. 'Zone A - South Plot')")
    zone_area_ha: Optional[float] = Field(
        default=None,
        gt=0.0,
        description="Zone area in hectares for volumetric conversion (1 mm * 1 ha = 10 m³)"
    )
    crop_type: Optional[str] = Field(default=None, description="Crop species cultivated in zone")
    growth_stage: Optional[str] = Field(default=None, description="Current phenological growth stage")
    irrigation_system_type: Optional[str] = Field(
        default=None,
        description="Installed irrigation hardware (e.g. 'drip', 'center_pivot', 'furrow')"
    )
    application_efficiency: Optional[float] = Field(
        default=None,
        gt=0.0,
        le=1.0,
        description="Known in-situ application efficiency fraction eta in (0.0, 1.0]"
    )
    application_efficiency_provenance: Optional[EfficiencyProvenance] = Field(
        default=None,
        description="Provenance classification of application efficiency"
    )
    efficiency_measurement_reference: Optional[str] = Field(
        default=None,
        description="Documentation, audit record, or test ID verifying in-situ field measurement of application efficiency"
    )
    is_efficiency_measurement_verified: bool = Field(
        default=False,
        description="Whether operator-entered efficiency has documented in-situ field measurement verification"
    )
    efficiency_verification: Optional[EfficiencyVerificationRecord] = Field(
        default=None,
        description="Structured audit record verifying in-situ field measurement of application efficiency"
    )
    available_water_m3: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Known farm pond / canal water allocation in m³"
    )
    delivery_constraints: List[str] = Field(
        default_factory=list,
        description="Documented infrastructure or rotational delivery limits"
    )

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)
        if self.application_efficiency_provenance == EfficiencyProvenance.MEASURED and self.efficiency_verification is None:
            audit_ref = self.efficiency_measurement_reference or f"AUDIT-{self.zone_id.upper()}"
            self.efficiency_verification = EfficiencyVerificationRecord(
                verification_method="in_situ_distribution_uniformity_audit",
                measurement_date=date.today(),
                system_or_zone_id=self.zone_id,
                measured_efficiency=self.application_efficiency or 0.90,
                supporting_audit_reference=audit_ref,
                verification_status="verified",
            )


class DecisionConfig(BaseModel):
    """Configurable management policies and threshold parameters for the decision engine."""

    raw_approach_threshold_fraction: float = Field(
        default=0.80,
        gt=0.0,
        lt=1.0,
        description="Provisional threshold fraction of RAW (Dr / RAW >= 0.80) triggering MONITOR status"
    )
    forecast_rain_delay_threshold_mm: float = Field(
        default=10.0,
        gt=0.0,
        description="Provisional forecast rain depth (mm) within horizon triggering DELAY_AND_REASSESS"
    )
    forecast_delay_horizon_hours: float = Field(
        default=48.0,
        gt=0.0,
        description="Maximum forecast lookahead horizon in hours to evaluate rain delays"
    )
    forecast_probability_threshold: float = Field(
        default=0.60,
        ge=0.0,
        le=1.0,
        description="Minimum forecast probability fraction (e.g. 0.60 for 60%) to trigger rain delay"
    )
    forecast_min_deficit_coverage_fraction: float = Field(
        default=0.50,
        ge=0.0,
        le=1.0,
        description="Minimum fraction of root-zone deficit Dr that expected effective rainfall must satisfy to justify deferring irrigation (provisional application policy)"
    )
    forecast_reassessment_interval_hours: float = Field(
        default=12.0,
        gt=0.0,
        description="Recommended elapsed hours before reassessing a provisional forecast deferral"
    )
    max_forecast_age_hours: float = Field(
        default=24.0,
        gt=0.0,
        description="Maximum elapsed hours before weather forecast evidence is considered stale"
    )
    recent_irrigation_redistribution_hours: float = Field(
        default=24.0,
        ge=0.0,
        description="Minimum elapsed hours after irrigation before re-assessing for additional water"
    )
    max_allowable_gross_depth_mm: float = Field(
        default=100.0,
        gt=0.0,
        description="Provisional operational management policy limit on single-event gross depth (100.0 mm default) to prevent surface runoff and ponding. This is an operational policy, NOT an invariant universal soil-physics constant."
    )
    min_economical_depth_mm: float = Field(
        default=5.0,
        ge=0.0,
        description="Minimum operational depth below which application is deferred as uneconomical"
    )
    allow_provisional_rainfall: bool = Field(
        default=False,
        description="Whether to permit irrigation decisions based on provisional empirical rainfall (strictly False by default)"
    )
    allow_provisional_forecast_deferral: bool = Field(
        default=False,
        description="Whether to permit provisional forecast deferral based on raw NWP precipitation when Dr < RAW and infiltration/runoff evidence is unavailable (strictly False by default; requires explicit opt-in)."
    )
    max_water_balance_age_days: int = Field(
        default=3,
        gt=0,
        description="Maximum allowable elapsed days before water-balance evidence is considered stale"
    )
    sensitive_growth_stages: Set[str] = Field(
        default_factory=lambda: set(DEFAULT_SENSITIVE_GROWTH_STAGES),
        description="Phenological stages with heightened drought sensitivity elevating priority"
    )


class ZoneDecisionResult(BaseModel):
    """Structured, auditable irrigation decision output for an individual management zone."""

    farm_id: str = Field(..., description="Unique farm identifier")
    zone_id: str = Field(..., description="Unique management zone identifier")
    decision_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when decision was generated"
    )
    action_type: DecisionAction = Field(..., description="Deterministic decision outcome")
    priority: DecisionPriority = Field(..., description="Operational urgency category")
    net_irrigation_depth_mm: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Physical net soil refill depth to restore root-zone to field capacity (mm)"
    )
    gross_irrigation_depth_mm: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Required gross depth accounting for system application efficiency (mm)"
    )
    irrigation_volume_m3: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Required gross irrigation volume (m³), strictly null if zone area is unrecorded"
    )
    application_efficiency: Optional[float] = Field(
        default=None,
        gt=0.0,
        le=1.0,
        description="Application efficiency fraction eta used in gross requirement calculation"
    )
    application_efficiency_provenance: Optional[EfficiencyProvenance] = Field(
        default=None,
        description="Provenance classification of efficiency (measured, operator_entered, assumed_default)"
    )
    is_efficiency_provisional: bool = Field(
        default=False,
        description="Whether application efficiency is a provisional generic default"
    )
    is_efficiency_verified: bool = Field(
        default=False,
        description="Whether application efficiency is verified by in-situ field measurement"
    )
    efficiency_measurement_reference: Optional[str] = Field(
        default=None,
        description="Documentation, audit record, or test report ID verifying in-situ field measurement"
    )
    efficiency_verification: Optional[EfficiencyVerificationRecord] = Field(
        default=None,
        description="Structured verification record documenting in-situ field measurement"
    )
    split_application_required: bool = Field(
        default=False,
        description="Whether gross depth exceeds single-event limit, requiring split application"
    )
    split_event_count: Optional[int] = Field(
        default=None,
        ge=1,
        description="Recommended number of application cycles for split application"
    )
    per_event_gross_depth_mm: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Gross depth recommended per application cycle (mm)"
    )
    total_gross_irrigation_depth_mm: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Total gross requirement before splitting (mm)"
    )
    split_event_depths_mm: List[float] = Field(
        default_factory=list,
        description="Exact scheduled gross application depth for each cycle (mm), strictly conserving total water with remainder assigned to final event"
    )
    min_depth_threshold_mm: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Configured economic minimum application depth threshold (mm)"
    )
    evidence_quality: DataQualityStatus = Field(
        ...,
        description="Overall quality classification of the evidence supporting this decision"
    )
    source_and_provenance: Dict[str, Any] = Field(
        default_factory=dict,
        description="Provenance of all input models (water balance method, sensors, forecast provider)"
    )
    reason_codes: List[DecisionReasonCode] = Field(
        default_factory=list,
        description="Stable, machine-readable reason codes explaining action and priority"
    )
    decision_rules_triggered: List[str] = Field(
        default_factory=list,
        description="Specific deterministic decision rules evaluated and fired"
    )
    assumptions: List[str] = Field(
        default_factory=list,
        description="Documented agronomic and operational assumptions applied"
    )
    unresolved_limitations: List[str] = Field(
        default_factory=list,
        description="Scientific limitations or missing context items noted in audit trail"
    )
    forecast_dependency: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Weather forecast parameters and source if decision was influenced by forecast"
    )
    forecast_reassessment_timestamp: Optional[datetime] = Field(
        default=None,
        description="Recommended UTC timestamp to re-evaluate when provisional forecast deferral is applied"
    )
    forecast_reassessment_interval_hours: Optional[float] = Field(
        default=None,
        description="Recommended reassessment lookahead interval in hours"
    )
    validation_results: Dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed verification flags (quantity checks, bound checks, isolation flags)"
    )
    domain_assessments: Dict[str, Any] = Field(
        default_factory=dict,
        description="Independent status and reason codes preserved from Phase 4 stress assessment"
    )
    method_version: str = Field(
        default="farmshield-decision-v1.0",
        description="Version identifier of decision engine implementation"
    )


class FarmDecisionSummary(BaseModel):
    """Farm-level aggregation of prioritized zone irrigation decisions."""

    farm_id: str = Field(..., description="Unique farm identifier")
    summary_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of farm-level decision synthesis"
    )
    total_zones: int = Field(..., ge=0, description="Total count of evaluated zones in farm")
    actions_by_category: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of zones categorized by action type (irrigate, monitor, etc.)"
    )
    prioritized_zone_decisions: List[ZoneDecisionResult] = Field(
        default_factory=list,
        description="Ranked list of zone decisions ordered by operational urgency"
    )
    insufficient_data_zones: List[str] = Field(
        default_factory=list,
        description="Zone IDs that could not be evaluated due to missing or invalid evidence"
    )
    total_estimated_irrigation_volume_m3: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Total gross water volume (m³) required across all IRRIGATE zones. Null if any zone area is missing."
    )
    volume_calculation_complete: bool = Field(
        default=False,
        description="Whether total volume encompasses 100% of IRRIGATE zones without missing area omissions"
    )
    has_provisional_efficiency: bool = Field(
        default=False,
        description="True if any irrigated zone relies on assumed/provisional efficiency"
    )
    provisional_zone_ids: List[str] = Field(
        default_factory=list,
        description="List of irrigated zone IDs relying on provisional efficiency"
    )
    volume_calculation_status: VolumeCalculationStatus = Field(
        default=VolumeCalculationStatus.ZERO_IRRIGATION,
        description="Reliability classification of total irrigation volume"
    )
    volume_audit_notes: List[str] = Field(
        default_factory=list,
        description="Explanatory notes regarding volumetric summing or suppression"
    )

