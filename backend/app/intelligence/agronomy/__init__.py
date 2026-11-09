"""Agronomic water-balance calculation engines for FarmShield AI.

Implements FAO-56 Penman-Monteith reference evapotranspiration, crop coefficient
determination, standard crop evapotranspiration (ETc), effective rainfall,
root-zone soil-water balance accounting, and net/gross irrigation requirements.
"""

from backend.app.intelligence.agronomy.et0 import (
    ET0CalculationResult,
    actual_vapour_pressure_from_dewpoint,
    actual_vapour_pressure_from_rh,
    atmospheric_pressure,
    calculate_fao56_penman_monteith_et0,
    mean_saturation_vapour_pressure,
    psychrometric_constant,
    saturation_vapour_pressure,
    slope_vapour_pressure_curve,
    solar_radiation_parameters,
    wind_speed_2m_conversion,
)
from backend.app.intelligence.agronomy.crop_coefficient import (
    CropAgronomicParameters,
    CropCoefficientResult,
    FAO56_CROP_DATABASE,
    adjust_depletion_fraction_p,
    calculate_climatic_kc_adjustment,
    get_crop_coefficient,
)
from backend.app.intelligence.agronomy.etc import (
    CropETResult,
    calculate_adjusted_crop_evapotranspiration,
    calculate_crop_evapotranspiration,
)
from backend.app.intelligence.agronomy.effective_rainfall import (
    EffectiveRainfallMethod,
    EffectiveRainfallResult,
    calculate_effective_rainfall,
    validate_consecutive_windows,
)
from backend.app.intelligence.agronomy.water_balance import (
    SoilWaterCapacities,
    WaterBalanceRainfallMode,
    WaterBalanceResult,
    calculate_soil_water_capacities,
    calculate_water_stress_coefficient,
    initial_depletion_from_moisture,
    update_root_zone_water_balance,
)
from backend.app.intelligence.agronomy.irrigation_requirement import (
    IrrigationManagementStrategy,
    IrrigationMethodEfficiency,
    IrrigationRequirementResult,
    calculate_irrigation_requirement,
)

__all__ = [
    # ET0
    "ET0CalculationResult",
    "calculate_fao56_penman_monteith_et0",
    "atmospheric_pressure",
    "psychrometric_constant",
    "saturation_vapour_pressure",
    "mean_saturation_vapour_pressure",
    "slope_vapour_pressure_curve",
    "actual_vapour_pressure_from_dewpoint",
    "actual_vapour_pressure_from_rh",
    "solar_radiation_parameters",
    "wind_speed_2m_conversion",
    # Crop Coefficient
    "CropAgronomicParameters",
    "CropCoefficientResult",
    "FAO56_CROP_DATABASE",
    "adjust_depletion_fraction_p",
    "calculate_climatic_kc_adjustment",
    "get_crop_coefficient",
    # ETc
    "CropETResult",
    "calculate_crop_evapotranspiration",
    "calculate_adjusted_crop_evapotranspiration",
    # Effective Rainfall
    "EffectiveRainfallMethod",
    "EffectiveRainfallResult",
    "calculate_effective_rainfall",
    "validate_consecutive_windows",
    # Water Balance
    "SoilWaterCapacities",
    "WaterBalanceRainfallMode",
    "WaterBalanceResult",
    "calculate_soil_water_capacities",
    "calculate_water_stress_coefficient",
    "initial_depletion_from_moisture",
    "update_root_zone_water_balance",
    # Irrigation Requirement
    "IrrigationManagementStrategy",
    "IrrigationMethodEfficiency",
    "IrrigationRequirementResult",
    "calculate_irrigation_requirement",
]

