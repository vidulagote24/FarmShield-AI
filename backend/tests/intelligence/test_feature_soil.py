"""Tests for soil feature engineering, hydraulic validation, and freshness policies."""

from datetime import datetime, timezone, timedelta
import pytest

from backend.app.intelligence.features.soil import (
    SoilFeatures,
    create_soil_features,
)
from backend.app.intelligence.types import (
    DataQualityStatus,
    ProvenanceType,
    SoilTextureClass,
)


def test_valid_soil_features_and_hand_calculated_awc():
    """Verify soil feature creation and automatic AWC calculation (AWC = FC - WP).

    Hand calculation:
    Field Capacity (FC) = 0.320 m³/m³
    Wilting Point (WP) = 0.140 m³/m³
    Expected AWC = 0.320 - 0.140 = 0.180 m³/m³
    """
    now = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)

    soil = create_soil_features(
        source_provider="FDR Soil Moisture Probe 01",
        provenance_type=ProvenanceType.SENSOR_MEASURED,
        observed_at=now,
        depth_min_cm=0.0,
        depth_max_cm=30.0,
        soil_moisture_m3_m3=0.240,
        soil_texture=SoilTextureClass.SANDY_CLAY_LOAM,
        field_capacity_m3_m3=0.320,
        wilting_point_m3_m3=0.140,
        soil_ph=7.2,
        electrical_conductivity_ds_m=0.85,
        as_of_time=now + timedelta(hours=2),
    )

    assert soil.source_provider == "FDR Soil Moisture Probe 01"
    assert soil.provenance_type == ProvenanceType.SENSOR_MEASURED
    assert soil.depth_min_cm == 0.0
    assert soil.depth_max_cm == 30.0
    assert soil.soil_moisture_m3_m3 == 0.240
    assert soil.soil_texture == SoilTextureClass.SANDY_CLAY_LOAM
    assert pytest.approx(soil.available_water_capacity_m3_m3, abs=1e-4) == 0.180
    assert soil.soil_ph == 7.2
    assert soil.electrical_conductivity_ds_m == 0.85
    assert soil.quality_status == DataQualityStatus.GOOD
    assert soil.is_stale == False

    # Caveats must be present
    assert len(soil.scientific_caveats) >= 3
    assert any("CANNOT be inferred from satellite" in c for c in soil.scientific_caveats)


def test_soil_hydraulic_consistency_validation():
    """Verify that physically impossible soil hydraulic parameters raise validation errors."""
    now = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)

    # 1. Wilting Point >= Field Capacity
    with pytest.raises(ValueError, match="Wilting Point .* >= Field Capacity"):
        SoilFeatures(
            source_provider="Lab",
            provenance_type=ProvenanceType.LABORATORY_ANALYZED,
            observed_at=now,
            field_capacity_m3_m3=0.200,
            wilting_point_m3_m3=0.250,
            quality_status=DataQualityStatus.GOOD,
        )

    # 2. Contradictory explicit AWC
    with pytest.raises(ValueError, match="AWC inconsistency"):
        SoilFeatures(
            source_provider="Lab",
            provenance_type=ProvenanceType.LABORATORY_ANALYZED,
            observed_at=now,
            field_capacity_m3_m3=0.300,
            wilting_point_m3_m3=0.100,
            available_water_capacity_m3_m3=0.500,  # Expected is 0.200
            quality_status=DataQualityStatus.GOOD,
        )

    # 3. Invalid depth layer: min >= max
    with pytest.raises(ValueError, match="depth_min .* >= depth_max"):
        SoilFeatures(
            source_provider="Sensor",
            provenance_type=ProvenanceType.SENSOR_MEASURED,
            observed_at=now,
            depth_min_cm=40.0,
            depth_max_cm=20.0,
            quality_status=DataQualityStatus.GOOD,
        )


def test_soil_freshness_policies_dynamic_vs_static():
    """Verify dynamic soil moisture readings expire much faster than static texture surveys."""
    t_obs = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)
    t_eval = datetime(2026, 11, 6, 10, 0, tzinfo=timezone.utc)  # 5 days later

    # Case A: High-frequency moisture reading (dynamic_stale_days = 3.0)
    # 5 days old > 3.0 days -> STALE
    dynamic_soil = create_soil_features(
        source_provider="Sensor",
        provenance_type=ProvenanceType.SENSOR_MEASURED,
        observed_at=t_obs,
        soil_moisture_m3_m3=0.200,
        as_of_time=t_eval,
        dynamic_stale_days=3.0,
    )
    assert dynamic_soil.is_stale == True
    assert dynamic_soil.quality_status == DataQualityStatus.STALE

    # Case B: Static soil survey (texture only, static_stale_days = 365.0)
    # 5 days old < 365 days -> FRESH (GOOD)
    static_soil = create_soil_features(
        source_provider="Laboratory Soil Survey",
        provenance_type=ProvenanceType.LABORATORY_ANALYZED,
        observed_at=t_obs,
        soil_texture=SoilTextureClass.CLAY_LOAM,
        field_capacity_m3_m3=0.35,
        wilting_point_m3_m3=0.18,
        as_of_time=t_eval,
        static_stale_days=365.0,
    )
    assert static_soil.is_stale == False
    assert static_soil.quality_status == DataQualityStatus.GOOD


def test_missing_soil_measurements_remain_none():
    """Verify missing soil properties remain strictly None without assumed defaults."""
    now = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)

    soil = create_soil_features(
        source_provider="Farmer Interview",
        provenance_type=ProvenanceType.FARMER_ENTERED,
        observed_at=now,
        soil_texture=SoilTextureClass.LOAM,
    )

    # Only texture was entered
    assert soil.soil_texture == SoilTextureClass.LOAM
    assert soil.soil_moisture_m3_m3 is None
    assert soil.field_capacity_m3_m3 is None
    assert soil.wilting_point_m3_m3 is None
    assert soil.available_water_capacity_m3_m3 is None
    assert soil.soil_ph is None
    assert soil.electrical_conductivity_ds_m is None
    assert soil.depth_min_cm is None
    assert soil.quality_status == DataQualityStatus.PARTIAL


def test_soil_analytical_methods_and_sensor_metadata():
    """Verify analytical method preservation and non-interchangeability caveats.

    Per Phase 2.1 requirements:
    - ph_method (e.g. '1:2.5_water') and ec_method (e.g. 'saturated_paste_extract_ECe') must be preserved.
    - Sensor type ('capacitance_fdr') must be preserved.
    - Scientific caveats must warn that different extraction ratios are not directly interchangeable.
    """
    now = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)

    soil = create_soil_features(
        source_provider="ICAR Krishi Vigyan Kendra Soil Lab",
        provenance_type=ProvenanceType.LABORATORY_ANALYZED,
        observed_at=now,
        depth_min_cm=0.0,
        depth_max_cm=15.0,
        soil_ph=7.4,
        ph_method="1:2.5_water",
        electrical_conductivity_ds_m=1.2,
        ec_method="saturated_paste_extract_ECe",
        soil_moisture_m3_m3=0.22,
        moisture_sensor_type="capacitance_fdr",
        field_capacity_m3_m3=0.30,
        wilting_point_m3_m3=0.15,
    )

    assert soil.ph_method == "1:2.5_water"
    assert soil.ec_method == "saturated_paste_extract_ECe"
    assert soil.moisture_sensor_type == "capacitance_fdr"
    assert soil.depth_min_cm == 0.0
    assert soil.depth_max_cm == 15.0

    # Verify analytical method warning is included
    caveat_text = " ".join(soil.scientific_caveats)
    assert "Analytical Method Warning" in caveat_text
    assert "1:5 extract vs saturated paste ECe" in caveat_text
    assert "NOT directly interchangeable" in caveat_text


