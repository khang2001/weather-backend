"""
Clothing recommendation module.

This module converts temperature deviation and wind conditions into specific clothing recommendations.
It determines the number of layers needed and selects appropriate clothing items from base layers,
mid layers, outer layers, and shells based on temperature deviation from comfort temperature.

The algorithm:
1. Calculates layers based on temperature deviation (1 layer per 20°F below comfort temp)
2. Adds 1 layer for every 5 mph of wind speed
3. Selects appropriate clothing items from each category
4. Ensures windproof outer layer when wind > 15 mph
5. Adds accessories based on temperature thresholds
6. Applies limits to prevent excessive recommendations
"""
import math
from src.config.common import (
    CLOTHING_SCORES,
    AUTO_ACCESSORIES,
    RECOMMENDATION_LIMITS,
    COMFORT_TEMPERATURE
)


def recommend_clothing(comfort_temperature, temperature, wind_speed):
    """
    Convert temperature deviation and wind conditions to clothing recommendations.
    
    Determines appropriate clothing layers based on temperature deviation from comfort
    temperature, adding 1 layer for every 20°F decrease below comfort temperature.
    Wind speed adds 1 layer for every 5 mph (e.g., 5 mph = 1 layer, 10 mph = 2 layers).
    Wind speed above 15 mph ensures a windproof outer layer is selected.
    
    Args:
        comfort_temperature: User's comfort temperature in Fahrenheit (float)
                           Defaults to 70°F if None
        temperature: Current temperature in Fahrenheit (float)
                    Used for layer calculation and accessory recommendations
        wind_speed: Wind speed in miles per hour (float)
                   Adds 1 layer for every 5 mph (e.g., 5 mph = 1 layer, 10 mph = 2 layers)
                   Ensures windproof outer layer when wind > 15 mph
        
    Returns:
        list: Recommended clothing items as dictionaries, each containing:
            - name: Item name (e.g., "tee", "sweater", "light_jacket")
            - score: Warmth score (int)
            - category: Layer category ("base", "mid", "outer", "shell", "accessory")
            - rainproof: Boolean if item is rainproof (optional)
            - windproof: Boolean if item is windproof (optional)
            - insulated: Boolean if item is insulated (optional)
            
    Layer Calculation:
        - Base layers = 1 + floor((comfort_temp - actual_temp) / 20)
        - Wind adjustment = floor(wind_speed / 5) - adds 1 layer per 5 mph
        - Minimum 1 layer, maximum limited by RECOMMENDATION_LIMITS
        
    Example:
        >>> recommend_clothing(70.0, 43.0, 20.0)
        # Temperature deviation: 70 - 43 = 27°F
        # Base layers: 1 + floor(27/20) = 1 + 1 = 2 layers
        # Wind adjustment: floor(20/5) = 4 layers
        # Total: 2 + 4 = 6 layers → [tee, sweater, windproof jacket, ...]
        
        >>> recommend_clothing(70.0, 30.0, 10.0)
        # Temperature deviation: 70 - 30 = 40°F
        # Base layers: 1 + floor(40/20) = 1 + 2 = 3 layers
        # Wind adjustment: floor(10/5) = 2 layers
        # Total: 3 + 2 = 5 layers → [tee, sweater, jacket, ...]
    """
    recommendations = []
    
    # Use default comfort temperature if not provided
    if comfort_temperature is None:
        comfort_temperature = COMFORT_TEMPERATURE
    
    # Calculate base layer count based on temperature deviation
    # Add 1 layer for every 20°F decrease below comfort temperature
    temp_deviation = max(0, comfort_temperature - temperature)
    base_layers_count = 1 + math.floor(temp_deviation / 20)
    
    # Add 1 layer for every 5 mph of wind speed
    wind_adjustment = math.floor(wind_speed / 5)
    warmth_needed = base_layers_count + wind_adjustment
    
    # Ensure minimum of 1 layer
    warmth_needed = max(1, warmth_needed)
    
    # Filter clothing items by category for easier selection
    base_layers = [item for item in CLOTHING_SCORES if item["category"] == "base"]
    mid_layers = [item for item in CLOTHING_SCORES if item["category"] == "mid"]
    outer_layers = [item for item in CLOTHING_SCORES if item["category"] == "outer"]
    shells = [item for item in CLOTHING_SCORES if item["category"] == "shell"]
    
    # Determine if we need a windproof outer layer
    needs_windproof = wind_speed > 15
    
    # Add base layer (always needed if warmth_needed >= 1)
    # Base layer is typically a tee or long-sleeve shirt
    if warmth_needed >= 1:
        recommendations.append(base_layers[0] if base_layers else None)
    
    # Add mid layer if warmth_needed >= 3
    # Mid layer provides additional insulation (e.g., sweater, fleece)
    if warmth_needed >= 3:
        recommendations.append(mid_layers[0] if mid_layers else None)
    
    # Add outer layer if warmth_needed >= 2
    # For 2 layers: base + light outer (windproof if wind > 15)
    # For 3+ layers: base + mid + outer (windproof if wind > 15)
    if warmth_needed >= 2:
        if needs_windproof:
            # Find windproof outer layer (prefer light_jacket if only 2 layers, heavier if more)
            windproof_outer = next(
                (item for item in outer_layers if item.get("windproof")), 
                None
            )
            if windproof_outer:
                recommendations.append(windproof_outer)
            else:
                # Fallback to any outer layer if no windproof available
                recommendations.append(outer_layers[0] if outer_layers else None)
        else:
            # No wind, use appropriate outer layer based on warmth needed
            if warmth_needed >= 4:
                # Use heaviest outer layer for maximum warmth
                recommendations.append(outer_layers[-1] if outer_layers else None)
            else:
                # Use light outer layer for moderate warmth
                recommendations.append(outer_layers[0] if outer_layers else None)
    
    # Add shell for additional protection if warmth_needed >= 4
    # Shell provides extra weather protection (rain/wind)
    if warmth_needed >= 4:
        # Prefer windproof shell if wind is high
        if needs_windproof:
            windproof_shell = next(
                (item for item in shells if item.get("windproof")), 
                None
            )
            if windproof_shell:
                recommendations.append(windproof_shell)
        else:
            # Add rain shell if available
            rain_shell = next((item for item in shells if item.get("rainproof")), None)
            if rain_shell:
                recommendations.append(rain_shell)
    
    # Auto-add accessories based on temperature thresholds
    # Accessories like hat, gloves, scarf are added for very cold temperatures
    for rule in AUTO_ACCESSORIES:
        if temperature < rule["when_temp_below"]:
            for accessory_name in rule["add"]:
                accessory = next((item for item in CLOTHING_SCORES if item["name"] == accessory_name), None)
                # Avoid duplicates
                if accessory and accessory not in recommendations:
                    recommendations.append(accessory)
    
    # Clean up: Remove any None values that may have been added
    recommendations = [r for r in recommendations if r is not None]
    
    # Apply maximum layer limit to prevent excessive recommendations
    # Default limit is 5 layers (base + mid + outer + shell + 1 accessory)
    max_layers = RECOMMENDATION_LIMITS.get("max_layers", 5)
    recommendations = recommendations[:max_layers]
    
    return recommendations

