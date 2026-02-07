"""
Weather scoring module.

This module calculates a comfort score based on weather conditions.
The score combines temperature deviation from comfort temperature, wind speed,
and forecast conditions to produce a single comfort score.

Formula: comfort_score = (temperature_score * wind_multiplier) + forecast_score

Higher scores indicate more comfortable conditions (warmer, less wind, better forecast).
Lower scores indicate less comfortable conditions (colder, windy, poor forecast).
"""
from src.config.common import FORECAST_SCORES, COMFORT_TEMPERATURE

# --- Temperature score (°F)------------------------
def score_temperature(temperature, comfort_temperature=None):
    """
    Score the temperature based on its distance from the comfort temperature.
    
    Calculates how comfortable the temperature is relative to the user's preferred
    comfort temperature (default: 70°F). The score decreases linearly as temperature
    deviates from the comfort temperature.
    
    Scoring formula:
    - Peak comfort at comfort_temperature (default 70°F) = +10 points
    - Decreases by 0.5 points per degree Fahrenheit away from comfort temperature
    - Example: 70°F = 10.0, 60°F = 5.0, 50°F = 0.0, 30°F = -10.0
    
    Args:
        temperature: Current temperature in Fahrenheit (float or convertible to float)
        comfort_temperature: User's preferred comfort temperature (default: uses COMFORT_TEMPERATURE constant)
        
    Returns:
        float: Temperature score (typically ranges from -10 to +10)
        
    Example:
        >>> score_temperature(70.0)
        10.0
        >>> score_temperature(60.0, 60.0)
        10.0
        >>> score_temperature(30.0)
        -10.0
    """
    # Use default comfort temperature if not provided
    if comfort_temperature is None:
        comfort_temperature = COMFORT_TEMPERATURE
    
    # Calculate absolute difference from comfort temperature
    diff = abs(float(temperature) - float(comfort_temperature))
    # Score decreases by 0.5 points per degree Fahrenheit away from comfort temp
    score = 10.0 - 0.5 * diff  # 0.5 pts per °F away from comfort_temperature
    return score

# --- Wind multiplier: always <= 1, decreases with wind ---
def wind_multiplier(wind_speed, start=5.0, step=0.1, floor=0.0):
    """
    Calculate wind multiplier to penalize comfort score for wind.
    
    Wind reduces comfort, especially in cold conditions. This multiplier
    is applied to the temperature score to account for wind chill effect.
    The multiplier decreases as wind speed increases above a threshold.
    
    Formula:
    - Wind <= start mph: multiplier = 1.0 (no penalty)
    - Wind > start mph: multiplier = 1.0 - step * (wind_speed - start)
    - Multiplier never goes below floor value
    
    Uses 0-10 scale with 0.1 increments for wind modifiers:
    - Each mph of wind above 5 mph reduces multiplier by 0.1
    - 15 mph wind = 1.0 - (0.1 * 10) = 0.0 multiplier (maximum penalty)
    
    Args:
        wind_speed: Wind speed in miles per hour (float or convertible to float)
        start: Wind speed threshold in mph before penalty applies (default: 5.0)
        step: Penalty per mph above threshold (default: 0.1)
        floor: Minimum multiplier value (default: 0.0)
        
    Returns:
        float: Wind multiplier between floor and 1.0
        
    Example:
        >>> wind_multiplier(5.0)   # No penalty
        1.0
        >>> wind_multiplier(10.0)  # 5 mph above threshold
        0.5
        >>> wind_multiplier(15.0)  # 10 mph above threshold
        0.0
    """
    # Calculate wind speed above threshold
    w = max(0.0, float(wind_speed) - start)
    # Calculate multiplier (decreases with wind at 0.1 per mph)
    m = 1.0 - step * w
    # Ensure multiplier doesn't go below floor
    return max(floor, m)



def score_weather(weather, comfort_temperature=None):
    """
    Calculate overall comfort score from weather conditions.
    
    Combines temperature, wind speed, and forecast conditions into a single
    comfort score normalized to 0-10 scale. The score is used to determine 
    appropriate clothing layers.
    
    Formula:
        raw_score = (temperature_score * wind_multiplier) + forecast_score
        comfort_score = clamp(raw_score, 0, 10)
    
    Where:
        - temperature_score: Based on deviation from comfort temperature
        - wind_multiplier: Reduces score for high wind speeds (0.1 increments)
        - forecast_score: Bonus/penalty based on forecast conditions
        - Result is clamped to 0-10 range (no negative values)
    
    Args:
        weather: Weather object with methods:
            - get_temperature(): Returns temperature in Fahrenheit
            - get_wind_speed(): Returns wind speed in mph
            - get_short_forecast(): Returns forecast description string
        comfort_temperature: User's preferred comfort temperature (default: uses COMFORT_TEMPERATURE constant)
            
    Returns:
        float: Comfort score between 0 and 10 (higher = more comfortable)
               0 = Very uncomfortable (cold/hot, windy, poor conditions)
               10 = Perfect comfort (ideal temp, calm, clear weather)
        
    Example:
        For 70°F, 5 mph wind, "sunny":
        - temperature_score = 10.0
        - wind_multiplier = 1.0
        - forecast_score = 0 (normalized)
        - Raw score = 10.0 * 1.0 + 0 = 10.0
        - Final score = clamp(10.0, 0, 10) = 10.0
        
        For 43°F, 20 mph wind, "mostly sunny":
        - temperature_score = -3.5
        - wind_multiplier = 0.0 (15 mph above threshold)
        - forecast_score = 0
        - Raw score = -3.5 * 0.0 + 0 = 0.0
        - Final score = clamp(0.0, 0, 10) = 0.0
        
        For 60°F, 8 mph wind, "partly cloudy":
        - temperature_score = 5.0
        - wind_multiplier = 0.7 (3 mph above threshold = 0.3 penalty)
        - forecast_score = 0
        - Raw score = 5.0 * 0.7 + 0 = 3.5
        - Final score = clamp(3.5, 0, 10) = 3.5
    """
    # Calculate base temperature score (-10 to +10 range)
    temperature = score_temperature(weather.get_temperature(), comfort_temperature)
    wind_speed = weather.get_wind_speed() 
    short_forecast = weather.get_short_forecast()

    # Apply wind multiplier to temperature score (0.0 to 1.0)
    # Wind reduces comfort, especially in cold conditions
    wind_multiplier_score = wind_multiplier(weather.get_wind_speed()) 
    temperature_score = temperature * wind_multiplier_score
    
    # Normalize temperature score to 0-10 range
    # Original range is -10 to +10, shift to 0-20, then scale to 0-10
    normalized_temp_score = (temperature_score + 10.0) / 2.0
    
    # Forecast adjustment (small modifier, ±1 point)
    # Simplified from large bonuses to minor adjustments
    forecast_modifier = 0
    if short_forecast and isinstance(short_forecast, str):
        forecast_lower = short_forecast.lower()
        if any(word in forecast_lower for word in ['sunny', 'clear']):
            forecast_modifier = 0.5
        elif any(word in forecast_lower for word in ['cloudy', 'overcast']):
            forecast_modifier = -0.25
        elif any(word in forecast_lower for word in ['rain', 'snow', 'storm']):
            forecast_modifier = -0.5
    
    # Combine normalized temperature with forecast modifier
    score = normalized_temp_score + forecast_modifier
    
    # Clamp final score to 0-10 range
    score = max(0.0, min(10.0, score))
    
    return score

