"""Data contracts and structured schemas for the Phase 6 Explanation Service.

Scientific and Operational Principles (per AGENTS.md, AI_SPEC.md, DATA_MODEL.md):
1. Explanatory, Not Decisional:
   The explanation service converts existing validated decisions and evidence
   into transparent, traceable explanations. It NEVER calculates new irrigation
   depths, never calculates new stress scores, and never overrides Phase 5 decisions.
2. Evidence Traceability:
   Every explanatory statement must link to an explicit input observation,
   calculated agronomic state, or deterministic decision rule.
3. Separation of Audiences:
   - Farmer Explanations: Plain language, multilingual (English, Marathi, Hindi),
     highlighting practical operational guidance, physical units, and key reasons.
   - Agronomist Explanations: Complete technical precision with FAO-56 physical parameters
     (Dr, RAW, TAW, Ks, ETc), forecast bounds, application efficiency provenance,
     and scientific limitations.
4. Truth in Data:
   - Assumed or provisional efficiencies are never presented as field-measured.
   - Forecast precipitation is never described as observed rainfall.
   - Missing or stale evidence is explicitly disclosed and never concealed.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.intelligence.decision.types import (
    DecisionAction,
    DecisionPriority,
    EfficiencyProvenance,
    VolumeCalculationStatus,
)
from backend.app.intelligence.types import DataQualityStatus, ProvenanceType


class ExplanationLanguage(str, Enum):
    """Supported human languages for deterministic farmer-facing explanations."""

    EN = "en"  # English
    MR = "mr"  # Marathi (मराठी)
    HI = "hi"  # Hindi (हिंदी)


class EvidenceType(str, Enum):
    """Classification of evidence origin and measurement character."""

    SENSOR_MEASURED = "sensor_measured"
    SATELLITE_DERIVED = "satellite_derived"
    CALCULATED = "calculated"
    FORECAST = "forecast"
    OPERATOR_ENTERED = "operator_entered"
    ASSUMED_DEFAULT = "assumed_default"
    SIMULATED = "simulated"
    UNKNOWN = "unknown"


class EvidenceItem(BaseModel):
    """Individual item of supporting evidence preserved with full provenance."""

    name: str = Field(..., description="Canonical metric or parameter name (e.g. 'root_zone_depletion_dr')")
    value: Optional[Any] = Field(default=None, description="Recorded or calculated numeric / categorical value")
    unit: Optional[str] = Field(default=None, description="Physical unit of measurement (e.g. 'mm', 'm³/m³', 'fraction')")
    source_provider: Optional[str] = Field(default=None, description="Data source or instrument reference")
    observation_timestamp: Optional[datetime] = Field(default=None, description="UTC timestamp of raw observation")
    evidence_type: EvidenceType = Field(default=EvidenceType.UNKNOWN, description="Origin classification")
    quality_status: DataQualityStatus = Field(default=DataQualityStatus.GOOD, description="Assessed evidence reliability")
    is_provisional: bool = Field(default=False, description="Whether value incorporates provisional or uncalibrated methods")
    is_missing: bool = Field(default=False, description="Whether this required parameter is missing from the record")
    is_stale: bool = Field(default=False, description="Whether parameter exceeds freshness tolerance")
    is_suspect: bool = Field(default=False, description="Whether measurement has quality anomalies or contamination")
    method_reference: Optional[str] = Field(default=None, description="Documented calculation or calibration methodology")
    notes: Optional[str] = Field(default=None, description="Contextual note or physical caveat")


class ReasonCodeExplanation(BaseModel):
    """Deterministic resolution of an intelligence reason code across audiences."""

    code: str = Field(..., description="Machine-readable reason code identifier")
    farmer_explanation: str = Field(..., description="Plain-language explanation for the farmer in requested language")
    agronomist_technical_note: str = Field(..., description="Technical description with FAO-56 / physical criteria")
    measurement_references: List[str] = Field(default_factory=list, description="Associated parameters (e.g. ['Dr', 'RAW', 'Ks'])")
    limitations: List[str] = Field(default_factory=list, description="Known operational or scientific caveats")
    is_unresolved: bool = Field(default=False, description="True if reason code was unmapped in registry")


class AgronomistTechnicalExplanation(BaseModel):
    """Comprehensive technical representation for agronomists, researchers, and extension officers."""

    # FAO-56 Root-Zone Water Balance Parameters
    depletion_dr_mm: Optional[float] = Field(default=None, description="Root-zone soil water depletion Dr (mm)")
    readily_available_water_raw_mm: Optional[float] = Field(default=None, description="Readily available water RAW (mm)")
    total_available_water_taw_mm: Optional[float] = Field(default=None, description="Total available water TAW (mm)")
    transpiration_reduction_ks: Optional[float] = Field(default=None, description="Transpiration reduction coefficient Ks (0.0 - 1.0)")
    crop_evapotranspiration_etc_mm: Optional[float] = Field(default=None, description="Non-stressed potential crop ETc (mm)")
    adjusted_etc_mm: Optional[float] = Field(default=None, description="Deficit-adjusted crop ETc,adj = Ks * ETc (mm)")

    # Weather & Forecast Windows
    forecast_etc_window: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Temporal validation metadata for forecast ETc accumulation (valid_from, valid_to, rate)"
    )
    forecast_rainfall_summary: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Forecast precipitation breakdown (gross vs effective, probability, onset)"
    )

    # Irrigation Scheduling & Application Physics
    net_irrigation_depth_mm: Optional[float] = Field(default=None, description="Physical refill depth back to Field Capacity (mm)")
    gross_irrigation_depth_mm: Optional[float] = Field(default=None, description="Required gross depth accounting for application losses (mm)")
    application_efficiency: Optional[float] = Field(default=None, description="System application efficiency fraction eta")
    application_efficiency_provenance: Optional[str] = Field(default=None, description="Provenance of efficiency (measured, operator, assumed)")
    is_efficiency_verified: bool = Field(default=False, description="Whether efficiency is verified by structured field audit")
    is_efficiency_provisional: bool = Field(default=False, description="Whether efficiency is an assumed or provisional benchmark")

    # Split-Application Schedule
    split_application_required: bool = Field(default=False, description="True if gross depth exceeds single-event soil intake limit")
    split_event_count: Optional[int] = Field(default=None, description="Recommended number of irrigation cycles")
    split_event_depths_mm: List[float] = Field(default_factory=list, description="Exact scheduled gross depth per cycle (mm)")

    # Multimodal Stress Indicators
    domain_stress_indicators: Dict[str, Any] = Field(
        default_factory=dict,
        description="Preserved domain-specific stress metrics (NDVI, NDMI, VPD, soil salinity ECe, pH)"
    )
    satellite_observation_quality: Optional[str] = Field(
        default=None,
        description="Sentinel-2 SCL classification and validity percentage"
    )

    # Method Provenance & Caveats
    method_assumptions: List[str] = Field(default_factory=list, description="Documented agronomic assumptions applied")
    scientific_limitations: List[str] = Field(default_factory=list, description="Identified data or modelling limitations")


class ZoneExplanation(BaseModel):
    """Structured, evidence-grounded explanation for an individual zone decision."""

    farm_id: str = Field(..., description="Unique farm identifier")
    zone_id: str = Field(..., description="Unique management zone identifier")
    decision_reference: str = Field(..., description="Traceable decision version or record identifier")
    action: DecisionAction = Field(..., description="Deterministic decision action explained")
    priority: DecisionPriority = Field(..., description="Operational urgency category")
    explanation_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when explanation was synthesized"
    )
    language: ExplanationLanguage = Field(
        default=ExplanationLanguage.EN,
        description="Language of rendered farmer-facing copy"
    )

    # Plain-Language Farmer Section
    short_summary: str = Field(..., description="Concise, plain-language summary of the action and current zone state")
    why_decision_produced: str = Field(..., description="Clear explanation of the physical/meteorological cause triggering this action")
    action_guidance: str = Field(..., description="Direct operational instruction for the farm operator")

    # Explicit Irrigation Quantities & Efficiency (Top-Level Integration Fields)
    net_irrigation_depth_mm: Optional[float] = Field(
        default=None,
        description="Physical net soil refill requirement d_net (mm) to restore root zone to Field Capacity"
    )
    gross_irrigation_depth_mm: Optional[float] = Field(
        default=None,
        description="Gross application depth d_gross = d_net / eta (mm) accounting for application efficiency"
    )
    irrigation_volume_m3: Optional[float] = Field(
        default=None,
        description="Gross irrigation volume requirement (m³), strictly null if zone area is unrecorded"
    )
    application_efficiency: Optional[float] = Field(
        default=None,
        description="Application efficiency fraction eta used to derive gross depth from net deficit"
    )
    application_efficiency_provenance: Optional[str] = Field(
        default=None,
        description="Provenance classification of efficiency (measured, operator_entered, provider_sourced, assumed_default)"
    )
    is_efficiency_verified: bool = Field(
        default=False,
        description="Whether efficiency is backed by a structured in-situ field measurement or audit"
    )
    is_efficiency_provisional: bool = Field(
        default=False,
        description="Whether efficiency relies on an assumed default or unverified operator value"
    )

    # Supporting Evidence Inventory
    supporting_evidence: List[EvidenceItem] = Field(
        default_factory=list,
        description="Traceable itemized evidence records with physical units and source provenance"
    )
    relevant_measurements: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key physical parameters with explicit units for display cards"
    )

    # Reason Codes & Technical Resolution
    reason_codes: List[str] = Field(
        default_factory=list,
        description="Stable machine-readable reason codes attached to the decision"
    )
    resolved_reason_explanations: List[ReasonCodeExplanation] = Field(
        default_factory=list,
        description="Detailed plain-text and technical mappings for each reason code"
    )

    # Data Quality, Caveats & Limitations
    missing_evidence: List[str] = Field(
        default_factory=list,
        description="Explicit list of absent parameters that constrained the evaluation"
    )
    stale_or_suspect_evidence: List[str] = Field(
        default_factory=list,
        description="List of observations flagged as stale, cloud-contaminated, or uncalibrated"
    )
    assumptions: List[str] = Field(
        default_factory=list,
        description="Operational and agronomic assumptions documented during rule evaluation"
    )
    provisional_calculation_flags: List[str] = Field(
        default_factory=list,
        description="Explicit caveats for any value relying on provisional/unverified policies"
    )
    uncertainty_and_limitations: List[str] = Field(
        default_factory=list,
        description="Identified uncertainties, model constraints, and sensor gaps"
    )

    # Reassessment Lookahead
    reassessment_timestamp: Optional[datetime] = Field(
        default=None,
        description="Scheduled UTC timestamp to re-evaluate (relevant for DELAY_AND_REASSESS)"
    )
    reassessment_interval_hours: Optional[float] = Field(
        default=None,
        description="Lookahead interval in hours until next scheduled assessment"
    )

    # Advanced Agronomist Section
    agronomist_explanation: AgronomistTechnicalExplanation = Field(
        ...,
        description="In-depth agronomic parameter breakdown for technical experts"
    )

    method_version: str = Field(
        default="farmshield-explanation-v1.0",
        description="Version identifier of explanation service implementation"
    )


class FarmExplanation(BaseModel):
    """Farm-level synthesized explanation aggregating multi-zone conditions and volumetric audit."""

    farm_id: str = Field(..., description="Unique farm identifier")
    explanation_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of farm-level explanation synthesis"
    )
    language: ExplanationLanguage = Field(
        default=ExplanationLanguage.EN,
        description="Language of rendered farm summary copy"
    )

    total_zones: int = Field(..., ge=0, description="Total number of evaluated management zones")
    zones_requiring_irrigation: List[str] = Field(default_factory=list, description="Zone IDs with IRRIGATE action")
    zones_being_monitored: List[str] = Field(default_factory=list, description="Zone IDs with MONITOR action")
    delayed_zones: List[str] = Field(default_factory=list, description="Zone IDs with DELAY_AND_REASSESS action")
    insufficient_data_zones: List[str] = Field(default_factory=list, description="Zone IDs with INSUFFICIENT_DATA action")
    no_action_zones: List[str] = Field(default_factory=list, description="Zone IDs with NO_ACTION_REQUIRED action")

    # Volumetric Accounting
    volume_calculation_status: VolumeCalculationStatus = Field(
        ...,
        description="Reliability classification of total farm irrigation volume"
    )
    total_estimated_volume_m3: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Total gross irrigation requirement in m³ across all IRRIGATE zones (null if suppressed)"
    )
    volume_calculation_complete: bool = Field(
        default=False,
        description="Whether volumetric calculation encompasses all irrigated zones without area omissions"
    )
    has_provisional_efficiency: bool = Field(
        default=False,
        description="True if any irrigated zone relies on assumed/provisional efficiency"
    )
    provisional_zone_ids: List[str] = Field(
        default_factory=list,
        description="List of irrigated zone IDs relying on provisional efficiency"
    )
    provisional_volume_warnings: List[str] = Field(
        default_factory=list,
        description="Audit warnings regarding volumetric estimation and efficiency assumptions"
    )

    # Synthesized Farm Summaries
    farm_summary_text: str = Field(..., description="High-level farm status overview in requested language")
    major_farm_limitations: List[str] = Field(
        default_factory=list,
        description="Farm-wide limitations (e.g. suppressed volume, missing zones, unverified efficiencies)"
    )
    zone_explanations: List[ZoneExplanation] = Field(
        default_factory=list,
        description="Detailed explanations for each management zone"
    )

    method_version: str = Field(
        default="farmshield-farm-explanation-v1.0",
        description="Version identifier of farm explanation synthesizer"
    )

