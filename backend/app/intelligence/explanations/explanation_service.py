"""Deterministic explanation service synthesizing evidence-grounded natural language explanations.

Scientific and Operational Principles (per AGENTS.md, AI_SPEC.md, DATA_MODEL.md):
1. Explaining, Never Calculating:
   This service consumes validated decisions, water balances, and multimodal evidence.
   It NEVER calculates new irrigation depths, volumes, stress scores, or overrides actions.
2. Complete Traceability:
   Every explanatory sentence is generated deterministically from explicit inputs and rule outcomes.
3. Multilingual Templates:
   English, Marathi, and Hindi templates preserve numbers, physical units, and operational constraints.
4. Transparency Regarding Net vs Gross Quantities & Efficiency:
   - Every IRRIGATE explanation distinguishes physical net crop water refill requirement
     from gross application depth and efficiency provenance.
   - Gross application depth is never labeled as net crop water demand.
   - If efficiency is unknown, net depth is reported while gross depth and volume are withheld.
5. Split Application Integrity:
   When Phase 5 splits an application, total gross requirement, event count, and per-event depths
   are explicitly communicated. The farmer is never instructed to apply a split quantity in one event.
6. No Overgeneralized Health Claims:
   NO_ACTION_REQUIRED strictly states that current water-balance evidence does not indicate a need
   for irrigation. It never claims the zone is universally healthy when independent agronomic concerns
   (salinity, alkalinity, vegetation decline, frost/heat) exist.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.app.intelligence.agronomy.water_balance import WaterBalanceResult
from backend.app.intelligence.decision.types import (
    DecisionAction,
    DecisionPriority,
    DecisionReasonCode,
    FarmDecisionSummary,
    FarmZoneContext,
    VolumeCalculationStatus,
    WeatherForecastContext,
    ZoneDecisionResult,
)
from backend.app.intelligence.explanations.evidence_builder import build_evidence_inventory
from backend.app.intelligence.explanations.reason_codes import resolve_reason_code
from backend.app.intelligence.explanations.types import (
    AgronomistTechnicalExplanation,
    ExplanationLanguage,
    FarmExplanation,
    ReasonCodeExplanation,
    ZoneExplanation,
)
from backend.app.intelligence.features.feature_builder import MultimodalZoneFeatureSet
from backend.app.intelligence.stress.assessment import ZoneStressAssessment


# ==============================================================================
# 1. ZONE EXPLANATION BUILDER
# ==============================================================================

def build_zone_explanation(
    decision: ZoneDecisionResult,
    water_balance: Optional[WaterBalanceResult] = None,
    stress_assessment: Optional[ZoneStressAssessment] = None,
    features: Optional[MultimodalZoneFeatureSet] = None,
    farm_zone: Optional[FarmZoneContext] = None,
    forecast: Optional[WeatherForecastContext] = None,
    language: ExplanationLanguage = ExplanationLanguage.EN,
) -> ZoneExplanation:
    """Generate a deterministic, evidence-grounded explanation for an individual zone decision.

    Args:
        decision: Evaluated Phase 5 ZoneDecisionResult.
        water_balance: Optional WaterBalanceResult from Phase 3.
        stress_assessment: Optional ZoneStressAssessment from Phase 4.
        features: Optional MultimodalZoneFeatureSet from Phase 2.
        farm_zone: Optional FarmZoneContext static metadata.
        forecast: Optional WeatherForecastContext meteorological inputs.
        language: Target human language (EN, MR, HI).

    Returns:
        Structured ZoneExplanation containing plain-language farmer sections,
        itemized evidence inventory, resolved reason codes, and agronomist metrics.
    """
    zone_id = decision.zone_id
    farm_id = decision.farm_id
    action = decision.action_type
    priority = decision.priority

    # 1. Extract and structure supporting evidence
    (
        evidence_items,
        measurements,
        missing_evidence,
        stale_or_suspect_evidence,
        provisional_flags,
    ) = build_evidence_inventory(
        decision=decision,
        water_balance=water_balance,
        stress_assessment=stress_assessment,
        features=features,
        farm_zone=farm_zone,
        forecast=forecast,
    )

    # 2. Resolve reason codes
    resolved_reasons: List[ReasonCodeExplanation] = []
    raw_reason_strings: List[str] = []
    for r in decision.reason_codes:
        code_str = r.value if hasattr(r, "value") else str(r)
        raw_reason_strings.append(code_str)
        resolved_reasons.append(resolve_reason_code(code_str, language=language))

    # 3. Formulate Plain-Language Farmer Text
    short_summary, why_produced, action_guidance = _render_farmer_text(
        decision=decision,
        water_balance=water_balance,
        stress_assessment=stress_assessment,
        farm_zone=farm_zone,
        forecast=forecast,
        missing_evidence=missing_evidence,
        language=language,
    )

    # 4. Formulate Agronomist Technical Section
    agronomist_expl = _build_agronomist_explanation(
        decision=decision,
        water_balance=water_balance,
        stress_assessment=stress_assessment,
        features=features,
        farm_zone=farm_zone,
        forecast=forecast,
    )

    # 5. Compile Assumptions and Limitations
    all_assumptions = list(decision.assumptions)
    all_limitations = list(decision.unresolved_limitations)
    for r_expl in resolved_reasons:
        for lim in r_expl.limitations:
            if lim not in all_limitations:
                all_limitations.append(lim)

    return ZoneExplanation(
        farm_id=farm_id,
        zone_id=zone_id,
        decision_reference=decision.method_version,
        action=action,
        priority=priority,
        explanation_timestamp=datetime.now(timezone.utc),
        language=language,
        short_summary=short_summary,
        why_decision_produced=why_produced,
        action_guidance=action_guidance,
        net_irrigation_depth_mm=round(float(decision.net_irrigation_depth_mm), 2) if decision.net_irrigation_depth_mm is not None else None,
        gross_irrigation_depth_mm=round(float(decision.gross_irrigation_depth_mm), 2) if decision.gross_irrigation_depth_mm is not None else None,
        irrigation_volume_m3=round(float(decision.irrigation_volume_m3), 2) if decision.irrigation_volume_m3 is not None else None,
        application_efficiency=round(float(decision.application_efficiency), 3) if decision.application_efficiency is not None else None,
        application_efficiency_provenance=decision.application_efficiency_provenance.value if decision.application_efficiency_provenance else None,
        is_efficiency_verified=decision.is_efficiency_verified,
        is_efficiency_provisional=decision.is_efficiency_provisional,
        supporting_evidence=evidence_items,
        relevant_measurements=measurements,
        reason_codes=raw_reason_strings,
        resolved_reason_explanations=resolved_reasons,
        missing_evidence=missing_evidence,
        stale_or_suspect_evidence=stale_or_suspect_evidence,
        assumptions=all_assumptions,
        provisional_calculation_flags=provisional_flags,
        uncertainty_and_limitations=all_limitations,
        reassessment_timestamp=decision.forecast_reassessment_timestamp,
        reassessment_interval_hours=decision.forecast_reassessment_interval_hours,
        agronomist_explanation=agronomist_expl,
        method_version="farmshield-explanation-v1.0",
    )


# ==============================================================================
# 2. FARM EXPLANATION BUILDER
# ==============================================================================

def build_farm_explanation(
    summary: FarmDecisionSummary,
    zone_explanations: List[ZoneExplanation],
    language: ExplanationLanguage = ExplanationLanguage.EN,
) -> FarmExplanation:
    """Synthesize a farm-level explanation summarizing all zone actions and volumetric reliability.

    Args:
        summary: Evaluated FarmDecisionSummary from Phase 5.
        zone_explanations: List of ZoneExplanation objects for each zone on the farm.
        language: Target human language (EN, MR, HI).

    Returns:
        Structured FarmExplanation containing categorized zone lists, volume status,
        audit warnings, and a plain-language executive summary.
    """
    farm_id = summary.farm_id
    total_zones = summary.total_zones

    # Categorize zones from summary decisions
    irrig_zones: List[str] = []
    mon_zones: List[str] = []
    delay_zones: List[str] = []
    insufficient_zones: List[str] = list(summary.insufficient_data_zones)
    no_act_zones: List[str] = []

    for zd in summary.prioritized_zone_decisions:
        if zd.action_type == DecisionAction.IRRIGATE:
            irrig_zones.append(zd.zone_id)
        elif zd.action_type == DecisionAction.MONITOR:
            mon_zones.append(zd.zone_id)
        elif zd.action_type == DecisionAction.DELAY_AND_REASSESS:
            delay_zones.append(zd.zone_id)
        elif zd.action_type == DecisionAction.INSUFFICIENT_DATA:
            if zd.zone_id not in insufficient_zones:
                insufficient_zones.append(zd.zone_id)
        elif zd.action_type == DecisionAction.NO_ACTION_REQUIRED:
            no_act_zones.append(zd.zone_id)

    # Compile farm-wide limitations
    farm_limits: List[str] = []
    if summary.volume_calculation_status == VolumeCalculationStatus.SUPPRESSED_MISSING_AREA:
        farm_limits.append(
            "Farm-wide irrigation volume is suppressed due to missing area (one or more irrigated zones lack recorded surface area)."
        )
    elif summary.volume_calculation_status == VolumeCalculationStatus.SUPPRESSED_UNKNOWN_EFFICIENCY:
        farm_limits.append(
            "Farm-wide irrigation volume is suppressed because application efficiency is unknown for one or more irrigated zones."
        )

    if summary.has_provisional_efficiency:
        farm_limits.append(
            f"Volumetric calculation incorporates provisional efficiency assumptions for zones: {', '.join(summary.provisional_zone_ids)}."
        )

    for n in summary.volume_audit_notes:
        if n not in farm_limits:
            farm_limits.append(n)

    # Render farm summary text
    summary_text = _render_farm_summary_text(
        farm_id=farm_id,
        total_zones=total_zones,
        irrig_count=len(irrig_zones),
        mon_count=len(mon_zones),
        delay_count=len(delay_zones),
        insufficient_count=len(insufficient_zones),
        no_action_count=len(no_act_zones),
        vol_status=summary.volume_calculation_status,
        total_vol_m3=summary.total_estimated_irrigation_volume_m3,
        language=language,
    )

    return FarmExplanation(
        farm_id=farm_id,
        explanation_timestamp=datetime.now(timezone.utc),
        language=language,
        total_zones=total_zones,
        zones_requiring_irrigation=irrig_zones,
        zones_being_monitored=mon_zones,
        delayed_zones=delay_zones,
        insufficient_data_zones=insufficient_zones,
        no_action_zones=no_act_zones,
        volume_calculation_status=summary.volume_calculation_status,
        total_estimated_volume_m3=summary.total_estimated_irrigation_volume_m3,
        volume_calculation_complete=summary.volume_calculation_complete,
        has_provisional_efficiency=summary.has_provisional_efficiency,
        provisional_zone_ids=summary.provisional_zone_ids,
        provisional_volume_warnings=list(summary.volume_audit_notes),
        farm_summary_text=summary_text,
        major_farm_limitations=farm_limits,
        zone_explanations=zone_explanations,
        method_version="farmshield-farm-explanation-v1.0",
    )


# ==============================================================================
# 3. INTERNAL RENDERING HELPERS
# ==============================================================================

def _format_efficiency_provenance_phrase(provenance: Optional[str], language: ExplanationLanguage) -> str:
    """Format human-readable efficiency provenance across languages."""
    prov = (provenance or "").lower()
    if "measured" in prov:
        if language == ExplanationLanguage.MR:
            return "शेतातील ऑडिटद्वारे सत्यापित"
        elif language == ExplanationLanguage.HI:
            return "इन-सीटू फील्ड ऑडिट द्वारा सत्यापित"
        return "verified field-measured"
    elif "operator" in prov:
        if language == ExplanationLanguage.MR:
            return "ऑपरेटरने नोंदवलेली"
        elif language == ExplanationLanguage.HI:
            return "ऑपरेटर द्वारा दर्ज"
        return "operator-entered"
    elif "provider" in prov:
        if language == ExplanationLanguage.MR:
            return "उपकरण निर्मात्याच्या तपशिलानुसार"
        elif language == ExplanationLanguage.HI:
            return "उपकरण निर्माता विनिर्देश अनुसार"
        return "manufacturer-specified"
    else:  # assumed_default or unknown
        if language == ExplanationLanguage.MR:
            return "अंदाजित डीफॉल्ट"
        elif language == ExplanationLanguage.HI:
            return "अनंतिम डिफ़ॉल्ट अनुमान"
        return "assumed default"


def _extract_independent_agronomic_alerts(
    decision: ZoneDecisionResult,
    stress_assessment: Optional[ZoneStressAssessment],
    language: ExplanationLanguage,
) -> List[str]:
    """Collect non-watering agronomic alerts from reason codes and Phase 4 stress assessment."""
    alerts: List[str] = []

    for rc in decision.reason_codes:
        rc_str = rc.value if hasattr(rc, "value") else str(rc)
        if rc_str == DecisionReasonCode.AGRONOMIC_FLAG_SOIL_SALINITY_NON_WATERING.value:
            if language == ExplanationLanguage.MR:
                alerts.append("मातीतील वाढलेले क्षार (क्षार निचरा मार्गदर्शक तत्त्वे पाळा)")
            elif language == ExplanationLanguage.HI:
                alerts.append("मृदा लवणता में वृद्धि (लीचिंग दिशानिर्देश देखें)")
            else:
                alerts.append("elevated soil salinity (consult leaching guidelines)")
        elif rc_str == DecisionReasonCode.AGRONOMIC_FLAG_SOIL_ALKALINE_NON_WATERING.value:
            if language == ExplanationLanguage.MR:
                alerts.append("अल्कधर्मी माती (pH > ८.५)")
            elif language == ExplanationLanguage.HI:
                alerts.append("क्षारीय मृदा pH (> 8.5)")
            else:
                alerts.append("alkaline soil pH (> 8.5)")
        elif rc_str == DecisionReasonCode.AGRONOMIC_FLAG_VEGETATION_ANOMALY_NON_WATERING.value:
            if language == ExplanationLanguage.MR:
                alerts.append("उपग्रहाद्वारे पिकाच्या जोमात घट (कीड/रोग/अन्नद्रव्ये तपासा)")
            elif language == ExplanationLanguage.HI:
                alerts.append("उपग्रह वनस्पति गिरावट (कीट/रोग/पोषक तत्वों की जांच करें)")
            else:
                alerts.append("satellite vegetation vigor decline (inspect for pests/disease/nutrition)")
        elif rc_str == DecisionReasonCode.AGRONOMIC_FLAG_WEATHER_HEAT_NON_WATERING.value:
            if language == ExplanationLanguage.MR:
                alerts.append("उच्च तापमान व बाष्प दाब तूट उष्णता ताण")
            elif language == ExplanationLanguage.HI:
                alerts.append("उच्च तापमान व वाष्प दाब घाटा तनाव")
            else:
                alerts.append("high temperature/VPD heat stress")
        elif rc_str == DecisionReasonCode.AGRONOMIC_FLAG_WEATHER_FROST_WARNING.value:
            if language == ExplanationLanguage.MR:
                alerts.append("गोठणबिंदू तापमान दंव/थंडीचा धोका")
            elif language == ExplanationLanguage.HI:
                alerts.append("हिमांक तापमान पाला जोखिम")
            else:
                alerts.append("freezing temperature frost hazard")

    # Domain evaluations from Phase 4 stress assessment
    if stress_assessment is not None:
        for domain, st in stress_assessment.domain_statuses.items():
            st_val = st.value if hasattr(st, "value") else str(st)
            if st_val in ("attention", "high_stress"):
                if domain == "soil" and not any("salin" in a.lower() for a in alerts):
                    if language == ExplanationLanguage.MR:
                        alerts.append("माती आरोग्य समस्या")
                    elif language == ExplanationLanguage.HI:
                        alerts.append("मृदा स्वास्थ्य चिंता")
                    else:
                        alerts.append("soil chemical condition concern")
                elif domain == "vegetation" and not any("vegetation" in a.lower() for a in alerts):
                    if language == ExplanationLanguage.MR:
                        alerts.append("पिकाच्या वाढीवर ताण")
                    elif language == ExplanationLanguage.HI:
                        alerts.append("फसल वनस्पति तनाव")
                    else:
                        alerts.append("vegetation canopy stress")
                elif domain == "weather" and not any("temperature" in a.lower() or "weather" in a.lower() for a in alerts):
                    if language == ExplanationLanguage.MR:
                        alerts.append("प्रतिकूल हवामान स्थिती")
                    elif language == ExplanationLanguage.HI:
                        alerts.append("प्रतिकूल मौसम स्थिति")
                    else:
                        alerts.append("extreme weather condition")

    return alerts


def _render_farmer_text(
    decision: ZoneDecisionResult,
    water_balance: Optional[WaterBalanceResult],
    stress_assessment: Optional[ZoneStressAssessment],
    farm_zone: Optional[FarmZoneContext],
    forecast: Optional[WeatherForecastContext],
    missing_evidence: List[str],
    language: ExplanationLanguage,
) -> Tuple[str, str, str]:
    """Render plain-language farmer text based on deterministic action outcome."""
    zid = decision.zone_id
    act = decision.action_type
    prio = decision.priority

    dr = getattr(water_balance, "final_depletion_mm", None)
    raw = getattr(water_balance, "readily_available_water_mm", None)
    taw = getattr(water_balance, "total_available_water_mm", None)
    ks = getattr(water_balance, "water_stress_coefficient_ks", None)
    d_gross = decision.gross_irrigation_depth_mm
    d_net = decision.net_irrigation_depth_mm
    eff = decision.application_efficiency
    eff_prov = decision.application_efficiency_provenance.value if decision.application_efficiency_provenance else None
    vol_m3 = decision.irrigation_volume_m3

    dr_s = f"{dr:.1f}" if dr is not None else "--"
    raw_s = f"{raw:.1f}" if raw is not None else "--"
    taw_s = f"{taw:.1f}" if taw is not None else "--"
    ks_s = f"{ks:.2f}" if ks is not None else "--"
    gross_s = f"{d_gross:.1f}" if d_gross is not None else "--"
    net_s = f"{d_net:.1f}" if d_net is not None else "--"
    eff_pct_s = f"{eff * 100:.0f}" if eff is not None else "--"
    eff_prov_s = _format_efficiency_provenance_phrase(eff_prov, language)

    # --------------------------------------------------------------------------
    # ACTION: IRRIGATE
    # --------------------------------------------------------------------------
    if act == DecisionAction.IRRIGATE:
        is_emergency = (
            prio == DecisionPriority.CRITICAL
            and DecisionReasonCode.ACTION_IRRIGATE_EMERGENCY_OVERRIDE in decision.reason_codes
        )

        # Volume phrases
        if vol_m3 is not None:
            vol_phrase_en = f", requiring an estimated total gross volume of {vol_m3:,.1f} m³ across the zone"
            vol_phrase_mr = f", ज्यासाठी या झोनमध्ये एकूण अंदाजित {vol_m3:,.1f} घनमीटर (m³) पाण्याची आवश्यकता आहे"
            vol_phrase_hi = f", जिसके लिए इस ज़ोन में कुल अनुमानित {vol_m3:,.1f} घन मीटर (m³) पानी की आवश्यकता है"
        elif farm_zone is not None and farm_zone.zone_area_ha is None:
            vol_phrase_en = " (total zone volume is withheld because zone area is unrecorded)"
            vol_phrase_mr = " (झोनचे क्षेत्रफळ नोंदवले नसल्याने एकूण आकारमान दिलेले नाही)"
            vol_phrase_hi = " (ज़ोन का क्षेत्रफल दर्ज न होने के कारण कुल आयतन रोक दिया गया है)"
        else:
            vol_phrase_en = ""
            vol_phrase_mr = ""
            vol_phrase_hi = ""

        # Check for split application
        is_split = (
            decision.split_application_required
            and decision.split_event_count is not None
            and decision.split_event_count > 1
            and len(decision.split_event_depths_mm) > 0
        )
        cnt = decision.split_event_count or 1

        if is_split:
            # Preserve exact precision of Phase 5 split depths without rounding loss
            split_prec = 1
            for d in decision.split_event_depths_mm:
                for p in range(1, 5):
                    if abs(round(d, p) - d) < 1e-6:
                        split_prec = max(split_prec, p)
                        break
            if d_gross is not None:
                for p in range(1, 5):
                    if abs(round(d_gross, p) - d_gross) < 1e-6:
                        split_prec = max(split_prec, p)
                        break
                gross_s = f"{d_gross:.{split_prec}f}"
            depths_formatted = ", ".join(f"{d:.{split_prec}f} mm" for d in decision.split_event_depths_mm)

            split_guidance_en = (
                f"Apply {gross_s} mm total gross depth across {cnt} split cycles ({depths_formatted}) "
                f"to prevent surface runoff and deep drainage losses; do not apply the entire {gross_s} mm in a single event."
            )
            split_guidance_mr = (
                f"मातीतून पाणी वाहून जाणे आणि जिरून वाया जाणे टाळण्यासाठी एकूण {gross_s} मिमी सिंचन {cnt} टप्प्यांत "
                f"विभागून ({depths_formatted}) द्या; एकाच वेळी पूर्ण {gross_s} मिमी पाणी देऊ नका."
            )
            split_guidance_hi = (
                f"मृदा अपवाह और गहरे रिसाव से होने वाले नुकसान से बचने के लिए कुल {gross_s} मिमी सिंचाई को {cnt} विभाजित "
                f"चरणों ({depths_formatted}) में दें; एक ही बार में पूरा {gross_s} मिमी पानी न दें."
            )
        else:
            depths_formatted = ", ".join(f"{d:.1f} mm" for d in decision.split_event_depths_mm)
            split_guidance_en = f"Apply {gross_s} mm gross irrigation to restore root-zone storage to Field Capacity."
            split_guidance_mr = f"जमिनीत शेत क्षमता (Field Capacity) पर्यंत ओलावा पूर्ववत करण्यासाठी {gross_s} मिमी एकूण सिंचन द्या."
            split_guidance_hi = f"जड़ क्षेत्र में खेत क्षमता (Field Capacity) तक नमी बहाल करने के लिए {gross_s} मिमी कुल सिंचाई दें."

        # Case 1A: Gross depth is AVAILABLE
        if d_gross is not None:
            if is_emergency:
                if is_split:
                    if language == ExplanationLanguage.MR:
                        short = f"तातडीची सूचना: झोन {zid} मध्ये {cnt} टप्प्यांत विभागून ({depths_formatted}) एकूण {gross_s} मिमी सिंचन त्वरित आवश्यक आहे (निव्वळ तुटवडा: {net_s} मिमी)."
                        why = (
                            f"पाण्याचा तुटवडा कायमस्वरूपी म्लानी बिंदूच्या उंबरठ्यावर पोहोचला आहे "
                            f"(कमतरता {dr_s} मिमी >= TAW {taw_s} मिमी, Ks = {ks_s}). पिकाची निव्वळ पाण्याची गरज {net_s} मिमी आहे; "
                            f"{eff_prov_s} सिंचन कार्यक्षमता ({eff_pct_s}%) विचारात घेता एकूण सिंचन खोली {gross_s} मिमी ही "
                            f"{cnt} टप्प्यांत विभागून ({depths_formatted}) आवश्यक आहे{vol_phrase_mr}."
                        )
                        guidance = split_guidance_mr
                    elif language == ExplanationLanguage.HI:
                        short = f"आपातकालीन सूचना: ज़ोन {zid} में {cnt} चरणों में विभाजित ({depths_formatted}) कुल {gross_s} मिमी सिंचाई तुरंत आवश्यक है (शुद्ध कमी: {net_s} मिमी)."
                        why = (
                            f"जल संकट स्थायी म्लानि बिंदु तक पहुँच गया है "
                            f"(कमी {dr_s} मिमी >= TAW {taw_s} मिमी, Ks = {ks_s}). शुद्ध फसल जल मांग {net_s} मिमी है; "
                            f"{eff_prov_s} सिंचाई दक्षता ({eff_pct_s}%) को ध्यान में रखते हुए कुल सिंचाई आवश्यकता {gross_s} मिमी को "
                            f"{cnt} चरणों ({depths_formatted}) में विभाजित किया गया है{vol_phrase_hi}."
                        )
                        guidance = split_guidance_hi
                    else:
                        short = f"EMERGENCY: Zone {zid} needs immediate {gross_s} mm gross irrigation across {cnt} split cycles ({depths_formatted}) (net crop deficit: {net_s} mm)."
                        why = (
                            f"Active moisture deficit has reached the permanent wilting point "
                            f"(depletion {dr_s} mm >= TAW {taw_s} mm, Ks = {ks_s}). Net crop refill demand is {net_s} mm; "
                            f"accounting for {eff_prov_s} application efficiency ({eff_pct_s}%), gross requirement is {gross_s} mm "
                            f"divided into {cnt} split cycles ({depths_formatted}){vol_phrase_en}."
                        )
                        guidance = split_guidance_en
                else:
                    if language == ExplanationLanguage.MR:
                        short = f"तातडीची सूचना: झोन {zid} मध्ये {gross_s} मिमी एकूण सिंचन त्वरित आवश्यक आहे (निव्वळ तुटवडा: {net_s} मिमी)."
                        why = (
                            f"पाण्याचा तुटवडा कायमस्वरूपी म्लानी बिंदूच्या उंबरठ्यावर पोहोचला आहे "
                            f"(कमतरता {dr_s} मिमी >= TAW {taw_s} मिमी, Ks = {ks_s}). पिकाची निव्वळ पाण्याची गरज {net_s} मिमी आहे; "
                            f"{eff_prov_s} सिंचन कार्यक्षमता ({eff_pct_s}%) विचारात घेता एकूण सिंचन खोली {gross_s} मिमी आवश्यक आहे{vol_phrase_mr}."
                        )
                        guidance = split_guidance_mr
                    elif language == ExplanationLanguage.HI:
                        short = f"आपातकालीन सूचना: ज़ोन {zid} में {gross_s} मिमी कुल सिंचाई तुरंत आवश्यक है (शुद्ध कमी: {net_s} मिमी)."
                        why = (
                            f"जल संकट स्थायी म्लानि बिंदु तक पहुँच गया है "
                            f"(कमी {dr_s} मिमी >= TAW {taw_s} मिमी, Ks = {ks_s}). शुद्ध फसल जल मांग {net_s} मिमी है; "
                            f"{eff_prov_s} सिंचाई दक्षता ({eff_pct_s}%) को ध्यान में रखते हुए कुल सिंचाई आवश्यकता {gross_s} मिमी है{vol_phrase_hi}."
                        )
                        guidance = split_guidance_hi
                    else:
                        short = f"EMERGENCY: Zone {zid} needs immediate {gross_s} mm gross irrigation (net crop deficit: {net_s} mm)."
                        why = (
                            f"Active moisture deficit has reached the permanent wilting point "
                            f"(depletion {dr_s} mm >= TAW {taw_s} mm, Ks = {ks_s}). Net crop refill demand is {net_s} mm; "
                            f"accounting for {eff_prov_s} application efficiency ({eff_pct_s}%), gross requirement is {gross_s} mm{vol_phrase_en}."
                        )
                        guidance = split_guidance_en
            else:
                if is_split:
                    if language == ExplanationLanguage.MR:
                        short = f"झोन {zid} मध्ये {cnt} टप्प्यांत विभागून ({depths_formatted}) एकूण {gross_s} मिमी सिंचन आवश्यक आहे (निव्वळ तुटवडा: {net_s} मिमी)."
                        why = (
                            f"मुळांच्या भागातील पाण्याचा तुटवडा ({dr_s} मिमी) निर्धारित मर्यादेबाहेर (RAW {raw_s} मिमी) गेला आहे. "
                            f"पिकाचे बाष्पोत्सर्जन मंदावले आहे (Ks = {ks_s}). निव्वळ पाण्याची गरज {net_s} मिमी असून, "
                            f"{eff_prov_s} सिंचन कार्यक्षमता ({eff_pct_s}%) विचारात घेता एकूण {gross_s} मिमी सिंचन हे "
                            f"{cnt} टप्प्यांत विभागून ({depths_formatted}) आवश्यक आहे{vol_phrase_mr}."
                        )
                        guidance = split_guidance_mr
                    elif language == ExplanationLanguage.HI:
                        short = f"ज़ोन {zid} में {cnt} चरणों में विभाजित ({depths_formatted}) कुल {gross_s} मिमी सिंचाई आवश्यक है (शुद्ध मांग: {net_s} मिमी)."
                        why = (
                            f"जड़ क्षेत्र में पानी की कमी ({dr_s} मिमी) निर्धारित सीमा (RAW {raw_s} मिमी) से अधिक हो गई है. "
                            f"फसल का वाष्पोत्सर्जन प्रभावित हुआ है (Ks = {ks_s}). शुद्ध फसल जल मांग {net_s} मिमी है; "
                            f"{eff_prov_s} सिंचाई दक्षता ({eff_pct_s}%) के आधार पर कुल सिंचाई आवश्यकता {gross_s} मिमी को "
                            f"{cnt} चरणों ({depths_formatted}) में विभाजित किया गया है{vol_phrase_hi}."
                        )
                        guidance = split_guidance_hi
                    else:
                        short = f"Zone {zid} needs {gross_s} mm gross irrigation across {cnt} split cycles ({depths_formatted}) (net crop deficit: {net_s} mm)."
                        why = (
                            f"Root-zone water depletion ({dr_s} mm) has reached the management threshold (RAW {raw_s} mm). "
                            f"Crop transpiration is constrained (Ks = {ks_s}). Net crop refill demand is {net_s} mm; "
                            f"accounting for {eff_prov_s} application efficiency ({eff_pct_s}%), required gross application depth is {gross_s} mm "
                            f"divided into {cnt} split cycles ({depths_formatted}){vol_phrase_en}."
                        )
                        guidance = split_guidance_en
                else:
                    if language == ExplanationLanguage.MR:
                        short = f"झोन {zid} मध्ये {gross_s} मिमी एकूण सिंचन आवश्यक आहे (निव्वळ तुटवडा: {net_s} मिमी)."
                        why = (
                            f"मुळांच्या भागातील पाण्याचा तुटवडा ({dr_s} मिमी) निर्धारित मर्यादेबाहेर (RAW {raw_s} मिमी) गेला आहे. "
                            f"पिकाचे बाष्पोत्सर्जन मंदावले आहे (Ks = {ks_s}). निव्वळ पाण्याची गरज {net_s} मिमी असून, "
                            f"{eff_prov_s} सिंचन कार्यक्षमता ({eff_pct_s}%) विचारात घेता एकूण {gross_s} मिमी सिंचन आवश्यक आहे{vol_phrase_mr}."
                        )
                        guidance = split_guidance_mr
                    elif language == ExplanationLanguage.HI:
                        short = f"ज़ोन {zid} में {gross_s} मिमी कुल सिंचाई आवश्यक है (शुद्ध मांग: {net_s} मिमी)."
                        why = (
                            f"जड़ क्षेत्र में पानी की कमी ({dr_s} मिमी) निर्धारित सीमा (RAW {raw_s} मिमी) से अधिक हो गई है. "
                            f"फसल का वाष्पोत्सर्जन प्रभावित हुआ है (Ks = {ks_s}). शुद्ध फसल जल मांग {net_s} मिमी है; "
                            f"{eff_prov_s} सिंचाई दक्षता ({eff_pct_s}%) के आधार पर कुल सिंचाई आवश्यकता {gross_s} मिमी है{vol_phrase_hi}."
                        )
                        guidance = split_guidance_hi
                    else:
                        short = f"Zone {zid} needs {gross_s} mm gross irrigation (net crop deficit: {net_s} mm)."
                        why = (
                            f"Root-zone water depletion ({dr_s} mm) has reached the management threshold (RAW {raw_s} mm). "
                            f"Crop transpiration is constrained (Ks = {ks_s}). Net crop refill demand is {net_s} mm; "
                            f"accounting for {eff_prov_s} application efficiency ({eff_pct_s}%), required gross application depth is {gross_s} mm{vol_phrase_en}."
                        )
                        guidance = split_guidance_en

        # Case 1B: Gross depth is UNAVAILABLE (efficiency unknown)
        else:
            if language == ExplanationLanguage.MR:
                short = f"झोन {zid} मध्ये निव्वळ पिकाचा पाण्याचा तुटवडा {net_s} मिमी आहे (एकूण सिंचन खोली उपलब्ध नाही)."
                why = (
                    f"मुळांच्या भागातील पाण्याचा तुटवडा ({dr_s} मिमी) निर्धारित मर्यादेबाहेर (RAW {raw_s} मिमी) गेला आहे. "
                    f"निव्वळ मातीतील ओलावा तुटवडा {net_s} मिमी आहे. सिंचन कार्यक्षमता माहित नसल्याने एकूण सिंचन खोली मोजता येत नाही; "
                    "अंदाजे पाण्याचे प्रमाण तयार करण्यास सक्त मनाई आहे."
                )
                guidance = f"पाणी देण्यापूर्वी शेत सेटिंग्जमध्ये सिंचन कार्यक्षमता तपासा आणि नोंदवा. सध्या पिकाची निव्वळ पाण्याची गरज {net_s} मिमी आहे."
            elif language == ExplanationLanguage.HI:
                short = f"ज़ोन {zid} में शुद्ध फसल जल कमी {net_s} मिमी है (कुल सिंचाई गहराई अनुपलब्ध)."
                why = (
                    f"जड़ क्षेत्र में पानी की कमी ({dr_s} मिमी) प्रबंधन सीमा (RAW {raw_s} मिमी) से अधिक है. "
                    f"शुद्ध फसल जल मांग {net_s} मिमी है. सिंचाई प्रणाली की दक्षता अज्ञात होने के कारण कुल सिंचाई गहराई की गणना नहीं की जा सकती; "
                    "कोई अनधिकृत मात्रा तय नहीं की जा सकती."
                )
                guidance = f"सिंचाई उपकरण संचालित करने से पहले सेटिंग्स में सिंचाई दक्षता सत्यापित और दर्ज करें. शुद्ध फसल जल मांग {net_s} मिमी है."
            else:
                short = f"Zone {zid} has a net crop water deficit of {net_s} mm (gross application depth unavailable)."
                why = (
                    f"Root-zone water depletion ({dr_s} mm) exceeds the management limit (RAW {raw_s} mm). "
                    f"Net crop refill requirement is {net_s} mm. Gross application depth cannot be calculated because application "
                    "efficiency is unknown; an unverified application quantity cannot be invented."
                )
                guidance = f"Configure and verify system application efficiency in farm settings before operating irrigation hardware. Net soil water refill requirement is {net_s} mm."

        return short, why, guidance

    # --------------------------------------------------------------------------
    # ACTION: MONITOR
    # --------------------------------------------------------------------------
    if act == DecisionAction.MONITOR:
        is_sub_economic = DecisionReasonCode.ACTION_MONITOR_DEFICIT_BELOW_MIN_DEPTH in decision.reason_codes
        min_depth_s = f"{decision.min_depth_threshold_mm:.1f}" if decision.min_depth_threshold_mm else "5.0"

        # Reassessment timing provenance (generic if unsupplied)
        timing_s_en = None
        timing_s_mr = None
        timing_s_hi = None
        if decision.forecast_reassessment_timestamp:
            tz_str = decision.forecast_reassessment_timestamp.tzname() or "UTC"
            ts_str = decision.forecast_reassessment_timestamp.strftime(f"%Y-%m-%d %H:%M {tz_str}")
            timing_s_en = f"next scheduled moisture reassessment at {ts_str}"
            timing_s_mr = f"पुढील नियोजित ओलावा पुनर्परीक्षण {ts_str} वाजता"
            timing_s_hi = f"अगली निर्धारित नमी समीक्षा {ts_str} पर"
        elif decision.forecast_reassessment_interval_hours is not None:
            h_val = decision.forecast_reassessment_interval_hours
            timing_s_en = f"re-check moisture levels within {h_val:.0f} hours"
            timing_s_mr = f"पुढील {h_val:.0f} तासांत ओलावा पुन्हा तपासा"
            timing_s_hi = f"अगले {h_val:.0f} घंटों में नमी की पुनः जांच करें"

        if is_sub_economic:
            if language == ExplanationLanguage.MR:
                short = f"झोन {zid} मधील पाण्याची तूट किमान किफायतशीर खोलीपेक्षा कमी आहे; निरीक्षण सुरू ठेवा."
                why = (
                    f"मुळांमधील पाण्याची कमतरता ({dr_s} मिमी) निर्धारित मर्यादेबाहेर (RAW {raw_s} मिमी) आहे, परंतु आवश्यक खोली "
                    f"किमान किफायतशीर सिंचन मर्यादेपेक्षा ({min_depth_s} मिमी) कमी आहे. पृष्ठभागावरील बाष्पीभवनाचे नुकसान फायद्यापेक्षा जास्त होईल."
                )
                guidance = f"पाण्याचा तुटवडा किमान किफायतशीर मर्यादेपर्यंत ({min_depth_s} मिमी) पोहोचेपर्यंत सिंचन पुढे ढकलून निरीक्षण सुरू ठेवा."
            elif language == ExplanationLanguage.HI:
                short = f"ज़ोन {zid} में पानी की कमी न्यूनतम किफायती अनुप्रयोग गहराई से कम है; निगरानी जारी रखें."
                why = (
                    f"जड़ क्षेत्र में पानी की कमी ({dr_s} मिमी) प्रबंधन सीमा (RAW {raw_s} मिमी) से अधिक है, लेकिन आवश्यक गहराई "
                    f"न्यूनतम किफायती सीमा ({min_depth_s} मिमी) से कम है. सतही वाष्पीकरण से होने वाला नुकसान लाभ से अधिक होगा."
                )
                guidance = f"जब तक पानी की कमी किफायती सीमा ({min_depth_s} मिमी) तक न पहुँच जाए, सिंचाई स्थगित रखकर निगरानी रखें."
            else:
                short = f"Zone {zid} has a minor deficit below economical application depth; monitoring."
                why = (
                    f"Root-zone water depletion ({dr_s} mm) exceeds management threshold (RAW {raw_s} mm), but calculated refill "
                    f"requirement is below the minimum economical depth ({min_depth_s} mm). Surface wetting losses would exceed agronomic benefits."
                )
                guidance = f"Hold irrigation under monitoring until depletion reaches an economically viable application depth ({min_depth_s} mm)."
        else:
            pct_s = f"{(dr / raw):.0%}" if (dr is not None and raw is not None and raw > 0) else "--"
            if language == ExplanationLanguage.MR:
                short = f"झोन {zid} मध्ये पाण्याची कमतरता निर्धारित मर्यादेजवळ पोहोचत आहे; नियमित निरीक्षण ठेवा."
                why = f"मुळांमधील पाण्याचा तुटवडा ({dr_s} मिमी) हा सुलभ उपलब्ध मर्यादेच्या (RAW {raw_s} मिमी) {pct_s} जवळ आहे. पिकाचे बाष्पोत्सर्जन सध्या सुरळीत आहे (Ks = {ks_s})."
                guidance = f"आज सिंचनाची आवश्यकता नाही. {timing_s_mr}." if timing_s_mr else "आज सिंचनाची आवश्यकता नाही. पुढील नियमित फेरीत ओलावा पुन्हा तपासा."
            elif language == ExplanationLanguage.HI:
                short = f"ज़ोन {zid} में पानी की कमी प्रबंधन सीमा के निकट पहुँच रही है; निगरानी जारी रखें."
                why = f"जड़ क्षेत्र में पानी की कमी ({dr_s} मिमी) सुलभ सीमा (RAW {raw_s} मिमी) के {pct_s} निकट है. फसल का वाष्पोत्सर्जन वर्तमान में अप्रतिबंधित है (Ks = {ks_s})."
                guidance = f"आज सिंचाई की आवश्यकता नहीं है. {timing_s_hi}." if timing_s_hi else "आज सिंचाई की आवश्यकता नहीं है. अगले निर्धारित चक्र में नमी की पुनः जांच करें."
            else:
                short = f"Zone {zid} is approaching the irrigation threshold; continue monitoring."
                why = f"Root-zone depletion ({dr_s} mm) is approaching Readily Available Water (RAW {raw_s} mm) ({pct_s} of RAW). Crop transpiration is unconstrained (Ks = {ks_s})."
                guidance = f"No irrigation is required today. {timing_s_en.capitalize()}." if timing_s_en else "No irrigation is required today. Re-check moisture levels in the next scheduled cycle."

        return short, why, guidance

    # --------------------------------------------------------------------------
    # ACTION: DELAY_AND_REASSESS
    # --------------------------------------------------------------------------
    if act == DecisionAction.DELAY_AND_REASSESS:
        is_recent_irrig = DecisionReasonCode.ACTION_DELAY_RECENT_IRRIGATION in decision.reason_codes

        if is_recent_irrig:
            if language == ExplanationLanguage.MR:
                short = f"नुकत्याच केलेल्या सिंचनामुळे झोन {zid} चे सिंचन पुढे ढकलण्यात आले आहे."
                why = "या झोनमध्ये नुकतेच पाणी दिले गेले होते. अचूक ओलावा मोजण्यापूर्वी गुरुत्वाकर्षण जल मातीत समान रीतीने पाझरण्यासाठी पुरेसा कालावधी आवश्यक असतो."
                guidance = "पुढील कृती करण्यापूर्वी दिलेल्या पाण्याला मातीत पूर्णपणे स्थिरावू द्या; पुढील नियमित फेरीत पुन्हा तपासणी करा."
            elif language == ExplanationLanguage.HI:
                short = f"हाल ही में की गई सिंचाई के कारण ज़ोन {zid} की सिंचाई स्थगित कर दी गई है."
                why = "इस ज़ोन में हाल ही में पानी दिया गया था. सटीक नमी मापने से पहले गुरुत्वाकर्षण जल को मिट्टी में समान रूप से पुनर्वितरित होने के लिए पर्याप्त समय आवश्यक है."
                guidance = "अगली कार्रवाई से पहले दिए गए पानी को मिट्टी में स्थिर होने दें; अगले निर्धारित चक्र में पुनः जांच करें."
            else:
                short = f"Irrigation for Zone {zid} is delayed due to recent water application."
                why = "Zone was irrigated recently. Gravitational soil water requires adequate time to redistribute uniformly through the root profile before accurate matric potential can be measured."
                guidance = "Allow applied water to equilibrate before taking further irrigation actions in the next scheduled assessment."
        else:
            # Weather Forecast Rain
            rain_val = forecast.forecast_precipitation_mm if forecast else 0.0
            prob_val = forecast.forecast_probability if forecast else None
            prob_s = f"{prob_val:.0%}" if prob_val is not None else "high"
            source_s = forecast.forecast_source if forecast else "NWP model"

            if forecast and forecast.forecast_period_hours:
                h_period = forecast.forecast_period_hours
                period_en = f"within {h_period:.0f}h"
                period_mr = f"पुढील {h_period:.0f} तासांत"
                period_hi = f"अगले {h_period:.0f} घंटों में"
            else:
                period_en = "within the forecast window"
                period_mr = "अंदाजित कालावधीत"
                period_hi = "पूर्वानुमान अवधि में"

            if decision.forecast_reassessment_timestamp:
                tz_str = decision.forecast_reassessment_timestamp.tzname() or "UTC"
                ts_str = decision.forecast_reassessment_timestamp.strftime(f"%Y-%m-%d %H:%M {tz_str}")
                reassess_guidance_en = f"Hold irrigation. Reassessment is scheduled for {ts_str} to verify actual atmospheric rainfall arrival."
                reassess_guidance_mr = f"सिंचन थांबवा. प्रत्यक्ष पावसाच्या आगमनाची खात्री करण्यासाठी {ts_str} वाजता पुनर्परीक्षण निर्धारित आहे."
                reassess_guidance_hi = f"सिंचाई रोकें. वास्तविक वर्षा के आगमन की पुष्टि के लिए {ts_str} पर पुनर्मूल्यांकन निर्धारित है."
            elif decision.forecast_reassessment_interval_hours is not None:
                h_int = decision.forecast_reassessment_interval_hours
                reassess_guidance_en = f"Hold irrigation. Reassessment is scheduled within {h_int:.0f} hours to verify actual atmospheric rainfall arrival."
                reassess_guidance_mr = f"सिंचन थांबवा. प्रत्यक्ष पावसाच्या आगमनाची खात्री करण्यासाठी पुढील {h_int:.0f} तासांत पुनर्परीक्षण निर्धारित आहे."
                reassess_guidance_hi = f"सिंचाई रोकें. वास्तविक वर्षा के आगमन की पुष्टि के लिए अगले {h_int:.0f} घंटों में पुनर्मूल्यांकन निर्धारित है."
            else:
                reassess_guidance_en = "Hold planned irrigation. Reassess during the next scheduled monitoring cycle or immediately following the rainfall event."
                reassess_guidance_mr = "नियोजित सिंचन थांबवा. प्रत्यक्ष पावसानंतर किंवा पुढील नियमित फेरीत पुनर्परीक्षण करा."
                reassess_guidance_hi = "नियोजित सिंचाई रोकें. वास्तविक वर्षा के बाद या अगले निर्धारित चक्र में पुनर्मूल्यांकन करें."

            if language == ExplanationLanguage.MR:
                short = f"पुढील पावसाच्या अंदाजामुळे झोन {zid} चे सिंचन पुढे ढकलण्यात आले आहे."
                why = f"{source_s} नुसार {period_mr} {prob_s} संभाव्यतेसह {rain_val:.1f} मिमी पावसाचा अंदाज आहे, जो पिकावर पाण्याचा ताण येण्यापूर्वी अपेक्षित आहे."
                guidance = reassess_guidance_mr
            elif language == ExplanationLanguage.HI:
                short = f"आगामी वर्षा के पूर्वानुमान के कारण ज़ोन {zid} की सिंचाई स्थगित कर दी गई है."
                why = f"{source_s} के अनुसार {period_hi} {prob_s} संभावना के साथ {rain_val:.1f} मिमी वर्षा का अनुमान है, जो फसल पर तनाव आने से पहले अपेक्षित है."
                guidance = reassess_guidance_hi
            else:
                short = f"Irrigation for Zone {zid} is delayed due to upcoming forecast rain."
                why = f"{rain_val:.1f} mm of precipitation is forecast with {prob_s} probability {period_en} by {source_s}, expected to arrive before crop moisture stress onset."
                guidance = reassess_guidance_en

        return short, why, guidance

    # --------------------------------------------------------------------------
    # ACTION: INSUFFICIENT_DATA
    # --------------------------------------------------------------------------
    if act == DecisionAction.INSUFFICIENT_DATA:
        missing_str = ", ".join(missing_evidence) if missing_evidence else "soil water balance evidence"
        if language == ExplanationLanguage.MR:
            short = f"अपुऱ्या किंवा अवैध माहितीमुळे झोन {zid} साठी सिंचन निर्णय निश्चित करता येत नाही."
            why = f"आवश्यक कृषी माहिती गहाळ, कालबाह्य किंवा संशयास्पद आहे: {missing_str}."
            guidance = "पुढील निर्णय घेण्यापूर्वी सेन्सर फीड तपासा किंवा गहाळ माती/पिकाची माहिती भरा. अंदाजे निर्णय तयार करण्यास सक्त मनाई आहे."
        elif language == ExplanationLanguage.HI:
            short = f"अपर्याप्त या अमान्य डेटा के कारण ज़ोन {zid} के लिए सिंचाई का निर्णय नहीं लिया जा सकता."
            why = f"आवश्यक कृषि डेटा अनुपलब्ध, पुराना या संदेहास्पद है: {missing_str}."
            guidance = "आगे बढ़ने से पहले सेंसर फीड की जांच करें या अनुपलब्ध मृदा/फसल डेटा प्रदान करें. मनमाने निर्णय लेना प्रतिबंधित है."
        else:
            short = f"Cannot determine an irrigation decision for Zone {zid} due to insufficient or invalid data."
            why = f"Required agronomic evidence is missing, stale, or suspect: {missing_str}."
            guidance = "Inspect sensor feeds or provide missing soil hydraulic and crop metadata before proceeding. Decisions cannot be fabricated."

        return short, why, guidance

    # --------------------------------------------------------------------------
    # ACTION: NO_ACTION_REQUIRED (Corrected Non-Overgeneralized Health Language)
    # --------------------------------------------------------------------------
    alerts = _extract_independent_agronomic_alerts(decision, stress_assessment, language)

    # Check for documented reassessment timing
    timing_nar_en = None
    timing_nar_mr = None
    timing_nar_hi = None
    if decision.forecast_reassessment_timestamp:
        tz_str = decision.forecast_reassessment_timestamp.tzname() or "UTC"
        ts_str = decision.forecast_reassessment_timestamp.strftime(f"%Y-%m-%d %H:%M {tz_str}")
        timing_nar_en = f"next scheduled assessment at {ts_str}"
        timing_nar_mr = f"पुढील तपासणी {ts_str} वाजता"
        timing_nar_hi = f"अगली समीक्षा {ts_str} पर निर्धारित है"
    elif decision.forecast_reassessment_interval_hours is not None:
        h_val = decision.forecast_reassessment_interval_hours
        timing_nar_en = f"next scheduled assessment within {h_val:.0f} hours"
        timing_nar_mr = f"पुढील {h_val:.0f} तासांत तपासणी"
        timing_nar_hi = f"अगले {h_val:.0f} घंटों में समीक्षा"

    if language == ExplanationLanguage.MR:
        if alerts:
            alerts_str = "; ".join(alerts)
            short = f"सध्याच्या जल संतुलन पुराव्यांवरून झोन {zid} मध्ये सिंचनाची कोणतीही आवश्यकता दिसून येत नाही; इतर स्वतंत्र कृषी समस्या तपासणे आवश्यक आहे."
            why = (
                f"मातीतील पाण्याच्या संतुलनानुसार पाण्याचा तुटवडा ({dr_s} मिमी) सुलभ उपलब्ध साठ्याच्या (RAW {raw_s} मिमी, Ks = 1.00) आत आहे. "
                f"तथापि, स्वतंत्र कृषी इशारे सक्रिय आहेत: {alerts_str}. सिंचनाची गरज नसणे म्हणजे पिकाला कोणताही कृषी प्रश्न नाही असा होत नाही."
            )
            guidance = f"मातीतील ओलाव्यानुसार सध्या सिंचनाची आवश्यकता नाही. तथापि, सिंचनाव्यतिरिक्त इतर समस्यांसाठी शेताची पाहणी करा: {alerts_str}."
        else:
            short = f"सध्याच्या जल संतुलन पुराव्यांवरून झोन {zid} मध्ये सिंचनाची कोणतीही आवश्यकता दिसून येत नाही."
            why = f"मातीतील पाण्याच्या संतुलनानुसार पाण्याचा तुटवडा ({dr_s} मिमी) सुलभ उपलब्ध साठ्याच्या (RAW {raw_s} मिमी, Ks = 1.00) मर्यादेत आहे. सध्याचा मातीतील ओलावा पिकाच्या बाष्पोत्सर्जनासाठी पुरेसा आहे."
            guidance = (
                f"मातीतील ओलाव्याच्या आधारे सध्या पाणी देण्याची आवश्यकता नाही. सामान्य शेती व्यवस्थापन सुरू ठेवा ({timing_nar_mr})."
                if timing_nar_mr
                else "मातीतील ओलाव्याच्या आधारे सध्या पाणी देण्याची आवश्यकता नाही. सामान्य शेती व्यवस्थापन सुरू ठेवा आणि पुढील नियमित फेरीत तपासणी करा."
            )

    elif language == ExplanationLanguage.HI:
        if alerts:
            alerts_str = "; ".join(alerts)
            short = f"वर्तमान जल संतुलन साक्ष्य के अनुसार ज़ोन {zid} में सिंचाई की कोई आवश्यकता नहीं पाई गई है; स्वतंत्र कृषि चिंताओं की समीक्षा आवश्यक है."
            why = (
                f"मृदा जल संतुलन के अनुसार पानी की कमी ({dr_s} मिमी) सुलभ उपलब्ध सीमा (RAW {raw_s} मिमी, Ks = 1.00) के भीतर है. "
                f"हालांकि, स्वतंत्र कृषि अलर्ट सक्रिय हैं: {alerts_str}. सिंचाई की आवश्यकता न होने का अर्थ फसल में किसी अन्य समस्या का अभाव नहीं है."
            )
            guidance = f"मृदा नमी के आधार पर सिंचाई आवश्यक नहीं है. हालांकि, गैर-सिंचाई समस्याओं के समाधान के लिए ज़ोन का निरीक्षण करें: {alerts_str}."
        else:
            short = f"वर्तमान जल संतुलन साक्ष्य के अनुसार ज़ोन {zid} में सिंचाई की कोई आवश्यकता नहीं पाई गई है."
            why = f"मृदा जल संतुलन के अनुसार पानी की कमी ({dr_s} मिमी) सुलभ उपलब्ध सीमा (RAW {raw_s} मिमी, Ks = 1.00) के भीतर है. वर्तमान मृदा नमी फसल के सामान्य वाष्पोत्सर्जन के लिए पर्याप्त है."
            guidance = (
                f"मृदा नमी के आधार पर इस समय पानी देने की आवश्यकता नहीं है. सामान्य खेत प्रबंधन बनाए रखें ({timing_nar_hi})."
                if timing_nar_hi
                else "मृदा नमी के आधार पर इस समय पानी देने की आवश्यकता नहीं है. सामान्य खेत प्रबंधन बनाए रखें और अगले निर्धारित चक्र में समीक्षा करें."
            )

    else:  # Default English
        if alerts:
            alerts_str = "; ".join(alerts)
            short = f"Current water-balance evidence does not indicate a need for irrigation in Zone {zid}; independent agronomic concerns require review."
            why = (
                f"Soil water balance indicates root-zone depletion ({dr_s} mm) is well within readily available limits (RAW {raw_s} mm, Ks = 1.00). "
                f"However, independent non-watering agronomic alerts are active: {alerts_str}. Absence of an irrigation requirement does not indicate absence of crop health problems."
            )
            guidance = f"No irrigation is indicated by soil moisture evidence. However, inspect the zone to address non-watering issues: {alerts_str}."
        else:
            short = f"Current water-balance evidence does not indicate a need for irrigation in Zone {zid}."
            why = f"Soil water balance shows root-zone depletion ({dr_s} mm) is well within readily available storage (RAW {raw_s} mm, Ks = 1.00). Current soil moisture is adequate to sustain non-stressed crop transpiration."
            guidance = (
                f"No water application is required at this time based on soil moisture evidence. Maintain normal field management ({timing_nar_en})."
                if timing_nar_en
                else "No water application is required at this time based on soil moisture evidence. Maintain normal field management and resume assessment during the next scheduled cycle."
            )

    return short, why, guidance


def _build_agronomist_explanation(
    decision: ZoneDecisionResult,
    water_balance: Optional[WaterBalanceResult],
    stress_assessment: Optional[ZoneStressAssessment],
    features: Optional[MultimodalZoneFeatureSet],
    farm_zone: Optional[FarmZoneContext],
    forecast: Optional[WeatherForecastContext],
) -> AgronomistTechnicalExplanation:
    """Compile in-depth agronomic and physical parameters for agronomists."""
    dr = getattr(water_balance, "final_depletion_mm", None)
    raw = getattr(water_balance, "readily_available_water_mm", None)
    taw = getattr(water_balance, "total_available_water_mm", None)
    ks = getattr(water_balance, "water_stress_coefficient_ks", None)
    etc = getattr(water_balance, "crop_evapotranspiration_mm", None)
    adj_etc = getattr(water_balance, "adjusted_crop_evapotranspiration_mm", None)

    # Forecast ETc window audit
    fc_etc_window = None
    if decision.forecast_dependency:
        dep = decision.forecast_dependency
        fc_etc_window = {
            "forecast_etc_mm": dep.get("forecast_etc_mm"),
            "forecast_etc_period_hours": dep.get("forecast_etc_period_hours"),
            "forecast_etc_rate_mm_per_hour": dep.get("forecast_etc_rate_mm_per_hour"),
            "is_etc_window_valid": dep.get("is_etc_window_valid"),
            "is_stress_onset_estimated": dep.get("is_stress_onset_estimated"),
            "stress_onset_hours": dep.get("stress_onset_hours"),
            "rainfall_onset_hours": dep.get("rainfall_onset_hours"),
        }

    # Forecast rainfall summary
    fc_rain_summary = None
    if forecast is not None:
        fc_rain_summary = {
            "precipitation_gross_mm": forecast.forecast_precipitation_mm,
            "precipitation_effective_mm": forecast.forecast_effective_rainfall_mm,
            "probability_fraction": forecast.forecast_probability,
            "forecast_horizon_hours": forecast.forecast_period_hours,
            "provider": forecast.forecast_source,
        }

    # Multimodal stress domain indicators
    domain_stress: Dict[str, Any] = {}
    if stress_assessment is not None:
        domain_items = getattr(stress_assessment, "domain_statuses", None)
        if domain_items is None and hasattr(stress_assessment, "domain_assessments"):
            domain_items = {d: getattr(ev, "status", ev) for d, ev in stress_assessment.domain_assessments.items()}
        if domain_items:
            for domain, status in domain_items.items():
                domain_stress[domain] = {
                    "status": status.value if hasattr(status, "value") else str(status),
                }
        if stress_assessment.vegetation_indicators:
            vi = stress_assessment.vegetation_indicators
            domain_stress["vegetation_metrics"] = {
                "ndvi": getattr(vi, "ndvi_mean", getattr(vi, "ndvi", None)),
                "ndmi": getattr(vi, "ndmi_mean", getattr(vi, "ndmi", None)),
                "canopy_cover_fraction": getattr(vi, "vegetation_coverage_fraction", getattr(vi, "canopy_cover_fraction", None)),
            }

    # Satellite quality
    sat_quality = None
    if features is not None and features.vegetation is not None:
        sat_quality = f"Status: {features.vegetation.quality_status.value}; Provider: {features.vegetation.source_provider}"

    return AgronomistTechnicalExplanation(
        depletion_dr_mm=round(float(dr), 2) if dr is not None else None,
        readily_available_water_raw_mm=round(float(raw), 2) if raw is not None else None,
        total_available_water_taw_mm=round(float(taw), 2) if taw is not None else None,
        transpiration_reduction_ks=round(float(ks), 3) if ks is not None else None,
        crop_evapotranspiration_etc_mm=round(float(etc), 2) if etc is not None else None,
        adjusted_etc_mm=round(float(adj_etc), 2) if adj_etc is not None else None,
        forecast_etc_window=fc_etc_window,
        forecast_rainfall_summary=fc_rain_summary,
        net_irrigation_depth_mm=round(float(decision.net_irrigation_depth_mm), 2) if decision.net_irrigation_depth_mm is not None else None,
        gross_irrigation_depth_mm=round(float(decision.gross_irrigation_depth_mm), 2) if decision.gross_irrigation_depth_mm is not None else None,
        application_efficiency=round(float(decision.application_efficiency), 3) if decision.application_efficiency is not None else None,
        application_efficiency_provenance=decision.application_efficiency_provenance.value if decision.application_efficiency_provenance else None,
        is_efficiency_verified=decision.is_efficiency_verified,
        is_efficiency_provisional=decision.is_efficiency_provisional,
        split_application_required=decision.split_application_required,
        split_event_count=decision.split_event_count,
        split_event_depths_mm=decision.split_event_depths_mm,
        domain_stress_indicators=domain_stress,
        satellite_observation_quality=sat_quality,
        method_assumptions=list(decision.assumptions),
        scientific_limitations=list(decision.unresolved_limitations),
    )


def _render_farm_summary_text(
    farm_id: str,
    total_zones: int,
    irrig_count: int,
    mon_count: int,
    delay_count: int,
    insufficient_count: int,
    no_action_count: int,
    vol_status: VolumeCalculationStatus,
    total_vol_m3: Optional[float],
    language: ExplanationLanguage,
) -> str:
    """Render high-level farm overview text across languages."""
    vol_str = f"{total_vol_m3:,.0f} m³" if total_vol_m3 is not None else "withheld"

    if language == ExplanationLanguage.MR:
        status_note = ""
        if vol_status == VolumeCalculationStatus.COMPLETE_MEASURED:
            status_note = f"एकूण आवश्यक पाणी: {vol_str} (सत्यापित कार्यक्षमतेसह)."
        elif vol_status == VolumeCalculationStatus.COMPLETE_PROVISIONAL:
            status_note = f"अंदाजित आवश्यक पाणी: {vol_str} (काही झोनमध्ये अंदाजित कार्यक्षमता समाविष्ट आहे)."
        elif vol_status == VolumeCalculationStatus.SUPPRESSED_MISSING_AREA:
            status_note = "झोनचे क्षेत्रफळ उपलब्ध नसल्यामुळे एकूण शेतातील सिंचन आकारमान मोजलेले नाही."
        elif vol_status == VolumeCalculationStatus.SUPPRESSED_UNKNOWN_EFFICIENCY:
            status_note = "सिंचन कार्यक्षमता माहित नसल्यामुळे एकूण शेतातील सिंचन आकारमान मोजलेले नाही."
        elif vol_status == VolumeCalculationStatus.ZERO_IRRIGATION:
            status_note = "सध्या कोणत्याही झोनमध्ये सिंचनाची आवश्यकता नाही."

        return (
            f"शेत {farm_id} सारांश: एकूण {total_zones} व्यवस्थापन झोन तपासले गेले. "
            f"सिंचन आवश्यक: {irrig_count}, निरीक्षण सुरू: {mon_count}, पुढे ढकललेले: {delay_count}, "
            f"अपुऱ्या माहितीमुळे प्रलंबित: {insufficient_count}, कोणतीही कृती नको: {no_action_count}. {status_note}"
        )

    if language == ExplanationLanguage.HI:
        status_note = ""
        if vol_status == VolumeCalculationStatus.COMPLETE_MEASURED:
            status_note = f"कुल आवश्यक पानी: {vol_str} (सत्यापित दक्षता के साथ)."
        elif vol_status == VolumeCalculationStatus.COMPLETE_PROVISIONAL:
            status_note = f"अनुमानित आवश्यक पानी: {vol_str} (कुछ ज़ोन में अनंतिम दक्षता शामिल है)."
        elif vol_status == VolumeCalculationStatus.SUPPRESSED_MISSING_AREA:
            status_note = "ज़ोन का क्षेत्रफल अनुपलब्ध होने के कारण कुल खेत सिंचाई मात्रा रोक दी गई है."
        elif vol_status == VolumeCalculationStatus.SUPPRESSED_UNKNOWN_EFFICIENCY:
            status_note = "सिंचाई दक्षता अज्ञात होने के कारण कुल खेत सिंचाई मात्रा रोक दी गई है."
        elif vol_status == VolumeCalculationStatus.ZERO_IRRIGATION:
            status_note = "वर्तमान में किसी भी ज़ोन में सिंचाई की आवश्यकता नहीं है."

        return (
            f"खेत {farm_id} सारांश: कुल {total_zones} प्रबंधन ज़ोन का मूल्यांकन किया गया. "
            f"सिंचाई आवश्यक: {irrig_count}, निगरानी में: {mon_count}, स्थगित: {delay_count}, "
            f"अपर्याप्त डेटा: {insufficient_count}, कार्रवाई आवश्यक नहीं: {no_action_count}. {status_note}"
        )

    # Default English
    status_note = ""
    if vol_status == VolumeCalculationStatus.COMPLETE_MEASURED:
        status_note = f"Total gross irrigation requirement: {vol_str} (backed by verified field-tested efficiency)."
    elif vol_status == VolumeCalculationStatus.COMPLETE_PROVISIONAL:
        status_note = f"Total estimated irrigation requirement: {vol_str} (incorporates provisional efficiency assumptions)."
    elif vol_status == VolumeCalculationStatus.SUPPRESSED_MISSING_AREA:
        status_note = "Total farm irrigation volume is withheld due to missing zone surface area."
    elif vol_status == VolumeCalculationStatus.SUPPRESSED_UNKNOWN_EFFICIENCY:
        status_note = "Total farm irrigation volume is withheld due to unknown application efficiency."
    elif vol_status == VolumeCalculationStatus.ZERO_IRRIGATION:
        status_note = "Zero zones currently require irrigation."

    return (
        f"Farm {farm_id} Summary: {total_zones} management zones evaluated. "
        f"Irrigate: {irrig_count}, Monitor: {mon_count}, Delayed: {delay_count}, "
        f"Insufficient Data: {insufficient_count}, No Action: {no_action_count}. {status_note}"
    )
