"""Effective Rainfall Estimation Module.

Distinguishes total precipitation from effective rainfall (P_eff) that actually
enters and is retained in the crop root zone, accounting for surface runoff,
deep drainage, and canopy interception losses.

Supported Methodologies:
1. FAO Dependable Daily Rainfall Method (Experimental / Provisional Empirical Adaptation):
   - Source: Empirical adaptation commonly cited in irrigation scheduling manuals
     adapting FAO Irrigation and Drainage Paper 24 (Doorenbos & Pruitt, 1977, pp. 74-76)
     and FAO-56 daily water budgets.
   - Temporal Resolution: Daily event aggregation (WeatherWindowType.DAILY_SUMMARY).
   - Geographic & Soil Applicability: Flat to gently undulating cultivated fields
     with medium-textured soils (loam, silt loam).
   - Gating & Guardrails: Explicitly marked as experimental/provisional. It is gated
     behind allow_provisional_method=True to prevent it from silently feeding operational
     irrigation calculations or farmer-facing decision outputs. Physical mass-balance
     mode (gross precipitation minus validated runoff) is the preferred operational pathway.
   - Core Formulation:
       * P <= 5 mm/day: P_eff = 0 mm
         (Assumes low-intensity rainfall is entirely lost to canopy interception and
          rapid bare-soil surface evaporation before entering root-zone storage).
       * 5 < P <= 50 mm/day: P_eff = 0.8 * P - 4.0 mm
         (Accounts for 20% runoff/deep drainage losses plus 4 mm initial surface abstraction).
       * P > 50 mm/day: P_eff = 0.7 * P
         (Heavy storm events with higher runoff fractions; effective fraction capped at 70%).
   - Boundary Discontinuity at P = 50 mm/day:
     * At P = 50.0 mm/day: P_eff = 0.8 * (50.0) - 4.0 = 36.0 mm (72.0% effective).
     * At P = 50.01 mm/day: P_eff = 0.7 * (50.01) = 35.007 mm (70.0% effective).
     * This creates a sudden mathematical drop of ~1.0 mm across the 50.0 mm/day boundary
       due to the piecewise empirical formulation. In physical root-zone modeling, this
       method must be treated strictly as a provisional empirical index.

2. USDA Soil Conservation Service (SCS) Monthly Method (FAO CROPWAT Simplified Variant):
   - Authoritative Source: Martin Smith (1992), FAO Irrigation and Drainage Paper No. 46:
     "CROPWAT: A computer program for irrigation planning and management", Section 3.2,
     FAO, Rome; and FAO CROPWAT 8.0.
   - Simplified SCS-Derived Variant: This empirical formula is a simplified piecewise
     parabola/linear fit to the multi-parameter USDA-SCS Technical Release No. 21 (TR-21, 1967/1970)
     nomograph curves, parameterized for average usable soil water storage (D ~ 75 mm)
     and typical crop consumptive use rates.
   - Comparison with FAO AquaCrop:
     * FAO AquaCrop (Reference Manual, Chapter 3) performs daily dynamic root-zone water balance
       and calculates event surface runoff using the event-based USDA-SCS Curve Number (CN)
       method (USDA 1964; Rallison 1980; Steenhuis et al. 1995), where S = 25400/CN - 254,
       Ia = 0.05S, and RO = (P - Ia)² / (P - Ia + S).
     * The monthly formula implemented here is NOT the AquaCrop daily CN method.
       It is the monthly empirical planning formulation from FAO CROPWAT Paper 46.
     * When monthly data is used in AquaCrop, it generates synthetic daily rain showers
       or applies full TR-21 procedures.
   - Full USDA-SCS TR-21 vs Implemented Formulation:
     * Full USDA-SCS TR-21 formulation:
       P_eff = f(D) * (1.25 * P_tot^0.824 - 2.93) * 10^(0.000955 * ETc)
       where f(D) is a cubic polynomial of usable soil water storage depth D.
     * The implemented FAO CROPWAT variant:
       For P_month <= 250 mm: P_eff,raw = P_month * (125.0 - 0.2 * P_month) / 125.0
       For P_month > 250 mm:  P_eff,raw = 125.0 + 0.1 * P_month
     * Physical & Agronomic Ceiling:
       P_eff = min(P_eff,raw, P_month, ETc,month)
       (P_eff cannot exceed actual monthly precipitation or monthly crop consumptive use).

3. Empirical Fixed Fraction Method:
   - P_eff = max(0.0, min(P, fraction * (P - threshold_mm)))
   - Simple linear model with explicit surface abstraction threshold.

Agronomic Guardrails:
1. Never Coerce Missing to Zero: None remains None. Missing rainfall evidence
   must NEVER be silently assumed to be 0 mm. Missing consumptive use in USDA-SCS
   returns effective_rainfall_mm=None with an explicit INSUFFICIENT result.
2. Genuine Zero vs Missing: When inputs are complete and yield zero effective rainfall
   (e.g. P <= 5 mm/day or ETc = 0), effective_rainfall_mm=0.0 is returned with GOOD quality.
3. Non-Negative Rainfall: P < 0 raises ValueError immediately.
4. Conservation of Mass & Agronomic Ceiling: Effective rainfall can never exceed total
   precipitation (P_eff <= P_total) nor crop consumptive use in USDA-SCS.
5. Window Compatibility: Validates that daily formulas are not misapplied to sub-hourly records,
   and monthly formulas strictly require complete non-overlapping monthly aggregation windows.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from backend.app.intelligence.types import DataQualityStatus, ProvenanceType, WeatherWindowType


class EffectiveRainfallMethod(str, Enum):
    """Supported scientific methodologies for effective rainfall estimation."""
    FAO_DEPENDABLE = "fao_dependable_daily"
    USDA_SCS = "usda_scs"  # FAO CROPWAT simplified USDA-SCS monthly formulation
    FAO_CROPWAT_USDA_SCS = "usda_scs"  # Canonical alias documenting FAO Paper 46 provenance
    FIXED_FRACTION = "fixed_fraction"


class EffectiveRainfallResult(BaseModel):
    """Structured result of effective rainfall estimation."""

    effective_rainfall_mm: Optional[float] = Field(default=None, ge=0.0, description="Estimated effective rainfall in mm (None if evidence is insufficient)")
    total_precipitation_mm: float = Field(..., ge=0.0, description="Total gross precipitation in mm")
    method: EffectiveRainfallMethod = Field(..., description="Estimation methodology applied")
    effective_fraction: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Ratio of effective to total precipitation")
    raw_effective_rainfall_mm: Optional[float] = Field(default=None, ge=0.0, description="Raw unconstrained empirical effective rainfall before consumptive use ceiling (mm)")
    crop_usable_effective_rainfall_mm: Optional[float] = Field(default=None, ge=0.0, description="Effective rainfall usable against crop consumptive use ETc (mm)")
    window_type: WeatherWindowType = Field(..., description="Aggregation temporal window of rainfall input")
    provenance_type: ProvenanceType = Field(..., description="Provenance of the underlying rainfall measurement")
    units: str = Field(default="mm", description="Depth measurement units")
    window_start_utc: Optional[datetime] = Field(default=None, description="Aggregation window start timestamp (UTC)")
    window_end_utc: Optional[datetime] = Field(default=None, description="Aggregation window end timestamp (UTC)")
    monthly_crop_consumptive_use_mm: Optional[float] = Field(default=None, ge=0.0, description="Monthly crop consumptive use (ETc) ceiling in mm")
    is_provisional_empirical: bool = Field(default=False, description="Whether method is a provisional empirical adaptation")
    limitations: List[str] = Field(default_factory=list, description="Methodological limitations and assumptions")
    quality_status: DataQualityStatus = Field(default=DataQualityStatus.GOOD, description="Quality classification")


def validate_consecutive_windows(
    windows: List[Tuple[datetime, datetime]],
    window_type: Optional[WeatherWindowType] = None,
    strict_continuity: bool = False,
) -> bool:
    """Validate that a sequence of monthly or 30-day windows is complete, chronological, and non-overlapping.

    Args:
        windows: List of (window_start_utc, window_end_utc) datetime tuples.
        window_type: Optional WeatherWindowType (e.g. WeatherWindowType.MONTHLY, WINDOW_30D, APPROXIMATE_30D).
            - If MONTHLY: verifies that every window strictly matches actual calendar-month boundaries
              (starts on the 1st of the month at 00:00:00 UTC and ends on the 1st of the subsequent month
              at 00:00:00 UTC). Rolling 30-day periods cannot be silently treated as calendar months.
            - If WINDOW_30D: verifies that duration is strictly exactly 30 elapsed days (720.0 hours).
            - If APPROXIMATE_30D: verifies that duration is between 28.0 and 31.5 days.
        strict_continuity: If True, rejects any temporal gaps between consecutive windows
            (requires next_start == curr_end). If False, allows disjoint periods as long as they
            are strictly chronological and non-overlapping.

    Returns:
        True if all windows are valid and meet continuity requirements.

    Raises:
        ValueError: If windows are empty, malformed, inverted (end <= start), timezone-naive,
            non-UTC, out of chronological order, overlapping, failing calendar boundaries,
            or containing gaps when strict_continuity=True.
        TypeError: If windows or elements are of incorrect types.
    """
    if not windows:
        raise ValueError("Window list cannot be empty.")

    for i, item in enumerate(windows):
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise ValueError(f"Window {i} must be a 2-tuple of (start_utc, end_utc) datetimes.")
        start, end = item
        if not isinstance(start, datetime) or not isinstance(end, datetime):
            raise TypeError(f"Window {i} start and end must be datetime objects, got ({type(start)}, {type(end)}).")

        # Timezone validation
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError(f"Window {i} timestamps must be timezone-aware (UTC), got naive timestamp.")
        start_offset = start.utcoffset()
        end_offset = end.utcoffset()
        if start_offset is None or start_offset.total_seconds() != 0 or end_offset is None or end_offset.total_seconds() != 0:
            raise ValueError(f"Window {i} timestamps must be in UTC timezone (offset zero), got incompatible timezone.")

        if end <= start:
            raise ValueError(
                f"Window {i} end ({end}) must be strictly after start ({start}) "
                f"(window_end_utc must be strictly after window_start_utc)."
            )

        # Calendar month validation: must align with exact calendar boundaries
        if window_type == WeatherWindowType.MONTHLY:
            if start.day != 1 or start.hour != 0 or start.minute != 0 or start.second != 0 or start.microsecond != 0:
                raise ValueError(
                    f"Window {i} start ({start}) does not align with a calendar month boundary. "
                    "Calendar-month periods must start on the 1st of the month at 00:00:00 UTC. "
                    "Rolling 30-day windows cannot be silently treated as calendar months."
                )
            expected_end_year = start.year + 1 if start.month == 12 else start.year
            expected_end_month = 1 if start.month == 12 else start.month + 1
            if (end.year != expected_end_year or end.month != expected_end_month or
                end.day != 1 or end.hour != 0 or end.minute != 0 or end.second != 0 or end.microsecond != 0):
                raise ValueError(
                    f"Window {i} end ({end}) does not align with the first day of the subsequent calendar month "
                    f"(expected {expected_end_year:04d}-{expected_end_month:02d}-01 00:00:00 UTC). "
                    "Rolling 30-day windows cannot be silently treated as calendar months."
                )
        elif window_type == WeatherWindowType.WINDOW_30D:
            duration_hours = (end - start).total_seconds() / 3600.0
            if abs(duration_hours - 720.0) > 0.1:
                raise ValueError(
                    f"WINDOW_30D aggregation duration must be between 28 and 31 days (strictly exactly 30 days / 720.0 hours), "
                    f"got {duration_hours / 24.0:.2f} days ({duration_hours:.1f} hours). "
                    "For provider-reported approximate 30-day periods (28-31.5 days), use WeatherWindowType.APPROXIMATE_30D. "
                    "For calendar months, use WeatherWindowType.MONTHLY."
                )
        elif window_type == WeatherWindowType.APPROXIMATE_30D:
            duration_days = (end - start).total_seconds() / 86400.0
            if duration_days < 28.0 or duration_days > 31.5:
                raise ValueError(
                    f"APPROXIMATE_30D aggregation duration must be between 28.0 and 31.5 days, got {duration_days:.2f} days."
                )

    # Check consecutive ordering, overlaps, and gaps
    for i in range(len(windows) - 1):
        curr_start, curr_end = windows[i]
        next_start, next_end = windows[i + 1]

        if next_start < curr_start:
            raise ValueError(
                f"Out of order window detected: Window {i+1} starts at {next_start} before "
                f"Window {i} starts at {curr_start}."
            )
        if next_start < curr_end:
            raise ValueError(
                f"Overlapping window detected: Window {i+1} starts at {next_start} before "
                f"Window {i} ends at {curr_end}. Overlapping or rolling windows cannot be "
                "silently treated as consecutive monthly observations."
            )
        if next_start > curr_end:
            if strict_continuity:
                gap_days = (next_start - curr_end).total_seconds() / 86400.0
                raise ValueError(
                    f"Discontinuous window gap detected: Window {i} ends at {curr_end} but "
                    f"Window {i+1} starts at {next_start} (gap of {gap_days:.1f} days). "
                    "In strict continuity mode, gaps between consecutive periods are prohibited."
                )

    return True


def calculate_effective_rainfall(
    precipitation_mm: Optional[float],
    method: EffectiveRainfallMethod = EffectiveRainfallMethod.FAO_DEPENDABLE,
    window_type: WeatherWindowType = WeatherWindowType.DAILY_SUMMARY,
    provenance_type: ProvenanceType = ProvenanceType.PROVIDER_MODELLED,
    fixed_fraction: float = 0.80,
    interception_threshold_mm: float = 2.0,
    monthly_crop_consumptive_use_mm: Optional[float] = None,
    window_start_utc: Optional[datetime] = None,
    window_end_utc: Optional[datetime] = None,
    units: str = "mm",
    allow_provisional_method: bool = False,
) -> EffectiveRainfallResult:
    """Calculate effective rainfall from total precipitation using a documented method.

    Args:
        precipitation_mm: Total gross rainfall in mm. Must not be None or negative.
        method: EffectiveRainfallMethod to apply.
        window_type: WeatherWindowType of input rainfall.
        provenance_type: ProvenanceType of the precipitation record.
        fixed_fraction: Multiplier fraction for FIXED_FRACTION method (0.1 - 1.0).
        interception_threshold_mm: Surface interception threshold in mm for FIXED_FRACTION.
        monthly_crop_consumptive_use_mm: Required monthly crop consumptive use (ETc,month) in mm
            for USDA-SCS method to enforce the physical consumptive ceiling. If None, USDA-SCS
            returns effective_rainfall_mm=None with INSUFFICIENT quality status.
        window_start_utc: Optional aggregation window start timestamp (UTC).
        window_end_utc: Optional aggregation window end timestamp (UTC).
        units: Depth measurement units (default 'mm').
        allow_provisional_method: Explicit opt-in flag required to evaluate the experimental/provisional
            FAO dependable daily method. If False and FAO_DEPENDABLE is requested, raises ValueError.

    Returns:
        EffectiveRainfallResult containing effective rainfall and audit trail.

    Raises:
        ValueError: If precipitation_mm is None, negative, timescale is incompatible, window duration
            is invalid, or provisional method is invoked without explicit opt-in.
    """
    if precipitation_mm is None:
        raise ValueError(
            "Cannot calculate effective rainfall: precipitation_mm is None. "
            "Missing rainfall evidence must not be silently coerced to zero."
        )

    if precipitation_mm < 0.0:
        raise ValueError(f"Precipitation cannot be negative: {precipitation_mm} mm.")

    p_tot = float(precipitation_mm)
    limitations: List[str] = []
    is_provisional = False

    # 1. Method Gating for Provisional Daily Method
    if method == EffectiveRainfallMethod.FAO_DEPENDABLE:
        if not allow_provisional_method:
            raise ValueError(
                "The FAO dependable daily effective rainfall method ('fao_dependable_daily') is an "
                "experimental/provisional empirical adaptation with a known mathematical step discontinuity "
                "at P=50 mm/day. It is gated to prevent silent propagation into operational irrigation "
                "calculations or farmer-facing decision outputs. Set allow_provisional_method=True to "
                "explicitly opt in for research or comparative analysis. For operational daily water balances, "
                "physical mass-balance mode (gross precipitation minus validated runoff) is the preferred pathway."
            )
        is_provisional = True
        limitations.append(
            "Method: FAO Dependable Daily Rainfall (EXPERIMENTAL / PROVISIONAL empirical adaptation of FAO-24 / FAO-56)."
        )
        limitations.append(
            "Assumptions: Daily event on flat-to-undulating agricultural field; medium soil texture. "
            "Not locally validated or universally applicable."
        )

        if p_tot == 0.0:
            p_eff = 0.0
            eff_frac = 1.0
        elif p_tot <= 5.0:
            p_eff = 0.0
            eff_frac = 0.0
            limitations.append(
                "Rainfall <= 5.0 mm/day: Assumed 100% lost to canopy interception and topsoil evaporation."
            )
        elif p_tot <= 50.0:
            p_eff = 0.8 * p_tot - 4.0
            eff_frac = p_eff / p_tot if p_tot > 0 else 0.0
            limitations.append(
                "Rainfall 5-50 mm/day: Applied Peff = 0.8 * P - 4.0 mm."
            )
        else:
            p_eff = 0.7 * p_tot
            eff_frac = 0.70
            limitations.append(
                "Rainfall > 50 mm/day: Applied Peff = 0.7 * P (increased storm runoff fraction). "
                "Notice: A mathematical step discontinuity of ~1.0 mm exists at P = 50.0 mm/day "
                "(P=50 gives 36.0 mm; P=50.01 gives 35.0 mm) inherent to this piecewise empirical formulation."
            )

        if window_type in {WeatherWindowType.HOURLY, WeatherWindowType.INSTANTANEOUS}:
            limitations.append(
                "Warning: FAO dependable formula was empirically calibrated for daily totals; "
                f"application to sub-daily ({window_type.value}) observations introduces uncertainty."
            )

    # 2. USDA-SCS Monthly Method
    elif method == EffectiveRainfallMethod.USDA_SCS:
        # Enforce strict timescale validation: must be actual monthly aggregation
        is_monthly_window = window_type in {
            WeatherWindowType.MONTHLY,
            WeatherWindowType.WINDOW_30D,
            WeatherWindowType.APPROXIMATE_30D,
        }

        if not is_monthly_window:
            raise ValueError(
                "USDA-SCS effective rainfall method strictly requires actual monthly accumulated rainfall "
                f"(WeatherWindowType.MONTHLY, WINDOW_30D, or APPROXIMATE_30D). Consuming daily or sub-daily observations "
                f"({window_type.value}) is prohibited. Individual daily observations cannot be scaled "
                "by assumed multipliers."
            )

        # Enforce explicit timestamps and duration for WINDOW_30D
        if window_type == WeatherWindowType.WINDOW_30D:
            if window_start_utc is None or window_end_utc is None:
                raise ValueError(
                    "WeatherWindowType.WINDOW_30D requires explicit window_start_utc and window_end_utc timestamps."
                )
            validate_consecutive_windows([(window_start_utc, window_end_utc)], window_type=WeatherWindowType.WINDOW_30D)
            duration_hours = (window_end_utc - window_start_utc).total_seconds() / 3600.0
            limitations.append(
                f"Method Variant: Non-calendar fixed 30-day accumulation window (approximate variant, exactly {duration_hours:.1f} hours). "
                "Caution: Canonical FAO CROPWAT USDA-SCS requires actual calendar-month aggregation. "
                "Fixed 30-day windows cannot be silently treated as calendar-month totals."
            )
        elif window_type == WeatherWindowType.APPROXIMATE_30D:
            if window_start_utc is None or window_end_utc is None:
                raise ValueError(
                    "WeatherWindowType.APPROXIMATE_30D requires explicit window_start_utc and window_end_utc timestamps."
                )
            validate_consecutive_windows([(window_start_utc, window_end_utc)], window_type=WeatherWindowType.APPROXIMATE_30D)
            duration_days = (window_end_utc - window_start_utc).total_seconds() / 86400.0
            limitations.append(
                f"Method Variant: Experimental non-calendar approximate 30-day variant ({duration_days:.1f} days). "
                "Caution: Canonical FAO CROPWAT USDA-SCS requires actual calendar-month aggregation. "
                "Approximate multi-day windows cannot be silently treated as calendar-month totals."
            )
        elif window_type == WeatherWindowType.MONTHLY:
            if window_start_utc is not None or window_end_utc is not None:
                if window_start_utc is None or window_end_utc is None:
                    raise ValueError(
                        "Calendar-month window requires both window_start_utc and window_end_utc when timestamps are provided."
                    )
                validate_consecutive_windows([(window_start_utc, window_end_utc)], window_type=WeatherWindowType.MONTHLY)
            limitations.append(
                "Method: Canonical FAO CROPWAT USDA-SCS monthly formulation (Martin Smith 1992, "
                "FAO Irrigation & Drainage Paper 46; derived from USDA-SCS TR-21). "
                "Aggregation convention: Standard calendar month."
            )

        # Compute raw unconstrained empirical monthly formula first
        if p_tot == 0.0:
            p_eff_raw = 0.0
        elif p_tot <= 250.0:
            p_eff_raw = min(p_tot, p_tot * (125.0 - 0.2 * p_tot) / 125.0)
        else:
            p_eff_raw = min(p_tot, 125.0 + 0.1 * p_tot)

        # Require monthly crop consumptive use - return None if missing, while preserving raw empirical result!
        if monthly_crop_consumptive_use_mm is None:
            return EffectiveRainfallResult(
                effective_rainfall_mm=None,
                total_precipitation_mm=round(p_tot, 2),
                method=method,
                effective_fraction=None,
                raw_effective_rainfall_mm=round(p_eff_raw, 2),
                crop_usable_effective_rainfall_mm=None,
                window_type=window_type,
                provenance_type=provenance_type,
                units=units,
                window_start_utc=window_start_utc,
                window_end_utc=window_end_utc,
                monthly_crop_consumptive_use_mm=None,
                is_provisional_empirical=False,
                limitations=[
                    "Aborted USDA-SCS estimation: Missing monthly crop consumptive use (ETc). "
                    "USDA-SCS TR-21 / FAO CROPWAT methodology requires monthly crop consumptive use to enforce "
                    "the agronomic effective rainfall ceiling (P_eff <= ETc,month). "
                    "Effective rainfall usable by the crop is withheld (None) to prevent treating missing evidence as zero. "
                    f"Raw unconstrained empirical effective rainfall is preserved as {p_eff_raw:.2f} mm."
                ],
                quality_status=DataQualityStatus.INSUFFICIENT,
            )

        if monthly_crop_consumptive_use_mm < 0.0:
            raise ValueError(
                f"Monthly crop consumptive use cannot be negative: {monthly_crop_consumptive_use_mm} mm."
            )

        etc_month = float(monthly_crop_consumptive_use_mm)
        limitations.append(
            "Method: FAO CROPWAT simplified USDA-SCS monthly formulation (Martin Smith 1992, "
            "FAO Irrigation & Drainage Paper 46; derived from USDA-SCS TR-21)."
        )

        if p_tot == 0.0:
            p_eff = 0.0
            p_eff_usable = 0.0
            eff_frac = 1.0
        else:
            # Enforce strict double upper bounds:
            # 1. P_eff <= actual monthly rainfall
            # 2. P_eff <= monthly crop consumptive use
            p_eff_usable = min(p_eff_raw, etc_month)
            p_eff_usable = max(0.0, p_eff_usable)
            p_eff = p_eff_usable
            eff_frac = p_eff_usable / p_tot if p_tot > 0 else 0.0

            if p_eff_usable < p_eff_raw:
                limitations.append(
                    f"Effective rainfall capped by monthly crop consumptive use ({etc_month:.2f} mm). "
                    f"Raw empirical effective rainfall was {p_eff_raw:.2f} mm."
                )

    # 3. Fixed Fraction Method
    elif method == EffectiveRainfallMethod.FIXED_FRACTION:
        if fixed_fraction <= 0.0 or fixed_fraction > 1.0:
            raise ValueError(f"Invalid fixed_fraction: {fixed_fraction}. Must be in (0, 1].")
        if p_tot == 0.0:
            p_eff = 0.0
            eff_frac = 1.0
        else:
            p_net = max(0.0, p_tot - interception_threshold_mm)
            p_eff = fixed_fraction * p_net
            eff_frac = p_eff / p_tot if p_tot > 0 else 0.0
            limitations.append(
                f"Applied fixed fraction ({fixed_fraction:.2f}) with {interception_threshold_mm:.1f} mm threshold."
            )

    else:
        raise ValueError(f"Unsupported effective rainfall method: {method}")

    # Enforce physical mass balance: 0.0 <= P_eff <= P_total
    p_eff_bounded = max(0.0, min(p_tot, float(p_eff)))
    final_fraction = p_eff_bounded / p_tot if p_tot > 0 else eff_frac
    raw_val = p_eff_raw if method == EffectiveRainfallMethod.USDA_SCS else p_eff_bounded

    return EffectiveRainfallResult(
        effective_rainfall_mm=round(p_eff_bounded, 2),
        total_precipitation_mm=round(p_tot, 2),
        method=method,
        effective_fraction=round(final_fraction, 4),
        raw_effective_rainfall_mm=round(raw_val, 2),
        crop_usable_effective_rainfall_mm=round(p_eff_bounded, 2),
        window_type=window_type,
        provenance_type=provenance_type,
        units=units,
        window_start_utc=window_start_utc,
        window_end_utc=window_end_utc,
        monthly_crop_consumptive_use_mm=round(monthly_crop_consumptive_use_mm, 2) if monthly_crop_consumptive_use_mm is not None else None,
        is_provisional_empirical=is_provisional,
        limitations=limitations,
        quality_status=DataQualityStatus.GOOD,
    )
