"""Tests for crop context features, phenological tracking, and validation."""

from datetime import date, datetime, timezone, timedelta
import pytest

from backend.app.intelligence.features.crop import (
    CropFeatures,
    create_crop_features,
)
from backend.app.intelligence.types import (
    DataQualityStatus,
    ProvenanceType,
)


def test_valid_crop_features_and_days_after_sowing():
    """Verify crop context creation and deterministic days-after-sowing calculation.

    Hand calculation:
    Sowing date = 2026-10-01
    Observation date = 2026-11-01
    Elapsed days = (2026-11-01 - 2026-10-01) = 31 days.
    """
    obs_time = datetime(2026, 11, 1, 9, 30, tzinfo=timezone.utc)
    sow_date = date(2026, 10, 1)

    crop = create_crop_features(
        crop_type="  Wheat ",
        observed_at=obs_time,
        variety="HD-2967",
        planting_date=sow_date,
        growth_stage="development",
        growth_stage_source="agronomist_inspected",
        rooting_depth_m=0.60,
        source_provider="Field Inspection Log",
        provenance_type=ProvenanceType.FARMER_ENTERED,
        as_of_time=obs_time + timedelta(days=2),
    )

    assert crop.crop_type == "wheat"  # Trimmed and canonicalized
    assert crop.variety == "HD-2967"
    assert crop.planting_date == sow_date
    assert crop.days_after_sowing == 31
    assert crop.growth_stage == "development"
    assert crop.growth_stage_source == "agronomist_inspected"
    assert crop.rooting_depth_m == 0.60
    assert crop.quality_status == DataQualityStatus.GOOD
    assert crop.is_stale == False

    # Caveats must be present
    assert len(crop.scientific_caveats) >= 3
    assert any("Crop identity MUST be supplied by farmer records" in c for c in crop.scientific_caveats)


def test_crop_planting_date_in_future_rejected():
    """Verify that a planting date in the future relative to observation is rejected."""
    obs_time = datetime(2026, 11, 1, 9, 30, tzinfo=timezone.utc)
    future_sow = date(2026, 11, 15)

    with pytest.raises(ValueError, match="cannot be in the future"):
        create_crop_features(
            crop_type="cotton",
            observed_at=obs_time,
            planting_date=future_sow,
        )


def test_crop_type_empty_rejected():
    """Verify blank or empty crop species string is rejected."""
    obs_time = datetime(2026, 11, 1, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="cannot be empty or blank"):
        create_crop_features(
            crop_type="   ",
            observed_at=obs_time,
        )


def test_crop_staleness_flagging():
    """Verify crop record older than freshness threshold is flagged stale."""
    t_obs = datetime(2026, 9, 1, tzinfo=timezone.utc)
    t_eval = datetime(2026, 11, 1, tzinfo=timezone.utc)  # 61 days later > 30d threshold

    crop = create_crop_features(
        crop_type="soybean",
        observed_at=t_obs,
        growth_stage="mid_season",
        planting_date=date(2026, 8, 1),
        as_of_time=t_eval,
        stale_days=30.0,
    )

    assert crop.is_stale == True
    assert crop.quality_status == DataQualityStatus.STALE

