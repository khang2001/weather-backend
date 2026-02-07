# weather.py
# Wrapper around the NWS client. Safe for new devs: imports are explicit, getters are defensive.

from src.clients.nws_client import get_current_conditions  # <-- REQUIRED import

class Weather:
    def __init__(self, latitude, longitude):
        """
        Create a Weather object and immediately fetch NWS data.
        If the fetch fails, weather_data becomes {} so getters won't crash.
        """
        self.latitude = latitude
        self.longitude = longitude
        self.score = 0  # clothing/comfort score you compute later

        try:
            self.weather_data = get_current_conditions(latitude, longitude)
        except Exception as e:
            # Keep the object usable even if network fails
            print(f"Could not retrieve weather data: {e}")
            self.weather_data = {}

    def __str__(self):
        """
        Human-friendly summary. Uses safe getters so it won't crash if data is missing.
        """
        return (f"Weather at ({self.latitude}, {self.longitude}): "
                f"{self.get_temperature():.1f}°F, {self.get_short_forecast()}, "
                f"wind {self.get_wind_speed():.1f} mph.")

    # ---- Quick health check ---------------------------------------------------
    def is_ready(self):
        """True if we have non-empty weather data."""
        return bool(self.weather_data)

    # ---- Accessors (defensive: use .get with defaults) -----------------------
    def get_weather_data(self):
        return self.weather_data

    def get_temperature(self):
        # Default 0.0 if missing so downstream math doesn't explode
        return float(self.weather_data.get("temp_f", 0.0))

    def get_temperature_celsius(self):
        return (self.get_temperature() - 32.0) * 5.0 / 9.0

    def get_wind_speed(self):
        return float(self.weather_data.get("wind_mph", 0.0))

    def get_short_forecast(self):
        return self.weather_data.get("short_forecast", "No forecast available").lower()

    def get_period_start(self):
        return self.weather_data.get("period_start", "Unknown")

    # ---- Scoring --------------------------------------------------------------
    def get_score(self):
        return self.score

    def set_score(self, score):
        self.score = score

