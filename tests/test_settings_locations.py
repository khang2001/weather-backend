"""
DB1 — saved locations are normalized into the `user_saved_locations` table
(indexed on (latitude, longitude)) instead of a JSON blob on the user row.

These tests pin the new storage AND the unchanged API contract: the location
endpoints stay index-based and the settings response still exposes a
`saved_locations` list, so the frontend needs no changes.
"""
import pytest


def _login(client, db_session, email="bob@example.com", username="bob", password="pw12345"):
    """Register a user and return (user_row, jwt). TestClient won't resend a
    Secure cookie over http, so we mint the token directly (see test_api.py)."""
    from app.database.models import User
    from app.security import create_access_token

    client.post("/auth/register", json={
        "username": username, "email": email, "password": password, "comfort_temperature": 70.0,
    })
    user = db_session.query(User).filter(User.email == email).first()
    return user, create_access_token(user.id)


def _add(client, user_id, token, name, lat, lon):
    return client.post(
        f"/settings/{user_id}/locations",
        cookies={"access_token": token},
        json={"name": name, "latitude": lat, "longitude": lon},
    )


# --- Schema: normalized table + index ---------------------------------------

def test_saved_location_table_has_lat_lon_index():
    from app.database.models import SavedLocation

    index_col_sets = {tuple(c.name for c in idx.columns) for idx in SavedLocation.__table__.indexes}
    assert ("latitude", "longitude") in index_col_sets
    assert SavedLocation.__tablename__ == "user_saved_locations"


# --- Add: writes a normalized row, keeps response contract ------------------

def test_add_location_creates_normalized_row(client, db_session):
    from app.database.models import SavedLocation

    user, token = _login(client, db_session)
    resp = _add(client, user.id, token, "Home", 40.0, -75.0)
    assert resp.status_code == 200

    rows = db_session.query(SavedLocation).filter_by(user_id=user.id).all()
    assert len(rows) == 1
    assert rows[0].name == "Home"
    assert rows[0].latitude == 40.0 and rows[0].longitude == -75.0

    # Contract preserved: response still returns a saved_locations list.
    locs = resp.json()["saved_locations"]
    assert locs[-1]["name"] == "Home"
    assert locs[-1]["latitude"] == 40.0


def test_duplicate_location_name_returns_400(client, db_session):
    user, token = _login(client, db_session)
    assert _add(client, user.id, token, "Home", 40.0, -75.0).status_code == 200
    assert _add(client, user.id, token, "Home", 41.0, -76.0).status_code == 400


# --- The point of DB1: query by coordinates via the indexed table -----------

def test_locations_queryable_by_lat_lon(client, db_session):
    from app.database.models import SavedLocation

    user, token = _login(client, db_session)
    _add(client, user.id, token, "Home", 40.0, -75.0)

    found = (
        db_session.query(SavedLocation)
        .filter(SavedLocation.latitude == 40.0, SavedLocation.longitude == -75.0)
        .first()
    )
    assert found is not None
    assert found.user_id == user.id


# --- Index-based update/delete still operate on the table -------------------

def test_delete_location_by_index_removes_row(client, db_session):
    from app.database.models import SavedLocation

    user, token = _login(client, db_session)
    _add(client, user.id, token, "Home", 40.0, -75.0)
    _add(client, user.id, token, "Work", 41.0, -74.0)

    resp = client.delete(f"/settings/{user.id}/locations/0", cookies={"access_token": token})
    assert resp.status_code == 200

    names = [r.name for r in db_session.query(SavedLocation)
             .filter_by(user_id=user.id).order_by(SavedLocation.id).all()]
    assert names == ["Work"]


def test_update_location_by_index(client, db_session):
    from app.database.models import SavedLocation

    user, token = _login(client, db_session)
    _add(client, user.id, token, "Home", 40.0, -75.0)

    resp = client.put(
        f"/settings/{user.id}/locations/0",
        cookies={"access_token": token},
        json={"name": "Cabin", "latitude": 44.0, "longitude": -71.0},
    )
    assert resp.status_code == 200

    row = db_session.query(SavedLocation).filter_by(user_id=user.id).one()
    assert row.name == "Cabin"
    assert row.latitude == 44.0
