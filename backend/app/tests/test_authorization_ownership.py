"""Tests for Resource Ownership Protection and Multi-tenant Authorization.

Verifies:
- Farmer A cannot access, view, modify, or delete Farmer B's farms, zones,
  observations, recommendations, irrigation events, or user profile.
- Admin users have authorized access across all resources.
- Farmers cannot query another farmer's resources.
"""

from datetime import datetime, timezone
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import create_access_token, get_password_hash
from app.models.farm import Farm, FarmZone
from app.models.irrigation import IrrigationEvent
from app.models.observation import Observation
from app.models.recommendation import Recommendation
from app.models.user import FarmerProfile, User


@pytest.fixture
def two_farmers_and_admin(db_session: Session):
    """Fixture creating Farmer A, Farmer B, and Admin in the database with JWT tokens."""
    suffix = uuid.uuid4().hex[:6]

    # Farmer A
    farmer_a = User(
        full_name=f"Farmer A {suffix}",
        email=f"farmer_a_{suffix}@farmshield.ai",
        hashed_password=get_password_hash("FarmerPassA123!"),
        role="farmer",
        is_active=True,
    )
    # Farmer B
    farmer_b = User(
        full_name=f"Farmer B {suffix}",
        email=f"farmer_b_{suffix}@farmshield.ai",
        hashed_password=get_password_hash("FarmerPassB123!"),
        role="farmer",
        is_active=True,
    )
    # Admin
    admin = User(
        full_name=f"Admin {suffix}",
        email=f"admin_{suffix}@farmshield.ai",
        hashed_password=get_password_hash("AdminPass123!"),
        role="admin",
        is_active=True,
    )
    db_session.add_all([farmer_a, farmer_b, admin])
    db_session.commit()
    db_session.refresh(farmer_a)
    db_session.refresh(farmer_b)
    db_session.refresh(admin)

    # Farmer profiles
    prof_a = FarmerProfile(
        user_id=farmer_a.id,
        preferred_language="mr",
        village="Village A",
        district="District A",
        state="State A",
        country="India",
    )
    prof_b = FarmerProfile(
        user_id=farmer_b.id,
        preferred_language="hi",
        village="Village B",
        district="District B",
        state="State B",
        country="India",
    )
    db_session.add_all([prof_a, prof_b])
    db_session.commit()

    token_a = create_access_token(farmer_a.id, farmer_a.role, farmer_a.email)
    token_b = create_access_token(farmer_b.id, farmer_b.role, farmer_b.email)
    token_admin = create_access_token(admin.id, admin.role, admin.email)

    data = {
        "farmer_a": farmer_a,
        "farmer_b": farmer_b,
        "admin": admin,
        "token_a": token_a,
        "token_b": token_b,
        "token_admin": token_admin,
    }

    yield data

    # Teardown
    db_session.query(Observation).delete()
    db_session.query(Recommendation).delete()
    db_session.query(IrrigationEvent).delete()
    db_session.query(FarmZone).delete()
    db_session.query(Farm).delete()
    db_session.query(FarmerProfile).filter(FarmerProfile.user_id.in_([farmer_a.id, farmer_b.id])).delete()
    db_session.query(User).filter(User.id.in_([farmer_a.id, farmer_b.id, admin.id])).delete()
    db_session.commit()


def test_farmer_cannot_access_other_farmer_farm(
    client: TestClient, two_farmers_and_admin, sample_farm_multipolygon
):
    """Verify Farmer B cannot view, edit, or delete Farmer A's farm."""
    token_a = two_farmers_and_admin["token_a"]
    token_b = two_farmers_and_admin["token_b"]
    token_admin = two_farmers_and_admin["token_admin"]

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}
    headers_admin = {"Authorization": f"Bearer {token_admin}"}

    # Farmer A creates a farm
    res = client.post(
        "/api/v1/farms",
        json={
            "name": "Farmer A Farm",
            "crop_type": "sugarcane",
            "boundary": sample_farm_multipolygon,
        },
        headers=headers_a,
    )
    assert res.status_code == 201
    farm_a_id = res.json()["id"]

    # Farmer A can get their farm
    get_res = client.get(f"/api/v1/farms/{farm_a_id}", headers=headers_a)
    assert get_res.status_code == 200

    # Farmer B attempts to get Farmer A's farm -> 403 Forbidden!
    b_get_res = client.get(f"/api/v1/farms/{farm_a_id}", headers=headers_b)
    assert b_get_res.status_code == 403
    assert "permission" in b_get_res.json()["detail"].lower()

    # Farmer B attempts to update Farmer A's farm -> 403 Forbidden!
    b_put_res = client.put(
        f"/api/v1/farms/{farm_a_id}",
        json={"name": "Hijacked Farm Name"},
        headers=headers_b,
    )
    assert b_put_res.status_code == 403

    # Farmer B attempts to delete Farmer A's farm -> 403 Forbidden!
    b_del_res = client.delete(f"/api/v1/farms/{farm_a_id}", headers=headers_b)
    assert b_del_res.status_code == 403

    # Farmer B attempts to get Farmer A's boundary -> 403 Forbidden!
    b_boundary_res = client.get(f"/api/v1/farms/{farm_a_id}/boundary", headers=headers_b)
    assert b_boundary_res.status_code == 403

    # Admin CAN access Farmer A's farm
    admin_get_res = client.get(f"/api/v1/farms/{farm_a_id}", headers=headers_admin)
    assert admin_get_res.status_code == 200


def test_farmer_cannot_query_other_farmer_farms_list(
    client: TestClient, two_farmers_and_admin, sample_farm_multipolygon
):
    """Verify Farmer B cannot query Farmer A's farms via owner_id filter."""
    token_a = two_farmers_and_admin["token_a"]
    token_b = two_farmers_and_admin["token_b"]
    farmer_a_id = two_farmers_and_admin["farmer_a"].id
    farmer_b_id = two_farmers_and_admin["farmer_b"].id

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Farmer A creates a farm
    client.post(
        "/api/v1/farms",
        json={"name": "A Farm", "crop_type": "rice", "boundary": sample_farm_multipolygon},
        headers=headers_a,
    )

    # Farmer B lists farms without filters: should NOT see Farmer A's farm
    b_list = client.get("/api/v1/farms", headers=headers_b)
    assert b_list.status_code == 200
    assert b_list.json()["total"] == 0

    # Farmer B explicitly specifies owner_id = Farmer A's ID -> 403 Forbidden!
    b_hack = client.get(f"/api/v1/farms?owner_id={farmer_a_id}", headers=headers_b)
    assert b_hack.status_code == 403


def test_farmer_cannot_access_other_farmer_zone(
    client: TestClient, two_farmers_and_admin, sample_farm_multipolygon, sample_inside_polygon
):
    """Verify Farmer B cannot access, modify, or delete Farmer A's farm zone."""
    token_a = two_farmers_and_admin["token_a"]
    token_b = two_farmers_and_admin["token_b"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Farmer A creates farm and zone
    farm_res = client.post(
        "/api/v1/farms",
        json={"name": "Zone Test Farm", "crop_type": "cotton", "boundary": sample_farm_multipolygon},
        headers=headers_a,
    )
    farm_id = farm_res.json()["id"]

    zone_res = client.post(
        f"/api/v1/farms/{farm_id}/zones",
        json={"zone_name": "A Zone 1", "zone_code": "Z-A1", "boundary": sample_inside_polygon},
        headers=headers_a,
    )
    assert zone_res.status_code == 201
    zone_id = zone_res.json()["id"]

    # Farmer B cannot create a zone on Farmer A's farm -> 403
    b_create_zone = client.post(
        f"/api/v1/farms/{farm_id}/zones",
        json={"zone_name": "B Rogue Zone", "zone_code": "Z-B-ROGUE", "boundary": sample_inside_polygon},
        headers=headers_b,
    )
    assert b_create_zone.status_code == 403

    # Farmer B cannot retrieve Farmer A's zone -> 403
    b_get_zone = client.get(f"/api/v1/zones/{zone_id}", headers=headers_b)
    assert b_get_zone.status_code == 403

    # Farmer B cannot update Farmer A's zone -> 403
    b_put_zone = client.put(
        f"/api/v1/zones/{zone_id}",
        json={"zone_name": "Modified by B"},
        headers=headers_b,
    )
    assert b_put_zone.status_code == 403

    # Farmer B cannot delete Farmer A's zone -> 403
    b_del_zone = client.delete(f"/api/v1/zones/{zone_id}", headers=headers_b)
    assert b_del_zone.status_code == 403


def test_farmer_cannot_access_other_farmer_observations_recommendations_irrigation(
    client: TestClient, two_farmers_and_admin, sample_farm_multipolygon
):
    """Verify Farmer B cannot inject or read observations, recommendations, or irrigation on Farmer A's farm."""
    token_a = two_farmers_and_admin["token_a"]
    token_b = two_farmers_and_admin["token_b"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Farmer A creates farm
    farm_res = client.post(
        "/api/v1/farms",
        json={"name": "Obs Rec Farm", "crop_type": "wheat", "boundary": sample_farm_multipolygon},
        headers=headers_a,
    )
    farm_id = farm_res.json()["id"]

    # Farmer B attempts to add observation to Farmer A's farm -> 403
    b_obs = client.post(
        "/api/v1/observations",
        json={
            "farm_id": farm_id,
            "observation_type": "weather",
            "source": "manual",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "value": 30.0,
        },
        headers=headers_b,
    )
    assert b_obs.status_code == 403

    # Farmer B attempts to query observations on Farmer A's farm -> 403
    b_query_obs = client.get(f"/api/v1/observations?farm_id={farm_id}", headers=headers_b)
    assert b_query_obs.status_code == 403

    # Farmer B attempts to add recommendation to Farmer A's farm -> 403
    b_rec = client.post(
        "/api/v1/recommendations",
        json={
            "farm_id": farm_id,
            "recommendation_type": "irrigation",
            "title": "Unauthorized Advice",
            "description": "Bogus advice",
            "priority": "low",
        },
        headers=headers_b,
    )
    assert b_rec.status_code == 403

    # Farmer B attempts to record irrigation on Farmer A's farm -> 403
    b_irr = client.post(
        "/api/v1/irrigation",
        json={
            "farm_id": farm_id,
            "irrigation_date": datetime.now(timezone.utc).isoformat(),
            "water_quantity": 5000.0,
            "water_unit": "liters",
            "irrigation_method": "flood",
        },
        headers=headers_b,
    )
    assert b_irr.status_code == 403


def test_farmer_cannot_access_or_modify_other_farmer_user_profile(
    client: TestClient, two_farmers_and_admin
):
    """Verify Farmer B cannot view or modify Farmer A's user details or farmer profile."""
    token_b = two_farmers_and_admin["token_b"]
    farmer_a_id = two_farmers_and_admin["farmer_a"].id
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Farmer B attempts to GET Farmer A's user record -> 403
    res_user = client.get(f"/api/v1/users/{farmer_a_id}", headers=headers_b)
    assert res_user.status_code == 403

    # Farmer B attempts to PUT Farmer A's user record -> 403
    res_put_user = client.put(
        f"/api/v1/users/{farmer_a_id}",
        json={"full_name": "Tampered Name"},
        headers=headers_b,
    )
    assert res_put_user.status_code == 403

    # Farmer B attempts to GET Farmer A's farmer profile -> 403
    res_prof = client.get(f"/api/v1/farmers/{farmer_a_id}/profile", headers=headers_b)
    assert res_prof.status_code == 403

    # Farmer B attempts to PUT Farmer A's farmer profile -> 403
    res_put_prof = client.put(
        f"/api/v1/farmers/{farmer_a_id}/profile",
        json={
            "preferred_language": "mr",
            "village": "Tampered Village",
            "district": "Tampered District",
            "state": "Tampered State",
        },
        headers=headers_b,
    )
    assert res_put_prof.status_code == 403
