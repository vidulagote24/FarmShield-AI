"""Validation routines and scientific safeguards for the Phase 5 Decision Engine.

Enforces:
1. Water balance evidence completeness, quality, and freshness.
2. Provisional empirical rainfall restrictions (blocked unless research mode is explicitly enabled).
3. Mathematical consistency between net depth, gross depth, application efficiency, and volume.
4. Strict isolation of vegetation optical anomalies and soil chemical hazards from irrigation triggers.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.app.intelligence.agronomy.water_balance import WaterBalanceResult
from backend.app.intelligence.decision.types import (
    DecisionConfig,
    DecisionReasonCode,
    FarmZoneContext,
    WeatherForecastContext,
)
from backend.app.intelligence.stress.assessment import ZoneStressAssessment
from backend.app.intelligence.types import DataQualityStatus, StressStatus


class EvidenceValidationResult:
    """Detailed outcome of evidence verification."""

    def __init__(self) -> None:
        self.is_valid: bool = True
        self.is_insufficient: bool = False
        self.is_stale: bool = False
        self.is_suspect: bool = False
        self.is_provisional_blocked: bool = False
        self.blocking_reasons: List[DecisionReasonCode] = []
        self.warnings: List[str] = []
        self.audit_trail: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "is_insufficient": self.is_insufficient,
            "is_stale": self.is_stale,
            "is_suspect": self.is_suspect,
            "is_provisional_blocked": self.is_provisional_blocked,
            "blocking_reasons": [r.value for r in self.blocking_reasons],
            "warnings": self.warnings,
            "audit_trail": self.audit_trail,
        }


class ForecastValidationResult:
    """Outcome of meteorological weather forecast verification for delay policies."""

    def __init__(self) -> None:
        self.is_valid: bool = True
        self.is_stale: bool = False
        self.is_actionable: bool = False
        self.probability_sufficient: bool = True
        self.raw_precipitation_mm: float = 0.0
        self.effective_rainfall_mm: Optional[float] = None
        self.forecast_etc_mm: Optional[float] = None
        self.forecast_etc_period_hours: Optional[float] = None
        self.forecast_etc_rate_mm_per_hour: Optional[float] = None
        self.is_etc_window_valid: bool = True
        self.etc_valid_from: Optional[datetime] = None
        self.etc_valid_to: Optional[datetime] = None
        self.is_stress_onset_estimated: bool = False
        self.pre_rain_depletion_mm: Optional[float] = None
        self.dr_at_rainfall_onset_mm: Optional[float] = None
        self.projected_depletion_mm: Optional[float] = None
        self.rainfall_onset_hours: Optional[float] = None
        self.stress_onset_hours: Optional[float] = None
        self.rainfall_after_stress: bool = False
        self.is_provisional_deferral: bool = False
        self.reassessment_timestamp: Optional[datetime] = None
        self.reassessment_interval_hours: Optional[float] = None
        self.reasons: List[DecisionReasonCode] = []
        self.warnings: List[str] = []
        self.audit_trail: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "is_stale": self.is_stale,
            "is_actionable": self.is_actionable,
            "probability_sufficient": self.probability_sufficient,
            "raw_precipitation_mm": self.raw_precipitation_mm,
            "effective_rainfall_mm": self.effective_rainfall_mm,
            "forecast_etc_mm": self.forecast_etc_mm,
            "forecast_etc_period_hours": self.forecast_etc_period_hours,
            "forecast_etc_rate_mm_per_hour": self.forecast_etc_rate_mm_per_hour,
            "is_etc_window_valid": self.is_etc_window_valid,
            "etc_valid_from": self.etc_valid_from.isoformat() if self.etc_valid_from else None,
            "etc_valid_to": self.etc_valid_to.isoformat() if self.etc_valid_to else None,
            "is_stress_onset_estimated": self.is_stress_onset_estimated,
            "pre_rain_depletion_mm": self.pre_rain_depletion_mm,
            "dr_at_rainfall_onset_mm": self.dr_at_rainfall_onset_mm,
            "projected_depletion_mm": self.projected_depletion_mm,
            "rainfall_onset_hours": self.rainfall_onset_hours,
            "stress_onset_hours": self.stress_onset_hours,
            "rainfall_after_stress": self.rainfall_after_stress,
            "is_provisional_deferral": self.is_provisional_deferral,
            "reassessment_timestamp": self.reassessment_timestamp.isoformat() if self.reassessment_timestamp else None,
            "reassessment_interval_hours": self.reassessment_interval_hours,
            "reasons": [r.value for r in self.reasons],
            "warnings": self.warnings,
            "audit_trail": self.audit_trail,
        }


def validate_etc_temporal_window(
    forecast: WeatherForecastContext,
    decision_timestamp: datetime,
) -> Tuple[bool, Optional[datetime], Optional[datetime], Optional[float], List[str]]:
    """Validate temporal coverage and timezone integrity of forecast ETc accumulation window.

    Scientific & Operational Principles (Phase 5.2.5):
    1. Timezone Integrity:
       Requires timezone-aware decision, ETc and rainfall timestamps; normalizes to UTC.
       Offset-naive datetimes fail temporal validation.
    2. Temporal Lookahead Precedence:
       Validates forecast_etc_valid_from <= decision_timestamp.
    3. Horizon Coverage:
       Validates forecast_etc_valid_to >= forecast_rainfall_onset (when onset known)
       or forecast_etc_valid_to >= decision_timestamp + forecast_period_hours (when onset unspecified).
    4. Interval Consistency:
       Rejects inverted (valid_to <= valid_from) or zero-length intervals.
       Validates duration against stated aggregation period (forecast_etc_period_hours).
    5. Non-Extrapolation:
       Do not extrapolate the uniform ETc rate beyond documented validity interval.

    Args:
        forecast: Meteorological weather forecast context.
        decision_timestamp: Current decision timestamp.

    Returns:
        Tuple of (is_valid, etc_from_utc, etc_to_utc, duration_hours, warnings).
    """
    warnings: List[str] = []

    # 1. Require timezone-aware decision timestamp
    if decision_timestamp.tzinfo is None:
        warnings.append("Decision timestamp must be timezone-aware; offset-naive datetime received.")
        return False, None, None, None, warnings

    decision_utc = decision_timestamp.astimezone(timezone.utc)

    # 2. Extract ETc window timestamps
    etc_from = forecast.forecast_etc_valid_from
    etc_to = forecast.forecast_etc_valid_to

    # Fallback to general forecast valid_from / valid_to if explicit ETc timestamps are omitted
    if etc_from is None and forecast.valid_from is not None:
        etc_from = forecast.valid_from
    if etc_to is None and forecast.valid_to is not None:
        etc_to = forecast.valid_to

    # Handle omitted timestamps (default to lookahead window from decision_utc)
    if etc_from is None and etc_to is None:
        dur_h = (
            forecast.forecast_etc_period_hours
            if (forecast.forecast_etc_period_hours is not None and forecast.forecast_etc_period_hours > 0.0)
            else forecast.forecast_period_hours
        )
        if dur_h <= 0.0:
            warnings.append(f"Invalid forecast ETc aggregation period duration ({dur_h}h <= 0).")
            return False, None, None, None, warnings

        etc_from_utc = decision_utc
        etc_to_utc = decision_utc + timedelta(hours=dur_h)

        # Validate rainfall onset if specified
        if forecast.expected_rainfall_start is not None:
            if forecast.expected_rainfall_start.tzinfo is None:
                warnings.append(
                    f"Forecast rainfall onset timestamp must be timezone-aware; offset-naive datetime received "
                    f"({forecast.expected_rainfall_start})."
                )
                return False, etc_from_utc, etc_to_utc, dur_h, warnings

            rain_start_utc = forecast.expected_rainfall_start.astimezone(timezone.utc)
            if etc_to_utc < rain_start_utc:
                warnings.append(
                    f"ETc validity window ({etc_to_utc.isoformat()}) ends before forecast rainfall onset "
                    f"({rain_start_utc.isoformat()}). Extrapolation beyond documented validity interval is prohibited."
                )
                return False, etc_from_utc, etc_to_utc, dur_h, warnings

        return True, etc_from_utc, etc_to_utc, dur_h, warnings

    # At least one explicit timestamp is provided: require both
    if etc_from is None or etc_to is None:
        warnings.append(
            f"Incomplete ETc validity window specification: both valid_from and valid_to are required "
            f"(got valid_from={etc_from}, valid_to={etc_to})."
        )
        return False, None, None, None, warnings

    # Require timezone-aware ETc timestamps
    if etc_from.tzinfo is None or etc_to.tzinfo is None:
        warnings.append(
            f"ETc validity window timestamps must be timezone-aware; offset-naive datetime received "
            f"(valid_from={etc_from}, valid_to={etc_to})."
        )
        return False, None, None, None, warnings

    etc_from_utc = etc_from.astimezone(timezone.utc)
    etc_to_utc = etc_to.astimezone(timezone.utc)

    # Reject inverted or zero-length intervals
    if etc_to_utc <= etc_from_utc:
        warnings.append(
            f"ETc validity window is inverted or zero-length: valid_to ({etc_to_utc.isoformat()}) "
            f"<= valid_from ({etc_from_utc.isoformat()})."
        )
        return False, etc_from_utc, etc_to_utc, None, warnings

    dur_h = (etc_to_utc - etc_from_utc).total_seconds() / 3600.0

    # Validate duration against stated aggregation period
    if forecast.forecast_etc_period_hours is not None and forecast.forecast_etc_period_hours > 0.0:
        if abs(dur_h - forecast.forecast_etc_period_hours) > 0.01:
            warnings.append(
                f"ETc validity window duration ({dur_h:.2f}h) does not match stated aggregation period "
                f"({forecast.forecast_etc_period_hours:.2f}h)."
            )
            return False, etc_from_utc, etc_to_utc, dur_h, warnings

    # Validate forecast_etc_valid_from <= decision_timestamp
    if etc_from_utc > decision_utc:
        warnings.append(
            f"ETc validity window starts after decision timestamp: valid_from ({etc_from_utc.isoformat()}) "
            f"> decision ({decision_utc.isoformat()}). Lookahead coverage is incomplete."
        )
        return False, etc_from_utc, etc_to_utc, dur_h, warnings

    # Validate forecast_etc_valid_to >= forecast_rainfall_onset
    if forecast.expected_rainfall_start is not None:
        if forecast.expected_rainfall_start.tzinfo is None:
            warnings.append(
                f"Forecast rainfall onset timestamp must be timezone-aware; offset-naive datetime received "
                f"({forecast.expected_rainfall_start})."
            )
            return False, etc_from_utc, etc_to_utc, dur_h, warnings

        rain_start_utc = forecast.expected_rainfall_start.astimezone(timezone.utc)
        if etc_to_utc < rain_start_utc:
            warnings.append(
                f"ETc validity window ends before forecast rainfall onset: valid_to ({etc_to_utc.isoformat()}) "
                f"< rainfall_onset ({rain_start_utc.isoformat()}). Extrapolation beyond documented validity interval is prohibited."
            )
            return False, etc_from_utc, etc_to_utc, dur_h, warnings
    else:
        # Unspecified rainfall onset: must cover full forecast horizon
        horizon_end_utc = decision_utc + timedelta(hours=forecast.forecast_period_hours)
        if etc_to_utc < horizon_end_utc:
            warnings.append(
                f"ETc validity window ({etc_to_utc.isoformat()}) does not cover full forecast horizon "
                f"({horizon_end_utc.isoformat()}) when rainfall onset timestamp is unspecified."
            )
            return False, etc_from_utc, etc_to_utc, dur_h, warnings

    return True, etc_from_utc, etc_to_utc, dur_h, warnings


def validate_forecast_evidence(
    forecast: Optional[WeatherForecastContext],
    config: DecisionConfig,
    deficit_dr_mm: Optional[float] = None,
    raw_mm: Optional[float] = None,
    as_of_time: Optional[datetime] = None,
) -> ForecastValidationResult:
    """Validate meteorological forecast against freshness, validity intervals, and policy thresholds.

    Distinguishes raw NWP forecast precipitation from validated effective root-zone rainfall.
    Accounts for expected crop water consumption (ETc) over the forecast horizon.
    Evaluates projected depletion Dr_proj = max(0, Dr + ETc - P_eff) rather than raw rainfall alone.
    Preserves rainfall timing relative to stress onset and forecast validity period.
    Where infiltration evidence is missing, retains a clearly marked provisional deferral policy
    with reassessment metadata without fabricating infiltration or runoff parameters.

    Args:
        forecast: Meteorological weather forecast context.
        config: Decision configuration with thresholds and horizons.
        deficit_dr_mm: Optional root-zone depletion Dr (mm) for deficit comparison.
        raw_mm: Optional readily available water RAW (mm) for stress relief evaluation.
        as_of_time: Current UTC evaluation time.

    Returns:
        ForecastValidationResult indicating validity and whether delay policy is actionable.
    """
    res = ForecastValidationResult()
    if forecast is None:
        res.is_valid = True
        res.is_actionable = False
        return res

    # Handle positional invocation where as_of_time was passed as 3rd parameter
    if isinstance(deficit_dr_mm, datetime):
        as_of_time = deficit_dr_mm
        deficit_dr_mm = None

    now_utc = as_of_time or datetime.now(timezone.utc)
    raw_precip = (
        forecast.forecast_total_precipitation_mm
        if forecast.forecast_total_precipitation_mm is not None
        else forecast.forecast_precipitation_mm
    )
    res.raw_precipitation_mm = raw_precip
    res.effective_rainfall_mm = forecast.forecast_effective_rainfall_mm

    # 1. Freshness Check: evaluate issue_time or retrieved_at
    ref_time = forecast.issue_time or forecast.retrieved_at
    if ref_time is not None:
        ref_time_utc = ref_time.replace(tzinfo=timezone.utc) if ref_time.tzinfo is None else ref_time.astimezone(timezone.utc)
        decision_time_utc = now_utc.replace(tzinfo=timezone.utc) if now_utc.tzinfo is None else now_utc.astimezone(timezone.utc)
        age_hours = (decision_time_utc - ref_time_utc).total_seconds() / 3600.0
        if age_hours > config.max_forecast_age_hours:
            res.is_valid = False
            res.is_stale = True
            res.reasons.append(DecisionReasonCode.FORECAST_EVIDENCE_STALE)
            res.warnings.append(
                f"Forecast evidence is stale (age: {age_hours:.1f}h > {config.max_forecast_age_hours:.0f}h limit); "
                "stale forecast cannot defer active irrigation."
            )

    # 2. Validity Window Check
    if forecast.valid_from is not None and forecast.valid_to is not None:
        vf = forecast.valid_from.replace(tzinfo=timezone.utc) if forecast.valid_from.tzinfo is None else forecast.valid_from.astimezone(timezone.utc)
        vt = forecast.valid_to.replace(tzinfo=timezone.utc) if forecast.valid_to.tzinfo is None else forecast.valid_to.astimezone(timezone.utc)
        if vt <= vf:
            res.is_valid = False
            res.reasons.append(DecisionReasonCode.FORECAST_EVIDENCE_INVALID)
            res.warnings.append("Forecast validity window is malformed (valid_to <= valid_from).")

    # 3. Horizon Check
    is_within_horizon = forecast.forecast_period_hours <= config.forecast_delay_horizon_hours

    # 4. Probability Check
    if forecast.forecast_probability is not None:
        if forecast.forecast_probability < config.forecast_probability_threshold:
            res.probability_sufficient = False
            res.reasons.append(DecisionReasonCode.FORECAST_PROBABILITY_BELOW_THRESHOLD)
            res.warnings.append(
                f"Forecast precipitation probability ({forecast.forecast_probability:.0%}) is below delay "
                f"threshold ({config.forecast_probability_threshold:.0%}); delay not triggered."
            )
        else:
            res.probability_sufficient = True
    else:
        # Unspecified probability fraction (deterministic model forecast)
        res.probability_sufficient = True
        res.audit_trail.append("Forecast probability is unspecified; treated as deterministic model forecast.")

    # 5. Crop ETc over Forecast Horizon & Temporal Window Validation (Phase 5.2.5)
    etc_horizon: Optional[float] = None
    etc_period_hours: Optional[float] = None
    etc_rate: Optional[float] = None

    if forecast.forecast_etc_mm is not None:
        etc_horizon = forecast.forecast_etc_mm
        res.forecast_etc_mm = etc_horizon
        res.reasons.append(DecisionReasonCode.FORECAST_ETC_EVALUATED)

        # Validate ETc temporal window coverage (Phase 5.2.5)
        is_window_valid, etc_from_utc, etc_to_utc, dur_h, window_warnings = validate_etc_temporal_window(
            forecast=forecast,
            decision_timestamp=now_utc,
        )

        res.is_etc_window_valid = is_window_valid
        res.etc_valid_from = etc_from_utc
        res.etc_valid_to = etc_to_utc
        res.forecast_etc_period_hours = dur_h or forecast.forecast_etc_period_hours

        if not is_window_valid:
            # Temporal coverage is insufficient / invalid
            res.reasons.append(DecisionReasonCode.FORECAST_ETC_WINDOW_INSUFFICIENT)
            res.warnings.extend(window_warnings)
            res.forecast_etc_rate_mm_per_hour = None
            res.stress_onset_hours = None
            res.is_stress_onset_estimated = False
            res.dr_at_rainfall_onset_mm = None
            res.pre_rain_depletion_mm = None
            res.projected_depletion_mm = None
            etc_rate = None
        else:
            etc_period_hours = dur_h
            etc_rate = (etc_horizon / etc_period_hours) if etc_period_hours > 0.0 else 0.0
            res.forecast_etc_rate_mm_per_hour = etc_rate

            from_str = etc_from_utc.isoformat() if etc_from_utc else "now"
            to_str = etc_to_utc.isoformat() if etc_to_utc else "end"
            res.audit_trail.append(
                f"Forecast ETc ({etc_horizon:.1f} mm over {etc_period_hours:.1f}h window [{from_str} to {to_str}]) evaluated. "
                f"Hourly consumption rate: {etc_rate:.3f} mm/h under documented uniform-rate approximation (provisional)."
            )
            if abs(etc_period_hours - forecast.forecast_period_hours) > 0.1:
                res.audit_trail.append(
                    f"Forecast ETc accumulation window ({etc_period_hours:.1f}h) differs from "
                    f"forecast rainfall horizon ({forecast.forecast_period_hours:.1f}h); consumption rate calculated from ETc window."
                )
    else:
        etc_horizon = None
        res.forecast_etc_mm = None
        res.forecast_etc_period_hours = None
        res.forecast_etc_rate_mm_per_hour = None
        res.is_etc_window_valid = False
        if DecisionReasonCode.FORECAST_ETC_MISSING not in res.reasons:
            res.reasons.append(DecisionReasonCode.FORECAST_ETC_MISSING)
        res.warnings.append(
            "Forecast ETc over horizon is missing (unavailable); projected depletion and timing cannot be evaluated. "
            "Unavailable crop demand is NOT treated as zero."
        )

    current_dr = deficit_dr_mm if deficit_dr_mm is not None else 0.0
    target_raw = raw_mm if (raw_mm is not None and raw_mm > 0.0) else (current_dr * 0.8)

    # 6. Rainfall Timing vs Water Stress Onset
    if forecast.expected_rainfall_start is not None:
        ref_start = forecast.expected_rainfall_start
        ref_start_utc = ref_start.replace(tzinfo=timezone.utc) if ref_start.tzinfo is None else ref_start.astimezone(timezone.utc)
        decision_utc_safe = now_utc.replace(tzinfo=timezone.utc) if now_utc.tzinfo is None else now_utc.astimezone(timezone.utc)
        t_rain = (ref_start_utc - decision_utc_safe).total_seconds() / 3600.0
        res.rainfall_onset_hours = max(0.0, t_rain)

        if etc_horizon is not None and etc_rate is not None and res.is_etc_window_valid:
            dr_at_onset = current_dr + (etc_rate * max(0.0, t_rain))
            res.dr_at_rainfall_onset_mm = round(dr_at_onset, 2)

            if raw_mm is not None and raw_mm > 0.0:
                if current_dr >= target_raw and t_rain > 0.0:
                    res.stress_onset_hours = 0.0
                    res.is_stress_onset_estimated = False
                    res.rainfall_after_stress = True
                    if DecisionReasonCode.FORECAST_RAINFALL_AFTER_STRESS not in res.reasons:
                        res.reasons.append(DecisionReasonCode.FORECAST_RAINFALL_AFTER_STRESS)
                    res.warnings.append(
                        f"Rainfall onset is in {t_rain:.1f}h, but root zone is already in water stress "
                        f"(Dr = {current_dr:.1f} mm >= RAW = {target_raw:.1f} mm). Deferral would prolong unmitigated stress."
                    )
                elif current_dr < target_raw and etc_rate > 0.0:
                    hrs_to_stress = (target_raw - current_dr) / etc_rate
                    res.stress_onset_hours = hrs_to_stress
                    res.is_stress_onset_estimated = True
                    res.audit_trail.append(
                        f"Estimated stress-onset time ({hrs_to_stress:.1f}h) derived from cumulative forecast ETc "
                        f"({etc_horizon:.1f} mm over {res.forecast_etc_period_hours:.1f}h validity interval) using documented "
                        f"uniform hourly rate ({etc_rate:.3f} mm/h) provisional approximation. Does not claim exact hourly diurnal transpiration."
                    )
                    if t_rain >= hrs_to_stress - 1e-6 or dr_at_onset >= target_raw - 1e-6:
                        res.rainfall_after_stress = True
                        if DecisionReasonCode.FORECAST_RAINFALL_AFTER_STRESS not in res.reasons:
                            res.reasons.append(DecisionReasonCode.FORECAST_RAINFALL_AFTER_STRESS)
                        res.warnings.append(
                            f"Water stress onset projected in {hrs_to_stress:.1f}h (estimated), but forecast rainfall does not arrive "
                            f"until {t_rain:.1f}h (projected Dr at onset = {dr_at_onset:.1f} mm >= RAW = {target_raw:.1f} mm). "
                            "Crop would experience moisture stress before rain; deferral denied."
                        )
                elif current_dr < target_raw and etc_rate == 0.0:
                    res.stress_onset_hours = None
                    res.is_stress_onset_estimated = False
        else:
            res.stress_onset_hours = None
            res.is_stress_onset_estimated = False
            res.dr_at_rainfall_onset_mm = None
            if raw_mm is not None and raw_mm > 0.0 and current_dr >= target_raw and t_rain > 0.0:
                res.rainfall_after_stress = True
                if DecisionReasonCode.FORECAST_RAINFALL_AFTER_STRESS not in res.reasons:
                    res.reasons.append(DecisionReasonCode.FORECAST_RAINFALL_AFTER_STRESS)
                res.warnings.append(
                    f"Rainfall onset is in {t_rain:.1f}h, and root zone is currently in water stress "
                    f"(Dr = {current_dr:.1f} mm >= RAW = {target_raw:.1f} mm). Deferral would prolong unmitigated stress."
                )
    else:
        # expected_rainfall_start is None
        res.rainfall_onset_hours = None
        if etc_horizon is not None and etc_rate is not None and res.is_etc_window_valid and target_raw is not None and target_raw > 0.0:
            if current_dr < target_raw and etc_rate > 0.0:
                hrs_to_stress = (target_raw - current_dr) / etc_rate
                res.stress_onset_hours = hrs_to_stress
                res.is_stress_onset_estimated = True
                res.audit_trail.append(
                    f"Estimated stress-onset time ({hrs_to_stress:.1f}h) derived from cumulative forecast ETc "
                    f"({etc_horizon:.1f} mm over {res.forecast_etc_period_hours:.1f}h validity interval) using documented "
                    f"uniform hourly rate ({etc_rate:.3f} mm/h) provisional approximation. Does not claim exact hourly diurnal transpiration."
                )
        else:
            res.stress_onset_hours = None
            res.is_stress_onset_estimated = False

    # 7. Effective Rainfall vs Projected Root-Zone Deficit Evaluation
    is_significant_rain = False
    if forecast.forecast_effective_rainfall_mm is not None:
        eff_rain = forecast.forecast_effective_rainfall_mm
        res.reasons.append(DecisionReasonCode.FORECAST_EFFECTIVE_RAINFALL_EVALUATED)
        res.audit_trail.append(
            f"Forecast effective rainfall ({eff_rain:.1f} mm) evaluated via method "
            f"'{forecast.effective_rainfall_method or 'provider_effective_estimate'}'."
        )

        if not res.is_etc_window_valid:
            res.pre_rain_depletion_mm = None
            res.projected_depletion_mm = None
            is_significant_rain = False
            res.warnings.append(
                "Forecast ETc validity window is insufficient or invalid. "
                "Confirmed safe forecast deferral cannot be evaluated without valid crop water consumption coverage. "
                "Forecast deferral withheld; continuing ordinary decision evaluation using validated current water-balance evidence."
            )
        elif etc_horizon is not None:
            pre_rain_dr = current_dr + etc_horizon
            res.pre_rain_depletion_mm = pre_rain_dr
            projected_dr = max(0.0, pre_rain_dr - eff_rain)
            res.projected_depletion_mm = projected_dr

            if deficit_dr_mm is not None and deficit_dr_mm > 0.0:
                target_raw = raw_mm if (raw_mm is not None and raw_mm > 0.0) else (deficit_dr_mm * 0.8)
                relieves_stress = projected_dr <= target_raw
                coverage_base = pre_rain_dr if pre_rain_dr > 0.0 else deficit_dr_mm
                coverage_fraction = eff_rain / coverage_base
                meets_coverage = coverage_fraction >= config.forecast_min_deficit_coverage_fraction
                meets_delay_threshold = eff_rain >= config.forecast_rain_delay_threshold_mm

                if res.rainfall_after_stress:
                    is_significant_rain = False
                elif (relieves_stress and (meets_coverage or meets_delay_threshold)) or (meets_coverage and projected_dr <= target_raw):
                    is_significant_rain = True
                    res.reasons.append(DecisionReasonCode.FORECAST_PREVENTS_STRESS)
                    res.audit_trail.append(
                        f"Forecast effective rain ({eff_rain:.1f} mm) adequately relieves projected deficit "
                        f"(pre-rain Dr: {pre_rain_dr:.1f} mm, projected Dr: {projected_dr:.1f} mm <= RAW {target_raw:.1f} mm, "
                        f"coverage: {coverage_fraction:.1%})."
                    )
                elif meets_delay_threshold and projected_dr <= target_raw:
                    is_significant_rain = True
                    res.reasons.append(DecisionReasonCode.FORECAST_PREVENTS_STRESS)
                    res.audit_trail.append(
                        f"Forecast effective rain ({eff_rain:.1f} mm) meets threshold and keeps projected Dr ({projected_dr:.1f} mm) <= RAW ({target_raw:.1f} mm)."
                    )
                else:
                    is_significant_rain = False
                    res.reasons.append(DecisionReasonCode.FORECAST_INSUFFICIENT_DEFICIT_RELIEF)
                    res.warnings.append(
                        f"Forecast effective rainfall ({eff_rain:.1f} mm) is smaller than required deficit relief: "
                        f"relieves only {coverage_fraction:.1%} of deficit (pre-rain Dr: {pre_rain_dr:.1f} mm); "
                        f"projected deficit ({projected_dr:.1f} mm) still exceeds RAW ({target_raw:.1f} mm). "
                        "Irrigation deferral denied."
                    )
            else:
                is_significant_rain = eff_rain >= config.forecast_rain_delay_threshold_mm and not res.rainfall_after_stress
        else:
            res.pre_rain_depletion_mm = None
            res.projected_depletion_mm = None
            is_significant_rain = False
            res.warnings.append(
                "Forecast effective rainfall is available, but forecast ETc is missing. "
                "Confirmed safe forecast deferral cannot be evaluated without projected crop water consumption. "
                "Forecast deferral withheld; continuing ordinary decision evaluation using validated current water-balance evidence."
            )
    else:
        # Missing infiltration/runoff evidence: do not fabricate data!
        # Strict Phase 5.2.3, 5.2.4 & 5.2.5 Policy:
        target_raw = raw_mm if (raw_mm is not None and raw_mm > 0.0) else None
        is_at_or_beyond_raw = target_raw is None or current_dr >= target_raw

        if is_at_or_beyond_raw:
            is_significant_rain = False
            res.is_provisional_deferral = False
            res.reasons.append(DecisionReasonCode.FORECAST_PROVISIONAL_BLOCKED_ACTIVE_DEFICIT)
            raw_str = f"{target_raw:.1f} mm" if target_raw is not None else "unrecorded"
            res.warnings.append(
                f"Provisional forecast deferral based on raw NWP precipitation ({raw_precip:.1f} mm) is blocked: "
                f"root-zone depletion Dr ({current_dr:.1f} mm) is at or beyond RAW ({raw_str}). "
                "Unverified gross atmospheric precipitation alone cannot defer irrigation during active deficit "
                "without verified effective rainfall and ETc evidence."
            )
        elif not config.allow_provisional_forecast_deferral:
            is_significant_rain = False
            res.is_provisional_deferral = False
            res.reasons.append(DecisionReasonCode.FORECAST_PROVISIONAL_OPT_IN_REQUIRED)
            res.warnings.append(
                "Provisional forecast-deferral policy is not enabled (allow_provisional_forecast_deferral=False). "
                "Unverified gross NWP precipitation cannot trigger deferral without explicit policy opt-in."
            )
        elif etc_horizon is None:
            # Phase 5.2.4: Require valid forecast ETc for provisional deferral!
            is_significant_rain = False
            res.is_provisional_deferral = False
            if DecisionReasonCode.FORECAST_ETC_MISSING not in res.reasons:
                res.reasons.append(DecisionReasonCode.FORECAST_ETC_MISSING)
            res.warnings.append(
                "Provisional forecast deferral requires valid forecast ETc over the lookahead period to project "
                "root-zone depletion and stress onset. Forecast ETc is missing; unavailable crop demand is NOT assumed 0.0. "
                "Provisional deferral withheld; continuing ordinary decision evaluation using validated current water-balance evidence."
            )
        elif not res.is_etc_window_valid:
            # Phase 5.2.5: ETc window insufficient
            is_significant_rain = False
            res.is_provisional_deferral = False
            if DecisionReasonCode.FORECAST_ETC_WINDOW_INSUFFICIENT not in res.reasons:
                res.reasons.append(DecisionReasonCode.FORECAST_ETC_WINDOW_INSUFFICIENT)
            res.warnings.append(
                "Provisional forecast deferral blocked: forecast ETc temporal validity window does not cover "
                "the lookahead period until rainfall arrival. Extrapolating uniform ETc rate beyond documented validity interval "
                "is prohibited. Deferral withheld; continuing ordinary decision evaluation using validated current water-balance evidence."
            )
        elif res.rainfall_after_stress:
            # Phase 5.2.4: Projected RAW crossing occurs before rainfall arrives (t_rain >= t_stress)
            is_significant_rain = False
            res.is_provisional_deferral = False
            res.warnings.append(
                f"Provisional forecast deferral blocked: projected water stress onset occurs before forecast rainfall arrives "
                f"(stress onset in {res.stress_onset_hours:.1f}h vs rainfall in {res.rainfall_onset_hours:.1f}h). "
                "Delaying irrigation would cause unmitigated crop moisture stress."
            )
        elif forecast.expected_rainfall_start is None and res.stress_onset_hours is not None and res.stress_onset_hours <= forecast.forecast_period_hours:
            # Phase 5.2.4: Depletion is projected to cross RAW within horizon, but arrival time is unrecorded
            is_significant_rain = False
            res.is_provisional_deferral = False
            if DecisionReasonCode.FORECAST_RAINFALL_AFTER_STRESS not in res.reasons:
                res.reasons.append(DecisionReasonCode.FORECAST_RAINFALL_AFTER_STRESS)
            res.warnings.append(
                f"Provisional forecast deferral blocked: depletion is projected to cross RAW in {res.stress_onset_hours:.1f}h "
                f"within forecast horizon ({forecast.forecast_period_hours:.0f}h), but rainfall arrival timestamp is unspecified. "
                "Cannot verify rain arrives before stress onset; deferral denied."
            )
        else:
            # Safe provisional deferral: Dr < RAW, opted in, valid ETc present, rain arrives before stress onset
            is_significant_rain = raw_precip >= config.forecast_rain_delay_threshold_mm
            if is_significant_rain:
                res.is_provisional_deferral = True
                res.reassessment_interval_hours = config.forecast_reassessment_interval_hours
                decision_utc_safe = now_utc.replace(tzinfo=timezone.utc) if now_utc.tzinfo is None else now_utc.astimezone(timezone.utc)
                res.reassessment_timestamp = decision_utc_safe + timedelta(hours=config.forecast_reassessment_interval_hours)
                res.reasons.append(DecisionReasonCode.FORECAST_DEFERRAL_PROVISIONAL_POLICY)
                stress_str = f"{res.stress_onset_hours:.1f}h (estimated)" if res.stress_onset_hours is not None else "outside horizon"
                rain_str = f"{res.rainfall_onset_hours:.1f}h" if res.rainfall_onset_hours is not None else "unspecified"
                res.audit_trail.append(
                    "Provisional forecast-deferral policy applied: in-situ infiltration/runoff parameters unavailable; "
                    f"deferral is based on raw NWP precipitation ({raw_precip:.1f} mm) while current Dr ({current_dr:.1f} mm) < RAW ({target_raw:.1f} mm). "
                    f"Rainfall onset ({rain_str}) verified before projected stress onset ({stress_str}). "
                    f"Reassessment scheduled at {res.reassessment_timestamp.isoformat()} (in {res.reassessment_interval_hours:.0f}h)."
                )

    # 8. Determine Actionability for Irrigation Delay
    if res.is_valid and not res.is_stale and is_within_horizon and is_significant_rain and res.probability_sufficient and not res.rainfall_after_stress and res.is_etc_window_valid:
        res.is_actionable = True
        res.audit_trail.append(
            f"Actionable forecast rain: {raw_precip:.1f} mm total within {forecast.forecast_period_hours:.0f}h "
            f"(prob: {forecast.forecast_probability if forecast.forecast_probability is not None else 'N/A'}, source: {forecast.forecast_source})."
        )
    else:
        res.is_actionable = False
        res.is_provisional_deferral = False
        res.reassessment_timestamp = None
        res.reassessment_interval_hours = None

    return res


def extract_water_balance_metrics(
    water_balance: Optional[WaterBalanceResult],
) -> Tuple[Optional[float], Optional[float], Optional[float], float]:
    """Extract (Dr, RAW, TAW, Ks) from WaterBalanceResult with alias fallback."""
    if water_balance is None:
        return None, None, None, 1.0

    dr = getattr(water_balance, "final_depletion_mm", None)
    if dr is None:
        dr = getattr(water_balance, "depletion_dr_mm", None)

    caps = getattr(water_balance, "soil_capacities", None)
    taw = caps.total_available_water_mm if caps else getattr(water_balance, "total_available_water_mm", None)
    if taw is None:
        taw = getattr(water_balance, "total_available_water_taw_mm", None)

    raw = caps.readily_available_water_mm if caps else getattr(water_balance, "readily_available_water_mm", None)
    if raw is None:
        raw = getattr(water_balance, "readily_available_water_raw_mm", None)

    ks = getattr(water_balance, "water_stress_coefficient_ks", 1.0)
    return dr, raw, taw, ks


def validate_water_balance_evidence(
    water_balance: Optional[WaterBalanceResult],
    config: DecisionConfig,
    as_of_time: Optional[datetime] = None,
) -> EvidenceValidationResult:
    """Validate physical water balance evidence against quality, completeness, and safety rules.

    Args:
        water_balance: Phase 3 daily water-balance result.
        config: DecisionConfig containing freshness and provisional rules.
        as_of_time: UTC timestamp for evaluation.

    Returns:
        EvidenceValidationResult indicating whether evidence is actionable.
    """
    res = EvidenceValidationResult()

    if water_balance is None:
        res.is_valid = False
        res.is_insufficient = True
        res.blocking_reasons.append(DecisionReasonCode.EVIDENCE_WATER_BALANCE_INSUFFICIENT)
        res.audit_trail.append("Water balance evidence is completely missing (None).")
        return res

    # 1. Quality Status Check
    if water_balance.quality_status in (DataQualityStatus.INSUFFICIENT, DataQualityStatus.MISSING):
        res.is_valid = False
        res.is_insufficient = True
        res.blocking_reasons.append(DecisionReasonCode.EVIDENCE_WATER_BALANCE_INSUFFICIENT)
        res.audit_trail.append(
            f"Water balance quality status is '{water_balance.quality_status.value}'. Insufficient evidence for irrigation decisions."
        )

    # 2. Required Numerical Variables
    dr, raw, taw, ks = extract_water_balance_metrics(water_balance)
    if dr is None or dr < 0.0:
        res.is_valid = False
        res.is_insufficient = True
        res.blocking_reasons.append(DecisionReasonCode.EVIDENCE_WATER_BALANCE_INSUFFICIENT)
        res.audit_trail.append("Root-zone depletion Dr is null or unphysically negative.")

    if taw is None or taw <= 0.0 or raw is None or raw <= 0.0:
        res.is_valid = False
        res.is_insufficient = True
        res.blocking_reasons.append(DecisionReasonCode.EVIDENCE_SOIL_CAPACITY_MISSING)
        res.audit_trail.append("Essential soil water capacities (TAW or RAW) are missing or non-positive.")

    # 3. Staleness Check
    if water_balance.quality_status == DataQualityStatus.STALE:
        res.is_valid = False
        res.is_stale = True
        res.blocking_reasons.append(DecisionReasonCode.EVIDENCE_WATER_BALANCE_STALE)
        res.audit_trail.append("Water balance evidence is explicitly marked as STALE.")

    # 4. Suspect / Sensor Defect Check
    if water_balance.quality_status == DataQualityStatus.SUSPECT:
        res.is_valid = False
        res.is_suspect = True
        res.blocking_reasons.append(DecisionReasonCode.EVIDENCE_WATER_BALANCE_SUSPECT)
        res.audit_trail.append("Water balance evidence is marked SUSPECT due to sensor defect or unphysical boundary.")

    # 5. Provisional Empirical Rainfall Gating (Phase 3.2.4 Contract)
    is_provisional = getattr(water_balance, "is_provisional_empirical", False)
    if is_provisional and not config.allow_provisional_rainfall:
        res.is_valid = False
        res.is_provisional_blocked = True
        res.blocking_reasons.append(DecisionReasonCode.EVIDENCE_PROVISIONAL_RAINFALL_BLOCKED)
        res.audit_trail.append(
            "Water balance relies on provisional empirical effective rainfall without explicit "
            "allow_provisional_rainfall=True opt-in. Decision action is blocked per agronomic safety rules."
        )

    if res.is_valid:
        res.audit_trail.append("Water balance evidence passed all verification checks.")

    return res


def validate_irrigation_quantities(
    net_depth_mm: Optional[float],
    gross_depth_mm: Optional[float],
    efficiency: Optional[float],
    area_ha: Optional[float],
    volume_m3: Optional[float],
    config: DecisionConfig,
) -> Tuple[bool, List[str], Dict[str, Any]]:
    """Validate mathematical consistency and physical bounds of calculated irrigation quantities.

    Returns:
        Tuple of (is_valid, validation_errors_or_warnings, metadata_dict).
    """
    errors: List[str] = []
    meta: Dict[str, Any] = {
        "net_depth_valid": True,
        "gross_depth_valid": True,
        "efficiency_valid": True,
        "volume_consistent": True,
        "operational_bound_respected": True,
        "split_application_required": False,
    }

    if net_depth_mm is None:
        return True, ["Quantities are null (no water recommended)."], meta

    # When net depth is positive, but efficiency is unknown: gross depth and volume are withheld
    if gross_depth_mm is None and efficiency is None:
        meta["efficiency_valid"] = False
        meta["gross_depth_valid"] = False
        meta["volume_consistent"] = (volume_m3 is None)
        errors.append("Application efficiency is unknown; gross depth and volume are withheld while net depth is reported.")
        return True, errors, meta

    # 1. Non-negative Check
    if net_depth_mm < 0.0 or (gross_depth_mm is not None and gross_depth_mm < 0.0):
        errors.append(f"Irrigation depth cannot be negative (net: {net_depth_mm}, gross: {gross_depth_mm}).")
        meta["net_depth_valid"] = False
        meta["gross_depth_valid"] = False

    # 2. Efficiency Range Check
    if efficiency is None or efficiency <= 0.0 or efficiency > 1.0:
        errors.append(f"Application efficiency must be in (0.0, 1.0], found: {efficiency}.")
        meta["efficiency_valid"] = False
    elif gross_depth_mm is not None:
        # Gross must be >= net (within float tolerance)
        expected_gross = net_depth_mm / efficiency
        if gross_depth_mm < net_depth_mm - 1e-4:
            errors.append(f"Gross depth ({gross_depth_mm:.2f} mm) cannot be less than net depth ({net_depth_mm:.2f} mm).")
            meta["gross_depth_valid"] = False
        if abs(gross_depth_mm - expected_gross) > 0.05:
            errors.append(f"Gross depth ({gross_depth_mm:.2f} mm) deviates from net / efficiency ({expected_gross:.2f} mm).")
            meta["gross_depth_valid"] = False

    # 3. Volume Check
    if area_ha is not None and area_ha > 0.0:
        if gross_depth_mm is not None:
            if volume_m3 is None:
                errors.append("Zone area is recorded but irrigation volume was not calculated.")
                meta["volume_consistent"] = False
            else:
                # 1 mm over 1 ha = 1e-3 m * 10000 m² = 10 m³
                expected_vol = gross_depth_mm * area_ha * 10.0
                if abs(volume_m3 - expected_vol) > 0.1:
                    errors.append(f"Volume ({volume_m3:.1f} m³) does not match gross_depth * area * 10 ({expected_vol:.1f} m³).")
                    meta["volume_consistent"] = False
        else:
            if volume_m3 is not None:
                errors.append("Volume must be null when gross depth is withheld.")
                meta["volume_consistent"] = False
    else:
        if volume_m3 is not None:
            errors.append(f"Volume must be null when zone area is unknown or zero, but found: {volume_m3}.")
            meta["volume_consistent"] = False

    # 4. Operational Upper Bound
    if gross_depth_mm is not None and gross_depth_mm > config.max_allowable_gross_depth_mm:
        errors.append(
            f"Gross depth ({gross_depth_mm:.1f} mm) exceeds single-event operational limit ({config.max_allowable_gross_depth_mm:.1f} mm). Split application required."
        )
        meta["operational_bound_respected"] = False
        meta["split_application_required"] = True
        meta["max_single_event_limit_mm"] = config.max_allowable_gross_depth_mm

    is_valid = len(errors) == 0 or all(
        "exceeds single-event operational limit" in e or "Application efficiency is unknown" in e
        for e in errors
    )
    return is_valid, errors, meta


def validate_agronomic_non_watering_isolation(
    stress_assessment: Optional[ZoneStressAssessment],
    water_balance: Optional[WaterBalanceResult],
) -> Tuple[List[DecisionReasonCode], List[str], List[str]]:
    """Enforce that vegetation optical anomalies and soil hazards do NOT inflate irrigation requirements.

    Scientific Principle:
    - SCL/NDVI canopy anomalies indicate greenness depression, which can result from disease,
      senescence, nutrient deficiency, or weed competition. They MUST NOT trigger irrigation
      if the root-zone water balance is healthy.
    - Soil salinity, alkalinity, and sodicity require drainage feasibility studies and leaching
      fraction calculations; they must NOT automatically increase water depth in MVP.

    Returns:
        Tuple of (non_watering_reason_codes, assumptions, audit_notes).
    """
    reasons: List[DecisionReasonCode] = []
    assumptions: List[str] = []
    audit: List[str] = []

    if stress_assessment is None:
        return reasons, assumptions, audit

    # 1. Vegetation Domain Isolation
    veg_eval = getattr(stress_assessment, "vegetation_evaluation", None)
    if veg_eval is None and hasattr(stress_assessment, "domain_assessments"):
        veg_eval = stress_assessment.domain_assessments.get("vegetation")
    if veg_eval is not None and veg_eval.status in (StressStatus.ATTENTION, StressStatus.HIGH_STRESS):
        reasons.append(DecisionReasonCode.AGRONOMIC_FLAG_VEGETATION_ANOMALY_NON_WATERING)
        assumptions.append(
            "Vegetation canopy spectral anomaly detected. Additional irrigation is strictly WITHHELD "
            "because root-zone water balance governs water requirement independently of spectral greenness."
        )
        audit.append(
            f"Vegetation status is '{veg_eval.status.value}'. Non-watering isolation policy applied."
        )

    # 2. Soil Domain Isolation
    soil_eval = getattr(stress_assessment, "soil_evaluation", None)
    if soil_eval is None and hasattr(stress_assessment, "domain_assessments"):
        soil_eval = stress_assessment.domain_assessments.get("soil")
    if soil_eval is not None and soil_eval.status in (StressStatus.ATTENTION, StressStatus.HIGH_STRESS):
        soil_reasons = getattr(soil_eval, "reason_codes", [])
        if any("SALINITY" in str(r) for r in soil_reasons):
            reasons.append(DecisionReasonCode.AGRONOMIC_FLAG_SOIL_SALINITY_NON_WATERING)
            assumptions.append(
                "Soil salinity hazard detected. Leaching fraction calculations and drainage verification "
                "are not automated; irrigation volume is NOT increased for salinity in MVP."
            )
            audit.append("Soil salinity hazard flagged for agronomist review; extra watering withheld.")
        if any("PH" in str(r) or "ALKALINE" in str(r) or "SODIC" in str(r) for r in soil_reasons):
            reasons.append(DecisionReasonCode.AGRONOMIC_FLAG_SOIL_ALKALINE_NON_WATERING)
            assumptions.append(
                "High soil pH / sodicity hazard flagged for agronomic soil management; extra watering withheld."
            )
            audit.append("Soil pH/sodicity flagged for soil management; extra watering withheld.")

    # 3. Weather Domain Flags
    weath_eval = getattr(stress_assessment, "weather_evaluation", None)
    if weath_eval is None and hasattr(stress_assessment, "domain_assessments"):
        weath_eval = stress_assessment.domain_assessments.get("weather")
    if weath_eval is not None:
        weath_reasons = getattr(weath_eval, "reason_codes", [])
        if any("FROST" in str(r) for r in weath_reasons):
            reasons.append(DecisionReasonCode.AGRONOMIC_FLAG_WEATHER_FROST_WARNING)
            audit.append("Meteorological frost risk flagged in weather domain.")
        if any("HEAT" in str(r) or "VAPOR_PRESSURE_DEFICIT" in str(r) for r in weath_reasons):
            reasons.append(DecisionReasonCode.AGRONOMIC_FLAG_WEATHER_HEAT_NON_WATERING)
            audit.append("Atmospheric evaporative demand / heat stress flagged; water balance governs refill.")

    return reasons, assumptions, audit
