# nws_client.py — async NWS client (A1 + A4 + A5)
#
# Uses httpx.AsyncClient so NWS calls never block the FastAPI event loop.
# Timeout capped at 3 s (A5 — was 12 s).
# Circuit breaker opens after 5 consecutive failures; resets after 60 s (A4).

import asyncio
import os
import random
from datetime import datetime
from urllib.parse import urljoin

import httpx
import pybreaker
from dotenv import load_dotenv

load_dotenv()

# --- Config -------------------------------------------------------------------

NWS_BASE_URL = "https://api.weather.gov/"
APPLICATION_NAME = os.getenv("APP_NAME", "WeatherLayers")
NWS_CONTACT_INFO = os.getenv("NWS_CONTACT", "you@example.com")
NWS_HEADERS = {
    "User-Agent": f"{APPLICATION_NAME} (contact: {NWS_CONTACT_INFO})",
    "Accept": "application/geo+json",
}
NWS_TIMEOUT = 3.0  # A5: was 12 s
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# A4 — circuit breaker: open after 5 failures, try again after 60 s
nws_breaker = pybreaker.CircuitBreaker(fail_max=5, reset_timeout=60)


# --- Internal helpers ---------------------------------------------------------

async def _do_get(url: str, params=None, max_attempts: int = 3) -> dict:
    """Async GET with exponential-backoff retries."""
    for attempt in range(1, max_attempts + 1):
        async with httpx.AsyncClient(timeout=NWS_TIMEOUT, headers=NWS_HEADERS) as client:
            response = await client.get(url, params=params)

        if response.status_code in RETRYABLE_STATUS_CODES:
            retry_after = response.headers.get("Retry-After")
            sleep_secs = int(retry_after) if (retry_after and retry_after.isdigit()) else 2 ** attempt
            await asyncio.sleep(sleep_secs)
            continue

        response.raise_for_status()
        return response.json()

    raise httpx.RequestError(f"NWS: failed after {max_attempts} attempts — {url}")


async def _get(url: str, params=None, max_attempts: int = 3) -> dict:
    """Circuit-breaker-protected wrapper around _do_get.

    NOTE: pybreaker's @decorator does NOT track failures for async functions —
    it must be driven via call_async() to count failures and open the circuit.
    """
    return await nws_breaker.call_async(_do_get, url, params, max_attempts)


def _parse_time(time_string: str) -> str:
    dt = datetime.fromisoformat(time_string)
    return f"{dt.strftime('%I:%M %p %Z')} on {dt.strftime('%B %d, %Y')}"


def _parse_wind_speed(raw: str) -> float:
    """'10 mph' → 10.0   '5 to 10 mph' → 7.5"""
    from src.utils.parsing import parse_wind_speed
    return parse_wind_speed(raw)


# --- Public API ---------------------------------------------------------------

async def get_point(latitude: float, longitude: float) -> dict:
    url = urljoin(NWS_BASE_URL, f"points/{latitude},{longitude}")
    return await _get(url)


async def get_hourly_forecast_url(latitude: float, longitude: float) -> str:
    point = await get_point(latitude, longitude)
    url = point.get("properties", {}).get("forecastHourly")
    if not url:
        raise RuntimeError(f"NWS /points did not return a forecastHourly URL for {latitude},{longitude}")
    return url


async def get_location(latitude: float, longitude: float) -> str:
    point = await get_point(latitude, longitude)
    loc = point.get("properties", {}).get("relativeLocation", {}).get("properties", {})
    city, state = loc.get("city"), loc.get("state")
    return f"{city}, {state}" if city and state else "Unknown"


async def get_current_conditions(latitude: float, longitude: float) -> dict:
    """
    Return current-hour weather for the given coordinates.

    Raises:
        pybreaker.CircuitBreakerError  — if NWS is in repeated failure
        httpx.TimeoutException         — if NWS takes > 3 s
        RuntimeError                   — if NWS returns no periods
    """
    hourly_url = await get_hourly_forecast_url(latitude, longitude)
    payload = await _get(hourly_url)

    periods = (payload.get("properties") or {}).get("periods") or []
    if not periods:
        raise RuntimeError("NWS returned no hourly periods for this location.")

    current = periods[0]
    wind_raw = current.get("windSpeed", "0 mph")

    return {
        "temp_f":         float(current.get("temperature", 0)),
        "wind_mph":       _parse_wind_speed(wind_raw) if wind_raw else 0.0,
        "short_forecast": current.get("shortForecast", ""),
        "period_start":   _parse_time(current.get("startTime", "")),
        "source":         "weather.gov",
        "location":       await get_location(latitude, longitude),
    }
