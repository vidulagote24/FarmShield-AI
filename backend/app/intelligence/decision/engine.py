"""Core orchestration engine for zone-level irrigation decisions and farm-level synthesis.

Scientific & Architectural Rules (per PRD.md, AI_SPEC.md, DATA_MODEL.md):
1. Purely Deterministic: No LLM, no ML models, no black-box scores.
2. Evidence-Grounded Gating: IRRIGATE is generated ONLY when water-balance evidence is valid.
3. Quantity Validation: Validates net refill, gross depth, and volumetric conversions.
4. Non-Watering Isolation: Vegetation anomalies and soil chemical hazards never inflate irrigation amounts.
5. Incomplete Data Safeguards: Never computes a misleading farm-wide volume from incomplete zones.
"""

import math
from decimal import Decimal, ROUND_HALF_UP, ROUND_FLOOR
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.app.intelligence.agronomy.irrigation_requirement import IrrigationMethodEfficiency
from backend.app.intelligence.agronomy.water_balance import WaterBalanceResult
from backend.app.intelligence.decision.prioritization import (
    determine_zone_priority,
    rank_zone_decisions,
)
from backend.app.intelligence.decision.rules import evaluate_decision_rules
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
    extract_water_balance_metrics,
    validate_agronomic_non_watering_isolation,
    validate_irrigation_quantities,
    validate_water_balance_evidence,
)
from backend.app.intelligence.stress.assessment import ZoneStressAssessment
from backend.app.intelligence.types import DataQualityStatus, StressStatus


def calculate_split_application_depths(
    gross_depth_mm: float,
    max_event_depth_mm: float,
    precision: int = 2,
) -> Tuple[List[float], float, int]:
    """Calculate exact split-application depths satisfying maximum event limits.

    Integrity Guarantees (Phase 5.2.2 Audit):
    1. Maximum bound invariant: max_event_depth_mm is NEVER rounded upward;
       uses downward rounding (ROUND_FLOOR) at configured output precision and validates
       against the original Decimal maximum bound.
    2. Exact integer ceiling division: avoids floating-point division errors.
    3. Strict validation: validates max_cents > 0 and max_event_depth_mm > 0.
    4. Exact sum conservation: sum of event depths exactly equals total gross depth to chosen precision.
    5. Production safety enforcement: explicit runtime exceptions rather than assertions alone.

    Args:
        gross_depth_mm: Total required gross irrigation depth (mm).
        max_event_depth_mm: Maximum single-event gross depth limit (mm).
        precision: Decimal precision for event depth scheduling (default 2).

    Returns:
        Tuple of (split_event_depths, rounded_total_gross, event_count).
    """
    if not isinstance(precision, int) or isinstance(precision, bool) or precision < 0:
        raise ValueError(f"precision must be a non-negative integer, got {precision!r}")

    if gross_depth_mm < 0.0:
        raise ValueError(f"gross_depth_mm cannot be negative, got {gross_depth_mm}")

    if gross_depth_mm == 0.0:
        return [], 0.0, 0

    if max_event_depth_mm <= 0.0:
        raise ValueError(f"max_event_depth_mm must be positive, got {max_event_depth_mm}")

    orig_dec_max = Decimal(str(max_event_depth_mm))
    scale = 10 ** precision
    quant = Decimal("10") ** -precision

    # Downward rounding ensures configured limit is NEVER rounded upward
    dec_max_down = orig_dec_max.quantize(quant, rounding=ROUND_FLOOR)
    max_cents = int(dec_max_down * scale)
    if max_cents <= 0:
        raise ValueError(
            f"Configured max_event_depth_mm ({max_event_depth_mm}) rounds downward to 0 "
            f"at precision {precision}. Must be >= {1.0 / scale}."
        )

    dec_total = Decimal(str(gross_depth_mm)).quantize(quant, rounding=ROUND_HALF_UP)
    total_rounded = float(dec_total)
    total_cents = int(dec_total * scale)

    if total_cents <= 0:
        return [], 0.0, 0

    # If single event satisfies both down-rounded bound and original bound
    if total_cents <= max_cents and dec_total <= orig_dec_max:
        return [total_rounded], total_rounded, 1

    # Exact integer ceiling division: (total_cents + max_cents - 1) // max_cents
    num_events = (total_cents + max_cents - 1) // max_cents
    base_cents = total_cents // num_events
    remainder_cents = total_cents % num_events

    depths: List[float] = []
    # Base cents to (num_events - remainder_cents) events, (base_cents + 1) to remainder_cents events
    for _ in range(num_events - remainder_cents):
        depths.append(round(base_cents / scale, precision))
    for _ in range(remainder_cents):
        depths.append(round((base_cents + 1) / scale, precision))

    # Production safety enforcements
    if any(Decimal(str(d)) > orig_dec_max for d in depths):
        raise ValueError(
            f"Maximum bound invariant violated: event in {depths} exceeds original maximum {orig_dec_max} mm"
        )
    if any(int(round(d * scale)) > max_cents for d in depths):
        raise ValueError(
            f"Maximum bound invariant violated: event in {depths} exceeds down-rounded limit {dec_max_down} mm"
        )
    if abs(sum(depths) - total_rounded) > 1e-5:
        raise ValueError(
            f"Sum conservation invariant violated: sum({depths})={sum(depths)} does not equal total={total_rounded}"
        )

    return depths, total_rounded, num_events


def _resolve_application_efficiency(
    explicit_efficiency: Optional[float],
    explicit_provenance: Optional[EfficiencyProvenance],
    irrigation_system_type: Optional[str],
    verification_record: Optional[EfficiencyVerificationRecord] = None,
    zone_id: Optional[str] = None,
) -> Tuple[Optional[float], EfficiencyProvenance, bool, bool, Optional[EfficiencyVerificationRecord], str]:
    """Resolve system application efficiency fraction and record its provenance and structured verification metadata.

    Efficiency Provenance Classification Policy (per Phase 5.2.2 Audit):
    - MEASURED: COMPLETE_MEASURED ONLY with a valid, structured EfficiencyVerificationRecord
      documenting in-situ field measurement. Arbitrary reference strings alone do NOT qualify.
    - OPERATOR_ENTERED: COMPLETE_PROVISIONAL unless supported by a valid EfficiencyVerificationRecord.
    - PROVIDER_SOURCED: COMPLETE_PROVISIONAL (equipment manufacturer spec; not in-situ field measurement).
    - ASSUMED_DEFAULT: COMPLETE_PROVISIONAL (generic FAO-56 benchmark lookup).
    - UNKNOWN: SUPPRESSED_UNKNOWN_EFFICIENCY (gross depth and volume strictly withheld).

    Returns:
        Tuple of (efficiency, provenance, is_provisional, is_verified, verification_record, description).
    """
    if explicit_efficiency is not None and 0.0 < explicit_efficiency <= 1.0:
        prov = explicit_provenance or EfficiencyProvenance.OPERATOR_ENTERED

        # Evaluate structured verification record
        is_verified = False
        if verification_record is not None:
            is_verified = verification_record.is_verified_field_measurement(
                expected_zone_id=zone_id,
                expected_efficiency=explicit_efficiency,
            )

        if prov == EfficiencyProvenance.MEASURED:
            if is_verified:
                return (
                    explicit_efficiency,
                    EfficiencyProvenance.MEASURED,
                    False,  # COMPLETE_MEASURED
                    True,
                    verification_record,
                    f"Documented in-situ field measurement via {verification_record.verification_method} "
                    f"({verification_record.supporting_audit_reference}, {verification_record.measurement_date})",
                )
            else:
                return (
                    explicit_efficiency,
                    EfficiencyProvenance.MEASURED,
                    True,  # PROVISIONAL because unverified!
                    False,
                    verification_record,
                    f"Measured efficiency ({explicit_efficiency:.2f}) claimed but lacks valid structured verification record (provisional)",
                )

        elif prov == EfficiencyProvenance.OPERATOR_ENTERED:
            if is_verified:
                return (
                    explicit_efficiency,
                    EfficiencyProvenance.MEASURED,
                    False,  # Verified field measurement qualifies for measured!
                    True,
                    verification_record,
                    f"Operator-entered efficiency ({explicit_efficiency:.2f}) verified by in-situ audit ({verification_record.supporting_audit_reference})",
                )
            else:
                return (
                    explicit_efficiency,
                    EfficiencyProvenance.OPERATOR_ENTERED,
                    True,  # Unverified operator entry -> provisional!
                    False,
                    verification_record,
                    f"Operator-entered application efficiency ({explicit_efficiency:.2f}) without structured field verification (provisional)",
                )

        elif prov == EfficiencyProvenance.PROVIDER_SOURCED:
            return (
                explicit_efficiency,
                EfficiencyProvenance.PROVIDER_SOURCED,
                True,  # Manufacturer spec is NOT field measurement!
                False,
                verification_record,
                f"Equipment manufacturer specification efficiency ({explicit_efficiency:.2f}) (provider_sourced; provisional)",
            )

        elif prov == EfficiencyProvenance.ASSUMED_DEFAULT:
            return (
                explicit_efficiency,
                EfficiencyProvenance.ASSUMED_DEFAULT,
                True,
                False,
                None,
                f"Generic FAO-56 benchmark standard ({explicit_efficiency:.2f}) (provisional)",
            )

        elif prov == EfficiencyProvenance.UNKNOWN:
            return (
                None,
                EfficiencyProvenance.UNKNOWN,
                True,
                False,
                None,
                "Application efficiency is unknown; gross depth and volume cannot be determined",
            )

    if irrigation_system_type:
        st = irrigation_system_type.strip().lower()
        eff: Optional[float] = None
        if "drip" in st:
            eff = IrrigationMethodEfficiency.DRIP.value
        elif "micro" in st:
            eff = IrrigationMethodEfficiency.MICRO_SPRINKLER.value
        elif "pivot" in st:
            eff = IrrigationMethodEfficiency.CENTER_PIVOT.value
        elif "sprinkler" in st:
            eff = IrrigationMethodEfficiency.SOLID_SET_SPRINKLER.value
        elif "furrow" in st:
            eff = IrrigationMethodEfficiency.FURROW_SURFACE.value
        elif "basin" in st or "flood" in st:
            eff = IrrigationMethodEfficiency.BASIN_FLOOD.value

        if eff is not None:
            return (
                eff,
                EfficiencyProvenance.ASSUMED_DEFAULT,
                True,
                False,
                None,
                f"Generic FAO-56 benchmark ({eff:.2f}) for system '{irrigation_system_type}' (provisional)",
            )

    return (
        None,
        EfficiencyProvenance.UNKNOWN,
        True,
        False,
        None,
        "Application efficiency is unknown; gross depth and volume cannot be determined",
    )


def evaluate_zone_decision(
    farm_zone: FarmZoneContext,
    water_balance: Optional[WaterBalanceResult],
    stress_assessment: Optional[ZoneStressAssessment] = None,
    forecast: Optional[WeatherForecastContext] = None,
    history: Optional[IrrigationHistoryContext] = None,
    config: Optional[DecisionConfig] = None,
    as_of_time: Optional[datetime] = None,
) -> ZoneDecisionResult:
    """Evaluate deterministic irrigation decision support for a single management zone.

    Args:
        farm_zone: Farm and zone metadata context.
        water_balance: Phase 3 daily water-balance result.
        stress_assessment: Optional Phase 4 multimodal stress assessment.
        forecast: Optional weather forecast context.
        history: Optional irrigation history context.
        config: Optional decision policy configuration.
        as_of_time: UTC timestamp of evaluation.

    Returns:
        Structured, auditable ZoneDecisionResult.
    """
    cfg = config or DecisionConfig()
    now_utc = as_of_time or datetime.now(timezone.utc)

    # 1. Validate Water Balance Evidence
    evidence_val = validate_water_balance_evidence(water_balance, cfg, now_utc)

    # 2. Extract Non-Watering Agronomic Attention Flags
    non_water_reasons, non_water_assumptions, non_water_audit = validate_agronomic_non_watering_isolation(
        stress_assessment, water_balance
    )

    # 3. Deterministic Decision Rule Pipeline
    rule_outcome = evaluate_decision_rules(
        validation=evidence_val,
        water_balance=water_balance,
        farm_zone=farm_zone,
        forecast=forecast,
        history=history,
        config=cfg,
        as_of_time=now_utc,
    )

    # Merge non-watering reasons and assumptions
    all_reasons: List[DecisionReasonCode] = list(rule_outcome.reason_codes)
    for r in non_water_reasons:
        if r not in all_reasons:
            all_reasons.append(r)

    all_assumptions: List[str] = list(rule_outcome.assumptions)
    all_assumptions.extend(non_water_assumptions)

    all_limitations: List[str] = list(rule_outcome.limitations)
    if water_balance and getattr(water_balance, "scientific_limitations", None):
        all_limitations.extend(water_balance.scientific_limitations)

    # 4. Determine Priority Category
    priority, prio_reasons, prio_audit = determine_zone_priority(
        action=rule_outcome.action,
        water_balance=water_balance,
        farm_zone=farm_zone,
        config=cfg,
    )
    for pr in prio_reasons:
        if pr not in all_reasons:
            all_reasons.append(pr)

    # 5. Calculate Irrigation Quantities & Split Applications
    net_depth: Optional[float] = None
    gross_depth: Optional[float] = None
    volume_m3: Optional[float] = None
    applied_eff: Optional[float] = None
    applied_eff_prov: Optional[EfficiencyProvenance] = None
    is_eff_prov: bool = False
    is_eff_verified: bool = False
    eff_record: Optional[EfficiencyVerificationRecord] = None
    eff_meas_ref: Optional[str] = None
    split_app_required: bool = False
    split_cnt: Optional[int] = None
    split_depths: List[float] = []
    per_event_gross: Optional[float] = None
    tot_gross: Optional[float] = None
    min_depth_threshold: Optional[float] = None
    qty_validation_meta: Dict[str, Any] = {}

    if rule_outcome.action == DecisionAction.IRRIGATE and water_balance is not None:
        dr, _, _, _ = extract_water_balance_metrics(water_balance)
        dr = dr or 0.0
        net_depth = round(max(0.0, dr), 2)

        applied_eff, applied_eff_prov, is_eff_prov, is_eff_verified, eff_record, eff_provenance = _resolve_application_efficiency(
            explicit_efficiency=farm_zone.application_efficiency,
            explicit_provenance=farm_zone.application_efficiency_provenance,
            irrigation_system_type=farm_zone.irrigation_system_type,
            verification_record=farm_zone.efficiency_verification,
            zone_id=farm_zone.zone_id,
        )

        if applied_eff is not None:
            raw_gross = net_depth / applied_eff
            gross_depth = round(raw_gross, 2)
            tot_gross = gross_depth

            if applied_eff_prov == EfficiencyProvenance.MEASURED and not is_eff_prov:
                all_reasons.append(DecisionReasonCode.EFFICIENCY_MEASURED)
                audit_str = f" ({eff_record.supporting_audit_reference})" if eff_record else ""
                all_assumptions.append(f"In-situ measured application efficiency eta = {applied_eff:.2f}{audit_str}.")
            elif applied_eff_prov == EfficiencyProvenance.PROVIDER_SOURCED:
                all_reasons.append(DecisionReasonCode.EFFICIENCY_PROVIDER_SOURCED)
                all_reasons.append(DecisionReasonCode.EFFICIENCY_PROVISIONAL_ASSUMPTION)
                all_assumptions.append(
                    f"System application efficiency eta = {applied_eff:.2f} (manufacturer hardware specification; not a field measurement)."
                )
            elif applied_eff_prov == EfficiencyProvenance.OPERATOR_ENTERED:
                if is_eff_prov:
                    all_reasons.append(DecisionReasonCode.EFFICIENCY_OPERATOR_UNVERIFIED)
                    all_reasons.append(DecisionReasonCode.EFFICIENCY_PROVISIONAL_ASSUMPTION)
                    all_assumptions.append(
                        f"Operator configured application efficiency eta = {applied_eff:.2f} (unverified in-situ; provisional)."
                    )
                else:
                    all_reasons.append(DecisionReasonCode.EFFICIENCY_MEASURED)
                    audit_str = f": {eff_record.supporting_audit_reference}" if eff_record else ""
                    all_assumptions.append(
                        f"Operator configured application efficiency eta = {applied_eff:.2f} (verified field measurement{audit_str})."
                    )
            elif is_eff_prov:
                all_reasons.append(DecisionReasonCode.EFFICIENCY_PROVISIONAL_ASSUMPTION)
                all_assumptions.append(f"System application efficiency eta = {applied_eff:.2f} ({eff_provenance}).")
            else:
                all_assumptions.append(f"Operator configured application efficiency eta = {applied_eff:.2f}.")

            # Split Application Arithmetic & Mass Conservation
            split_depths, rounded_gross, split_cnt = calculate_split_application_depths(
                gross_depth_mm=gross_depth,
                max_event_depth_mm=cfg.max_allowable_gross_depth_mm,
                precision=2,
            )
            gross_depth = rounded_gross
            per_event_gross = split_depths[0] if split_depths else None
            split_app_required = split_cnt > 1

            if split_app_required:
                all_reasons.append(DecisionReasonCode.ACTION_IRRIGATE_SPLIT_APPLICATION_REQUIRED)
                all_assumptions.append(
                    f"Total gross irrigation requirement ({gross_depth:.2f} mm) exceeds single-event operational limit "
                    f"({cfg.max_allowable_gross_depth_mm:.1f} mm). Split application required: {split_cnt} cycles "
                    f"({split_depths} mm) to prevent surface runoff, ponding, and hypoxia. Configured limit is an operational "
                    "policy constraint, not an invariant universal soil-physics constant."
                )

            if farm_zone.zone_area_ha is not None and farm_zone.zone_area_ha > 0.0:
                # 1 mm * 1 ha = 10 m³
                volume_m3 = round(gross_depth * farm_zone.zone_area_ha * 10.0, 2)
            else:
                volume_m3 = None
                all_limitations.append("Zone area is unrecorded; gross volumetric requirement (m³) remains null.")
        else:
            gross_depth = None
            volume_m3 = None
            split_app_required = False
            split_cnt = None
            split_depths = []
            per_event_gross = None
            tot_gross = None
            all_reasons.append(DecisionReasonCode.EFFICIENCY_UNKNOWN_WITHHELD)
            all_limitations.append(
                "Application efficiency eta is unknown; gross depth and volume are withheld while net refill depth "
                f"({net_depth:.1f} mm) is reported independently."
            )

        # Validate Quantities
        is_qty_valid, qty_errs, qty_validation_meta = validate_irrigation_quantities(
            net_depth_mm=net_depth,
            gross_depth_mm=gross_depth,
            efficiency=applied_eff,
            area_ha=farm_zone.zone_area_ha,
            volume_m3=volume_m3,
            config=cfg,
        )
        if not is_qty_valid:
            all_limitations.extend(qty_errs)

    elif rule_outcome.action == DecisionAction.MONITOR:
        if DecisionReasonCode.ACTION_MONITOR_DEFICIT_BELOW_MIN_DEPTH in all_reasons and water_balance is not None:
            dr, _, _, _ = extract_water_balance_metrics(water_balance)
            dr = dr or 0.0
            net_depth = round(dr, 2)
            min_depth_threshold = cfg.min_economical_depth_mm
            qty_validation_meta["sub_economic_net_depth_mm"] = net_depth
            qty_validation_meta["min_economic_threshold_mm"] = cfg.min_economical_depth_mm
        else:
            net_depth = None
        gross_depth = None
        volume_m3 = None
        applied_eff = None
        applied_eff_prov = None
        is_eff_prov = False
        split_app_required = False
        split_cnt = None
        split_depths = []
        per_event_gross = None
        tot_gross = None
    else:
        # Non-irrigate actions have null depths
        net_depth = None
        gross_depth = None
        volume_m3 = None
        applied_eff = None
        applied_eff_prov = None
        is_eff_prov = False
        split_app_required = False
        split_cnt = None
        split_depths = []
        per_event_gross = None
        tot_gross = None

    # 6. Assemble Input Provenance
    source_prov: Dict[str, Any] = {
        "water_balance_available": water_balance is not None,
        "water_balance_quality": water_balance.quality_status.value if water_balance else "missing",
        "effective_rainfall_method": getattr(water_balance, "effective_rainfall_method", None),
        "is_provisional_rainfall": getattr(water_balance, "is_provisional_empirical", False),
        "crop_type": farm_zone.crop_type,
        "growth_stage": farm_zone.growth_stage,
        "forecast_considered": forecast is not None,
        "irrigation_history_considered": history is not None,
        "efficiency_provenance": applied_eff_prov.value if applied_eff_prov else "none",
        "is_efficiency_provisional": is_eff_prov,
    }

    # 7. Preserve Phase 4 Domain Assessments
    domain_assessments: Dict[str, Any] = {}
    if stress_assessment is not None:
        st_status = getattr(stress_assessment, "status", None) or getattr(stress_assessment, "overall_status", None)
        doms = getattr(stress_assessment, "domain_assessments", {})
        wat = getattr(stress_assessment, "water_evaluation", None) or doms.get("water")
        veg = getattr(stress_assessment, "vegetation_evaluation", None) or doms.get("vegetation")
        wea = getattr(stress_assessment, "weather_evaluation", None) or doms.get("weather")
        soi = getattr(stress_assessment, "soil_evaluation", None) or doms.get("soil")

        domain_assessments = {
            "overall_status": st_status.value if st_status else "unknown",
            "water": wat.status.value if wat else "unknown",
            "vegetation": veg.status.value if veg else "unknown",
            "weather": wea.status.value if wea else "unknown",
            "soil": soi.status.value if soi else "unknown",
            "stress_reason_codes": [r.value for r in getattr(stress_assessment, "reason_codes", [])],
        }

    # Evidence Quality Status
    if not evidence_val.is_valid:
        evidence_quality = DataQualityStatus.INSUFFICIENT
    elif water_balance and water_balance.quality_status in (DataQualityStatus.PARTIAL, DataQualityStatus.SUSPECT):
        evidence_quality = water_balance.quality_status
    else:
        evidence_quality = DataQualityStatus.GOOD

    forecast_reassess_ts: Optional[datetime] = None
    forecast_reassess_hrs: Optional[float] = None
    if rule_outcome.action == DecisionAction.DELAY_AND_REASSESS and rule_outcome.forecast_dependency:
        raw_ts = rule_outcome.forecast_dependency.get("reassessment_timestamp")
        if raw_ts:
            try:
                forecast_reassess_ts = datetime.fromisoformat(raw_ts)
            except Exception:
                forecast_reassess_ts = None
        forecast_reassess_hrs = rule_outcome.forecast_dependency.get("reassessment_interval_hours")

    return ZoneDecisionResult(
        farm_id=farm_zone.farm_id,
        zone_id=farm_zone.zone_id,
        decision_timestamp=now_utc,
        action_type=rule_outcome.action,
        priority=priority,
        net_irrigation_depth_mm=net_depth,
        gross_irrigation_depth_mm=gross_depth,
        irrigation_volume_m3=volume_m3,
        application_efficiency=applied_eff,
        application_efficiency_provenance=applied_eff_prov,
        is_efficiency_provisional=is_eff_prov,
        is_efficiency_verified=is_eff_verified,
        efficiency_measurement_reference=eff_record.supporting_audit_reference if eff_record else farm_zone.efficiency_measurement_reference,
        efficiency_verification=eff_record,
        split_application_required=split_app_required,
        split_event_count=split_cnt,
        per_event_gross_depth_mm=per_event_gross,
        total_gross_irrigation_depth_mm=tot_gross,
        split_event_depths_mm=split_depths,
        min_depth_threshold_mm=min_depth_threshold,
        evidence_quality=evidence_quality,
        source_and_provenance=source_prov,
        reason_codes=all_reasons,
        decision_rules_triggered=rule_outcome.rules_triggered,
        assumptions=all_assumptions,
        unresolved_limitations=all_limitations,
        forecast_dependency=rule_outcome.forecast_dependency,
        forecast_reassessment_timestamp=forecast_reassess_ts,
        forecast_reassessment_interval_hours=forecast_reassess_hrs,
        validation_results={
            "evidence": evidence_val.to_dict(),
            "quantities": qty_validation_meta,
        },
        domain_assessments=domain_assessments,
        method_version="farmshield-decision-v1.0",
    )


def evaluate_farm_decisions(
    farm_id: str,
    zone_contexts: List[FarmZoneContext],
    water_balances: Dict[str, Optional[WaterBalanceResult]],
    stress_assessments: Optional[Dict[str, Optional[ZoneStressAssessment]]] = None,
    weather_forecasts: Optional[Dict[str, Optional[WeatherForecastContext]]] = None,
    irrigation_histories: Optional[Dict[str, Optional[IrrigationHistoryContext]]] = None,
    config: Optional[DecisionConfig] = None,
    as_of_time: Optional[datetime] = None,
) -> FarmDecisionSummary:
    """Evaluate decisions across all zones in a farm, rank by operational urgency, and synthesize summary.

    Args:
        farm_id: Unique farm identifier.
        zone_contexts: List of FarmZoneContext objects for all zones.
        water_balances: Mapping of zone_id -> WaterBalanceResult.
        stress_assessments: Mapping of zone_id -> ZoneStressAssessment.
        weather_forecasts: Mapping of zone_id -> WeatherForecastContext.
        irrigation_histories: Mapping of zone_id -> IrrigationHistoryContext.
        config: Optional decision configuration.
        as_of_time: UTC timestamp.

    Returns:
        FarmDecisionSummary aggregating actions, rankings, and validated total water volume.
    """
    now_utc = as_of_time or datetime.now(timezone.utc)
    cfg = config or DecisionConfig()

    decisions: List[ZoneDecisionResult] = []
    actions_count: Dict[str, int] = {
        DecisionAction.IRRIGATE.value: 0,
        DecisionAction.MONITOR.value: 0,
        DecisionAction.DELAY_AND_REASSESS.value: 0,
        DecisionAction.NO_ACTION_REQUIRED.value: 0,
        DecisionAction.INSUFFICIENT_DATA.value: 0,
    }
    insufficient_zones: List[str] = []

    for z_ctx in zone_contexts:
        zid = z_ctx.zone_id
        wb = water_balances.get(zid)
        sa = stress_assessments.get(zid) if stress_assessments else None
        fc = weather_forecasts.get(zid) if weather_forecasts else None
        hist = irrigation_histories.get(zid) if irrigation_histories else None

        res = evaluate_zone_decision(
            farm_zone=z_ctx,
            water_balance=wb,
            stress_assessment=sa,
            forecast=fc,
            history=hist,
            config=cfg,
            as_of_time=now_utc,
        )
        decisions.append(res)
        actions_count[res.action_type.value] += 1

        if res.action_type == DecisionAction.INSUFFICIENT_DATA:
            insufficient_zones.append(zid)

    # Deterministic Multi-Zone Urgency Ranking
    ranked_decisions = rank_zone_decisions(decisions)

    # Farm-Wide Total Volume Calculation & Reliability Classification
    total_volume: Optional[float] = 0.0
    volume_complete: bool = True
    volume_audit: List[str] = []

    irrigated_zones = [d for d in decisions if d.action_type == DecisionAction.IRRIGATE]

    provisional_zone_ids = [
        iz.zone_id for iz in irrigated_zones if iz.is_efficiency_provisional
    ]
    has_provisional_eff = len(provisional_zone_ids) > 0

    if not irrigated_zones:
        total_volume = 0.0
        volume_complete = True
        calc_status = VolumeCalculationStatus.ZERO_IRRIGATION
        volume_audit.append("Zero zones require irrigation; total estimated volume is 0.0 m³.")
    else:
        missing_eff_zones = [iz.zone_id for iz in irrigated_zones if iz.application_efficiency is None]
        missing_area_zones = [
            iz.zone_id for iz in irrigated_zones if iz.application_efficiency is not None and iz.irrigation_volume_m3 is None
        ]

        if missing_eff_zones:
            total_volume = None
            volume_complete = False
            calc_status = VolumeCalculationStatus.SUPPRESSED_UNKNOWN_EFFICIENCY
            for zid in missing_eff_zones:
                volume_audit.append(
                    f"Zone '{zid}' requires irrigation but application efficiency is unknown (volume withheld). "
                    "Farm-wide volume sum is suppressed to prevent misleading partial totals."
                )
        elif missing_area_zones:
            total_volume = None
            volume_complete = False
            calc_status = VolumeCalculationStatus.SUPPRESSED_MISSING_AREA
            for zid in missing_area_zones:
                volume_audit.append(
                    f"Zone '{zid}' requires irrigation but lacks recorded area (ha). "
                    "Farm-wide volume sum is suppressed to prevent misleading partial totals."
                )
        else:
            total_volume = round(sum(iz.irrigation_volume_m3 for iz in irrigated_zones if iz.irrigation_volume_m3 is not None), 2)
            volume_complete = True
            if has_provisional_eff:
                calc_status = VolumeCalculationStatus.COMPLETE_PROVISIONAL
                volume_audit.append(
                    f"Total gross irrigation volume across {len(irrigated_zones)} zone(s): {total_volume:.1f} m³. "
                    f"Volume is numerically calculable but PROVISIONAL: zone(s) {provisional_zone_ids} rely on assumed efficiency."
                )
            else:
                calc_status = VolumeCalculationStatus.COMPLETE_MEASURED
                volume_audit.append(
                    f"Total gross irrigation volume across {len(irrigated_zones)} zone(s): {total_volume:.1f} m³. "
                    "Volume is COMPLETE and based on in-situ MEASURED application efficiency across all irrigated zones."
                )

    return FarmDecisionSummary(
        farm_id=farm_id,
        summary_timestamp=now_utc,
        total_zones=len(zone_contexts),
        actions_by_category=actions_count,
        prioritized_zone_decisions=ranked_decisions,
        insufficient_data_zones=insufficient_zones,
        total_estimated_irrigation_volume_m3=total_volume,
        volume_calculation_complete=volume_complete,
        has_provisional_efficiency=has_provisional_eff,
        provisional_zone_ids=provisional_zone_ids,
        volume_calculation_status=calc_status,
        volume_audit_notes=volume_audit,
    )
