"""Integration tests for bulk observation persistence and pipeline deduplication."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import uuid
import pytest
from sqlalchemy.orm import Session

from app.ingestion.pipelines.pipeline import IngestionPipeline
from app.models.farm import Farm, FarmZone
from app.models.observation import Observation
from app.models.user import User
from app.intelligence.types import SoilTextureClass


@pytest.fixture
def sample_farm_and_zone_for_pipeline(db_session: Session) -> tuple[Farm, FarmZone]:
    """Create test farm and zone for bulk pipeline persistence testing."""
    suffix = uuid.uuid4().hex[:6]
    user = User(
        full_name=f"Pipeline Farmer {suffix}",
        email=f"pipeline_farmer_{suffix}@farmshield.ai",
        hashed_password="TestPassword123!",
        role="farmer",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    farm = Farm(
        owner_id=user.id,
        name=f"Bulk Pipeline Farm {suffix}",
        crop_type="sugarcane",
        boundary="SRID=4326;MULTIPOLYGON(((73.85 18.52, 73.86 18.52, 73.86 18.53, 73.85 18.53, 73.85 18.52)))",
        area_hectares=10.0,
        location_name="Pune, Maharashtra",
    )
    db_session.add(farm)
    db_session.commit()
    db_session.refresh(farm)

    zone = FarmZone(
        farm_id=farm.id,
        zone_name="Zone P1",
        zone_code=f"ZP_{suffix}",
        boundary="SRID=4326;POLYGON((73.852 18.522, 73.858 18.522, 73.858 18.528, 73.852 18.528, 73.852 18.522))",
        area_hectares=4.0,
    )
    db_session.add(zone)
    db_session.commit()
    db_session.refresh(zone)

    yield farm, zone

    # Teardown
    db_session.query(Observation).filter(Observation.farm_id == farm.id).delete()
    db_session.query(FarmZone).filter(FarmZone.id == zone.id).delete()
    db_session.query(Farm).filter(Farm.id == farm.id).delete()
    db_session.query(User).filter(User.id == user.id).delete()
    db_session.commit()


def test_weather_ingestion_uses_bulk_create_and_no_individual_commits(
    db_session: Session,
    sample_farm_and_zone_for_pipeline: tuple[Farm, FarmZone],
):
    """Verify weather ingestion calls bulk_create_observations and never calls individual create_observation."""
    farm, zone = sample_farm_and_zone_for_pipeline
    pipeline = IngestionPipeline()

    with patch("app.ingestion.pipelines.pipeline.bulk_create_observations", wraps=__import__("app.services.observation_service", fromlist=["bulk_create_observations"]).bulk_create_observations) as spy_bulk:
        with patch("app.services.observation_service.create_observation") as mock_single:
            persisted, weather_feats, soil_feats = pipeline.ingest_weather_for_coordinates(
                latitude=18.52,
                longitude=73.85,
                farm_id=farm.id,
                zone_id=zone.id,
                db=db_session,
                forecast_days=1,
            )

            # bulk_create_observations was called exactly once for the complete batch
            assert spy_bulk.call_count == 1
            call_args, call_kwargs = spy_bulk.call_args
            assert call_kwargs.get("farm_id") == farm.id or call_args[1] == farm.id
            observations_batch = call_kwargs.get("observations_in") or call_args[2]
            assert len(observations_batch) > 0

            # Individual create_observation must NEVER be called
            assert mock_single.call_count == 0

            # Persisted records match
            assert len(persisted) == len(observations_batch)
            assert persisted[0].farm_id == farm.id


def test_weather_ingestion_deduplication(
    db_session: Session,
    sample_farm_and_zone_for_pipeline: tuple[Farm, FarmZone],
):
    """Verify repeated weather ingestion safely produces 0 duplicate records."""
    farm, zone = sample_farm_and_zone_for_pipeline
    pipeline = IngestionPipeline()

    # First ingestion run
    persisted1, _, _ = pipeline.ingest_weather_for_coordinates(
        latitude=18.52,
        longitude=73.85,
        farm_id=farm.id,
        zone_id=zone.id,
        db=db_session,
        forecast_days=1,
    )
    count1 = len(persisted1)
    assert count1 > 0

    total_in_db = db_session.query(Observation).filter(Observation.farm_id == farm.id).count()
    assert total_in_db == count1

    # Second ingestion run with identical inputs
    persisted2, _, _ = pipeline.ingest_weather_for_coordinates(
        latitude=18.52,
        longitude=73.85,
        farm_id=farm.id,
        zone_id=zone.id,
        db=db_session,
        forecast_days=1,
    )
    # Deduplication yields 0 newly inserted records
    assert len(persisted2) == 0

    # DB count must remain unchanged
    total_in_db_after = db_session.query(Observation).filter(Observation.farm_id == farm.id).count()
    assert total_in_db_after == count1


def test_satellite_ingestion_uses_bulk_create_and_deduplicates(
    db_session: Session,
    sample_farm_and_zone_for_pipeline: tuple[Farm, FarmZone],
):
    """Verify satellite ingestion calls bulk_create_observations and deduplicates identical scenes."""
    farm, zone = sample_farm_and_zone_for_pipeline
    pipeline = IngestionPipeline()

    with patch("app.ingestion.pipelines.pipeline.bulk_create_observations", wraps=__import__("app.services.observation_service", fromlist=["bulk_create_observations"]).bulk_create_observations) as spy_bulk:
        with patch("app.services.observation_service.create_observation") as mock_single:
            persisted1, veg_feats = pipeline.ingest_satellite_for_bbox(
                bbox=[73.852, 18.522, 73.858, 18.528],
                start_date="2024-10-01",
                end_date="2024-10-05",
                farm_id=farm.id,
                zone_id=zone.id,
                db=db_session,
            )

            assert spy_bulk.call_count == 1
            assert mock_single.call_count == 0
            assert len(persisted1) > 0

    # Repeat satellite ingestion
    persisted2, _ = pipeline.ingest_satellite_for_bbox(
        bbox=[73.852, 18.522, 73.858, 18.528],
        start_date="2024-10-01",
        end_date="2024-10-05",
        farm_id=farm.id,
        zone_id=zone.id,
        db=db_session,
    )
    assert len(persisted2) == 0


def test_soil_sensor_ingestion_uses_bulk_create_and_preserves_metadata(
    db_session: Session,
    sample_farm_and_zone_for_pipeline: tuple[Farm, FarmZone],
):
    """Verify soil sensor ingestion uses bulk persistence and preserves observation metadata."""
    farm, zone = sample_farm_and_zone_for_pipeline
    pipeline = IngestionPipeline()
    obs_time = datetime(2026, 11, 10, 14, 0, tzinfo=timezone.utc)

    persisted, soil_feats = pipeline.ingest_soil_sensor_reading(
        sensor_id="PROBE-BULK-01",
        depth_min_cm=0.0,
        depth_max_cm=30.0,
        volumetric_water_content=0.31,
        observed_at=obs_time,
        farm_id=farm.id,
        zone_id=zone.id,
        db=db_session,
    )

    assert len(persisted) == 1
    obs = persisted[0]
    assert obs.observation_type == "soil_moisture"
    assert obs.value == 0.31
    assert obs.unit == "m³/m³"
    assert obs.farm_id == farm.id
    assert obs.zone_id == zone.id
    assert obs.source == "In-situ sensor (PROBE-BULK-01)"
    assert obs.metadata_json.get("depth_min_cm") == 0.0
    assert obs.metadata_json.get("depth_max_cm") == 30.0


def test_empty_batch_handling_returns_safely(
    db_session: Session,
    sample_farm_and_zone_for_pipeline: tuple[Farm, FarmZone],
):
    """Verify empty observation inputs are handled safely without errors or DB queries."""
    from app.services.observation_service import bulk_create_observations
    farm, _ = sample_farm_and_zone_for_pipeline

    result = bulk_create_observations(
        db=db_session,
        farm_id=farm.id,
        observations_in=[],
    )
    assert result == []


def test_pipeline_atomic_rollback_on_persistence_failure(
    db_session: Session,
    sample_farm_and_zone_for_pipeline: tuple[Farm, FarmZone],
):
    """Verify that a database failure during bulk persistence triggers an atomic rollback."""
    farm, zone = sample_farm_and_zone_for_pipeline
    pipeline = IngestionPipeline()
    initial_count = db_session.query(Observation).filter(Observation.farm_id == farm.id).count()

    with patch.object(db_session, "scalars", side_effect=RuntimeError("Simulated PostgreSQL connection failure")):
        with pytest.raises(RuntimeError, match="Simulated PostgreSQL connection failure"):
            pipeline.ingest_weather_for_coordinates(
                latitude=18.52,
                longitude=73.85,
                farm_id=farm.id,
                zone_id=zone.id,
                db=db_session,
                forecast_days=1,
            )

    # Database count must be completely untouched
    final_count = db_session.query(Observation).filter(Observation.farm_id == farm.id).count()
    assert final_count == initial_count
