"""
Weather scoring module.

This module calculates a comfort score based on weather conditions.
The score combines temperature deviation from comfort temperature, wind speed,
and forecast conditions to produce a single comfort score.

Formula: comfort_score = (temperature_score * wind_multiplier) + forecast_score

Higher scores indicate more comfortable conditions (warmer, less wind, better forecast).
Lower scores indicate less comfortable conditions (colder, windy, poor forecast).
"""
from src.config.common import (
    FORECAST_SCORES,
    COMFORT_TEMPERATURE,
    COLD_PENALTY_PER_DEGREE,
    HEAT_PENALTY_PER_DEGREE,
)

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



def score_weather(
    weather,
    comfort_temperature=None,
    cold_penalty_per_degree=None,
    heat_penalty_per_degree=None,
):
    """
    Calculate overall comfort score from weather conditions (0–10 scale).

    Additive model (SC2 fix — removed the (score + 10)/2 normalization that
    produced a phantom +5 floor whenever wind_mult zeroed the temperature score):

        temp_penalty  = cold_slope * (comfort - temp)   if temp < comfort  (cold side)
                      | heat_slope * (temp - comfort)   if temp >= comfort (hot side)
        wind_penalty  = max(0.0, 0.1 * (wind - 5))      # 0 below 5 mph, 1.0 at 15 mph
        forecast_mod  = +0.5 (sunny/clear)
                      | -0.25 (cloudy/overcast)
                      | -0.5  (rain/snow/storm)
                      |  0    (other)
        score = clamp(10.0 - temp_penalty - wind_penalty + forecast_mod, 0, 10)

    SC3 — asymmetric comfort: cold_penalty_per_degree / heat_penalty_per_degree
    let cold and hot deviations be weighted differently (e.g. a heat-sensitive
    user). Both default to the symmetric 0.5/°F, so omitting them reproduces the
    original behavior exactly.

    Examples (symmetric defaults):
        70°F / 0 mph / sunny  (comfort 70°F) → 10 - 0 - 0 + 0.5 → 10.0
        43°F / 20 mph / clear (comfort 70°F) → 10 - 13.5 - 1.5 + 0.5 → 0.0
        5°F  / 30 mph / rain  (comfort 70°F) → 10 - 32.5 - 2.5 - 0.5 → 0.0
        60°F / 5 mph  / cloudy(comfort 70°F) → 10 - 5 - 0 - 0.25 → 4.75
    """
    if comfort_temperature is None:
        comfort_temperature = COMFORT_TEMPERATURE
    if cold_penalty_per_degree is None:
        cold_penalty_per_degree = COLD_PENALTY_PER_DEGREE
    if heat_penalty_per_degree is None:
        heat_penalty_per_degree = HEAT_PENALTY_PER_DEGREE

    temp   = float(weather.get_temperature())
    wind   = float(weather.get_wind_speed())
    fcast  = weather.get_short_forecast() or ""
    comfort = float(comfort_temperature)

    if temp < comfort:
        temp_penalty = cold_penalty_per_degree * (comfort - temp)
    else:
        temp_penalty = heat_penalty_per_degree * (temp - comfort)
    wind_penalty = max(0.0, 0.1 * (wind - 5.0))

    forecast_mod = 0.0
    if isinstance(fcast, str):
        fl = fcast.lower()
        if any(w in fl for w in ("sunny", "clear")):
            forecast_mod = 0.5
        elif any(w in fl for w in ("cloudy", "overcast")):
            forecast_mod = -0.25
        elif any(w in fl for w in ("rain", "snow", "storm")):
            forecast_mod = -0.5

    score = 10.0 - temp_penalty - wind_penalty + forecast_mod
    return max(0.0, min(10.0, score))

