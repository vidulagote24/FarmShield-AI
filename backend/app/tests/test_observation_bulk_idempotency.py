"""Integration tests for atomic bulk observation persistence, deduplication, and concurrency."""

import concurrent.futures
from datetime import datetime, timedelta, timezone
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.farm import Farm, FarmZone
from app.models.observation import Observation
from app.models.user import User
from app.schemas.observation import ObservationCreate
from app.services.observation_service import (
    ZoneMismatchError,
    bulk_create_observations,
)


@pytest.fixture
def bulk_test_farm_and_zone(db_session: Session) -> tuple[Farm, FarmZone]:
    """Create a dedicated farm and zone for bulk ingestion tests."""
    user = User(
        full_name="Bulk Test Farmer",
        email=f"bulk_farmer_{uuid.uuid4().hex[:8]}@farmshield.ai",
        hashed_password="SecurePassword123!",
        role="farmer",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    farm = Farm(
        owner_id=user.id,
        name="Bulk Ingest Farm",
        crop_type="sugarcane",
        boundary="SRID=4326;MULTIPOLYGON(((74.58 18.15, 74.59 18.15, 74.59 18.16, 74.58 18.16, 74.58 18.15)))",
        area_hectares=15.0,
        location_name="Baramati, Maharashtra",
    )
    db_session.add(farm)
    db_session.commit()
    db_session.refresh(farm)

    zone = FarmZone(
        farm_id=farm.id,
        zone_name="Zone Bulk A",
        zone_code=f"ZB_{uuid.uuid4().hex[:4]}",
        boundary="SRID=4326;POLYGON((74.581 18.151, 74.589 18.151, 74.589 18.159, 74.581 18.159, 74.581 18.151))",
        area_hectares=5.0,
    )
    db_session.add(zone)
    db_session.commit()
    db_session.refresh(zone)

    return farm, zone


def _make_sample_observations(
    farm_id: uuid.UUID,
    zone_id: uuid.UUID,
    base_time: datetime,
) -> list[ObservationCreate]:
    """Helper to generate a realistic batch of observation inputs."""
    return [
        ObservationCreate(
            farm_id=farm_id,
            zone_id=None,  # Farm-level weather
            observation_type="weather",
            source="Open-Meteo Forecast API",
            observed_at=base_time,
            value=24.5,
            unit="°C",
            metadata={"temp_max": 31.0, "temp_min": 18.0},
        ),
        ObservationCreate(
            farm_id=farm_id,
            zone_id=None,
            observation_type="rainfall",
            source="Open-Meteo Forecast API",
            observed_at=base_time + timedelta(hours=1),
            value=12.4,
            unit="mm",
            metadata={"period": "1h"},
        ),
        ObservationCreate(
            farm_id=farm_id,
            zone_id=zone_id,  # Zone-level soil reading
            observation_type="soil_moisture",
            source="In-situ sensor (TDR-01)",
            observed_at=base_time + timedelta(hours=2),
            value=0.28,
            unit="m³/m³",
            metadata={"depth_min_cm": 0.0, "depth_max_cm": 30.0},
        ),
        ObservationCreate(
            farm_id=farm_id,
            zone_id=zone_id,
            observation_type="vegetation_index",
            source="Copernicus Sentinel-2 L2A",
            observed_at=base_time + timedelta(hours=3),
            value=0.65,
            unit="index",
            metadata={"index_name": "NDVI", "cloud_cover": 2.1},
        ),
    ]


def test_bulk_ingest_first_run_creates_observations(
    db_session: Session,
    bulk_test_farm_and_zone: tuple[Farm, FarmZone],
):
    """Test 1: First ingestion atomically creates the expected observations in PostgreSQL."""
    farm, zone = bulk_test_farm_and_zone
    base_time = datetime(2026, 11, 10, 8, 0, tzinfo=timezone.utc)
    batch = _make_sample_observations(farm.id, zone.id, base_time)

    persisted = bulk_create_observations(db_session, farm.id, batch)

    assert len(persisted) == 4
    for record in persisted:
        assert isinstance(record, Observation)
        assert record.id is not None
        assert record.farm_id == farm.id

    # Verify directly from database
    db_records = (
        db_session.query(Observation)
        .filter(Observation.farm_id == farm.id)
        .order_by(Observation.observed_at.asc())
        .all()
    )
    assert len(db_records) == 4
    assert db_records[0].observation_type == "weather"
    assert db_records[0].zone_id is None
    assert db_records[0].value == 24.5
    assert db_records[2].observation_type == "soil_moisture"
    assert db_records[2].zone_id == zone.id
    assert db_records[2].value == 0.28


def test_bulk_ingest_repeated_batch_creates_no_duplicates(
    db_session: Session,
    bulk_test_farm_and_zone: tuple[Farm, FarmZone],
):
    """Test 2: Repeating the exact same batch produces 0 duplicate records."""
    farm, zone = bulk_test_farm_and_zone
    base_time = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
    batch = _make_sample_observations(farm.id, zone.id, base_time)

    # First run
    first_persisted = bulk_create_observations(db_session, farm.id, batch)
    assert len(first_persisted) == 4

    # Second run (exact duplicate inputs)
    second_persisted = bulk_create_observations(db_session, farm.id, batch)
    assert len(second_persisted) == 0, "Repeated batch must not re-insert duplicate observations."

    # Verify database count remains unchanged
    total_in_db = (
        db_session.query(Observation)
        .filter(Observation.farm_id == farm.id)
        .count()
    )
    assert total_in_db == 4

    # With return_all=True, it returns all 4 existing observations
    all_persisted = bulk_create_observations(
        db_session, farm.id, batch, return_all=True
    )
    assert len(all_persisted) == 4


def test_bulk_ingest_partial_duplicate_batch_handles_new_records(
    db_session: Session,
    bulk_test_farm_and_zone: tuple[Farm, FarmZone],
):
    """Test 3: A batch containing a duplicate and a new observation inserts only the new observation."""
    farm, zone = bulk_test_farm_and_zone
    base_time = datetime(2026, 11, 10, 14, 0, tzinfo=timezone.utc)
    initial_batch = _make_sample_observations(farm.id, zone.id, base_time)[:2]

    # Insert initial 2 records
    persisted_initial = bulk_create_observations(db_session, farm.id, initial_batch)
    assert len(persisted_initial) == 2

    # New batch: 1 duplicate from initial_batch, and 1 brand new observation
    new_obs = ObservationCreate(
        farm_id=farm.id,
        zone_id=zone.id,
        observation_type="temperature",
        source="Field Station",
        observed_at=base_time + timedelta(hours=5),
        value=28.2,
        unit="°C",
    )
    mixed_batch = [initial_batch[0], new_obs]

    # Ingest mixed batch
    mixed_persisted = bulk_create_observations(db_session, farm.id, mixed_batch)
    assert len(mixed_persisted) == 1, "Only the 1 novel observation should be newly persisted."
    assert mixed_persisted[0].observation_type == "temperature"
    assert mixed_persisted[0].value == 28.2

    # Total in DB should now be 3 (2 initial + 1 new)
    total_in_db = (
        db_session.query(Observation)
        .filter(Observation.farm_id == farm.id)
        .count()
    )
    assert total_in_db == 3


def test_bulk_ingest_atomic_rollback_on_failure(
    db_session: Session,
    bulk_test_farm_and_zone: tuple[Farm, FarmZone],
):
    """Test 4: A simulated mid-batch validation or DB failure leaves no partial records."""
    farm, zone = bulk_test_farm_and_zone
    base_time = datetime(2026, 11, 10, 18, 0, tzinfo=timezone.utc)

    # Initial count before attempting failing batch
    initial_count = (
        db_session.query(Observation)
        .filter(Observation.farm_id == farm.id)
        .count()
    )

    # Foreign zone UUID not belonging to this farm
    foreign_zone_id = uuid.uuid4()

    failing_batch = [
        ObservationCreate(
            farm_id=farm.id,
            zone_id=zone.id,
            observation_type="weather",
            source="Open-Meteo",
            observed_at=base_time,
            value=21.0,
            unit="°C",
        ),
        ObservationCreate(
            farm_id=farm.id,
            zone_id=foreign_zone_id,  # Invalid zone triggers ZoneMismatchError
            observation_type="soil_moisture",
            source="Sensor",
            observed_at=base_time + timedelta(hours=1),
            value=0.30,
            unit="m³/m³",
        ),
    ]

    with pytest.raises(ZoneMismatchError):
        bulk_create_observations(db_session, farm.id, failing_batch)

    # Verify strict atomic rollback: 0 partial records added
    final_count = (
        db_session.query(Observation)
        .filter(Observation.farm_id == farm.id)
        .count()
    )
    assert final_count == initial_count


def test_bulk_ingest_concurrency_race_condition(
    bulk_test_farm_and_zone: tuple[Farm, FarmZone],
):
    """Test 5: Concurrent ingestion requests across multiple threads produce no duplicate rows."""
    farm, zone = bulk_test_farm_and_zone
    base_time = datetime(2026, 11, 10, 20, 0, tzinfo=timezone.utc)
    batch = _make_sample_observations(farm.id, zone.id, base_time)

    def _worker():
        # Each worker thread uses its own dedicated SessionLocal
        worker_session = SessionLocal()
        try:
            return bulk_create_observations(worker_session, farm.id, batch)
        finally:
            worker_session.close()

    # Launch 5 concurrent threads executing the exact same batch simultaneously
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_worker) for _ in range(5)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # Across all 5 parallel workers, total newly inserted records across all threads must equal 4
    total_newly_inserted = sum(len(res) for res in results)
    assert total_newly_inserted == 4, (
        f"Expected exactly 4 records to be inserted across concurrent runs, got {total_newly_inserted}"
    )

    # Verify PostgreSQL table contains exactly 4 records (no duplicates from race conditions)
    verify_session = SessionLocal()
    try:
        total_in_db = (
            verify_session.query(Observation)
            .filter(Observation.farm_id == farm.id)
            .count()
        )
        assert total_in_db == 4
    finally:
        verify_session.close()


def test_bulk_ingested_observations_retrievable_via_api(
    client: TestClient,
    db_session: Session,
    bulk_test_farm_and_zone: tuple[Farm, FarmZone],
):
    """Test 6: Existing observation retrieval API endpoint retrieves bulk ingested observations."""
    farm, zone = bulk_test_farm_and_zone
    user = db_session.query(User).filter(User.id == farm.owner_id).first()

    # Authenticate farmer via JWT
    from app.core.security import create_access_token
    token = create_access_token(subject=user.id, role=user.role, email=user.email)
    headers = {"Authorization": f"Bearer {token}"}

    base_time = datetime(2026, 11, 11, 6, 0, tzinfo=timezone.utc)
    batch = _make_sample_observations(farm.id, zone.id, base_time)

    persisted = bulk_create_observations(db_session, farm.id, batch)
    assert len(persisted) == 4

    # Query observations via existing GET /api/v1/farms/{farm_id}/observations
    response = client.get(
        f"/api/v1/farms/{farm.id}/observations",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "items" in data
    assert data["total"] >= 4

    # Test filtering by observation_type="weather"
    weather_resp = client.get(
        f"/api/v1/farms/{farm.id}/observations?observation_type=weather",
        headers=headers,
    )
    assert weather_resp.status_code == 200
    weather_data = weather_resp.json()
    assert weather_data["total"] >= 1
    assert all(item["observation_type"] == "weather" for item in weather_data["items"])
