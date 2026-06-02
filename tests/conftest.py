"""
Shared pytest fixtures and factory fakes.

Design follows the wiki testing cluster:
- Reusable factory fakes (create*Fake) instead of per-test mocks — see test-doubles.
- Unit tests stay isolated (no real DB / no network); the app-level tests use an
  in-memory SQLite DB and dependency overrides so they never touch Postgres or NWS.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


# ---------------------------------------------------------------------------
# Factory fakes (test doubles)
# ---------------------------------------------------------------------------

class FakeWeather:
    """Stand-in for src.domain.models.weather.Weather — no network."""
    def __init__(self, temp_f=70.0, wind_mph=0.0, short_forecast="", ready=True):
        self._data = {
            "temp_f": temp_f,
            "wind_mph": wind_mph,
            "short_forecast": short_forecast,
            "location": "Testville, TS",
            "period_start": "12:00 PM on January 01, 2026",
        }
        self._ready = ready

    def is_ready(self):            return self._ready
    def get_temperature(self):     return float(self._data["temp_f"])
    def get_wind_speed(self):      return float(self._data["wind_mph"])
    def get_short_forecast(self):  return (self._data["short_forecast"] or "").lower()
    def get_period_start(self):    return self._data["period_start"]
    @property
    def weather_data(self):        return self._data


def create_weather_payload(temp_f=70.0, wind_mph=5.0, short_forecast="sunny"):
    """A canned NWS get_current_conditions() return value."""
    return {
        "temp_f": temp_f,
        "wind_mph": wind_mph,
        "short_forecast": short_forecast,
        "period_start": "12:00 PM on January 01, 2026",
        "source": "weather.gov",
        "location": "Testville, TS",
    }


# ---------------------------------------------------------------------------
# In-memory DB + app client (for route/integration tests)
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session():
    """Fresh in-memory SQLite session per test, with all tables created."""
    from app.database.connection import Base
    import app.database.models  # noqa: F401  (register models on Base)

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    """
    FastAPI TestClient with get_db overridden to the in-memory session.
    NWS is patched per-test (see test_api.py) so no network is hit.
    """
    from fastapi.testclient import TestClient
    from app import web
    from app.database.connection import get_db

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    web.app.dependency_overrides[get_db] = _override_get_db
    with TestClient(web.app) as c:
        yield c
    web.app.dependency_overrides.clear()
