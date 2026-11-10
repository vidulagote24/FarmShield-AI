"""Unit and integration tests for Sentinel-2 satellite data ingestion."""

from datetime import datetime, timezone
import pytest

from app.ingestion.normalizers.satellite_normalizer import (
    SatelliteNormalizationError,
    normalize_sentinel2_vegetation,
)
from app.ingestion.providers.sentinel2_stac import Sentinel2STACProvider
from backend.app.intelligence.types import (
    DataQualityStatus,
    ProvenanceType,
    SpatialQualityStatus,
    ZoneRasterStats,
)


SAMPLE_STAC_FIXTURE = {
    "type": "Feature",
    "id": "S2A_43QDA_20241030_0_L2A",
    "properties": {
        "datetime": "2024-10-30T05:43:53.681000Z",
        "eo:cloud_cover": 4.5,
        "platform": "Sentinel-2A",
    },
    "assets": {
        "red": {"href": "https://example.com/B04.tif"},
        "nir": {"href": "https://example.com/B08.tif"},
        "scl": {"href": "https://example.com/SCL.tif"},
    },
}


def test_sentinel2_stac_health_check():
    """Verify STAC catalog health check."""
    provider = Sentinel2STACProvider(timeout_seconds=8.0)
    assert provider.health_check() is True


def test_sentinel2_search_scenes_live_or_fallback():
    """Verify searching Sentinel-2 scenes by bounding box."""
    provider = Sentinel2STACProvider(timeout_seconds=8.0)
    res = provider.search_scenes(
        bbox=[74.5, 18.1, 74.6, 18.2],
        start_date="2024-10-01",
        end_date="2024-11-01",
        max_cloud_cover_pct=20.0,
        limit=2,
        fallback_fixture={"features": [SAMPLE_STAC_FIXTURE]},
    )
    assert res.status_code == 200
    assert "features" in res.payload


def test_satellite_normalizer_with_indices():
    """Verify normalizer creates valid ZoneVegetationFeatures with NDVI/NDMI stats."""
    ndvi_stats = ZoneRasterStats(
        index_name="NDVI",
        mean=0.62,
        median=0.61,
        min=0.45,
        max=0.78,
        std=0.08,
        total_pixels_in_geometry=125,
        valid_pixel_count=120,
        valid_pixel_fraction=120 / 125,
        min_valid_fraction_threshold=0.5,
        quality_status=SpatialQualityStatus.GOOD,
    )
    ndmi_stats = ZoneRasterStats(
        index_name="NDMI",
        mean=0.28,
        median=0.28,
        min=0.15,
        max=0.38,
        std=0.05,
        total_pixels_in_geometry=125,
        valid_pixel_count=120,
        valid_pixel_fraction=120 / 125,
        min_valid_fraction_threshold=0.5,
        quality_status=SpatialQualityStatus.GOOD,
    )

    obs_list, veg_feats = normalize_sentinel2_vegetation(
        stac_item=SAMPLE_STAC_FIXTURE,
        ndvi_stats=ndvi_stats,
        ndmi_stats=ndmi_stats,
        total_pixels_in_geometry=125,
        valid_pixels_count=120,
    )

    # Scientific integrity checks
    assert veg_feats.scene_id == "S2A_43QDA_20241030_0_L2A"
    assert veg_feats.source_provider == "Copernicus Sentinel-2 L2A"
    assert veg_feats.provenance_type == ProvenanceType.SATELLITE_DERIVED
    assert veg_feats.cloud_fraction == 0.045
    assert veg_feats.quality_status == DataQualityStatus.GOOD
    assert veg_feats.ndvi_mean == 0.62
    assert veg_feats.ndmi_mean == 0.28

    # Verify backend observation records
    ndvi_obs = [o for o in obs_list if o.metadata_json.get("index_name") == "NDVI"]
    assert len(ndvi_obs) == 1
    assert ndvi_obs[0].value == 0.62
    assert ndvi_obs[0].observation_type == "vegetation_index"

    ndmi_obs = [o for o in obs_list if o.metadata_json.get("index_name") == "NDMI"]
    assert len(ndmi_obs) == 1
    assert ndmi_obs[0].value == 0.28

    sat_obs = [o for o in obs_list if o.observation_type == "satellite"]
    assert len(sat_obs) == 1
    assert sat_obs[0].value == 4.5


def test_satellite_normalizer_high_cloud_flagging():
    """Verify high cloud scenes are marked CLOUD_CONTAMINATED."""
    cloudy_fixture = {
        "type": "Feature",
        "id": "S2A_CLOUDY",
        "properties": {
            "datetime": "2024-10-30T05:43:53Z",
            "eo:cloud_cover": 75.0,
        },
    }
    _, veg_feats = normalize_sentinel2_vegetation(
        stac_item=cloudy_fixture,
        total_pixels_in_geometry=100,
        valid_pixels_count=40,
    )
    assert veg_feats.quality_status == DataQualityStatus.CLOUD_CONTAMINATED
    assert veg_feats.cloud_fraction == 0.75
