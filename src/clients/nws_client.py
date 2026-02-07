# nws_client.py
# Purpose:
#   A clean, beginner-friendly client for the U.S. National Weather Service (weather.gov) API.
#   It provides a single function, `get_current_conditions`, that returns the current hour's
#   temperature (°F), wind speed (mph), short forecast text, and period start time.
#
# Why not "scrape" HTML?
#   Because the official API is reliable, legal, and designed for automation. This module
#   uses that API in a polite way (proper headers, backoff, Retry-After support).
#
# Requirements:
#   pip install requests python-dotenv
#
# .env file (used ONLY to build a good User-Agent per NWS guidance):
#   APP_NAME=WeatherLayers
#   NWS_CONTACT=you@example.com

import os, re, time, json, math, requests
from datetime import datetime, timezone 
from urllib.parse import urljoin
from dotenv import load_dotenv

# Load environment variables from a local .env file if present.
# This lets developers keep personal info (like contact email) out of source control.
load_dotenv()

# -------------------------------
# Constants and Global Session
# -------------------------------

# Base URL for the National Weather Service API.
NWS_BASE_URL: str = "https://api.weather.gov/"

# These two values are used to construct a User-Agent string that NWS requests we send.
# The contact value should be an email or URL where NWS can reach you if there is a problem.
APPLICATION_NAME: str = os.getenv("APP_NAME", "WeatherLayers")
NWS_CONTACT_INFO: str = os.getenv("NWS_CONTACT", "you@example.com")

# Construct a User-Agent that identifies our application and provides contact information.
# This is important: it helps avoid throttling and is simply good API hygiene.
USER_AGENT: str = f"{APPLICATION_NAME} (contact: {NWS_CONTACT_INFO})"

# Create a single shared HTTP session so that connection pooling and headers are reused.
HTTP_SESSION: requests.Session = requests.Session()
HTTP_SESSION.headers.update(
    {
        # NWS requests that you identify your application + contact details.
        "User-Agent": USER_AGENT,
        # Ask for GeoJSON, which is what the API returns for forecast endpoints.
        "Accept": "application/geo+json",
    }
)

# HTTP status codes that signal a transient problem. We should retry these.
RETRYABLE_STATUS_CODES: set[int] = {429, 500, 502, 503, 504}


# -------------------------------
# Internal Helpers (Private)
# -------------------------------


def _get_forecast(url, params=None, max_attempts=3, timeout=12):
    """
    Make a GET request and parse JSON with polite retries.

    Behavior:
    - Retries on common transient statuses (429, 5xx).
    - Honors `Retry-After` response header if present, otherwise uses exponential backoff (2, 4, 8, 16 seconds).
    - Raises for non-retryable HTTP errors (e.g., 404 Not Found).
    - Returns a Python dict parsed from the JSON body on success.

    Args:
        url: Full URL to request.
        params: Optional query parameters to append to the URL.
        max_attempts: Maximum number of attempts before giving up.
        timeout: Per-request timeout to avoid hanging forever.

    Returns:
        Parsed JSON as a Python dictionary.
    """

    for attempt in range(1, max_attempts + 1):  # Try up to max_attempts times
        # Make the HTTP request with a per-request timeout
        response = HTTP_SESSION.get(url, params=params, timeout=timeout)

        # If server asks us to slow down or has a temporary issue, retry
        if response.status_code in RETRYABLE_STATUS_CODES:
            retry_after = response.headers.get("Retry-After")  # seconds, if provided

            # Use server hint if available, else exponential backoff (2, 4, 8...)
            if retry_after and retry_after.isdigit():
                sleep_seconds = int(retry_after)
            else:
                sleep_seconds = 2 ** attempt

            time.sleep(sleep_seconds)
            continue  # try again

        # If response status is not retryable and is still an error, raise it
        response.raise_for_status()

        # Success path — parse and return JSON response
        try:
            return response.json()
        except ValueError:
            raise ValueError(f"Response from {url} was not valid JSON.")

    # If all retries failed, raise an exception
    raise requests.exceptions.RequestException(f"Failed to get data after {max_attempts} attempts")

def _parse_time(time_string):
    """
    Parse a time string from the NWS API into a readable format.
    Example: "2025-10-27T12:00:00-04:00" -> "12:00 PM - 4:00 PM EST on October 27, 2025"
    """ 
    datetime_obj = datetime.fromisoformat(time_string)
    date = datetime_obj.strftime("%B %d, %Y") # Get the date from the datetime object
    time = datetime_obj.strftime("%I:%M %p") # Get the time from the datetime object
    timezone = datetime_obj.strftime("%Z") # Get the timezone from the datetime object
    return f"{time} {timezone} on {date} " # Return the time and date in a readable format
    
# --- Public API ----------------------------------------------------------------

def get_point(latitude, longitude):
    """Call /points/{lat,lon} to resolve the correct forecast office/grid and URLs.

    This is the official first step for weather.gov: it maps a location (lat/lon) to the
    appropriate forecast grid and gives us the URLs for forecast resources.

    Args:
        lat_degrees: Latitude in decimal degrees (e.g., 40.7128).
        lon_degrees: Longitude in decimal degrees (e.g., -74.0060).

    Returns:
        Full JSON object from the /points endpoint.
    """
    url = urljoin(NWS_BASE_URL, f"points/{latitude},{longitude}")
    return _get_forecast(url)

def get_hourly_forecast(latitude, longitude):
    """
    Get the official hourly forecast URL for a given location.

    Preferred source:
      properties.forecastHourly (returned by /points)
    Fallback:
      Construct /gridpoints/{wfo}/{x},{y}/forecast/hourly if forecastHourly is missing.
    """
    point_payload   = get_point(latitude, longitude) # Get the point payload from the API
    forecast_url = point_payload.get("properties", {}).get("forecastHourly") # Get the forecast URL from the point payload
    if not forecast_url:
        gridpoints = point_payload.get("properties", {}).get("gridpoints") # Get the gridpoints from the point payload
        if gridpoints:
            wfo, x, y = gridpoints.get("wfo"), gridpoints.get("x"), gridpoints.get("y") # Get the WFO, X, and Y from the gridpoints
            forecast_url = f"/gridpoints/{wfo}/{x},{y}/forecast/hourly" # Construct the forecast URL
    return urljoin(NWS_BASE_URL, forecast_url) # Return the forecast URL from the API

def get_location(latitude, longitude):
    """
    Get the location from the forecast payload.
    """
    point_payload = get_point(latitude, longitude) # Get the point payload from the API
    location = point_payload.get("properties", {}).get("relativeLocation", {}).get("properties", {}) # Get the location from the forecast payload
    city = location.get("city") # Get the city from the location
    state = location.get("state") # Get the state from the location
    return f"{city}, {state}" # Return the location in a readable format

import time
import random

US_MIN_LAT, US_MAX_LAT = 25.0, 49.0
US_MIN_LON, US_MAX_LON = -124.0, -66.0

def fetch_short_forecast_once(lat, lon):
    """
    Resolve an hourly forecast URL for (lat, lon), download the payload,
    and return the first period's shortForecast string (or None).
    """
    try:
        hourly_url = get_hourly_forecast(lat, lon)  # must return a full URL
        if not hourly_url or "/forecast/hourly" not in hourly_url:
            # Guard: if resolution failed or malformed, skip
            return None

        hourly_forecast_payload = _get_forecast(hourly_url)
        periods = (hourly_forecast_payload.get("properties", {}) or {}).get("periods", [])
        if not periods or not isinstance(periods, list) or not isinstance(periods[0], dict):
            return None

        return periods[0].get("shortForecast")
    except requests.HTTPError as e:
        # 404 or other HTTP error – skip this point
        return None
    except Exception:
        # Any other transient/network/parse error – skip
        return None

def get_all_short_forecasts(sample_size=100, sleep_seconds=1.0):
    """
    Collect up to `sample_size` shortForecast strings from random U.S. locations.
    Returns a list of dicts: {lat, lon, short_forecast}
    """
    results = []
    tries = 0
    while len(results) < sample_size and tries < sample_size * 4:
        tries += 1
        # Random U.S. continental point
        lat = round(random.uniform(US_MIN_LAT, US_MAX_LAT), 3)
        lon = round(random.uniform(US_MIN_LON, US_MAX_LON), 3)

        short_fc = fetch_short_forecast_once(lat, lon)
        if short_fc:
            results.append({"lat": lat, "lon": lon, "short_forecast": short_fc})
            print(f"[{len(results)}/{sample_size}] ({lat}, {lon}): {short_fc}")
        else:
            print(f"[skip] ({lat}, {lon}) no usable forecast")

        time.sleep(sleep_seconds)  # be polite; avoid rate limits
    return results



def get_current_conditions(latitude, longitude):
    """
    Fetch the current (or next) hour's conditions for a location.
    Call /stations/{station_id}/observations/latest 

    Notes:
    - The hourly forecast "periods" array is time-sliced; the first element is typically the
      current hour (or the next upcoming hour). We return that slice.
    - Temperature is already in Fahrenheit for this endpoint, so no unit conversion is needed.
    - Wind speed is a human-friendly string; we convert it into a numeric mph value.

    Args:
        lat_degrees: Latitude in decimal degrees.
        lon_degrees: Longitude in decimal degrees.

    Returns:
        A dictionary with:
          {
            "temp_f": float,          # temperature in Fahrenheit
            "wind_mph": float,        # wind speed in mph (averaged if given as a range)
            "short_forecast": str,    # short text description
            "period_start": str,      # ISO timestamp of the hourly period start
            "source": "weather.gov"
          }

    Raises:
        RuntimeError: If the hourly forecast has no periods to read.
        requests.RequestException / requests.HTTPError: For networking/HTTP issues.
        ValueError: If success returned non-JSON (rare).
    """
    from src.utils.parsing import parse_wind_speed
    
    hourly_forecast_url = get_hourly_forecast(latitude, longitude) # Get the hourly forecast URL from the API
    hourly_forecast_payload = _get_forecast(hourly_forecast_url) # Get the forecast payload from the API

    periods = hourly_forecast_payload.get("properties", {}).get("periods", []) or []
    if not periods:
        raise RuntimeError("No hourly periods available from NWS for this location.")
    current_period = periods[0] # Get the current period from the forecast payload

    temperature = current_period.get("temperature") # Get the temperature in Fahrenheit from the current period
    wind_speed = current_period.get("windSpeed") # Get the wind speed in mph from the current period
    short_forecast = current_period.get("shortForecast") # Get the short forecast from the current period
    period_start = _parse_time(current_period.get("startTime"))  # Get the period start time from the current period
    location = get_location(latitude, longitude)

    # source = "weather.gov" # Set the source to weather.gov  
    
    # Parse wind speed using utility function
    wind_mph = parse_wind_speed(wind_speed) if wind_speed else 0.0

    return {
        "temp_f": temperature,
        "wind_mph": wind_mph,
        "short_forecast": short_forecast,
        "period_start": period_start,
        "source": "weather.gov",
        "location": location
    } # Return the current period from the forecast payload

