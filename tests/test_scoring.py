# test_scoring.py
# Basic sanity tests for scoring functions

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.scoring.weather_scoring import score_temperature, wind_multiplier, score_weather
from src.domain.models.weather import Weather


def test_score_temperature():
    """Test temperature scoring"""
    from src.config.common import COMFORT_TEMPERATURE
    
    # Test at comfort temperature
    score = score_temperature(COMFORT_TEMPERATURE)
    assert score == 10.0, f"Expected 10.0 at comfort temp, got {score}"
    
    # Test 10 degrees away
    score = score_temperature(COMFORT_TEMPERATURE + 10)
    assert score == 5.0, f"Expected 5.0 at +10°F, got {score}"
    
    print("✓ test_score_temperature passed")


def test_wind_multiplier():
    """Test wind multiplier"""
    # Test at start threshold
    mult = wind_multiplier(5.0)
    assert abs(mult - 1.0) < 0.01, f"Expected ~1.0 at 5 mph, got {mult}"
    
    # Test above threshold
    mult = wind_multiplier(15.0)
    assert 0.7 < mult < 0.9, f"Expected ~0.8 at 15 mph, got {mult}"
    
    print("✓ test_wind_multiplier passed")


def test_score_weather():
    """Test weather scoring with mock weather"""
    # Create a mock weather object
    class MockWeather:
        def __init__(self):
            self.weather_data = {
                "temp_f": 70.0,
                "wind_mph": 5.0,
                "short_forecast": "sunny"
            }
        
        def get_temperature(self):
            return self.weather_data["temp_f"]
        
        def get_wind_speed(self):
            return self.weather_data["wind_mph"]
        
        def get_short_forecast(self):
            return self.weather_data["short_forecast"]
    
    weather = MockWeather()
    score = score_weather(weather)
    
    # Should be positive (comfortable temp + sunny)
    assert score > 0, f"Expected positive score, got {score}"
    print(f"✓ test_score_weather passed (score: {score})")


if __name__ == "__main__":
    print("Running scoring tests...")
    test_score_temperature()
    test_wind_multiplier()
    test_score_weather()
    print("\nAll tests passed!")

