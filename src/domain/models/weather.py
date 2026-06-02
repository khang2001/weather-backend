# weather.py — Weather value object (A1 refactor)
#
# Constructor now takes a pre-fetched data dict (never blocks).
# Use the async classmethod Weather.fetch() to create from NWS.
# Use Weather.from_cache() to create from a cached dict — zero network calls.

from __future__ import annotations


class Weather:
    def __init__(self, weather_data: dict, latitude: float, longitude: float) -> None:
        self.latitude = latitude
        self.longitude = longitude
        self.weather_data = weather_data
        self.score = 0.0

    # -- Factories -------------------------------------------------------------

    @classmethod
    async def fetch(cls, latitude: float, longitude: float) -> "Weather":
        """Fetch from NWS (async). Returns an empty-data instance on failure."""
        from src.clients.nws_client import get_current_conditions
        try:
            data = await get_current_conditions(latitude, longitude)
        except Exception as exc:
            print(f"Weather.fetch failed for ({latitude}, {longitude}): {exc}")
            data = {}
        return cls(data, latitude, longitude)

    @classmethod
    def from_cache(cls, weather_data: dict, latitude: float, longitude: float) -> "Weather":
        """Build from a cached dict — no network call."""
        return cls(weather_data, latitude, longitude)

    # -- Accessors -------------------------------------------------------------

    def is_ready(self) -> bool:
        return bool(self.weather_data)

    def get_weather_data(self) -> dict:
        return self.weather_data

    def get_temperature(self) -> float:
        return float(self.weather_data.get("temp_f", 0.0))

    def get_temperature_celsius(self) -> float:
        return (self.get_temperature() - 32.0) * 5.0 / 9.0

    def get_wind_speed(self) -> float:
        return float(self.weather_data.get("wind_mph", 0.0))

    def get_short_forecast(self) -> str:
        return self.weather_data.get("short_forecast", "No forecast available").lower()

    def get_period_start(self) -> str:
        return self.weather_data.get("period_start", "Unknown")

    def get_score(self) -> float:
        return self.score

    def set_score(self, score: float) -> None:
        self.score = score

    def __str__(self) -> str:
        return (
            f"Weather at ({self.latitude}, {self.longitude}): "
            f"{self.get_temperature():.1f}°F, {self.get_short_forecast()}, "
            f"wind {self.get_wind_speed():.1f} mph."
        )
