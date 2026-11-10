"""Explanation and intelligence synthesis module for FarmShield AI.

Produces structured, audience-specific explanations (farmer and agronomist)
for all zone decisions and farm summaries in English, Marathi, and Hindi.
"""

from backend.app.intelligence.explanations.evidence_builder import build_evidence_inventory
from backend.app.intelligence.explanations.explanation_service import (
    build_farm_explanation,
    build_zone_explanation,
)
from backend.app.intelligence.explanations.reason_codes import (
    AgronomyReasonCode,
    resolve_reason_code,
)
from backend.app.intelligence.explanations.types import (
    AgronomistTechnicalExplanation,
    EvidenceItem,
    EvidenceType,
    ExplanationLanguage,
    FarmExplanation,
    ReasonCodeExplanation,
    ZoneExplanation,
)

__all__ = [
    "ExplanationLanguage",
    "EvidenceType",
    "EvidenceItem",
    "ReasonCodeExplanation",
    "AgronomyReasonCode",
    "AgronomistTechnicalExplanation",
    "ZoneExplanation",
    "FarmExplanation",
    "build_zone_explanation",
    "build_farm_explanation",
    "resolve_reason_code",
    "build_evidence_inventory",
]

