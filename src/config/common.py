"""
Common configuration constants.

This module contains shared configuration constants used throughout the application.
These values can be modified to tune the scoring and recommendation algorithms.

Constants include:
- COMFORT_TEMPERATURE: Default comfort temperature for scoring
- FORECAST_SCORES: Scores for different forecast conditions
- CLOTHING_SCORES: Available clothing items with properties
- AUTO_ACCESSORIES: Rules for automatically adding accessories
- RECOMMENDATION_LIMITS: Limits on number of recommendations
"""

# Default comfort temperature in Fahrenheit
# Used as the baseline for temperature scoring
# Users can override this via API parameter (future feature)
COMFORT_TEMPERATURE = 70

# Forecast condition scores
# These scores are added to the temperature score to calculate final comfort score
# Positive scores indicate pleasant conditions, negative scores indicate adverse conditions
# Scores are matched case-insensitively against forecast descriptions from NWS API
FORECAST_SCORES = {
    # ☀️ Excellent conditions (adds to comfort score)
    "sunny": 10,
    "mostly sunny": 8,
    "partly cloudy": 6,

    # ☁️ Neutral to mild discomfort (small impact)
    "mostly cloudy": 3,
    "cloudy": 1,
    "fog": -2,

    # 🌧️ Adverse weather (reduces comfort score)
    "rain": -5,
    "sleet": -6,
    "snow": -7,

    # 🌩️ Severe or dangerous conditions (significant penalty)
    "thunderstorms": -8,
    "heavy rain": -9,
    "heavy snow": -10,
}

# Configuration version for tracking changes
CONFIG_VERSION = "1.0.0"

# Clothing items database
# Each item has a warmth score, category, and optional flags (rainproof, windproof, insulated)
# Warmth scores are roughly additive across layers
# Categories: base (light) → mid (medium) → outer (heavy) → shell (weather protection)
# Edit these values to tune recommendations without changing algorithms
CLOTHING_SCORES = [
    # --- Base layers (1–2 pts) ---
    {"name": "tee",               "score": 1, "category": "base"},
    {"name": "long_sleeve",       "score": 2, "category": "base"},
    {"name": "thermal_base",      "score": 3, "category": "base"},

    # --- Mid layers (2–4 pts) ---
    {"name": "sweater",           "score": 3, "category": "mid"},
    {"name": "fleece",            "score": 3, "category": "mid"},
    {"name": "heavy_sweater",     "score": 4, "category": "mid"},

    # --- Outer layers (3–6 pts) ---
    {"name": "light_jacket",      "score": 3, "category": "outer", "windproof": True},
    {"name": "insulated_jacket",  "score": 5, "category": "outer", "insulated": True},
    {"name": "down_coat",         "score": 6, "category": "outer", "insulated": True},

    # --- Shells (weather protection; small warmth + flags) ---
    {"name": "rain_shell",        "score": 2, "category": "shell", "rainproof": True, "windproof": True},
    {"name": "softshell",         "score": 3, "category": "shell", "windproof": True},

    # --- Accessories (fractional; add on top for extremes) ---
    {"name": "scarf",             "score": 1, "category": "accessory"},
    {"name": "hat",               "score": 1, "category": "accessory"},
    {"name": "gloves",            "score": 1, "category": "accessory"},
    {"name": "thermal_leggings",  "score": 2, "category": "bottom"},
]

# Auto-add accessory rules for extreme temperatures
# These rules automatically add accessories when temperature drops below thresholds
# Rules are evaluated in order, so lower thresholds should come first
# Format: {"when_temp_below": temperature_in_fahrenheit, "add": [list_of_accessory_names]}
AUTO_ACCESSORIES = [
    {"when_temp_below": 32, "add": ["hat", "gloves"]},      # Freezing: add hat and gloves
    {"when_temp_below": 20, "add": ["scarf"]},              # Very cold: add scarf
    {"when_temp_below": 15, "add": ["thermal_leggings"]},    # Extremely cold: add thermal leggings
]

# Recommendation limits to prevent excessive clothing suggestions
# These caps ensure recommendations remain practical and not overwhelming
RECOMMENDATION_LIMITS = {
    "max_layers": 5,         # Maximum total layers (base + mid + outer + shell + 1 accessory)
    "max_accessories": 3     # Maximum number of accessories (currently not enforced)
}

