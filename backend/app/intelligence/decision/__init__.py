"""Evidence-grounded irrigation decision engine and prioritization module.

Translates validated root-zone water balance (Phase 3) and multimodal stress assessments (Phase 4)
into actionable, prioritized irrigation advisories.
"""

from backend.app.intelligence.decision.engine import (
    calculate_split_application_depths,
    evaluate_farm_decisions,
    evaluate_zone_decision,
)
from backend.app.intelligence.decision.prioritization import (
    determine_zone_priority,
    rank_zone_decisions,
)
from backend.app.intelligence.decision.rules import (
    RuleEvaluationOutcome,
    evaluate_decision_rules,
)
from backend.app.intelligence.decision.types import (
    DecisionAction,
    DecisionConfig,
    DecisionPriority,
    DecisionReasonCode,
    EfficiencyProvenance,
    EfficiencyVerificationRecord,
    FarmDecisionSummary,
    FarmZoneContext,
    IrrigationHistoryContext,
    VolumeCalculationStatus,
    WeatherForecastContext,
    ZoneDecisionResult,
)
from backend.app.intelligence.decision.validator import (
    EvidenceValidationResult,
    ForecastValidationResult,
    validate_agronomic_non_watering_isolation,
    validate_forecast_evidence,
    validate_irrigation_quantities,
    validate_water_balance_evidence,
)

__all__ = [
    "DecisionAction",
    "DecisionPriority",
    "DecisionReasonCode",
    "EfficiencyProvenance",
    "EfficiencyVerificationRecord",
    "VolumeCalculationStatus",
    "WeatherForecastContext",
    "IrrigationHistoryContext",
    "FarmZoneContext",
    "DecisionConfig",
    "ZoneDecisionResult",
    "FarmDecisionSummary",
    "evaluate_zone_decision",
    "evaluate_farm_decisions",
    "calculate_split_application_depths",
    "determine_zone_priority",
    "rank_zone_decisions",
    "evaluate_decision_rules",
    "RuleEvaluationOutcome",
    "validate_water_balance_evidence",
    "validate_forecast_evidence",
    "validate_irrigation_quantities",
    "validate_agronomic_non_watering_isolation",
    "EvidenceValidationResult",
    "ForecastValidationResult",
]

