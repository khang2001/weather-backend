"""
SC3 per-user wiring — heat/cold tolerance is stored on the user, surfaced via
the settings endpoints, and consumed by /score (same flow as comfort_temperature:
persisted on the user, passed in the score request body).

Tolerances are stored as penalty-per-degree slopes (default 0.5 = symmetric).
"""
import pytest

from app import web
from tests.conftest import create_weather_payload


def _login(client, db_session, email="carol@example.com", username="carol", password="pw12345"):
    from app.database.models import User
    from app.security import create_access_token

    client.post("/auth/register", json={
        "username": username, "email": email, "password": password, "comfort_temperature": 70.0,
    })
    user = db_session.query(User).filter(User.email == email).first()
    return user, create_access_token(user.id)


# --- Model: sensible symmetric defaults -------------------------------------

def test_new_user_has_symmetric_default_tolerances(client, db_session):
    user, _ = _login(client, db_session)
    assert user.cold_penalty_per_degree == pytest.approx(0.5)
    assert user.heat_penalty_per_degree == pytest.approx(0.5)


# --- Settings: persist + return the tolerances ------------------------------

def test_update_settings_persists_tolerances(client, db_session):
    from app.database.models import User

    user, token = _login(client, db_session)
    resp = client.put(
        f"/settings/{user.id}",
        cookies={"access_token": token},
        json={"cold_penalty_per_degree": 0.25, "heat_penalty_per_degree": 0.75},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["cold_penalty_per_degree"] == pytest.approx(0.25)
    assert body["heat_penalty_per_degree"] == pytest.approx(0.75)

    db_session.expire_all()
    refreshed = db_session.query(User).filter(User.id == user.id).one()
    assert refreshed.cold_penalty_per_degree == pytest.approx(0.25)
    assert refreshed.heat_penalty_per_degree == pytest.approx(0.75)


# --- /score: consume tolerances from the request body -----------------------

def test_score_applies_request_tolerances(client, monkeypatch):
    async def hot(lat, lon):
        return create_weather_payload(temp_f=80.0, wind_mph=0.0, short_forecast="sunny")

    monkeypatch.setattr(web, "get_current_conditions", hot)
    monkeypatch.setattr(web, "_cache_lookup", lambda db, lat, lon: None)
    monkeypatch.setattr(web, "_cache_upsert", lambda db, lat, lon, data: None)
    monkeypatch.setattr(web, "_save_recommendation", lambda *a, **k: None)

    base = client.post("/score", json={
        "latitude": 40.0, "longitude": -75.0, "comfort_temperature": 70.0,
    }).json()["comfort_score"]

    heat_sensitive = client.post("/score", json={
        "latitude": 40.0, "longitude": -75.0, "comfort_temperature": 70.0,
        "heat_penalty_per_degree": 1.0,
    }).json()["comfort_score"]

    # 80°F is 10° above comfort; a heat-sensitive slope must lower the score.
    assert heat_sensitive < base
