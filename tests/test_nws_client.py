"""
Phase 2 — async NWS client (A1, A5, A4).

Uses respx to mock api.weather.gov so no real network is hit. The fake NWS is a
stub (canned data); A4 asserts breaker behaviour on repeated failure.
"""
import httpx
import pybreaker
import pytest
import respx

from src.clients import nws_client
from src.clients.nws_client import get_current_conditions, nws_breaker, NWS_TIMEOUT


POINTS = "https://api.weather.gov/points/40.0,-75.0"
HOURLY = "https://api.weather.gov/gridpoints/PHI/50,75/forecast/hourly"


@pytest.fixture(autouse=True)
def reset_breaker():
    """Each test starts with a closed circuit."""
    nws_breaker.close()
    yield
    nws_breaker.close()


def _points_payload():
    return {
        "properties": {
            "forecastHourly": HOURLY,
            "relativeLocation": {"properties": {"city": "Philadelphia", "state": "PA"}},
        }
    }


def _hourly_payload():
    return {
        "properties": {
            "periods": [{
                "temperature": 68,
                "windSpeed": "10 mph",
                "shortForecast": "Sunny",
                "startTime": "2026-01-01T12:00:00-05:00",
            }]
        }
    }


# --- A1: happy path parses the payload -------------------------------------

@respx.mock
async def test_get_current_conditions_parses_payload():
    respx.get(POINTS).mock(return_value=httpx.Response(200, json=_points_payload()))
    respx.get(HOURLY).mock(return_value=httpx.Response(200, json=_hourly_payload()))

    result = await get_current_conditions(40.0, -75.0)

    assert result["temp_f"] == 68.0
    assert result["wind_mph"] == 10.0
    assert result["short_forecast"] == "Sunny"
    assert result["location"] == "Philadelphia, PA"
    assert result["source"] == "weather.gov"


# --- A5: timeout is capped at 3s -------------------------------------------

def test_timeout_is_three_seconds():
    assert NWS_TIMEOUT == 3.0


@respx.mock
async def test_timeout_propagates():
    respx.get(POINTS).mock(side_effect=httpx.TimeoutException("slow"))
    with pytest.raises((httpx.TimeoutException, pybreaker.CircuitBreakerError)):
        await get_current_conditions(40.0, -75.0)


# --- A4: circuit breaker opens after repeated failures ---------------------

@respx.mock
async def test_circuit_breaker_opens_after_five_failures():
    # 404 is non-retryable → each call raises immediately (fast)
    respx.get(POINTS).mock(return_value=httpx.Response(404))

    breaker_opened = False
    for _ in range(nws_breaker.fail_max + 2):
        try:
            await get_current_conditions(40.0, -75.0)
        except pybreaker.CircuitBreakerError:
            breaker_opened = True
            break
        except Exception:
            pass  # underlying NWS failure (counts toward the breaker threshold)

    assert breaker_opened, "breaker never opened after repeated NWS failures"
    assert nws_breaker.current_state == "open"
