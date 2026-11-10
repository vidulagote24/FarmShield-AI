"""Tests for root-zone soil water balance, TAW/RAW capacities, and daily depletion updates."""

import pytest

from backend.app.intelligence.agronomy.water_balance import (
    SoilWaterCapacities,
    WaterBalanceRainfallMode,
    WaterBalanceResult,
    calculate_soil_water_capacities,
    initial_depletion_from_moisture,
    update_root_zone_water_balance,
)
from backend.app.intelligence.types import DataQualityStatus, ProvenanceType


def test_hand_calculated_taw_and_raw_capacities():
    """Verify TAW and RAW calculations against hand-calculated references.

    Formulas:
    TAW = 1000 * (theta_FC - theta_WP) * Zr
    RAW = p * TAW

    Test values:
    theta_FC = 0.320 m³/m³
    theta_WP = 0.140 m³/m³
    AWC = 0.320 - 0.140 = 0.180 m³/m³
    Zr = 1.0 m
    p = 0.55 (Wheat)

    Expected:
    TAW = 1000 * 0.180 * 1.0 = 180.0 mm
    RAW = 0.55 * 180.0 = 99.0 mm
    """
    caps = calculate_soil_water_capacities(
        field_capacity_m3_m3=0.320,
        wilting_point_m3_m3=0.140,
        rooting_depth_m=1.0,
        depletion_fraction_p=0.55,
    )
    assert pytest.approx(caps.available_water_capacity_m3_m3, abs=1e-4) == 0.180
    assert pytest.approx(caps.total_available_water_mm, abs=1e-2) == 180.00
    assert pytest.approx(caps.readily_available_water_mm, abs=1e-2) == 99.00


def test_initial_depletion_from_in_situ_soil_moisture():
    """Verify conversion of in-situ volumetric moisture into initial depletion Dr.

    Dr = 1000 * (theta_FC - theta) * Zr
    theta_FC = 0.320, Zr = 1.0 m
    If theta = 0.230 m³/m³:
    Expected Dr = 1000 * (0.320 - 0.230) * 1.0 = 90.0 mm
    """
    caps = calculate_soil_water_capacities(0.320, 0.140, 1.0, 0.55)
    dr, notes = initial_depletion_from_moisture(0.230, caps)
    assert pytest.approx(dr, abs=1e-2) == 90.00
    assert any("Computed initial Dr = 90.0 mm" in n for n in notes)


def test_hand_calculated_daily_water_balance_update():
    """Verify daily water balance accounting with hand-calculated inputs.

    Scenario:
    Dr,0 = 90.0 mm (from previous test)
    Peff = 10.0 mm
    Irrigation = 0.0 mm
    ETc = 5.0 mm

    Expected:
    Dr,1 = Dr,0 - Peff - I + ETc = 90.0 - 10.0 - 0.0 + 5.0 = 85.0 mm
    Deep percolation DP = 0.0 mm
    Dr,1 (85.0 mm) <= RAW (99.0 mm) -> is_in_stress_zone = False
    Equivalent soil moisture theta = 0.320 - (85.0 / (1000 * 1.0)) = 0.235 m³/m³
    """
    caps = calculate_soil_water_capacities(0.320, 0.140, 1.0, 0.55)

    res = update_root_zone_water_balance(
        soil_capacities=caps,
        initial_depletion_mm=90.0,
        effective_rainfall_mm=10.0,
        effective_rainfall_method="calibrated_water_balance",
        effective_rainfall_provenance=ProvenanceType.CALCULATED,
        etc_mm=5.0,
        applied_irrigation_mm=0.0,
    )

    assert res.quality_status == DataQualityStatus.GOOD
    assert pytest.approx(res.final_depletion_mm, abs=1e-2) == 85.00
    assert res.deep_percolation_mm == 0.0
    assert res.is_in_stress_zone == False
    assert res.stress_deficit_mm == 0.0
    assert pytest.approx(res.root_zone_moisture_m3_m3, abs=1e-4) == 0.2350


def test_deep_percolation_when_rainfall_exceeds_depletion():
    """Verify deep percolation accounting when rain exceeds depletion (soil wetter than FC).

    Scenario:
    Dr,0 = 20.0 mm
    Peff = 45.0 mm
    ETc = 5.0 mm

    Unconstrained Dr,raw = 20.0 - 45.0 + 5.0 = -20.0 mm
    Expected:
    Deep percolation DP = 20.0 mm
    Final Dr = 0.0 mm (soil restored exactly to FC)
    """
    caps = calculate_soil_water_capacities(0.320, 0.140, 1.0, 0.55)

    res = update_root_zone_water_balance(
        soil_capacities=caps,
        initial_depletion_mm=20.0,
        effective_rainfall_mm=45.0,
        etc_mm=5.0,
        effective_rainfall_method="calibrated_water_balance",
        effective_rainfall_provenance=ProvenanceType.CALCULATED,
    )

    assert res.final_depletion_mm == 0.0
    assert pytest.approx(res.deep_percolation_mm, abs=1e-2) == 20.00
    assert pytest.approx(res.root_zone_moisture_m3_m3, abs=1e-4) == 0.3200  # Exactly at FC


def test_water_stress_threshold_crossing():
    """Verify stress flag triggers when depletion exceeds readily available water (Dr > RAW).

    Scenario:
    TAW = 180.0 mm, RAW = 99.0 mm
    Dr,0 = 96.0 mm
    Peff = 0.0 mm
    ETc = 6.0 mm

    Expected:
    Dr,1 = 96.0 + 6.0 = 102.0 mm
    Dr,1 (102.0 mm) > RAW (99.0 mm) -> is_in_stress_zone = True
    Stress deficit = 102.0 - 99.0 = 3.0 mm
    """
    caps = calculate_soil_water_capacities(0.320, 0.140, 1.0, 0.55)

    res = update_root_zone_water_balance(
        soil_capacities=caps,
        initial_depletion_mm=96.0,
        etc_mm=6.0,
    )

    assert res.final_depletion_mm == 102.00
    assert res.is_in_stress_zone == True
    assert pytest.approx(res.stress_deficit_mm, abs=1e-2) == 3.00


def test_insufficient_data_rejection_when_context_absent():
    """Verify scientific restriction: missing soil context or initial state returns INSUFFICIENT."""
    caps = calculate_soil_water_capacities(0.320, 0.140, 1.0, 0.55)

    # Case 1: Missing soil capacities completely
    res_no_caps = update_root_zone_water_balance(
        soil_capacities=None,
        etc_mm=5.0,
    )
    assert res_no_caps.quality_status == DataQualityStatus.INSUFFICIENT
    assert any("Missing soil hydraulic properties" in a for a in res_no_caps.audit_trail)

    # Case 2: Missing initial moisture/depletion
    res_no_init = update_root_zone_water_balance(
        soil_capacities=caps,
        initial_depletion_mm=None,
        soil_moisture_m3_m3=None,
        etc_mm=5.0,
    )
    assert res_no_init.quality_status == DataQualityStatus.INSUFFICIENT
    assert any("No initial soil moisture or depletion evidence" in a for a in res_no_init.audit_trail)


def test_hydraulic_physics_validation():
    """Verify that physically impossible soil hydraulic parameters raise ValueError."""
    # WP >= FC
    with pytest.raises(ValueError, match="Wilting Point .* >= Field Capacity"):
        calculate_soil_water_capacities(
            field_capacity_m3_m3=0.200,
            wilting_point_m3_m3=0.250,
            rooting_depth_m=1.0,
        )

    # Negative depletion
    caps = calculate_soil_water_capacities(0.320, 0.140, 1.0, 0.55)
    with pytest.raises(ValueError, match="Initial depletion cannot be negative"):
        update_root_zone_water_balance(
            soil_capacities=caps,
            initial_depletion_mm=-5.0,
            etc_mm=5.0,
        )


def test_fao56_water_stress_coefficient_ks_hand_calculated():
    """Verify FAO-56 Eq. 84 water stress coefficient Ks across all depletion zones.

    Formula:
    Ks = 1.0                        for Dr <= RAW
    Ks = (TAW - Dr) / (TAW - RAW)   for Dr > RAW
    0.0 <= Ks <= 1.0
    """
    from backend.app.intelligence.agronomy.water_balance import calculate_water_stress_coefficient

    taw = 100.0
    raw = 50.0

    # 1. No stress: Dr = 20 mm < RAW
    assert calculate_water_stress_coefficient(20.0, raw, taw) == 1.0

    # 2. Threshold boundary: Dr = 50 mm == RAW
    assert calculate_water_stress_coefficient(50.0, raw, taw) == 1.0

    # 3. Mid stress: Dr = 75 mm -> (100 - 75) / (100 - 50) = 25 / 50 = 0.50
    assert calculate_water_stress_coefficient(75.0, raw, taw) == 0.50

    # 4. Severe stress: Dr = 90 mm -> (100 - 90) / 50 = 10 / 50 = 0.20
    assert pytest.approx(calculate_water_stress_coefficient(90.0, raw, taw), abs=1e-4) == 0.20

    # 5. Wilting point: Dr = 100 mm == TAW -> (100 - 100) / 50 = 0.0
    assert calculate_water_stress_coefficient(100.0, raw, taw) == 0.0

    # 6. Beyond wilting point: Dr = 120 mm > TAW -> clamped to 0.0
    assert calculate_water_stress_coefficient(120.0, raw, taw) == 0.0

    # 7. Saturated / negative depletion: Dr = -10 mm < 0 -> 1.0
    assert calculate_water_stress_coefficient(-10.0, raw, taw) == 1.0

    # 8. Edge case: RAW == TAW == 100.0
    assert calculate_water_stress_coefficient(50.0, 100.0, 100.0) == 1.0
    assert calculate_water_stress_coefficient(100.0, 100.0, 100.0) == 0.0


def test_water_balance_daily_update_with_active_stress_reduction():
    """Verify daily water balance update reduces actual ETc and depletion when Dr > RAW.

    Scenario:
    AWC = 0.200 m³/m³, Zr = 0.5 m -> TAW = 100.0 mm
    p = 0.50 -> RAW = 50.0 mm
    Initial Dr,0 = 75.0 mm (in stress zone)
    Peff = 0.0 mm, Irrig = 0.0 mm
    Standard ETc = 4.0 mm/day

    Step 1: Dr,pre = 75.0 mm
    Step 2: Ks = (100 - 75) / (100 - 50) = 25 / 50 = 0.50
    Step 3: ETc,adj = 0.50 * 4.0 = 2.0 mm
    Step 4: Dr,1 = 75.0 + 2.0 = 77.0 mm (vs 79.0 mm without stress adjustment)
    """
    caps = calculate_soil_water_capacities(
        field_capacity_m3_m3=0.350,
        wilting_point_m3_m3=0.150,
        rooting_depth_m=0.5,
        depletion_fraction_p=0.50,
    )
    assert caps.total_available_water_mm == 100.0
    assert caps.readily_available_water_mm == 50.0

    res = update_root_zone_water_balance(
        soil_capacities=caps,
        initial_depletion_mm=75.0,
        etc_mm=4.0,
        applied_irrigation_mm=0.0,
        apply_water_stress_adjustment=True,
    )

    assert res.water_stress_coefficient_ks == 0.500
    assert res.crop_evapotranspiration_mm == 4.00
    assert res.adjusted_crop_evapotranspiration_mm == 2.00
    assert res.final_depletion_mm == 77.00
    assert res.is_in_stress_zone is True
    assert res.stress_deficit_mm == 27.00  # 77.0 - 50.0


def test_physical_rainfall_balance_double_counting_avoidance():
    """Verify physical precipitation balance (Gross P - RO) prevents double counting losses.

    Scenario:
    Dr,0 = 30.0 mm
    Gross P = 50.0 mm
    Surface RO = 10.0 mm
    Infiltrating P = 50.0 - 10.0 = 40.0 mm
    Standard ETc = 4.0 mm

    Accounting:
    Pre-ET Dr = 30.0 - 40.0 = -10.0 mm (wetter than FC by 10 mm)
    Ks = 1.0 (soil saturated)
    Raw Dr = -10.0 + 4.0 = -6.0 mm
    Deep Percolation DP = 6.0 mm
    Final Dr = 0.0 mm
    """
    caps = calculate_soil_water_capacities(0.350, 0.150, 0.5, 0.50)

    res = update_root_zone_water_balance(
        soil_capacities=caps,
        initial_depletion_mm=30.0,
        gross_precipitation_mm=50.0,
        surface_runoff_mm=10.0,
        etc_mm=4.0,
    )

    assert res.gross_precipitation_mm == 50.0
    assert res.surface_runoff_mm == 10.0
    assert res.infiltrated_precipitation_mm == 40.0
    assert res.effective_rainfall_mm is None
    assert res.rainfall_mode == WaterBalanceRainfallMode.PHYSICAL
    assert res.deep_percolation_mm == 6.0
    assert res.final_depletion_mm == 0.0


def test_physical_mode_missing_runoff_rejection():
    """Verify physical mass-balance mode strictly rejects missing surface runoff (None)."""
    caps = calculate_soil_water_capacities(0.350, 0.150, 0.5, 0.50)
    with pytest.raises(ValueError, match="Physical mass-balance mode requires an explicit, validated surface_runoff_mm"):
        update_root_zone_water_balance(
            soil_capacities=caps,
            initial_depletion_mm=30.0,
            gross_precipitation_mm=50.0,
            surface_runoff_mm=None,  # Missing runoff
            etc_mm=4.0,
        )


def test_physical_mode_runoff_exceeding_precipitation_rejection():
    """Verify physical mode rejects runoff greater than gross precipitation."""
    caps = calculate_soil_water_capacities(0.350, 0.150, 0.5, 0.50)
    with pytest.raises(ValueError, match="cannot exceed gross precipitation"):
        update_root_zone_water_balance(
            soil_capacities=caps,
            initial_depletion_mm=30.0,
            gross_precipitation_mm=50.0,
            surface_runoff_mm=55.0,  # Runoff > Rainfall
            etc_mm=4.0,
        )


def test_mutually_exclusive_modes_rejection():
    """Verify that physical and empirical rainfall mode inputs cannot be mixed."""
    caps = calculate_soil_water_capacities(0.350, 0.150, 0.5, 0.50)

    # 1. Both gross_precipitation_mm and effective_rainfall_mm supplied
    with pytest.raises(ValueError, match="Mutually exclusive rainfall modes"):
        update_root_zone_water_balance(
            soil_capacities=caps,
            initial_depletion_mm=30.0,
            gross_precipitation_mm=50.0,
            effective_rainfall_mm=40.0,
            surface_runoff_mm=10.0,
            etc_mm=4.0,
            effective_rainfall_method="calibrated_water_balance",
            effective_rainfall_provenance=ProvenanceType.CALCULATED,
        )

    # 2. Supplying surface_runoff_mm in Empirical mode
    with pytest.raises(ValueError, match="Cannot supply surface_runoff_mm in Empirical rainfall mode"):
        update_root_zone_water_balance(
            soil_capacities=caps,
            initial_depletion_mm=30.0,
            effective_rainfall_mm=40.0,
            surface_runoff_mm=10.0,
            etc_mm=4.0,
            effective_rainfall_method="calibrated_water_balance",
            effective_rainfall_provenance=ProvenanceType.CALCULATED,
        )


def test_rejection_of_monthly_usda_scs_in_daily_water_balance():
    """Verify daily water balance rejects direct monthly USDA-SCS input without temporal disaggregation."""
    from backend.app.intelligence.agronomy.effective_rainfall import (
        EffectiveRainfallMethod,
        calculate_effective_rainfall,
    )
    from backend.app.intelligence.types import WeatherWindowType

    caps = calculate_soil_water_capacities(0.350, 0.150, 0.5, 0.50)
    monthly_scs_res = calculate_effective_rainfall(
        precipitation_mm=100.0,
        method=EffectiveRainfallMethod.USDA_SCS,
        window_type=WeatherWindowType.MONTHLY,
        monthly_crop_consumptive_use_mm=120.0,
    )

    with pytest.raises(ValueError, match="Monthly USDA-SCS effective rainfall cannot be consumed directly"):
        update_root_zone_water_balance(
            soil_capacities=caps,
            initial_depletion_mm=30.0,
            rainfall_result=monthly_scs_res,
            etc_mm=4.0,
        )


def test_daily_mass_conservation_both_modes():
    """Verify exact daily mass conservation for both Physical and Empirical modes.

    Equation:
    Dr,final - Dr,start = -P_inf - Irrig + ETc_adj + DP
    """
    caps = calculate_soil_water_capacities(0.350, 0.150, 1.0, 0.50)
    # TAW = 200 mm, RAW = 100 mm

    # Case A: Physical Mode
    # Dr,start = 80 mm, Gross P = 40 mm, Runoff = 10 mm -> P_inf = 30 mm, Irrig = 10 mm
    # Pre-ET Dr = 80 - 30 - 10 = 40 mm <= RAW (100 mm) -> Ks = 1.0
    # ETc = 5.0 mm -> Dr,raw = 40 + 5 = 45 mm -> DP = 0 mm, Dr,final = 45 mm
    res_phys = update_root_zone_water_balance(
        soil_capacities=caps,
        initial_depletion_mm=80.0,
        gross_precipitation_mm=40.0,
        surface_runoff_mm=10.0,
        applied_irrigation_mm=10.0,
        etc_mm=5.0,
    )
    delta_dr_phys = res_phys.final_depletion_mm - res_phys.initial_depletion_mm
    expected_delta_phys = -res_phys.infiltrated_precipitation_mm - res_phys.applied_irrigation_mm + res_phys.adjusted_crop_evapotranspiration_mm + res_phys.deep_percolation_mm
    assert pytest.approx(delta_dr_phys, abs=1e-2) == expected_delta_phys

    # Case B: Empirical Mode with Drainage
    # Dr,start = 30 mm, Peff = 50 mm, Irrig = 0 mm -> P_inf = 50 mm
    # Pre-ET Dr = 30 - 50 = -20 mm -> Ks = 1.0 (saturated)
    # ETc = 5.0 mm -> Dr,raw = -20 + 5 = -15 mm -> DP = 15 mm, Dr,final = 0.0 mm
    res_emp = update_root_zone_water_balance(
        soil_capacities=caps,
        initial_depletion_mm=30.0,
        effective_rainfall_mm=50.0,
        applied_irrigation_mm=0.0,
        etc_mm=5.0,
        effective_rainfall_method="calibrated_water_balance",
        effective_rainfall_provenance=ProvenanceType.CALCULATED,
    )
    delta_dr_emp = res_emp.final_depletion_mm - res_emp.initial_depletion_mm
    expected_delta_emp = -res_emp.infiltrated_precipitation_mm - res_emp.applied_irrigation_mm + res_emp.adjusted_crop_evapotranspiration_mm + res_emp.deep_percolation_mm
    assert pytest.approx(delta_dr_emp, abs=1e-2) == expected_delta_emp
    assert res_emp.final_depletion_mm == 0.0
    assert pytest.approx(res_emp.deep_percolation_mm, abs=1e-2) == 15.0


def test_climatic_p_adjustment_in_capacities():
    """Verify calculate_soil_water_capacities adjusts depletion fraction p for high ETc."""
    caps_high_etc = calculate_soil_water_capacities(
        field_capacity_m3_m3=0.350,
        wilting_point_m3_m3=0.150,
        rooting_depth_m=1.0,
        depletion_fraction_p=0.55,
        etc_mm_day=8.0,
        adjust_p_for_etc=True,
    )
    # p_adj = 0.55 + 0.04 * (5.0 - 8.0) = 0.55 - 0.12 = 0.43
    assert caps_high_etc.is_p_adjusted is True
    assert caps_high_etc.depletion_fraction_p_table == 0.55
    assert pytest.approx(caps_high_etc.depletion_fraction_p, abs=1e-3) == 0.43
    # TAW = 1000 * 0.20 * 1.0 = 200 mm
    # RAW = 0.43 * 200 = 86.0 mm
    assert pytest.approx(caps_high_etc.readily_available_water_mm, abs=1e-2) == 86.0


def test_downstream_propagation_of_missing_effective_rainfall():
    """Verify water balance returns INSUFFICIENT when rainfall_result has missing (None) effective rainfall."""
    from backend.app.intelligence.agronomy.effective_rainfall import (
        EffectiveRainfallMethod,
        calculate_effective_rainfall,
    )
    from backend.app.intelligence.types import WeatherWindowType

    caps = calculate_soil_water_capacities(0.320, 0.140, 1.0, 0.55)

    # Missing monthly ETc -> effective_rainfall_mm is None, quality_status is INSUFFICIENT
    missing_rain = calculate_effective_rainfall(
        precipitation_mm=50.0,
        method=EffectiveRainfallMethod.USDA_SCS,
        window_type=WeatherWindowType.MONTHLY,
        monthly_crop_consumptive_use_mm=None,
    )
    assert missing_rain.effective_rainfall_mm is None
    assert missing_rain.quality_status == DataQualityStatus.INSUFFICIENT

    wb_res = update_root_zone_water_balance(
        soil_capacities=caps,
        initial_depletion_mm=30.0,
        rainfall_result=missing_rain,
        etc_mm=4.0,
    )

    assert wb_res.quality_status == DataQualityStatus.INSUFFICIENT
    assert any("missing effective rainfall" in n for n in wb_res.audit_trail)


def test_provisional_daily_method_gating_in_water_balance():
    """Verify daily water balance gates the provisional FAO dependable daily method."""
    from backend.app.intelligence.agronomy.effective_rainfall import (
        EffectiveRainfallMethod,
        calculate_effective_rainfall,
    )
    from backend.app.intelligence.types import WeatherWindowType

    caps = calculate_soil_water_capacities(0.320, 0.140, 1.0, 0.55)

    prov_rain = calculate_effective_rainfall(
        precipitation_mm=25.0,
        method=EffectiveRainfallMethod.FAO_DEPENDABLE,
        window_type=WeatherWindowType.DAILY_SUMMARY,
        allow_provisional_method=True,
    )
    assert prov_rain.is_provisional_empirical is True
    assert prov_rain.effective_rainfall_mm == pytest.approx(16.0)

    # 1. Without allow_provisional_method -> raises ValueError
    with pytest.raises(ValueError, match="provisional daily method and is gated"):
        update_root_zone_water_balance(
            soil_capacities=caps,
            initial_depletion_mm=40.0,
            rainfall_result=prov_rain,
            etc_mm=4.0,
            allow_provisional_method=False,
        )

    # 2. With allow_provisional_method=True -> succeeds
    wb_res = update_root_zone_water_balance(
        soil_capacities=caps,
        initial_depletion_mm=40.0,
        rainfall_result=prov_rain,
        etc_mm=4.0,
        allow_provisional_method=True,
    )
    assert wb_res.quality_status == DataQualityStatus.GOOD
    # Dr,start = 40.0 - 16.0 + 4.0 = 28.0 mm
    assert pytest.approx(wb_res.final_depletion_mm, abs=1e-2) == 28.00
    assert any("PROVISIONAL" in n for n in wb_res.audit_trail)


def test_scalar_effective_rainfall_provenance_and_contract():
    """Verify Phase 3.2.4 strict scalar effective rainfall contract and provenance propagation."""
    from backend.app.intelligence.agronomy.effective_rainfall import EffectiveRainfallMethod
    from backend.app.intelligence.agronomy.irrigation_requirement import calculate_irrigation_requirement

    caps = calculate_soil_water_capacities(0.320, 0.140, 1.0, 0.55)

    # 1. No method -> raises ValueError
    with pytest.raises(ValueError, match="explicit effective_rainfall_method is required"):
        update_root_zone_water_balance(
            soil_capacities=caps,
            initial_depletion_mm=30.0,
            effective_rainfall_mm=15.0,
            etc_mm=4.0,
            effective_rainfall_method=None,
            effective_rainfall_provenance=ProvenanceType.CALCULATED,
        )

    # 2. No provenance -> raises ValueError
    with pytest.raises(ValueError, match="explicit effective_rainfall_provenance is required"):
        update_root_zone_water_balance(
            soil_capacities=caps,
            initial_depletion_mm=30.0,
            effective_rainfall_mm=15.0,
            etc_mm=4.0,
            effective_rainfall_method="calibrated_water_balance",
            effective_rainfall_provenance=None,
        )

    # 3. Unknown provenance -> raises ValueError
    with pytest.raises(ValueError, match="effective_rainfall_provenance cannot be 'unknown'"):
        update_root_zone_water_balance(
            soil_capacities=caps,
            initial_depletion_mm=30.0,
            effective_rainfall_mm=15.0,
            etc_mm=4.0,
            effective_rainfall_method="calibrated_water_balance",
            effective_rainfall_provenance="unknown",
        )

    # 4. Known physical/approved provenance -> succeeds and preserves metadata
    wb_approved = update_root_zone_water_balance(
        soil_capacities=caps,
        initial_depletion_mm=30.0,
        effective_rainfall_mm=15.0,
        etc_mm=4.0,
        effective_rainfall_method="calibrated_water_balance",
        effective_rainfall_provenance=ProvenanceType.CALCULATED,
    )
    assert wb_approved.effective_rainfall_method == "calibrated_water_balance"
    assert wb_approved.effective_rainfall_provenance == ProvenanceType.CALCULATED
    assert wb_approved.is_provisional_empirical is False

    # 5. Provisional method without opt-in -> raises ValueError
    with pytest.raises(ValueError, match="provisional daily method and is gated"):
        update_root_zone_water_balance(
            soil_capacities=caps,
            initial_depletion_mm=30.0,
            effective_rainfall_mm=15.0,
            etc_mm=4.0,
            effective_rainfall_method=EffectiveRainfallMethod.FAO_DEPENDABLE,
            effective_rainfall_provenance=ProvenanceType.CALCULATED,
            allow_provisional_method=False,
        )

    # 6. Provisional method with explicit opt-in -> succeeds and derives is_provisional_empirical=True
    wb_prov = update_root_zone_water_balance(
        soil_capacities=caps,
        initial_depletion_mm=30.0,
        effective_rainfall_mm=15.0,
        etc_mm=4.0,
        effective_rainfall_method=EffectiveRainfallMethod.FAO_DEPENDABLE,
        effective_rainfall_provenance=ProvenanceType.CALCULATED,
        allow_provisional_method=True,
    )
    assert wb_prov.is_provisional_empirical is True
    assert wb_prov.effective_rainfall_method == "fao_dependable_daily"
    assert wb_prov.effective_rainfall_provenance == ProvenanceType.CALCULATED

    # 7. Conflicting method and provisional Boolean -> raises ValueError
    with pytest.raises(ValueError, match="Conflicting provisional configuration"):
        update_root_zone_water_balance(
            soil_capacities=caps,
            initial_depletion_mm=30.0,
            effective_rainfall_mm=15.0,
            etc_mm=4.0,
            effective_rainfall_method=EffectiveRainfallMethod.FAO_DEPENDABLE,
            effective_rainfall_provenance=ProvenanceType.CALCULATED,
            is_provisional_empirical=False,
            allow_provisional_method=True,
        )

    # 8. Provenance propagation through IrrigationRequirementResult
    irrig_app = calculate_irrigation_requirement(wb_approved)
    assert irrig_app.effective_rainfall_method == "calibrated_water_balance"
    assert irrig_app.effective_rainfall_provenance == ProvenanceType.CALCULATED
    assert irrig_app.is_provisional_empirical is False

    irrig_prov = calculate_irrigation_requirement(wb_prov)
    assert irrig_prov.effective_rainfall_method == "fao_dependable_daily"
    assert irrig_prov.effective_rainfall_provenance == ProvenanceType.CALCULATED
    assert irrig_prov.is_provisional_empirical is True



