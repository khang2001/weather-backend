"""
Route-level integration tests via FastAPI TestClient.

Covers: health, /score validation + happy path (NWS + cache patched),
S4 (no exception leakage), the auth flow (S1+S2), and protected-route
status codes (S2/D5). D1: GET /score returns 405 (POST-only).

NWS and the Postgres-only cache UPSERT are patched so these run on SQLite
with no network — keeping the tests Isolated (unit-testing-best-practices).
"""
import pytest

from app import web
from tests.conftest import create_weather_payload


@pytest.fixture
def patch_nws(monkeypatch):
    """Patch the /score route's NWS call + cache so no network/Postgres is needed."""
    async def fake_conditions(lat, lon):
        return create_weather_payload(temp_f=70.0, wind_mph=5.0, short_forecast="sunny")

    monkeypatch.setattr(web, "get_current_conditions", fake_conditions)
    monkeypatch.setattr(web, "_cache_lookup", lambda db, lat, lon: None)
    monkeypatch.setattr(web, "_cache_upsert", lambda db, lat, lon, data: None)


# --- Health ----------------------------------------------------------------

def test_health_returns_200(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


# --- /score validation + happy path ---------------------------------------

def test_score_missing_coords_returns_400(client):
    # No body and no query params → route's own "coords required" guard (400).
    resp = client.post("/score")
    assert resp.status_code == 400


def test_score_post_returns_recommendation(client, patch_nws):
    resp = client.post("/score", json={"latitude": 40.0, "longitude": -75.0, "comfort_temperature": 70})
    assert resp.status_code == 200
    body = resp.json()
    assert body["comfort_score"] == pytest.approx(10.0, abs=0.01)  # 70°F/5mph/sunny
    assert body["weather"]["temp_f"] == 70.0
    assert len(body["clothing_recommendations"]) >= 1


def test_score_get_returns_405(client):
    # D1: /score is POST-only; GET is no longer routed.
    resp = client.get("/score", params={"latitude": 40.0, "longitude": -75.0})
    assert resp.status_code == 405


# --- A3: /score persists recommendation history (BackgroundTasks) -----------

def test_score_persists_recommendation_history(client, db_session, patch_nws, monkeypatch):
    # A3: after /score returns, a Recommendation row is written fire-and-forget.
    # The background task opens its OWN session via SessionLocal (the request
    # session is already closed by then) — bind that to the test DB.
    from app.database.models import Recommendation
    from app import web

    monkeypatch.setattr(web, "SessionLocal", lambda: db_session)

    resp = client.post("/score", json={"latitude": 40.0, "longitude": -75.0, "comfort_temperature": 70})
    assert resp.status_code == 200  # response is unchanged by the history write

    rows = db_session.query(Recommendation).all()
    assert len(rows) == 1
    rec = rows[0]
    assert rec.latitude == 40.0
    assert rec.longitude == -75.0
    assert rec.comfort_temperature == 70.0
    assert rec.comfort_score == pytest.approx(10.0, abs=0.01)
    assert isinstance(rec.clothing_recommendations, list)
    assert len(rec.clothing_recommendations) >= 1


def test_score_succeeds_even_if_history_write_fails(client, patch_nws, monkeypatch):
    # A3: history persistence is fire-and-forget — a DB failure in the background
    # task must not surface to the caller; /score still returns 200.
    from app import web

    def boom():
        raise RuntimeError("history DB down")

    monkeypatch.setattr(web, "SessionLocal", boom)

    resp = client.post("/score", json={"latitude": 40.0, "longitude": -75.0, "comfort_temperature": 70})
    assert resp.status_code == 200


# --- D3: /v1 dual-mount -----------------------------------------------------

def test_v1_score_returns_recommendation(client, patch_nws):
    # The /v1-prefixed route resolves and behaves identically to the legacy path.
    resp = client.post("/v1/score", json={"latitude": 40.0, "longitude": -75.0, "comfort_temperature": 70})
    assert resp.status_code == 200
    assert resp.json()["comfort_score"] == pytest.approx(10.0, abs=0.01)


def test_v1_settings_without_auth_returns_401(client):
    # Versioned router still enforces auth (proves the auth router is mounted under /v1 too).
    resp = client.get("/v1/settings/1")
    assert resp.status_code == 401


def test_health_is_not_versioned(client):
    # Health/root stay unversioned — probes target a stable path.
    assert client.get("/health").status_code == 200
    assert client.get("/v1/health").status_code == 404


# --- S4: no exception message leakage --------------------------------------

def test_score_error_does_not_leak_internals(client, monkeypatch):
    async def boom(lat, lon):
        raise ValueError("psycopg2 FATAL: secret connection string leaked")

    monkeypatch.setattr(web, "get_current_conditions", boom)
    monkeypatch.setattr(web, "_cache_lookup", lambda db, lat, lon: None)

    resp = client.post("/score", json={"latitude": 40.0, "longitude": -75.0})
    assert resp.status_code == 503
    assert "psycopg2" not in resp.text
    assert "secret" not in resp.text


# --- Auth flow: S1 (hashing) + S2 (JWT cookie) -----------------------------

def _register(client, username="alice", email="alice@example.com", password="hunter2"):
    return client.post("/auth/register", json={
        "username": username, "email": email, "password": password, "comfort_temperature": 70.0,
    })


def test_register_stores_bcrypt_hash(client, db_session):
    from app.database.models import User
    resp = _register(client)
    assert resp.status_code == 201
    user = db_session.query(User).filter(User.email == "alice@example.com").first()
    assert user.password.startswith("$2b$")        # S1: never plaintext


def test_login_sets_httponly_cookie(client):
    _register(client)
    resp = client.post("/auth/login", json={"email": "alice@example.com", "password": "hunter2"})
    assert resp.status_code == 200
    assert "access_token" in resp.cookies            # S2: JWT issued as cookie


def test_login_unknown_user_returns_404(client):
    resp = client.post("/auth/login", json={"email": "nobody@example.com", "password": "x"})
    assert resp.status_code == 404


def test_login_wrong_password_returns_401(client):
    _register(client)
    resp = client.post("/auth/login", json={"email": "alice@example.com", "password": "WRONG"})
    assert resp.status_code == 401


# --- Protected routes: S2 + D5 status codes --------------------------------

def test_settings_without_auth_returns_401(client):
    resp = client.get("/settings/1")
    assert resp.status_code == 401                   # not authenticated


def test_settings_for_other_user_returns_403(client, db_session):
    # alice registers; mint her token directly (TestClient won't resend a Secure
    # cookie over http — a test-env artifact, production is https), then she tries
    # to read user_id=999 which is not her.
    from app.database.models import User
    from app.security import create_access_token

    _register(client)
    alice = db_session.query(User).filter(User.email == "alice@example.com").first()
    token = create_access_token(alice.id)

    resp = client.get("/settings/999", cookies={"access_token": token})
    assert resp.status_code == 403                   # authenticated but forbidden
