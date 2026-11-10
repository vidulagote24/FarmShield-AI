"""Deterministic decision rules for zone-level irrigation action selection.

Explicit Decision Precedence Hierarchy:
1. Precedence 1: Invalid or Insufficient Evidence Gating -> INSUFFICIENT_DATA (UNRANKED)
   (Data quality status, sensor defects, staleness, unapproved provisional empirical rainfall)
2. Precedence 2: Valid Emergency Water-Deficit Condition -> IRRIGATE (CRITICAL)
   (Severe wilting point hazard Dr >= TAW, Ks <= 0.20; overrides forecast and redistribution deferrals)
3. Precedence 3: Forecast or Redistribution Deferral Where Safe -> DELAY_AND_REASSESS
   - 3A: Imminent Significant Weather Forecast Rain Delay (within horizon, prob >= threshold, fresh)
   - 3B: Recent Irrigation Redistribution Delay (< 24h elapsed since last application)
4. Precedence 4: Standard Irrigation Threshold -> IRRIGATE or MONITOR
   - 4A: Deficit below minimum economical depth (Dr < min_economic_depth_mm) -> MONITOR (sub-economic)
   - 4B: Deficit exceeds RAW and >= min depth -> IRRIGATE
5. Precedence 5: Monitor or No-Action Outcomes
   - 5A: Water Deficit Approaching RAW (>= 80% RAW or sensitive stage) -> MONITOR
   - 5B: Healthy Root-Zone Water Content (< 80% RAW) -> NO_ACTION_REQUIRED
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.app.intelligence.agronomy.water_balance import WaterBalanceResult
from backend.app.intelligence.decision.types import (
    DecisionAction,
    DecisionConfig,
    DecisionReasonCode,
    FarmZoneContext,
    IrrigationHistoryContext,
    WeatherForecastContext,
)
from backend.app.intelligence.decision.validator import (
    EvidenceValidationResult,
    extract_water_balance_metrics,
    validate_forecast_evidence,
)


class RuleEvaluationOutcome:
    """Outcome of rule pipeline execution."""

    def __init__(self, action: DecisionAction) -> None:
        self.action: DecisionAction = action
        self.rules_triggered: List[str] = []
        self.reason_codes: List[DecisionReasonCode] = []
        self.assumptions: List[str] = []
        self.limitations: List[str] = []
        self.forecast_dependency: Optional[Dict[str, Any]] = None
        self.audit_trail: List[str] = []


def evaluate_decision_rules(
    validation: EvidenceValidationResult,
    water_balance: Optional[WaterBalanceResult],
    farm_zone: FarmZoneContext,
    forecast: Optional[WeatherForecastContext],
    history: Optional[IrrigationHistoryContext],
    config: DecisionConfig,
    as_of_time: Optional[datetime] = None,
) -> RuleEvaluationOutcome:
    """Execute the deterministic rule pipeline to determine the zone's DecisionAction.

    Returns:
        RuleEvaluationOutcome detailing action, fired rules, reason codes, and audit notes.
    """
    now_utc = as_of_time or datetime.now(timezone.utc)

    # --------------------------------------------------------------------------
    # PRECEDENCE 1: Invalid or Insufficient Evidence Gating
    # Safety Invariant: Emergency status NEVER overrides insufficient or suspect data quality!
    # --------------------------------------------------------------------------
    if not validation.is_valid and validation.is_insufficient:
        out = RuleEvaluationOutcome(DecisionAction.INSUFFICIENT_DATA)
        out.rules_triggered.append("RULE_1_INSUFFICIENT_EVIDENCE_GATING")
        out.reason_codes.extend(validation.blocking_reasons)
        out.assumptions.append("Missing required root-zone water balance evidence; action withheld.")
        out.limitations.extend(validation.audit_trail)
        out.audit_trail.append("Rule 1 fired: Insufficient evidence blocks irrigation decisions.")
        return out

    if not validation.is_valid and (validation.is_stale or validation.is_suspect):
        out = RuleEvaluationOutcome(DecisionAction.INSUFFICIENT_DATA)
        out.rules_triggered.append("RULE_2_STALE_OR_SUSPECT_EVIDENCE_GATING")
        out.reason_codes.extend(validation.blocking_reasons)
        out.assumptions.append("Water balance evidence is stale or suspect; action withheld for data integrity.")
        out.limitations.extend(validation.audit_trail)
        out.audit_trail.append("Rule 2 fired: Stale or suspect evidence blocks irrigation decisions.")
        return out

    if not validation.is_valid and validation.is_provisional_blocked:
        out = RuleEvaluationOutcome(DecisionAction.INSUFFICIENT_DATA)
        out.rules_triggered.append("RULE_3_PROVISIONAL_RAINFALL_GATING")
        out.reason_codes.extend(validation.blocking_reasons)
        out.assumptions.append(
            "Effective rainfall was estimated via unapproved provisional empirical formula. "
            "Action withheld per Phase 3.2.4 agronomic safety protocol."
        )
        out.limitations.append("Provisional rainfall method requires explicit allow_provisional_rainfall opt-in.")
        out.audit_trail.append("Rule 3 fired: Provisional empirical rainfall blocked.")
        return out

    # At this point, water_balance is guaranteed valid and verified
    assert water_balance is not None
    dr, raw, taw, ks = extract_water_balance_metrics(water_balance)
    dr = dr or 0.0
    raw = raw or 1.0
    taw = taw or 1.0

    # Pre-validate weather forecast evidence if present
    forecast_val = validate_forecast_evidence(
        forecast=forecast,
        config=config,
        deficit_dr_mm=dr,
        raw_mm=raw,
        as_of_time=now_utc,
    )
    if forecast is not None:
        raw_p = (
            forecast.forecast_total_precipitation_mm
            if forecast.forecast_total_precipitation_mm is not None
            else forecast.forecast_precipitation_mm
        )
        out_forecast_dep = {
            "forecast_precipitation_mm": raw_p,
            "forecast_total_precipitation_mm": raw_p,
            "forecast_effective_rainfall_mm": forecast.forecast_effective_rainfall_mm,
            "forecast_etc_mm": forecast_val.forecast_etc_mm,
            "forecast_etc_period_hours": forecast_val.forecast_etc_period_hours,
            "forecast_etc_rate_mm_per_hour": forecast_val.forecast_etc_rate_mm_per_hour,
            "is_etc_window_valid": forecast_val.is_etc_window_valid,
            "etc_valid_from": forecast_val.etc_valid_from.isoformat() if forecast_val.etc_valid_from else None,
            "etc_valid_to": forecast_val.etc_valid_to.isoformat() if forecast_val.etc_valid_to else None,
            "is_stress_onset_estimated": forecast_val.is_stress_onset_estimated,
            "pre_rain_depletion_mm": forecast_val.pre_rain_depletion_mm,
            "dr_at_rainfall_onset_mm": forecast_val.dr_at_rainfall_onset_mm,
            "projected_depletion_mm": forecast_val.projected_depletion_mm,
            "rainfall_onset_hours": forecast_val.rainfall_onset_hours,
            "stress_onset_hours": forecast_val.stress_onset_hours,
            "rainfall_after_stress": forecast_val.rainfall_after_stress,
            "reassessment_timestamp": forecast_val.reassessment_timestamp.isoformat() if forecast_val.reassessment_timestamp else None,
            "reassessment_interval_hours": forecast_val.reassessment_interval_hours,
            "effective_rainfall_method": forecast.effective_rainfall_method,
            "effective_rainfall_provenance": forecast.effective_rainfall_provenance,
            "forecast_period_hours": forecast.forecast_period_hours,
            "forecast_probability": forecast.forecast_probability,
            "forecast_source": forecast.forecast_source,
            "delay_threshold_mm": config.forecast_rain_delay_threshold_mm,
            "probability_threshold": config.forecast_probability_threshold,
            "is_actionable": forecast_val.is_actionable,
            "is_provisional_deferral": forecast_val.is_provisional_deferral,
            "audit": forecast_val.audit_trail,
            "warnings": forecast_val.warnings,
        }
    else:
        out_forecast_dep = None

    # --------------------------------------------------------------------------
    # PRECEDENCE 2: Valid Emergency Water-Deficit Condition
    # Wilting point reached: Dr >= TAW and Ks <= 0.20, or is_wilting_point_reached
    # Overrides weather forecast delay and irrigation redistribution deferral
    # --------------------------------------------------------------------------
    is_wilting_point = getattr(water_balance, "is_wilting_point_reached", False)
    is_emergency_deficit = (dr >= taw and ks <= 0.20) or is_wilting_point

    if is_emergency_deficit:
        out = RuleEvaluationOutcome(DecisionAction.IRRIGATE)
        out.rules_triggered.append("RULE_2_EMERGENCY_WATER_DEFICIT_OVERRIDE")
        out.reason_codes.append(DecisionReasonCode.ACTION_IRRIGATE_EMERGENCY_OVERRIDE)
        out.reason_codes.append(DecisionReasonCode.ACTION_IRRIGATE_WILTING_POINT_HAZARD)
        out.reason_codes.append(DecisionReasonCode.ACTION_IRRIGATE_DEPLETION_EXCEEDS_RAW)
        if ks < 1.0:
            out.reason_codes.append(DecisionReasonCode.ACTION_IRRIGATE_KS_STRESS_ACTIVE)
        if forecast is not None and DecisionReasonCode.FORECAST_ETC_MISSING in forecast_val.reasons:
            out.reason_codes.append(DecisionReasonCode.FORECAST_ETC_MISSING)
        if forecast is not None and DecisionReasonCode.FORECAST_ETC_WINDOW_INSUFFICIENT in forecast_val.reasons:
            out.reason_codes.append(DecisionReasonCode.FORECAST_ETC_WINDOW_INSUFFICIENT)
        out.forecast_dependency = out_forecast_dep

        out.assumptions.append(
            f"Valid emergency moisture deficit: Root-zone depletion Dr ({dr:.1f} mm) >= TAW ({taw:.1f} mm) "
            f"with acute transpiration reduction (Ks = {ks:.2f} <= 0.20). Plant wilting hazard is active."
        )

        # Check for contradictory measurement: recent irrigation logged within 24h
        if history is not None and history.last_irrigated_at is not None:
            last_dt = history.last_irrigated_at
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            elapsed_hours = (now_utc - last_dt).total_seconds() / 3600.0
            if 0.0 <= elapsed_hours < history.redistribution_hours:
                out.reason_codes.append(DecisionReasonCode.WARNING_CONTRADICTORY_RECENT_IRRIGATION)
                warning_msg = (
                    f"Contradictory measurement: Zone was recorded as irrigated {elapsed_hours:.1f}h ago "
                    f"({history.last_depth_mm or 'unrecorded'} mm), yet physical soil water evidence indicates "
                    f"emergency wilting depletion (Dr = {dr:.1f} mm >= TAW = {taw:.1f} mm, Ks = {ks:.2f}). "
                    "Possible application hardware failure, severe emitter clog, or sensor anomaly. "
                    "Emergency override triggered to prioritize immediate inspection and water application."
                )
                out.assumptions.append(warning_msg)
                out.audit_trail.append(f"Contradictory warning: {warning_msg}")

        # Check if forecast rain was present (noting why it is overridden)
        if forecast is not None and forecast.forecast_precipitation_mm >= config.forecast_rain_delay_threshold_mm:
            out.assumptions.append(
                f"Imminent forecast rainfall ({forecast.forecast_precipitation_mm:.1f} mm) is acknowledged "
                "but overridden: unobserved atmospheric forecast cannot defer action during acute permanent wilting."
            )
            out.audit_trail.append("Forecast delay overridden by emergency wilting condition.")

        out.audit_trail.append(
            f"Precedence 2 fired: Emergency root-zone depletion Dr ({dr:.1f} mm) >= TAW ({taw:.1f} mm). IRRIGATE."
        )
        return out

    # --------------------------------------------------------------------------
    # PRECEDENCE 3: Forecast or Redistribution Deferral Where Safe
    # --------------------------------------------------------------------------
    # 3A. Weather Forecast Rain Delay Policy (Effective Rain vs Root-Zone Deficit)
    if forecast_val.is_actionable and forecast is not None:
        out = RuleEvaluationOutcome(DecisionAction.DELAY_AND_REASSESS)
        out.rules_triggered.append("RULE_4_SIGNIFICANT_WEATHER_FORECAST_DELAY")
        out.reason_codes.append(DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN)
        for r in forecast_val.reasons:
            if r not in out.reason_codes:
                out.reason_codes.append(r)
        out.forecast_dependency = out_forecast_dep

        prob_str = f"{forecast.forecast_probability:.0%}" if forecast.forecast_probability is not None else "unspecified"
        if forecast.forecast_effective_rainfall_mm is not None:
            etc_info = f", projected ETc: {forecast_val.forecast_etc_mm:.1f} mm" if forecast_val.forecast_etc_mm is not None else ""
            proj_info = f", projected Dr: {forecast_val.projected_depletion_mm:.1f} mm <= RAW {raw:.1f} mm" if forecast_val.projected_depletion_mm is not None else ""
            out.assumptions.append(
                f"Significant effective rainfall ({forecast.forecast_effective_rainfall_mm:.1f} mm out of {raw_p:.1f} mm total) "
                f"is forecast within {forecast.forecast_period_hours:.0f} hours by {forecast.forecast_source} (prob: {prob_str}{etc_info}{proj_info}). "
                f"Effective rainfall relieves root-zone deficit Dr ({dr:.1f} mm vs RAW {raw:.1f} mm). Deferring irrigation."
            )
        else:
            onset_str = (
                f"Rainfall onset at {forecast_val.rainfall_onset_hours:.1f}h verified before projected stress onset at {forecast_val.stress_onset_hours:.1f}h."
                if (forecast_val.rainfall_onset_hours is not None and forecast_val.stress_onset_hours is not None)
                else "Rainfall arrival verified before stress onset."
            )
            out.assumptions.append(
                "Provisional forecast-deferral policy applied: in-situ infiltration/runoff parameters unavailable; "
                f"deferral is based on raw NWP precipitation ({raw_p:.1f} mm within {forecast.forecast_period_hours:.0f}h by {forecast.forecast_source}, prob: {prob_str}). "
                f"{onset_str}"
            )
            if forecast_val.forecast_etc_rate_mm_per_hour is not None:
                out.assumptions.append(
                    f"Uniform hourly ETc rate ({forecast_val.forecast_etc_rate_mm_per_hour:.3f} mm/h derived from cumulative "
                    f"{forecast_val.forecast_etc_mm:.1f} mm over {forecast_val.forecast_etc_period_hours:.1f}h window) applied under documented provisional approximation."
                )
            if forecast_val.reassessment_timestamp is not None:
                out.assumptions.append(
                    f"Provisional forecast-deferral reassessment scheduled at {forecast_val.reassessment_timestamp.isoformat()} "
                    f"(in {forecast_val.reassessment_interval_hours:.0f}h)."
                )
        out.audit_trail.append(
            f"Rule 4 fired: Actionable forecast rain ({raw_p:.1f} mm total, prob {prob_str}). Delaying irrigation."
        )
        return out

    # 3B. Recent Irrigation Redistribution Delay
    if history is not None and history.last_irrigated_at is not None:
        last_dt = history.last_irrigated_at
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        elapsed_hours = (now_utc - last_dt).total_seconds() / 3600.0

        if 0.0 <= elapsed_hours < history.redistribution_hours:
            out = RuleEvaluationOutcome(DecisionAction.DELAY_AND_REASSESS)
            out.rules_triggered.append("RULE_5_RECENT_IRRIGATION_REDISTRIBUTION_DELAY")
            out.reason_codes.append(DecisionReasonCode.ACTION_DELAY_RECENT_IRRIGATION)
            out.forecast_dependency = out_forecast_dep
            out.assumptions.append(
                f"Zone was irrigated {elapsed_hours:.1f} hours ago ({history.last_depth_mm or 'unrecorded'} mm). "
                f"Soil water requires {history.redistribution_hours:.0f} hours to redistribute. "
                "Reassess after redistribution is complete."
            )
            out.audit_trail.append(
                f"Rule 5 fired: Irrigation applied {elapsed_hours:.1f}h ago < {history.redistribution_hours:.0f}h redistribution window."
            )
            return out

    # --------------------------------------------------------------------------
    # PRECEDENCE 4: Standard Irrigation Threshold (Dr >= RAW or Ks < 1.0)
    # Includes Minimum Application Depth Edge Case Evaluation
    # --------------------------------------------------------------------------
    is_exceeding_raw = getattr(water_balance, "is_depletion_exceeding_raw", False) or getattr(water_balance, "is_in_stress_zone", False)
    if dr >= raw or ks < 1.0 or is_exceeding_raw:
        # Check Minimum Economic Application Depth
        if dr < config.min_economical_depth_mm:
            out = RuleEvaluationOutcome(DecisionAction.MONITOR)
            out.rules_triggered.append("RULE_6_SUB_ECONOMIC_DEFICIT_MONITOR")
            out.reason_codes.append(DecisionReasonCode.ACTION_MONITOR_DEFICIT_BELOW_MIN_DEPTH)
            out.forecast_dependency = out_forecast_dep
            out.assumptions.append(
                f"Root-zone water depletion ({dr:.1f} mm) exceeds RAW ({raw:.1f} mm), indicating an active deficit. "
                f"However, calculated refill depth is below the minimum economic application threshold "
                f"({config.min_economical_depth_mm:.1f} mm). Deferring water application under MONITOR "
                "until depletion reaches an economically viable application depth."
            )
            out.audit_trail.append(
                f"Rule 6 fired: Deficit Dr ({dr:.1f} mm) >= RAW ({raw:.1f} mm) but < min_economical_depth "
                f"({config.min_economical_depth_mm:.1f} mm). Action: MONITOR (sub-economic deficit)."
            )
            return out

        out = RuleEvaluationOutcome(DecisionAction.IRRIGATE)
        out.rules_triggered.append("RULE_6_WATER_DEFICIT_EXCEEDS_RAW")
        out.reason_codes.append(DecisionReasonCode.ACTION_IRRIGATE_DEPLETION_EXCEEDS_RAW)
        out.forecast_dependency = out_forecast_dep

        if DecisionReasonCode.FORECAST_INSUFFICIENT_DEFICIT_RELIEF in forecast_val.reasons:
            out.reason_codes.append(DecisionReasonCode.FORECAST_INSUFFICIENT_DEFICIT_RELIEF)
        if DecisionReasonCode.FORECAST_RAINFALL_AFTER_STRESS in forecast_val.reasons:
            out.reason_codes.append(DecisionReasonCode.FORECAST_RAINFALL_AFTER_STRESS)
        if DecisionReasonCode.FORECAST_ETC_MISSING in forecast_val.reasons:
            out.reason_codes.append(DecisionReasonCode.FORECAST_ETC_MISSING)
        if DecisionReasonCode.FORECAST_ETC_WINDOW_INSUFFICIENT in forecast_val.reasons:
            out.reason_codes.append(DecisionReasonCode.FORECAST_ETC_WINDOW_INSUFFICIENT)
            out.assumptions.append(
                "Forecast ETc validity window is insufficient or does not cover lookahead until rainfall onset; "
                "uniform rate cannot be extrapolated beyond valid window. Deferral withheld; decision based on valid current water-balance evidence."
            )
        if DecisionReasonCode.FORECAST_PROVISIONAL_OPT_IN_REQUIRED in forecast_val.reasons:
            out.reason_codes.append(DecisionReasonCode.FORECAST_PROVISIONAL_OPT_IN_REQUIRED)
        if DecisionReasonCode.FORECAST_PROVISIONAL_BLOCKED_ACTIVE_DEFICIT in forecast_val.reasons:
            out.reason_codes.append(DecisionReasonCode.FORECAST_PROVISIONAL_BLOCKED_ACTIVE_DEFICIT)
            out.assumptions.append(
                f"Provisional forecast deferral based on raw NWP precipitation is blocked: root-zone depletion Dr "
                f"({dr:.1f} mm) is at or beyond RAW ({raw:.1f} mm). Unverified gross atmospheric precipitation alone "
                "cannot defer irrigation during active deficit without verified effective rainfall and ETc evidence."
            )
        if DecisionReasonCode.FORECAST_PROVISIONAL_OPT_IN_REQUIRED in forecast_val.reasons:
            out.reason_codes.append(DecisionReasonCode.FORECAST_PROVISIONAL_OPT_IN_REQUIRED)

        if ks < 1.0:
            out.reason_codes.append(DecisionReasonCode.ACTION_IRRIGATE_KS_STRESS_ACTIVE)
        if dr >= taw or ks <= 0.20 or getattr(water_balance, "is_wilting_point_reached", False):
            out.reason_codes.append(DecisionReasonCode.ACTION_IRRIGATE_WILTING_POINT_HAZARD)

        out.assumptions.append(
            f"Root-zone water depletion ({dr:.1f} mm) exceeds RAW ({raw:.1f} mm), reducing crop transpiration (Ks = {ks:.2f}). "
            "Irrigation is recommended to refill the root zone back to Field Capacity."
        )
        out.audit_trail.append(
            f"Rule 6 fired: Root-zone deficit Dr ({dr:.1f} mm) >= RAW ({raw:.1f} mm). Triggering IRRIGATE."
        )
        return out

    # --------------------------------------------------------------------------
    # PRECEDENCE 5: Monitor or No-Action Outcomes
    # --------------------------------------------------------------------------
    # 5A. Water Deficit Approaching RAW -> MONITOR
    approach_threshold = config.raw_approach_threshold_fraction * raw
    is_sensitive_stage = False
    if farm_zone.growth_stage:
        is_sensitive_stage = farm_zone.growth_stage.strip().lower() in config.sensitive_growth_stages

    # Sensitive stage triggers monitoring earlier (at 70% RAW)
    effective_approach = 0.70 * raw if is_sensitive_stage else approach_threshold

    if dr >= effective_approach:
        out = RuleEvaluationOutcome(DecisionAction.MONITOR)
        out.rules_triggered.append("RULE_7_WATER_DEFICIT_APPROACHING_RAW")
        out.reason_codes.append(DecisionReasonCode.ACTION_MONITOR_APPROACHING_RAW)
        out.forecast_dependency = out_forecast_dep

        if DecisionReasonCode.FORECAST_RAINFALL_AFTER_STRESS in forecast_val.reasons:
            out.reason_codes.append(DecisionReasonCode.FORECAST_RAINFALL_AFTER_STRESS)
        if DecisionReasonCode.FORECAST_INSUFFICIENT_DEFICIT_RELIEF in forecast_val.reasons:
            out.reason_codes.append(DecisionReasonCode.FORECAST_INSUFFICIENT_DEFICIT_RELIEF)
        if DecisionReasonCode.FORECAST_ETC_MISSING in forecast_val.reasons:
            out.reason_codes.append(DecisionReasonCode.FORECAST_ETC_MISSING)
        if DecisionReasonCode.FORECAST_ETC_WINDOW_INSUFFICIENT in forecast_val.reasons:
            out.reason_codes.append(DecisionReasonCode.FORECAST_ETC_WINDOW_INSUFFICIENT)
            out.assumptions.append(
                "Forecast ETc validity window is insufficient or does not cover lookahead until rainfall onset; "
                "uniform rate cannot be extrapolated beyond valid window. Deferral withheld; decision based on valid current water-balance evidence."
            )
        if DecisionReasonCode.FORECAST_PROVISIONAL_OPT_IN_REQUIRED in forecast_val.reasons:
            out.reason_codes.append(DecisionReasonCode.FORECAST_PROVISIONAL_OPT_IN_REQUIRED)

        if is_sensitive_stage:
            out.reason_codes.append(DecisionReasonCode.ACTION_MONITOR_SENSITIVE_STAGE)
            out.assumptions.append(
                f"Crop is in sensitive growth stage '{farm_zone.growth_stage}'. "
                f"Depletion ({dr:.1f} mm) is approaching threshold ({effective_approach:.1f} mm). Monitor closely."
            )
        else:
            out.assumptions.append(
                f"Root-zone water depletion ({dr:.1f} mm) is approaching RAW ({raw:.1f} mm) "
                f"({dr/raw:.1%} of RAW). Plant transpiration is currently unconstrained (Ks = 1.00)."
            )
        out.audit_trail.append(
            f"Rule 7 fired: Depletion Dr ({dr:.1f} mm) approaching RAW ({raw:.1f} mm). Triggering MONITOR."
        )
        return out

    # 5B. Healthy Root-Zone Moisture -> NO_ACTION_REQUIRED
    out = RuleEvaluationOutcome(DecisionAction.NO_ACTION_REQUIRED)
    out.rules_triggered.append("RULE_8_HEALTHY_ROOT_ZONE_WATER_CONTENT")
    out.reason_codes.append(DecisionReasonCode.ACTION_NO_ACTION_ROOT_ZONE_HEALTHY)
    if DecisionReasonCode.FORECAST_ETC_MISSING in forecast_val.reasons:
        out.reason_codes.append(DecisionReasonCode.FORECAST_ETC_MISSING)
    if DecisionReasonCode.FORECAST_ETC_WINDOW_INSUFFICIENT in forecast_val.reasons:
        out.reason_codes.append(DecisionReasonCode.FORECAST_ETC_WINDOW_INSUFFICIENT)
    if DecisionReasonCode.FORECAST_RAINFALL_AFTER_STRESS in forecast_val.reasons:
        out.reason_codes.append(DecisionReasonCode.FORECAST_RAINFALL_AFTER_STRESS)
    if DecisionReasonCode.FORECAST_PROVISIONAL_OPT_IN_REQUIRED in forecast_val.reasons:
        out.reason_codes.append(DecisionReasonCode.FORECAST_PROVISIONAL_OPT_IN_REQUIRED)
    out.forecast_dependency = out_forecast_dep
    out.assumptions.append(
        f"Root-zone water content is well within readily available limits (Dr = {dr:.1f} mm, RAW = {raw:.1f} mm, Ks = 1.00). "
        "No irrigation action is currently necessary."
    )
    out.audit_trail.append(
        f"Rule 8 fired: Depletion Dr ({dr:.1f} mm) < approach threshold ({effective_approach:.1f} mm). NO_ACTION_REQUIRED."
    )
    return out
