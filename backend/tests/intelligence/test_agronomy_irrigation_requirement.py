"""Tests for irrigation requirement calculations, application efficiencies, and volumetric scaling."""

import pytest

from backend.app.intelligence.agronomy.irrigation_requirement import (
    IrrigationManagementStrategy,
    IrrigationMethodEfficiency,
    IrrigationRequirementResult,
    calculate_irrigation_requirement,
)
from backend.app.intelligence.agronomy.water_balance import (
    SoilWaterCapacities,
    WaterBalanceResult,
    calculate_soil_water_capacities,
)
from backend.app.intelligence.types import DataQualityStatus


@pytest.fixture
def sample_water_balance():
    caps = calculate_soil_water_capacities(
        field_capacity_m3_m3=0.320,
        wilting_point_m3_m3=0.140,
        rooting_depth_m=1.0,
        depletion_fraction_p=0.55,
    )
    # TAW = 180.0 mm, RAW = 99.0 mm
    return WaterBalanceResult(
        soil_capacities=caps,
        initial_depletion_mm=50.0,
        effective_rainfall_mm=10.0,
        applied_irrigation_mm=0.0,
        crop_evapotranspiration_mm=5.0,
        deep_percolation_mm=0.0,
        final_depletion_mm=45.0,  # 50 - 10 + 5 = 45 mm
        root_zone_moisture_m3_m3=0.275,
        is_in_stress_zone=False,
        quality_status=DataQualityStatus.GOOD,
    )


def test_hand_calculated_net_and_gross_irrigation_depths(sample_water_balance):
    """Verify net and gross irrigation depth calculation with hand-calculated references.

    Scenario:
    Dr = 45.0 mm
    Strategy: Refill to Field Capacity -> Net Depth = 45.0 mm
    Drip Efficiency eta = 0.90
    Expected Gross Depth = 45.0 / 0.90 = 50.0 mm
    """
    res = calculate_irrigation_requirement(
        water_balance=sample_water_balance,
        application_efficiency=0.90,
        strategy=IrrigationManagementStrategy.REFILL_TO_FIELD_CAPACITY,
    )

    assert pytest.approx(res.net_irrigation_depth_mm, abs=1e-2) == 45.00
    assert pytest.approx(res.gross_irrigation_depth_mm, abs=1e-2) == 50.00
    assert res.application_efficiency == 0.90
    assert res.gross_irrigation_depth_mm >= res.net_irrigation_depth_mm
    assert res.is_irrigation_needed == True


def test_volumetric_conversion_with_known_area(sample_water_balance):
    """Verify conversion from depth (mm) to volume (m³) given field area in hectares.

    Formulas:
    Area = 2.5 ha = 25,000 m²
    Net depth = 45.0 mm -> Net volume = 45.0 * 25,000 / 1000 = 1,125.0 m³
    Gross depth = 50.0 mm -> Gross volume = 50.0 * 25,000 / 1000 = 1,250.0 m³
    """
    res = calculate_irrigation_requirement(
        water_balance=sample_water_balance,
        application_efficiency=0.90,
        area_ha=2.5,
    )

    assert res.area_ha == 2.5
    assert pytest.approx(res.net_irrigation_volume_m3, abs=0.1) == 1125.0
    assert pytest.approx(res.gross_irrigation_volume_m3, abs=0.1) == 1250.0
    assert res.gross_irrigation_volume_m3 >= res.net_irrigation_volume_m3


def test_strict_volume_withholding_when_area_is_unknown(sample_water_balance):
    """Verify scientific rule: volume (m³) is strictly withheld (None) when area is unknown."""
    res = calculate_irrigation_requirement(
        water_balance=sample_water_balance,
        application_efficiency=0.85,
        area_ha=None,  # Unknown area
    )

    assert res.net_irrigation_depth_mm > 0.0
    assert res.gross_irrigation_depth_mm > 0.0
    assert res.area_ha is None
    assert res.net_irrigation_volume_m3 is None
    assert res.gross_irrigation_volume_m3 is None
    assert any("volumetric requirements withheld" in n for n in res.audit_notes)


def test_irrigation_strategy_avoid_stress_threshold(sample_water_balance):
    """Verify 'IRRIGATE_WHEN_STRESSED' strategy only triggers when Dr > RAW."""
    # RAW is 99.0 mm
    # Case A: Dr = 45.0 mm <= 99.0 mm -> No irrigation needed today
    res_unstressed = calculate_irrigation_requirement(
        water_balance=sample_water_balance,
        application_efficiency=0.85,
        strategy=IrrigationManagementStrategy.IRRIGATE_WHEN_STRESSED,
    )
    assert res_unstressed.is_irrigation_needed == False
    assert res_unstressed.net_irrigation_depth_mm == 0.0
    assert res_unstressed.gross_irrigation_depth_mm == 0.0

    # Case B: Dr = 105.0 mm > 99.0 mm -> Stress triggered!
    stressed_wb = sample_water_balance.model_copy(update={"final_depletion_mm": 105.0, "is_in_stress_zone": True})
    res_stressed = calculate_irrigation_requirement(
        water_balance=stressed_wb,
        application_efficiency=0.85,
        strategy=IrrigationManagementStrategy.IRRIGATE_WHEN_STRESSED,
    )
    assert res_stressed.is_irrigation_needed == True
    assert res_stressed.net_irrigation_depth_mm == 105.0
    assert pytest.approx(res_stressed.gross_irrigation_depth_mm, abs=1e-2) == 105.0 / 0.85


def test_irrigation_method_lookup_and_efficiency_validation(sample_water_balance):
    """Verify irrigation method lookup and rejection of invalid efficiencies."""
    # Lookup 'drip' -> 0.90
    res_drip = calculate_irrigation_requirement(
        water_balance=sample_water_balance,
        irrigation_method="drip",
    )
    assert res_drip.application_efficiency == 0.90
    assert "drip" in res_drip.efficiency_source

    # Lookup 'furrow' -> 0.60
    res_furrow = calculate_irrigation_requirement(
        water_balance=sample_water_balance,
        irrigation_method="furrow_surface",
    )
    assert res_furrow.application_efficiency == 0.60

    # Rejection: efficiency <= 0
    with pytest.raises(ValueError, match="Application efficiency must be strictly in"):
        calculate_irrigation_requirement(
            water_balance=sample_water_balance,
            application_efficiency=0.0,
        )

    # Rejection: efficiency > 1.0
    with pytest.raises(ValueError, match="Application efficiency must be strictly in"):
        calculate_irrigation_requirement(
            water_balance=sample_water_balance,
            application_efficiency=1.10,
        )


def test_net_refill_to_field_capacity_semantics_separation(sample_water_balance):
    """Verify net_refill_to_field_capacity_mm is separated from strategy trigger."""
    # When Dr = 45.0 mm and RAW = 99.0 mm
    # Strategy IRRIGATE_WHEN_STRESSED -> not triggered (net_irrigation_depth_mm = 0)
    # BUT physical net_refill_to_field_capacity_mm remains 45.0 mm!
    res = calculate_irrigation_requirement(
        water_balance=sample_water_balance,
        application_efficiency=0.90,
        strategy=IrrigationManagementStrategy.IRRIGATE_WHEN_STRESSED,
    )
    assert res.net_refill_to_field_capacity_mm == 45.00
    assert res.net_irrigation_depth_mm == 0.00
    assert res.is_irrigation_needed is False

    # When strategy is REFILL_TO_FIELD_CAPACITY
    # net_refill_to_field_capacity_mm and net_irrigation_depth_mm both equal 45.0 mm
    res_refill = calculate_irrigation_requirement(
        water_balance=sample_water_balance,
        application_efficiency=0.90,
        strategy=IrrigationManagementStrategy.REFILL_TO_FIELD_CAPACITY,
    )
    assert res_refill.net_refill_to_field_capacity_mm == 45.00
    assert res_refill.net_irrigation_depth_mm == 45.00
    assert res_refill.is_irrigation_needed is True


def test_management_allowed_depletion_fraction_trigger(sample_water_balance):
    """Verify MAD fraction trigger threshold separation from RAW."""
    # TAW = 180.0 mm. Set MAD fraction = 0.20 -> MAD threshold = 36.0 mm
    # Current Dr = 45.0 mm. Since 45.0 > 36.0, irrigation triggers even though Dr < RAW (99.0 mm)!
    res_mad = calculate_irrigation_requirement(
        water_balance=sample_water_balance,
        application_efficiency=0.90,
        strategy=IrrigationManagementStrategy.IRRIGATE_WHEN_STRESSED,
        management_allowed_depletion_fraction=0.20,
    )
    assert res_mad.management_allowed_depletion_mm == 36.0
    assert res_mad.is_irrigation_needed is True
    assert res_mad.net_irrigation_depth_mm == 45.0



def test_insufficient_water_balance_propagation():
    """Verify that an INSUFFICIENT water balance propagates cleanly into irrigation requirements."""
    insufficient_wb = WaterBalanceResult(
        quality_status=DataQualityStatus.INSUFFICIENT,
        final_depletion_mm=None,
    )

    res = calculate_irrigation_requirement(insufficient_wb)
    assert res.quality_status == DataQualityStatus.INSUFFICIENT
    assert res.is_irrigation_needed == False
    assert any("Input water balance is incomplete or insufficient" in n for n in res.audit_notes)

