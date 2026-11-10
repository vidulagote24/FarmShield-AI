"""Evidence extractor, inventory builder, and provenance tracker for Phase 6 Explanations.

Extracts, structures, and audits supporting evidence from:
- ZoneDecisionResult (Phase 5)
- WaterBalanceResult (Phase 3)
- ZoneStressAssessment (Phase 4)
- MultimodalZoneFeatureSet (Phase 2)
- FarmZoneContext and WeatherForecastContext

Scientific & Operational Rules:
1. No Silent Imputation: Missing parameters remain explicitly flagged as missing (value None).
2. Explicit Provenance: Source provider, observation timestamp, and evidence type are preserved.
3. Provisional Flagging: Any estimate relying on provisional or unverified assumptions is visibly flagged.
4. Physical Units: All physical numbers retain explicit SI / agronomic units.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from backend.app.intelligence.agronomy.water_balance import WaterBalanceResult
from backend.app.intelligence.decision.types import (
    EfficiencyProvenance,
    FarmZoneContext,
    WeatherForecastContext,
    ZoneDecisionResult,
)
from backend.app.intelligence.explanations.types import EvidenceItem, EvidenceType
from backend.app.intelligence.features.feature_builder import MultimodalZoneFeatureSet
from backend.app.intelligence.stress.assessment import ZoneStressAssessment
from backend.app.intelligence.types import DataQualityStatus, ProvenanceType


def _map_provenance_type(prov: Optional[Any]) -> EvidenceType:
    """Map internal ProvenanceType or EfficiencyProvenance to EvidenceType."""
    if prov is None:
        return EvidenceType.UNKNOWN
    
    val = prov.value if hasattr(prov, "value") else str(prov).lower()

    if "sensor" in val or "measured" in val or val == "laboratory_analyzed":
        return EvidenceType.SENSOR_MEASURED
    if "satellite" in val:
        return EvidenceType.SATELLITE_DERIVED
    if "calculated" in val:
        return EvidenceType.CALCULATED
    if "forecast" in val or "nwp" in val:
        return EvidenceType.FORECAST
    if "operator" in val or "farmer" in val:
        return EvidenceType.OPERATOR_ENTERED
    if "assumed" in val or "default" in val:
        return EvidenceType.ASSUMED_DEFAULT
    if "simulated" in val:
        return EvidenceType.SIMULATED

    return EvidenceType.UNKNOWN


def build_evidence_inventory(
    decision: ZoneDecisionResult,
    water_balance: Optional[WaterBalanceResult] = None,
    stress_assessment: Optional[ZoneStressAssessment] = None,
    features: Optional[MultimodalZoneFeatureSet] = None,
    farm_zone: Optional[FarmZoneContext] = None,
    forecast: Optional[WeatherForecastContext] = None,
) -> Tuple[List[EvidenceItem], Dict[str, Any], List[str], List[str], List[str]]:
    """Synthesize complete evidence inventory, display measurements, and audit caveats.

    Args:
        decision: Evaluated ZoneDecisionResult from Phase 5.
        water_balance: Root-zone soil-water balance from Phase 3.
        stress_assessment: Multimodal stress assessment from Phase 4.
        features: Multimodal feature set from Phase 2.
        farm_zone: Zone static metadata and configuration.
        forecast: Meteorological weather forecast context.

    Returns:
        Tuple of:
            - supporting_evidence: List of structured EvidenceItem objects.
            - relevant_measurements: Key display metrics with explicit units.
            - missing_evidence: List of absent parameters.
            - stale_or_suspect_evidence: List of stale or contaminated observations.
            - provisional_flags: List of provisional method notices.
    """
    evidence_items: List[EvidenceItem] = []
    relevant_measurements: Dict[str, Any] = {}
    missing_evidence: List[str] = []
    stale_or_suspect_evidence: List[str] = []
    provisional_flags: List[str] = []

    # --------------------------------------------------------------------------
    # 1. Physical Water Balance Evidence (Phase 3)
    # --------------------------------------------------------------------------
    if water_balance is not None:
        wb_quality = getattr(water_balance, "quality_status", DataQualityStatus.GOOD)
        is_wb_stale = wb_quality == DataQualityStatus.STALE
        is_wb_suspect = wb_quality in (DataQualityStatus.SUSPECT, DataQualityStatus.CLOUD_CONTAMINATED)
        is_wb_prov = getattr(water_balance, "is_provisional_empirical", False)

        if is_wb_stale:
            stale_or_suspect_evidence.append("Water balance evidence is stale (> 3 days old).")
        if is_wb_suspect:
            stale_or_suspect_evidence.append("Water balance quality is suspect or anomalous.")
        if is_wb_prov:
            provisional_flags.append("Water balance uses provisional empirical effective rainfall calculation.")

        # Root-Zone Depletion Dr
        dr_val = getattr(water_balance, "final_depletion_mm", None)
        if dr_val is not None:
            evidence_items.append(
                EvidenceItem(
                    name="root_zone_depletion_dr",
                    value=round(float(dr_val), 2),
                    unit="mm",
                    source_provider="FAO-56 Soil Water Balance",
                    evidence_type=EvidenceType.CALCULATED,
                    quality_status=wb_quality,
                    is_provisional=is_wb_prov,
                    is_missing=False,
                    is_stale=is_wb_stale,
                    is_suspect=is_wb_suspect,
                    method_reference="FAO-56 Chapter 8 Daily Accounting",
                    notes="Current water deficit below Field Capacity in the crop root zone.",
                )
            )
            relevant_measurements["depletion_dr_mm"] = round(float(dr_val), 2)
        else:
            missing_evidence.append("Root-zone water depletion (Dr) is missing.")
            evidence_items.append(
                EvidenceItem(
                    name="root_zone_depletion_dr",
                    value=None,
                    unit="mm",
                    evidence_type=EvidenceType.CALCULATED,
                    quality_status=DataQualityStatus.MISSING,
                    is_missing=True,
                    notes="Depletion could not be calculated.",
                )
            )

        # Readily Available Water RAW
        raw_val = getattr(water_balance, "readily_available_water_mm", None)
        if raw_val is not None:
            evidence_items.append(
                EvidenceItem(
                    name="readily_available_water_raw",
                    value=round(float(raw_val), 2),
                    unit="mm",
                    source_provider="Soil Properties & Crop rooting",
                    evidence_type=EvidenceType.CALCULATED,
                    quality_status=wb_quality,
                    method_reference="FAO-56 RAW = p * TAW",
                    notes="Management threshold for no-stress transpiration.",
                )
            )
            relevant_measurements["readily_available_water_raw_mm"] = round(float(raw_val), 2)
        else:
            missing_evidence.append("Readily Available Water (RAW) is missing.")

        # Total Available Water TAW
        taw_val = getattr(water_balance, "total_available_water_mm", None)
        if taw_val is not None:
            evidence_items.append(
                EvidenceItem(
                    name="total_available_water_taw",
                    value=round(float(taw_val), 2),
                    unit="mm",
                    source_provider="Soil Capacities (FC - WP) * Zr",
                    evidence_type=EvidenceType.CALCULATED,
                    quality_status=wb_quality,
                    method_reference="FAO-56 TAW = 1000 * (theta_FC - theta_WP) * Zr",
                    notes="Total water-holding capacity between Field Capacity and Wilting Point.",
                )
            )
            relevant_measurements["total_available_water_taw_mm"] = round(float(taw_val), 2)
        else:
            missing_evidence.append("Total Available Water (TAW) is missing.")

        # Water Stress Coefficient Ks
        ks_val = getattr(water_balance, "water_stress_coefficient_ks", None)
        if ks_val is not None:
            evidence_items.append(
                EvidenceItem(
                    name="transpiration_reduction_ks",
                    value=round(float(ks_val), 3),
                    unit="fraction",
                    source_provider="FAO-56 Eq. 84",
                    evidence_type=EvidenceType.CALCULATED,
                    quality_status=wb_quality,
                    method_reference="Ks = (TAW - Dr) / (TAW - RAW) when Dr > RAW",
                    notes="Fraction of potential crop transpiration currently active (1.0 = no stress).",
                )
            )
            relevant_measurements["transpiration_reduction_ks"] = round(float(ks_val), 3)

        # Standard & Adjusted ETc
        etc_val = getattr(water_balance, "crop_evapotranspiration_mm", None)
        adj_etc_val = getattr(water_balance, "adjusted_crop_evapotranspiration_mm", None)
        if etc_val is not None:
            relevant_measurements["potential_etc_mm"] = round(float(etc_val), 2)
            evidence_items.append(
                EvidenceItem(
                    name="crop_evapotranspiration_etc",
                    value=round(float(etc_val), 2),
                    unit="mm/day",
                    source_provider="ET0 * Kc",
                    evidence_type=EvidenceType.CALCULATED,
                    quality_status=wb_quality,
                    method_reference="FAO-56 Single Crop Coefficient",
                )
            )
        if adj_etc_val is not None:
            relevant_measurements["adjusted_etc_mm"] = round(float(adj_etc_val), 2)
    else:
        missing_evidence.append("Water balance result object is completely absent.")

    # --------------------------------------------------------------------------
    # 2. Irrigation System & Operational Context (Phase 5 / FarmZoneContext)
    # --------------------------------------------------------------------------
    if farm_zone is not None:
        # Zone Area
        if farm_zone.zone_area_ha is not None:
            evidence_items.append(
                EvidenceItem(
                    name="zone_area",
                    value=round(float(farm_zone.zone_area_ha), 3),
                    unit="ha",
                    source_provider="Cadastral / Farm Registry",
                    evidence_type=EvidenceType.OPERATOR_ENTERED,
                    quality_status=DataQualityStatus.GOOD,
                    notes="Surface boundary area of management zone.",
                )
            )
            relevant_measurements["zone_area_ha"] = round(float(farm_zone.zone_area_ha), 3)
        else:
            missing_evidence.append("Zone boundary area (ha) is unrecorded.")

        # Application Efficiency
        eff = farm_zone.application_efficiency
        if eff is None and decision.application_efficiency is not None:
            eff = decision.application_efficiency

        eff_prov = (
            farm_zone.application_efficiency_provenance
            or decision.application_efficiency_provenance
            or EfficiencyProvenance.UNKNOWN
        )
        eff_type = _map_provenance_type(eff_prov)
        is_eff_prov = (
            decision.is_efficiency_provisional
            or eff_prov in (EfficiencyProvenance.ASSUMED_DEFAULT, EfficiencyProvenance.UNKNOWN)
            or not decision.is_efficiency_verified
            or not farm_zone.is_efficiency_measurement_verified
        )
        if eff is not None:
            evidence_items.append(
                EvidenceItem(
                    name="application_efficiency",
                    value=round(float(eff), 3),
                    unit="fraction",
                    source_provider=f"Efficiency ({eff_prov.value})",
                    evidence_type=eff_type,
                    quality_status=DataQualityStatus.GOOD if decision.is_efficiency_verified else DataQualityStatus.PARTIAL,
                    is_provisional=is_eff_prov,
                    method_reference="Field audit" if decision.is_efficiency_verified else "FAO-56 default",
                    notes=decision.efficiency_measurement_reference or farm_zone.efficiency_measurement_reference or "Hardware/Default specification",
                )
            )
            relevant_measurements["application_efficiency"] = round(float(eff), 3)
            relevant_measurements["efficiency_provenance"] = eff_prov.value
            if is_eff_prov:
                provisional_flags.append(
                    f"Application efficiency ({eff:.0%}) is based on {eff_prov.value} assumption, not in-situ field measurement."
                )
        else:
            missing_evidence.append("Application efficiency is unknown.")

        # Growth Stage
        if farm_zone.growth_stage:
            relevant_measurements["growth_stage"] = farm_zone.growth_stage
            evidence_items.append(
                EvidenceItem(
                    name="growth_stage",
                    value=farm_zone.growth_stage,
                    unit="phenological_stage",
                    source_provider="Farm Record / Crop Calendar",
                    evidence_type=EvidenceType.OPERATOR_ENTERED,
                    quality_status=DataQualityStatus.GOOD,
                )
            )

        # Irrigation System Type
        if farm_zone.irrigation_system_type:
            relevant_measurements["irrigation_system_type"] = farm_zone.irrigation_system_type
    else:
        missing_evidence.append("Farm zone metadata context is absent.")

    # --------------------------------------------------------------------------
    # 3. Weather Forecast Evidence (Phase 5 / WeatherForecastContext)
    # --------------------------------------------------------------------------
    if forecast is not None:
        p_rain = forecast.forecast_precipitation_mm
        p_eff = forecast.forecast_effective_rainfall_mm
        prob = forecast.forecast_probability
        source = forecast.forecast_source

        evidence_items.append(
            EvidenceItem(
                name="forecast_precipitation",
                value=round(float(p_rain), 2),
                unit="mm",
                source_provider=source,
                observation_timestamp=forecast.issue_time,
                evidence_type=EvidenceType.FORECAST,
                quality_status=DataQualityStatus.GOOD,
                notes=f"Accumulation over {forecast.forecast_period_hours:.0f}h forecast window (NWP model).",
            )
        )
        relevant_measurements["forecast_precipitation_mm"] = round(float(p_rain), 2)

        if prob is not None:
            relevant_measurements["forecast_probability_fraction"] = round(float(prob), 2)
            evidence_items.append(
                EvidenceItem(
                    name="forecast_precipitation_probability",
                    value=round(float(prob), 2),
                    unit="fraction",
                    source_provider=source,
                    evidence_type=EvidenceType.FORECAST,
                    quality_status=DataQualityStatus.GOOD,
                )
            )

        if p_eff is not None:
            relevant_measurements["forecast_effective_rainfall_mm"] = round(float(p_eff), 2)
            evidence_items.append(
                EvidenceItem(
                    name="forecast_effective_rainfall",
                    value=round(float(p_eff), 2),
                    unit="mm",
                    source_provider=forecast.effective_rainfall_provenance or source,
                    evidence_type=EvidenceType.CALCULATED,
                    quality_status=DataQualityStatus.GOOD,
                    method_reference=forecast.effective_rainfall_method or "Infiltration/Runoff model",
                    notes="Expected water entering root-zone storage after infiltration and runoff.",
                )
            )
        else:
            if decision.forecast_dependency and decision.forecast_dependency.get("is_provisional_deferral"):
                provisional_flags.append(
                    "Forecast deferral is based on raw atmospheric precipitation; in-situ infiltration/runoff evidence is unavailable."
                )

        # Forecast ETc
        if forecast.forecast_etc_mm is not None:
            relevant_measurements["forecast_etc_mm"] = round(float(forecast.forecast_etc_mm), 2)
            evidence_items.append(
                EvidenceItem(
                    name="forecast_etc",
                    value=round(float(forecast.forecast_etc_mm), 2),
                    unit="mm",
                    source_provider=source,
                    evidence_type=EvidenceType.FORECAST,
                    quality_status=DataQualityStatus.GOOD,
                    notes=f"Projected atmospheric demand over {forecast.forecast_etc_period_hours or forecast.forecast_period_hours:.0f}h.",
                )
            )
        else:
            if decision.forecast_dependency:
                missing_evidence.append("Forecast ETc is missing; uniform transpirational rate could not be evaluated.")

        # Rainfall Start / Timing
        if forecast.expected_rainfall_start is not None:
            relevant_measurements["expected_rainfall_start_utc"] = forecast.expected_rainfall_start.isoformat()
    else:
        # Forecast was not provided to decision
        pass

    # --------------------------------------------------------------------------
    # 4. Multimodal Features & Stress Assessment (Phase 2 & Phase 4)
    # --------------------------------------------------------------------------
    if features is not None:
        # Satellite Vegetation Features
        if features.vegetation is not None:
            veg = features.vegetation
            veg_quality = veg.quality_status
            if veg.ndvi_mean is not None:
                evidence_items.append(
                    EvidenceItem(
                        name="sentinel2_ndvi_mean",
                        value=round(float(veg.ndvi_mean), 3),
                        unit="index",
                        source_provider=veg.source_provider or "Copernicus Sentinel-2",
                        observation_timestamp=getattr(veg, "observed_at", getattr(veg, "observation_timestamp", None)),
                        evidence_type=EvidenceType.SATELLITE_DERIVED,
                        quality_status=veg_quality,
                        notes="Zone-averaged Normalized Difference Vegetation Index.",
                    )
                )
                relevant_measurements["satellite_ndvi"] = round(float(veg.ndvi_mean), 3)

            if veg.ndmi_mean is not None:
                relevant_measurements["satellite_ndmi"] = round(float(veg.ndmi_mean), 3)

            if veg_quality in (DataQualityStatus.CLOUD_CONTAMINATED, DataQualityStatus.SUSPECT):
                stale_or_suspect_evidence.append("Satellite optical pass has cloud, shadow, or cirrus contamination.")

        # Weather Features
        if features.weather is not None:
            w = features.weather
            if w.temperature_max_c is not None:
                relevant_measurements["weather_max_temperature_c"] = round(float(w.temperature_max_c), 1)
            vpd = getattr(w, "vapor_pressure_deficit_kpa", None)
            if vpd is not None:
                relevant_measurements["vapor_pressure_deficit_kpa"] = round(float(vpd), 2)

        # Soil Features
        if features.soil is not None:
            s = features.soil
            ec = getattr(s, "electrical_conductivity_ds_m", getattr(s, "electrical_conductivity_e_ce", None))
            if ec is not None:
                relevant_measurements["soil_salinity_ece_ds_m"] = round(float(ec), 2)
            ph = getattr(s, "soil_ph", getattr(s, "ph", None))
            if ph is not None:
                relevant_measurements["soil_ph"] = round(float(ph), 2)

    # --------------------------------------------------------------------------
    # 5. Decision Output Quantities (Phase 5)
    # --------------------------------------------------------------------------
    if decision.net_irrigation_depth_mm is not None:
        relevant_measurements["net_irrigation_depth_mm"] = round(float(decision.net_irrigation_depth_mm), 2)
    if decision.gross_irrigation_depth_mm is not None:
        relevant_measurements["gross_irrigation_depth_mm"] = round(float(decision.gross_irrigation_depth_mm), 2)
    if decision.irrigation_volume_m3 is not None:
        relevant_measurements["irrigation_volume_m3"] = round(float(decision.irrigation_volume_m3), 2)

    if decision.split_application_required:
        relevant_measurements["split_event_count"] = decision.split_event_count
        relevant_measurements["split_event_depths_mm"] = decision.split_event_depths_mm

    return evidence_items, relevant_measurements, missing_evidence, stale_or_suspect_evidence, provisional_flags
