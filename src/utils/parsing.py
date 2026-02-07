# parsing.py
# Utility functions for parsing wind strings and time helpers

def parse_wind_speed(wind_speed_str):
    """
    Parse wind speed string from NWS API into numeric mph value.
    
    Handles formats like:
    - "5 mph" -> 5.0
    - "10-15 mph" -> 12.5 (average)
    - "calm" -> 0.0
    
    Args:
        wind_speed_str: String representation of wind speed from API
        
    Returns:
        float: Wind speed in mph
    """
    if not wind_speed_str:
        return 0.0
    
    wind_speed_str = str(wind_speed_str).lower().strip()
    
    # Handle "calm" or empty
    if wind_speed_str == "calm" or not wind_speed_str:
        return 0.0
    
    # Remove "mph" suffix if present (Python 3.9+ has removesuffix, fallback for older versions)
    if wind_speed_str.endswith(" mph"):
        wind_speed_str = wind_speed_str[:-4].strip()
    
    # Handle range (e.g., "10-15")
    if "-" in wind_speed_str:
        parts = wind_speed_str.split("-")
        if len(parts) == 2:
            try:
                min_speed = float(parts[0].strip())
                max_speed = float(parts[1].strip())
                return (min_speed + max_speed) / 2.0  # Return average
            except ValueError:
                pass
    
    # Handle single value
    try:
        return float(wind_speed_str)
    except ValueError:
        return 0.0

