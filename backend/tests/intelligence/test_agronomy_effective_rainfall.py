"""Tests for effective rainfall estimation, mass balance, and missing-evidence handling."""

from datetime import datetime, timezone
import pytest

from backend.app.intelligence.agronomy.effective_rainfall import (
    EffectiveRainfallMethod,
    EffectiveRainfallResult,
    calculate_effective_rainfall,
    validate_consecutive_windows,
)
from backend.app.intelligence.types import DataQualityStatus, ProvenanceType, WeatherWindowType


def test_provisional_daily_method_gating():
    """Verify that FAO dependable daily method cannot be used without explicit opt-in."""
    with pytest.raises(ValueError, match="is an experimental/provisional empirical adaptation with a known mathematical step discontinuity"):
        calculate_effective_rainfall(
            precipitation_mm=25.0,
            method=EffectiveRainfallMethod.FAO_DEPENDABLE,
            allow_provisional_method=False,
        )


def test_hand_calculated_fao_dependable_daily_rainfall():
    """Verify FAO dependable daily rainfall formulas against exact hand calculations when opted in.

    Formulas:
    1. P <= 5 mm -> Peff = 0 mm (canopy interception & direct evaporation loss)
    2. 5 < P <= 50 mm -> Peff = 0.8 * P - 4.0 mm
    3. P > 50 mm -> Peff = 0.7 * P (runoff loss)
    """
    # Case 1: P = 4.0 mm <= 5.0 mm -> Peff = 0.0 mm (genuine calculated zero!)
    r_light = calculate_effective_rainfall(
        precipitation_mm=4.0,
        method=EffectiveRainfallMethod.FAO_DEPENDABLE,
        allow_provisional_method=True,
    )
    assert r_light.effective_rainfall_mm == 0.0
    assert r_light.total_precipitation_mm == 4.0
    assert r_light.effective_fraction == 0.0
    assert r_light.is_provisional_empirical is True
    assert r_light.quality_status == DataQualityStatus.GOOD

    # Case 2: P = 25.0 mm in (5, 50] -> Peff = 0.8 * 25.0 - 4.0 = 20.0 - 4.0 = 16.0 mm
    r_mod = calculate_effective_rainfall(
        precipitation_mm=25.0,
        method=EffectiveRainfallMethod.FAO_DEPENDABLE,
        allow_provisional_method=True,
    )
    assert r_mod.effective_rainfall_mm == 16.0
    assert r_mod.effective_fraction == 16.0 / 25.0  # 0.6400

    # Case 3: P = 80.0 mm > 50 mm -> Peff = 0.7 * 80.0 = 56.0 mm
    r_heavy = calculate_effective_rainfall(
        precipitation_mm=80.0,
        method=EffectiveRainfallMethod.FAO_DEPENDABLE,
        allow_provisional_method=True,
    )
    assert r_heavy.effective_rainfall_mm == 56.0
    assert r_heavy.effective_fraction == 0.7000


def test_fao_dependable_boundary_discontinuity_at_50mm():
    """Investigate and verify the documented piecewise mathematical discontinuity at P = 50.0 mm/day.

    At P = 50.0 mm: Peff = 0.8 * 50.0 - 4.0 = 36.0 mm (72% effective).
    At P = 50.01 mm: Peff = 0.7 * 50.01 = 35.007 mm (70% effective).
    Result: A step decrease of ~1.0 mm occurs due to empirical slope change.
    """
    res_at_50 = calculate_effective_rainfall(
        precipitation_mm=50.0,
        method=EffectiveRainfallMethod.FAO_DEPENDABLE,
        window_type=WeatherWindowType.DAILY_SUMMARY,
        allow_provisional_method=True,
    )
    res_above_50 = calculate_effective_rainfall(
        precipitation_mm=50.01,
        method=EffectiveRainfallMethod.FAO_DEPENDABLE,
        window_type=WeatherWindowType.DAILY_SUMMARY,
        allow_provisional_method=True,
    )

    assert res_at_50.effective_rainfall_mm == 36.0
    assert pytest.approx(res_above_50.effective_rainfall_mm, abs=1e-2) == 35.01
    assert res_above_50.effective_rainfall_mm < res_at_50.effective_rainfall_mm
    assert any("step discontinuity" in note for note in res_above_50.limitations)


def test_hand_calculated_usda_scs_rainfall():
    """Verify FAO CROPWAT simplified USDA-SCS effective rainfall formula against hand calculations.

    Reference: Martin Smith (1992), FAO Irrigation & Drainage Paper 46, Section 3.2.
    Formulas:
    1. P <= 250 mm:
       Peff = P * (125 - 0.2 * P) / 125
       For P = 100.0 mm, ETc = 120.0 mm:
       Peff = 100 * (125 - 20) / 125 = 100 * 105 / 125 = 84.00 mm
       For P = 150.0 mm, ETc = 160.0 mm:
       Peff = 150 * (125 - 30) / 125 = 150 * 95 / 125 = 114.00 mm
    2. P > 250 mm:
       Peff = 125 + 0.1 * P
       For P = 300.0 mm, ETc = 200.0 mm:
       Peff = 125 + 0.1 * 300 = 155.00 mm <= 200.0 mm -> 155.00 mm
    """
    # Case 1: P = 100 mm <= 250 mm
    res1 = calculate_effective_rainfall(
        precipitation_mm=100.0,
        method=EffectiveRainfallMethod.USDA_SCS,
        window_type=WeatherWindowType.MONTHLY,
        monthly_crop_consumptive_use_mm=120.0,
    )
    assert pytest.approx(res1.effective_rainfall_mm, abs=1e-2) == 84.00
    assert pytest.approx(res1.effective_fraction, abs=1e-4) == 0.8400
    assert res1.quality_status == DataQualityStatus.GOOD

    # Case 2: P = 150 mm using canonical alias FAO_CROPWAT_USDA_SCS
    res2 = calculate_effective_rainfall(
        precipitation_mm=150.0,
        method=EffectiveRainfallMethod.FAO_CROPWAT_USDA_SCS,
        window_type=WeatherWindowType.MONTHLY,
        monthly_crop_consumptive_use_mm=160.0,
    )
    assert pytest.approx(res2.effective_rainfall_mm, abs=1e-2) == 114.00
    assert pytest.approx(res2.effective_fraction, abs=1e-4) == 0.7600
    assert any("FAO CROPWAT simplified USDA-SCS monthly formulation" in note for note in res2.limitations)

    # Case 3: P = 300 mm > 250 mm
    res3 = calculate_effective_rainfall(
        precipitation_mm=300.0,
        method=EffectiveRainfallMethod.USDA_SCS,
        window_type=WeatherWindowType.MONTHLY,
        monthly_crop_consumptive_use_mm=200.0,
    )
    assert pytest.approx(res3.effective_rainfall_mm, abs=1e-2) == 155.00
    assert pytest.approx(res3.effective_fraction, abs=1e-4) == 155.0 / 300.0


def test_usda_scs_timescale_rejection():
    """Verify USDA-SCS strictly rejects daily and sub-daily observations."""
    with pytest.raises(ValueError, match="USDA-SCS effective rainfall method strictly requires actual monthly accumulated rainfall"):
        calculate_effective_rainfall(
            precipitation_mm=10.0,
            method=EffectiveRainfallMethod.USDA_SCS,
            window_type=WeatherWindowType.DAILY_SUMMARY,
        )

    with pytest.raises(ValueError, match="USDA-SCS effective rainfall method strictly requires actual monthly accumulated rainfall"):
        calculate_effective_rainfall(
            precipitation_mm=5.0,
            method=EffectiveRainfallMethod.USDA_SCS,
            window_type=WeatherWindowType.HOURLY,
        )


def test_usda_scs_missing_consumptive_use_returns_none():
    """Verify missing monthly crop consumptive use returns effective_rainfall_mm=None with INSUFFICIENT."""
    res = calculate_effective_rainfall(
        precipitation_mm=100.0,
        method=EffectiveRainfallMethod.USDA_SCS,
        window_type=WeatherWindowType.MONTHLY,
        monthly_crop_consumptive_use_mm=None,
    )
    assert res.quality_status == DataQualityStatus.INSUFFICIENT
    assert res.effective_rainfall_mm is None  # Must be None, not 0.0!
    assert res.effective_fraction is None
    assert any("Missing monthly crop consumptive use" in note for note in res.limitations)
    assert any("withheld (None)" in note for note in res.limitations)


def test_genuine_zero_effective_rainfall_distinguishable_from_missing():
    """Verify that a genuine calculated 0.0 mm effective rainfall is distinguishable from missing evidence (None)."""
    # 1. Missing evidence -> None with INSUFFICIENT
    res_missing = calculate_effective_rainfall(
        precipitation_mm=100.0,
        method=EffectiveRainfallMethod.USDA_SCS,
        window_type=WeatherWindowType.MONTHLY,
        monthly_crop_consumptive_use_mm=None,
    )
    assert res_missing.effective_rainfall_mm is None
    assert res_missing.quality_status == DataQualityStatus.INSUFFICIENT

    # 2. Genuine zero rainfall event -> 0.0 with GOOD
    res_zero_p = calculate_effective_rainfall(
        precipitation_mm=0.0,
        method=EffectiveRainfallMethod.USDA_SCS,
        window_type=WeatherWindowType.MONTHLY,
        monthly_crop_consumptive_use_mm=50.0,
    )
    assert res_zero_p.effective_rainfall_mm == 0.0
    assert res_zero_p.quality_status == DataQualityStatus.GOOD

    # 3. Genuine zero crop demand (fallow / dormancy) -> 0.0 with GOOD
    res_zero_etc = calculate_effective_rainfall(
        precipitation_mm=50.0,
        method=EffectiveRainfallMethod.USDA_SCS,
        window_type=WeatherWindowType.MONTHLY,
        monthly_crop_consumptive_use_mm=0.0,
    )
    assert res_zero_etc.effective_rainfall_mm == 0.0
    assert res_zero_etc.quality_status == DataQualityStatus.GOOD

    # 4. Low daily rainfall completely lost to interception -> 0.0 with GOOD
    res_fao_low = calculate_effective_rainfall(
        precipitation_mm=3.0,
        method=EffectiveRainfallMethod.FAO_DEPENDABLE,
        allow_provisional_method=True,
    )
    assert res_fao_low.effective_rainfall_mm == 0.0
    assert res_fao_low.quality_status == DataQualityStatus.GOOD


def test_usda_scs_effective_rainfall_capped_by_consumptive_use():
    """Verify effective rainfall cannot exceed monthly crop consumptive use."""
    # Monthly P = 100.0 mm -> unconstrained USDA-SCS Peff = 84.0 mm
    # But monthly ETc = 50.0 mm -> Peff must be capped at 50.0 mm!
    res = calculate_effective_rainfall(
        precipitation_mm=100.0,
        method=EffectiveRainfallMethod.USDA_SCS,
        window_type=WeatherWindowType.MONTHLY,
        monthly_crop_consumptive_use_mm=50.0,
    )
    assert res.effective_rainfall_mm == 50.0
    assert res.effective_fraction == 50.0 / 100.0  # 0.50
    assert any("capped by monthly crop consumptive use (50.00 mm)" in note for note in res.limitations)


def test_monthly_window_validity_and_duration():
    """Verify WINDOW_30D requires explicit timestamps and valid 28-31 day duration."""
    t_start = datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc)
    t_end_30d = datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc)  # exactly 30 days

    # 1. Valid 30-day window
    res = calculate_effective_rainfall(
        precipitation_mm=150.0,
        method=EffectiveRainfallMethod.USDA_SCS,
        window_type=WeatherWindowType.WINDOW_30D,
        monthly_crop_consumptive_use_mm=120.0,
        window_start_utc=t_start,
        window_end_utc=t_end_30d,
        units="mm",
    )
    assert res.window_start_utc == t_start
    assert res.window_end_utc == t_end_30d
    assert res.units == "mm"
    assert any("Non-calendar fixed 30-day accumulation window" in note for note in res.limitations)

    # 2. Missing timestamps for WINDOW_30D
    with pytest.raises(ValueError, match="WINDOW_30D requires explicit window_start_utc and window_end_utc"):
        calculate_effective_rainfall(
            precipitation_mm=100.0,
            method=EffectiveRainfallMethod.USDA_SCS,
            window_type=WeatherWindowType.WINDOW_30D,
            monthly_crop_consumptive_use_mm=100.0,
            window_start_utc=None,
        )

    # 3. Inverted timestamps (end <= start)
    with pytest.raises(ValueError, match="must be strictly after window_start_utc"):
        calculate_effective_rainfall(
            precipitation_mm=100.0,
            method=EffectiveRainfallMethod.USDA_SCS,
            window_type=WeatherWindowType.WINDOW_30D,
            monthly_crop_consumptive_use_mm=100.0,
            window_start_utc=t_end_30d,
            window_end_utc=t_start,
        )

    # 4. Invalid duration: 15 days (too short)
    t_short = datetime(2026, 6, 16, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="duration must be between 28 and 31 days"):
        calculate_effective_rainfall(
            precipitation_mm=100.0,
            method=EffectiveRainfallMethod.USDA_SCS,
            window_type=WeatherWindowType.WINDOW_30D,
            monthly_crop_consumptive_use_mm=100.0,
            window_start_utc=t_start,
            window_end_utc=t_short,
        )

    # 5. Invalid duration: 45 days (too long)
    t_long = datetime(2026, 7, 16, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="duration must be between 28 and 31 days"):
        calculate_effective_rainfall(
            precipitation_mm=100.0,
            method=EffectiveRainfallMethod.USDA_SCS,
            window_type=WeatherWindowType.WINDOW_30D,
            monthly_crop_consumptive_use_mm=100.0,
            window_start_utc=t_start,
            window_end_utc=t_long,
        )


def test_validate_consecutive_windows_rejection_of_overlapping():
    """Verify validation of consecutive monthly periods rejects overlapping or out-of-order windows."""
    w1 = (datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc), datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc))
    w2 = (datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc), datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc))
    w_overlap = (datetime(2026, 6, 20, 0, 0, tzinfo=timezone.utc), datetime(2026, 7, 20, 0, 0, tzinfo=timezone.utc))

    # Valid non-overlapping sequence
    assert validate_consecutive_windows([w1, w2]) is True

    # Rejection of overlapping rolling windows
    with pytest.raises(ValueError, match="Overlapping window detected"):
        validate_consecutive_windows([w1, w_overlap])

    # Rejection of reversed chronological order
    with pytest.raises(ValueError, match="Out of order window detected"):
        validate_consecutive_windows([w2, w1])


def test_zero_precipitation_handling():
    """Verify that zero precipitation yields zero effective rainfall without error."""
    res = calculate_effective_rainfall(0.0, method=EffectiveRainfallMethod.FIXED_FRACTION)
    assert res.effective_rainfall_mm == 0.0
    assert res.total_precipitation_mm == 0.0
    assert res.effective_fraction == 1.0


def test_missing_precipitation_rejection():
    """Verify scientific restriction: None is NEVER coerced to 0.0 mm."""
    with pytest.raises(ValueError, match="Cannot calculate effective rainfall: precipitation_mm is None"):
        calculate_effective_rainfall(None)


def test_negative_precipitation_rejection():
    """Verify that physically impossible negative precipitation raises ValueError."""
    with pytest.raises(ValueError, match="Precipitation cannot be negative"):
        calculate_effective_rainfall(-10.0)


def test_mass_conservation_invariant():
    """Verify fundamental mass conservation: Peff is mathematically <= P_total for all positive rain."""
    for p in [0.0, 1.0, 5.0, 10.0, 30.0, 50.0, 75.0, 150.0, 300.0]:
        for method in [EffectiveRainfallMethod.FAO_DEPENDABLE, EffectiveRainfallMethod.USDA_SCS, EffectiveRainfallMethod.FIXED_FRACTION]:
            window = WeatherWindowType.MONTHLY if method == EffectiveRainfallMethod.USDA_SCS else WeatherWindowType.DAILY_SUMMARY
            res = calculate_effective_rainfall(
                p,
                method=method,
                window_type=window,
                monthly_crop_consumptive_use_mm=200.0 if method == EffectiveRainfallMethod.USDA_SCS else None,
                allow_provisional_method=True,
            )
            assert res.effective_rainfall_mm <= res.total_precipitation_mm
            assert res.effective_rainfall_mm >= 0.0


def test_validate_consecutive_windows_strict_continuity_gaps():
    """Verify continuity detection distinguishes gaps from overlaps and enforces strict mode."""
    # June and August (July is missing -> gap of 31 days)
    w_june = (datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc), datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc))
    w_aug = (datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc), datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc))

    # In default mode (strict_continuity=False): allowed since they are chronological and disjoint
    assert validate_consecutive_windows([w_june, w_aug], strict_continuity=False) is True

    # In strict mode (strict_continuity=True): gap must be rejected
    with pytest.raises(ValueError, match="Discontinuous window gap detected"):
        validate_consecutive_windows([w_june, w_aug], strict_continuity=True)


def test_validate_consecutive_windows_malformed_and_inverted():
    """Verify validation rejects empty, malformed, non-datetime, or inverted windows."""
    # 1. Empty list
    with pytest.raises(ValueError, match="Window list cannot be empty"):
        validate_consecutive_windows([])

    # 2. Malformed tuple (not 2 items)
    with pytest.raises(ValueError, match="must be a 2-tuple"):
        validate_consecutive_windows([(datetime(2026, 6, 1, tzinfo=timezone.utc),)])

    # 3. Non-datetime elements
    with pytest.raises(TypeError, match="must be datetime objects"):
        validate_consecutive_windows([("2026-06-01", "2026-07-01")])

    # 4. Inverted window (end <= start)
    w_inv = (datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc), datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc))
    with pytest.raises(ValueError, match="must be strictly after start"):
        validate_consecutive_windows([w_inv])


def test_validate_consecutive_windows_timezone_incompatibility():
    """Verify validation strictly rejects timezone-naive and non-UTC timezone timestamps."""
    from datetime import timedelta

    # 1. Timezone-naive datetime
    w_naive = (datetime(2026, 6, 1, 0, 0), datetime(2026, 7, 1, 0, 0))
    with pytest.raises(ValueError, match="must be timezone-aware"):
        validate_consecutive_windows([w_naive])

    # 2. Timezone-aware but non-UTC (e.g. IST +05:30)
    ist = timezone(timedelta(hours=5, minutes=30))
    w_ist = (datetime(2026, 6, 1, 0, 0, tzinfo=ist), datetime(2026, 7, 1, 0, 0, tzinfo=ist))
    with pytest.raises(ValueError, match="must be in UTC timezone"):
        validate_consecutive_windows([w_ist])


def test_validate_consecutive_windows_calendar_month_boundaries():
    """Verify calendar month mode strictly rejects non-calendar and rolling 30-day windows."""
    # 1. Rolling 30-day window (June 15 to July 15)
    w_rolling = (datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc), datetime(2026, 7, 15, 0, 0, tzinfo=timezone.utc))
    with pytest.raises(ValueError, match="does not align with a calendar month boundary"):
        validate_consecutive_windows([w_rolling], window_type=WeatherWindowType.MONTHLY)

    # 2. Starts on 1st but wrong end (June 1 to June 25)
    w_partial = (datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc), datetime(2026, 6, 25, 0, 0, tzinfo=timezone.utc))
    with pytest.raises(ValueError, match="does not align with the first day of the subsequent calendar month"):
        validate_consecutive_windows([w_partial], window_type=WeatherWindowType.MONTHLY)

    # 3. Valid consecutive calendar months (June and July 2026)
    w_june = (datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc), datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc))
    w_july = (datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc), datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc))
    assert validate_consecutive_windows([w_june, w_july], window_type=WeatherWindowType.MONTHLY, strict_continuity=True) is True


def test_provisional_flag_propagation_through_water_balance_and_irrigation():
    """Verify that is_provisional_empirical flag survives all calculations and cannot be bypassed."""
    from backend.app.intelligence.agronomy.water_balance import (
        calculate_soil_water_capacities,
        update_root_zone_water_balance,
    )
    from backend.app.intelligence.agronomy.irrigation_requirement import (
        calculate_irrigation_requirement,
    )

    # 1. Gated generation of provisional result
    prov_rain = calculate_effective_rainfall(
        precipitation_mm=25.0,
        method=EffectiveRainfallMethod.FAO_DEPENDABLE,
        allow_provisional_method=True,
    )
    assert prov_rain.is_provisional_empirical is True

    # 2. Cannot bypass in water balance without allow_provisional_method=True
    caps = calculate_soil_water_capacities(0.320, 0.140, 1.0, 0.55)
    with pytest.raises(ValueError, match="provisional daily method and is gated"):
        update_root_zone_water_balance(
            soil_capacities=caps,
            initial_depletion_mm=30.0,
            rainfall_result=prov_rain,
            etc_mm=4.0,
            allow_provisional_method=False,
        )

    # 3. Survives into WaterBalanceResult
    wb_res = update_root_zone_water_balance(
        soil_capacities=caps,
        initial_depletion_mm=30.0,
        rainfall_result=prov_rain,
        etc_mm=4.0,
        allow_provisional_method=True,
    )
    assert wb_res.is_provisional_empirical is True
    assert any("PROVISIONAL" in n for n in wb_res.audit_trail)

    # 4. Survives into IrrigationRequirementResult
    irrig_res = calculate_irrigation_requirement(
        water_balance=wb_res,
        area_ha=2.5,
    )
    assert irrig_res.is_provisional_empirical is True
    assert any("PROVISIONAL" in n for n in irrig_res.audit_notes)


def test_window_30d_exact_duration_and_rejections():
    """Verify WINDOW_30D strictly requires exactly 30 elapsed days (720.0 hours)."""
    from datetime import timedelta
    t_start = datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc)

    # 1. Exactly 30 days (720 hours) -> Valid
    t_30d = t_start + timedelta(days=30)
    assert validate_consecutive_windows([(t_start, t_30d)], window_type=WeatherWindowType.WINDOW_30D) is True

    # 2. 28 days (672 hours) -> Rejected for WINDOW_30D
    t_28d = t_start + timedelta(days=28)
    with pytest.raises(ValueError, match="strictly exactly 30 days"):
        validate_consecutive_windows([(t_start, t_28d)], window_type=WeatherWindowType.WINDOW_30D)

    # 3. 31 days (744 hours) -> Rejected for WINDOW_30D
    t_31d = t_start + timedelta(days=31)
    with pytest.raises(ValueError, match="strictly exactly 30 days"):
        validate_consecutive_windows([(t_start, t_31d)], window_type=WeatherWindowType.WINDOW_30D)

    # 4. 31.5 days (756 hours) -> Rejected for WINDOW_30D
    t_31_5d = t_start + timedelta(days=31, hours=12)
    with pytest.raises(ValueError, match="strictly exactly 30 days"):
        validate_consecutive_windows([(t_start, t_31_5d)], window_type=WeatherWindowType.WINDOW_30D)


def test_approximate_30d_window_durations():
    """Verify APPROXIMATE_30D accepts provider-reported periods between 28 and 31.5 days."""
    from datetime import timedelta
    t_start = datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc)

    # 1. 28 days -> Valid
    assert validate_consecutive_windows([(t_start, t_start + timedelta(days=28))], window_type=WeatherWindowType.APPROXIMATE_30D) is True

    # 2. 30 days -> Valid
    assert validate_consecutive_windows([(t_start, t_start + timedelta(days=30))], window_type=WeatherWindowType.APPROXIMATE_30D) is True

    # 3. 31 days -> Valid
    assert validate_consecutive_windows([(t_start, t_start + timedelta(days=31))], window_type=WeatherWindowType.APPROXIMATE_30D) is True

    # 4. 31.5 days -> Valid
    assert validate_consecutive_windows([(t_start, t_start + timedelta(days=31, hours=12))], window_type=WeatherWindowType.APPROXIMATE_30D) is True

    # 5. 27 days -> Rejected
    with pytest.raises(ValueError, match="APPROXIMATE_30D aggregation duration must be between 28.0 and 31.5 days"):
        validate_consecutive_windows([(t_start, t_start + timedelta(days=27))], window_type=WeatherWindowType.APPROXIMATE_30D)

    # 6. 32 days -> Rejected
    with pytest.raises(ValueError, match="APPROXIMATE_30D aggregation duration must be between 28.0 and 31.5 days"):
        validate_consecutive_windows([(t_start, t_start + timedelta(days=32))], window_type=WeatherWindowType.APPROXIMATE_30D)


def test_calendar_month_cannot_be_silently_classified_as_window_30d():
    """Verify that calendar months are distinct from WINDOW_30D and not interchangeable."""
    # January has 31 days (2026-01-01 to 2026-02-01)
    jan_start = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    jan_end = datetime(2026, 2, 1, 0, 0, tzinfo=timezone.utc)

    # Valid as calendar MONTHLY
    assert validate_consecutive_windows([(jan_start, jan_end)], window_type=WeatherWindowType.MONTHLY) is True

    # Cannot be classified as WINDOW_30D (duration is 31 days, not 30 days!)
    with pytest.raises(ValueError, match="WINDOW_30D aggregation duration must be between 28 and 31 days"):
        validate_consecutive_windows([(jan_start, jan_end)], window_type=WeatherWindowType.WINDOW_30D)


def test_raw_effective_rainfall_versus_crop_usable_rainfall():
    """Verify distinction and simultaneous preservation of raw empirical rainfall and crop-usable rainfall."""
    # 1. P = 100 mm, ETc = 50 mm: Raw is 84.0 mm, Crop usable is 50.0 mm
    res_capped = calculate_effective_rainfall(
        precipitation_mm=100.0,
        method=EffectiveRainfallMethod.USDA_SCS,
        window_type=WeatherWindowType.MONTHLY,
        monthly_crop_consumptive_use_mm=50.0,
    )
    assert res_capped.raw_effective_rainfall_mm == pytest.approx(84.00, abs=1e-2)
    assert res_capped.crop_usable_effective_rainfall_mm == pytest.approx(50.00, abs=1e-2)
    assert res_capped.effective_rainfall_mm == pytest.approx(50.00, abs=1e-2)
    assert res_capped.quality_status == DataQualityStatus.GOOD

    # 2. Missing monthly ETc: Raw is 84.0 mm, Crop usable is None, Quality is INSUFFICIENT
    res_missing = calculate_effective_rainfall(
        precipitation_mm=100.0,
        method=EffectiveRainfallMethod.USDA_SCS,
        window_type=WeatherWindowType.MONTHLY,
        monthly_crop_consumptive_use_mm=None,
    )
    assert res_missing.raw_effective_rainfall_mm == pytest.approx(84.00, abs=1e-2)
    assert res_missing.crop_usable_effective_rainfall_mm is None
    assert res_missing.effective_rainfall_mm is None
    assert res_missing.quality_status == DataQualityStatus.INSUFFICIENT
    assert any("Raw unconstrained empirical effective rainfall is preserved as 84.00 mm" in note for note in res_missing.limitations)

    # 3. P = 0.0 mm: Both raw and usable are 0.0 mm
    res_zero = calculate_effective_rainfall(
        precipitation_mm=0.0,
        method=EffectiveRainfallMethod.USDA_SCS,
        window_type=WeatherWindowType.MONTHLY,
        monthly_crop_consumptive_use_mm=50.0,
    )
    assert res_zero.raw_effective_rainfall_mm == 0.0
    assert res_zero.crop_usable_effective_rainfall_mm == 0.0
    assert res_zero.effective_rainfall_mm == 0.0
    assert res_zero.quality_status == DataQualityStatus.GOOD


def test_provisional_rainfall_scalar_pathway_gating_and_provenance():
    """Verify that provisional status and provenance cannot be lost through the scalar effective_rainfall_mm pathway."""
    from backend.app.intelligence.agronomy.water_balance import (
        calculate_soil_water_capacities,
        update_root_zone_water_balance,
    )

    caps = calculate_soil_water_capacities(0.320, 0.140, 1.0, 0.55)

    # 1. Scalar input marked is_provisional_empirical=True without opt-in -> raises ValueError
    with pytest.raises(ValueError, match="effective rainfall input is derived from or marked as the provisional daily method and is gated"):
        update_root_zone_water_balance(
            soil_capacities=caps,
            initial_depletion_mm=30.0,
            effective_rainfall_mm=16.0,
            etc_mm=4.0,
            effective_rainfall_method=EffectiveRainfallMethod.FAO_DEPENDABLE,
            effective_rainfall_provenance=ProvenanceType.CALCULATED,
            is_provisional_empirical=True,
            allow_provisional_method=False,
        )

    # 2. Scalar input marked is_provisional_empirical=True with allow_provisional_method=True -> succeeds and exposes flag
    wb_res = update_root_zone_water_balance(
        soil_capacities=caps,
        initial_depletion_mm=30.0,
        effective_rainfall_mm=16.0,
        etc_mm=4.0,
        effective_rainfall_method=EffectiveRainfallMethod.FAO_DEPENDABLE,
        effective_rainfall_provenance=ProvenanceType.CALCULATED,
        is_provisional_empirical=True,
        allow_provisional_method=True,
    )
    assert wb_res.is_provisional_empirical is True
    assert any("PROVISIONAL" in n for n in wb_res.audit_trail)

    # 3. Scalar input with effective_rainfall_method=FAO_DEPENDABLE without opt-in -> raises ValueError
    with pytest.raises(ValueError, match="effective rainfall input is derived from or marked as the provisional daily method and is gated"):
        update_root_zone_water_balance(
            soil_capacities=caps,
            initial_depletion_mm=30.0,
            effective_rainfall_mm=16.0,
            etc_mm=4.0,
            effective_rainfall_method=EffectiveRainfallMethod.FAO_DEPENDABLE,
            effective_rainfall_provenance=ProvenanceType.CALCULATED,
            allow_provisional_method=False,
        )

    # 4. Scalar input with effective_rainfall_method=USDA_SCS -> raises ValueError (monthly method rejected in daily balance)
    with pytest.raises(ValueError, match="Monthly USDA-SCS effective rainfall cannot be consumed directly"):
        update_root_zone_water_balance(
            soil_capacities=caps,
            initial_depletion_mm=30.0,
            effective_rainfall_mm=16.0,
            etc_mm=4.0,
            effective_rainfall_method=EffectiveRainfallMethod.USDA_SCS,
            effective_rainfall_provenance=ProvenanceType.CALCULATED,
        )

    # 5. Provenance metadata is preserved in WaterBalanceResult
    wb_res_prov = update_root_zone_water_balance(
        soil_capacities=caps,
        initial_depletion_mm=30.0,
        effective_rainfall_mm=12.0,
        etc_mm=4.0,
        effective_rainfall_method="calibrated_field_water_budget",
        effective_rainfall_provenance=ProvenanceType.SENSOR_MEASURED,
    )
    assert wb_res_prov.effective_rainfall_method == "calibrated_field_water_budget"
    assert wb_res_prov.effective_rainfall_provenance == ProvenanceType.SENSOR_MEASURED
    assert wb_res_prov.is_provisional_empirical is False


