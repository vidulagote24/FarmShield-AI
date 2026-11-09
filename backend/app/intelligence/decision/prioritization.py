"""Deterministic priority assignment and multi-zone operational urgency ranking.

Scientific Principles:
- Priority categories represent operational urgency, NOT an arbitrary weighted composite score.
- Ranking is governed by validated root-zone water deficit, proximity to wilting point,
  crop phenological sensitivity, and time-sensitive delivery windows.
- Insufficient-data zones are explicitly categorized as UNRANKED and segregated from active zones.
"""

from typing import List, Optional, Tuple

from backend.app.intelligence.agronomy.water_balance import WaterBalanceResult
from backend.app.intelligence.decision.types import (
    DecisionAction,
    DecisionConfig,
    DecisionPriority,
    DecisionReasonCode,
    FarmZoneContext,
    ZoneDecisionResult,
)
from backend.app.intelligence.decision.validator import extract_water_balance_metrics


def determine_zone_priority(
    action: DecisionAction,
    water_balance: Optional[WaterBalanceResult],
    farm_zone: FarmZoneContext,
    config: DecisionConfig,
) -> Tuple[DecisionPriority, List[DecisionReasonCode], List[str]]:
    """Determine operational urgency priority for a zone based on validated water deficit and crop sensitivity.

    Returns:
        Tuple of (priority, reason_codes, audit_trail).
    """
    reasons: List[DecisionReasonCode] = []
    audit: List[str] = []

    # 1. Insufficient Data -> UNRANKED
    if action == DecisionAction.INSUFFICIENT_DATA or water_balance is None:
        reasons.append(DecisionReasonCode.PRIORITY_UNRANKED_INSUFFICIENT_DATA)
        audit.append("Priority is UNRANKED due to insufficient evidence.")
        return DecisionPriority.UNRANKED, reasons, audit

    # 2. Healthy / No Action -> LOW
    if action == DecisionAction.NO_ACTION_REQUIRED:
        reasons.append(DecisionReasonCode.PRIORITY_LOW_HEALTHY)
        audit.append("Priority is LOW: root-zone moisture is healthy.")
        return DecisionPriority.LOW, reasons, audit

    dr, raw, taw, ks = extract_water_balance_metrics(water_balance)
    dr = dr or 0.0
    raw = raw or 1.0
    taw = taw or 1.0

    is_sensitive_stage = False
    if farm_zone.growth_stage:
        is_sensitive_stage = farm_zone.growth_stage.strip().lower() in config.sensitive_growth_stages

    # 3. Delay and Reassess -> Dependent on underlying deficit severity
    if action == DecisionAction.DELAY_AND_REASSESS:
        if dr >= taw or ks <= 0.20:
            reasons.append(DecisionReasonCode.PRIORITY_HIGH_RAW_EXCEEDED)
            audit.append("Priority is HIGH while delaying: severe underlying water deficit.")
            return DecisionPriority.HIGH, reasons, audit
        elif dr >= raw:
            reasons.append(DecisionReasonCode.PRIORITY_MEDIUM_MONITORING)
            audit.append("Priority is MEDIUM while delaying: deficit exceeds RAW awaiting rain.")
            return DecisionPriority.MEDIUM, reasons, audit
        else:
            reasons.append(DecisionReasonCode.PRIORITY_LOW_HEALTHY)
            audit.append("Priority is LOW while delaying: mild depletion.")
            return DecisionPriority.LOW, reasons, audit

    # 4. Monitor -> MEDIUM or HIGH if sensitive
    if action == DecisionAction.MONITOR:
        if dr >= raw:
            # Active deficit exceeding RAW deferred due to sub-economic application depth
            if is_sensitive_stage:
                reasons.append(DecisionReasonCode.PRIORITY_HIGH_SENSITIVE_STAGE)
                audit.append(
                    f"Priority is HIGH: Crop in sensitive stage '{farm_zone.growth_stage}' has active deficit "
                    f"(Dr = {dr:.1f} mm >= RAW = {raw:.1f} mm) deferred under MONITOR due to sub-economic application depth."
                )
                return DecisionPriority.HIGH, reasons, audit
            else:
                reasons.append(DecisionReasonCode.PRIORITY_MEDIUM_MONITORING)
                audit.append(
                    f"Priority is MEDIUM: Active deficit (Dr = {dr:.1f} mm >= RAW = {raw:.1f} mm) deferred under MONITOR "
                    "due to sub-economic application depth."
                )
                return DecisionPriority.MEDIUM, reasons, audit

        if is_sensitive_stage:
            reasons.append(DecisionReasonCode.PRIORITY_HIGH_SENSITIVE_STAGE)
            audit.append(
                f"Priority is HIGH: crop in sensitive stage '{farm_zone.growth_stage}' is approaching RAW."
            )
            return DecisionPriority.HIGH, reasons, audit
        else:
            reasons.append(DecisionReasonCode.PRIORITY_MEDIUM_MONITORING)
            audit.append("Priority is MEDIUM: depletion approaching RAW.")
            return DecisionPriority.MEDIUM, reasons, audit

    # 5. IRRIGATE -> CRITICAL, HIGH, or MEDIUM
    assert action == DecisionAction.IRRIGATE

    # Case A: Wilting point reached OR severe deficit during sensitive stage -> CRITICAL
    if dr >= taw or ks <= 0.20:
        reasons.append(DecisionReasonCode.PRIORITY_CRITICAL_WILTING_POINT)
        audit.append(
            f"Priority is CRITICAL: Root-zone depletion Dr ({dr:.1f} mm) >= TAW ({taw:.1f} mm) "
            f"(transpiration severely reduced, Ks = {ks:.2f}). Plant wilting hazard."
        )
        return DecisionPriority.CRITICAL, reasons, audit

    if is_sensitive_stage and (dr >= raw or ks < 1.0):
        reasons.append(DecisionReasonCode.PRIORITY_CRITICAL_FLOWERING_DEFICIT)
        audit.append(
            f"Priority is CRITICAL: Crop in sensitive flowering/yield stage '{farm_zone.growth_stage}' "
            f"is experiencing moisture stress (Dr = {dr:.1f} mm >= RAW = {raw:.1f} mm). Immediate refill required to prevent yield loss."
        )
        return DecisionPriority.CRITICAL, reasons, audit

    # Case B: Significant stress (Ks < 0.75) in vegetative stage -> HIGH
    if ks < 0.75 or (dr / taw > 0.65):
        reasons.append(DecisionReasonCode.PRIORITY_HIGH_RAW_EXCEEDED)
        audit.append(
            f"Priority is HIGH: Transpiration reduced (Ks = {ks:.2f} < 0.75, Dr/TAW = {dr/taw:.1%})."
        )
        return DecisionPriority.HIGH, reasons, audit

    # Case C: Mild exceedance in standard vegetative / ripening stage -> MEDIUM
    reasons.append(DecisionReasonCode.PRIORITY_HIGH_RAW_EXCEEDED)
    audit.append(
        f"Priority is HIGH: Deficit Dr ({dr:.1f} mm) exceeds RAW ({raw:.1f} mm), Ks = {ks:.2f}."
    )
    return DecisionPriority.HIGH, reasons, audit


def rank_zone_decisions(decisions: List[ZoneDecisionResult]) -> List[ZoneDecisionResult]:
    """Sort a list of zone decisions by deterministic operational urgency.

    Ordering Hierarchy:
    1. Priority level: CRITICAL (0) > HIGH (1) > MEDIUM (2) > LOW (3) > UNRANKED (4)
    2. Action urgency: IRRIGATE (0) > MONITOR (1) > DELAY_AND_REASSESS (2) > NO_ACTION_REQUIRED (3) > INSUFFICIENT_DATA (4)
    3. Deficit severity: descending net irrigation depth (mm)
    4. Deterministic tie-breaker: ascending zone_id
    """
    priority_order = {
        DecisionPriority.CRITICAL: 0,
        DecisionPriority.HIGH: 1,
        DecisionPriority.MEDIUM: 2,
        DecisionPriority.LOW: 3,
        DecisionPriority.UNRANKED: 4,
    }

    action_order = {
        DecisionAction.IRRIGATE: 0,
        DecisionAction.MONITOR: 1,
        DecisionAction.DELAY_AND_REASSESS: 2,
        DecisionAction.NO_ACTION_REQUIRED: 3,
        DecisionAction.INSUFFICIENT_DATA: 4,
    }

    def _sort_key(d: ZoneDecisionResult) -> Tuple[int, int, float, str]:
        p_rank = priority_order.get(d.priority, 5)
        a_rank = action_order.get(d.action_type, 5)
        # Descending depth: invert depth
        depth_rank = -(d.net_irrigation_depth_mm or 0.0)
        return (p_rank, a_rank, depth_rank, d.zone_id)

    return sorted(decisions, key=_sort_key)
