# Backend API

FastAPI backend for weather-based clothing recommendations.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and configure:
```bash
cp .env.example .env
```

3. Run the server:
```bash
uvicorn app.web:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

- `GET /health` - Health check
- `GET /score` - Get clothing recommendations (query params: latitude, longitude, comfort_temperature)
- `POST /score` - Get clothing recommendations (JSON body)
- `GET /weather/current` - Get current weather conditions
- `GET /recommendations` - Alias for `/score`

### Clothing Recommendation Algorithm

The backend uses a temperature deviation-based algorithm to calculate clothing layers:

**Layer Calculation:**
1. **Base Layers**: `1 + floor((comfort_temperature - actual_temperature) / 20)`
   - Adds 1 layer for every 20°F decrease below comfort temperature
   - Minimum 1 layer (base layer)

2. **Wind Adjustment**: Adds 1 layer for every 5 mph of wind speed
   - Formula: `wind_layers = floor(wind_speed / 5)`
   - Examples: 5 mph = 1 layer, 10 mph = 2 layers, 15 mph = 3 layers, 20 mph = 4 layers
   - Ensures windproof outer layer is selected when wind > 15 mph

3. **Layer Selection**:
   - 1 layer: Base layer only (tee)
   - 2 layers: Base + light outer (windproof if wind > 15 mph)
   - 3 layers: Base + mid + outer (windproof if wind > 15 mph)
   - 4+ layers: Base + mid + heavy outer + shell (windproof if wind > 15 mph)

**Example Calculation:**
```
Temperature: 43°F
Wind Speed: 20 mph
Comfort Temperature: 70°F

Temperature deviation: 70 - 43 = 27°F
Base layers: 1 + floor(27/20) = 1 + 1 = 2 layers
Wind adjustment: floor(20/5) = 4 layers
Total layers: 2 + 4 = 6 layers

Result: tee (base) + sweater (mid) + light_jacket (outer, windproof) + additional layers
```

## Development

The backend uses:
- FastAPI for the API framework
- SQLAlchemy for database ORM
- PostgreSQL for the database (configurable via DATABASE_URL)
- National Weather Service (NWS) API for weather data

### Key Components

- **Weather Scoring** (`src/services/scoring/weather_scoring.py`): Calculates comfort scores based on temperature, wind, and forecast
- **Clothing Scoring** (`src/services/scoring/clothing_scoring.py`): Converts temperature deviation and wind conditions into clothing recommendations
- **NWS Client** (`src/clients/nws_client.py`): Fetches real-time weather data from the National Weather Service API
- **Configuration** (`src/config/common.py`): Centralized configuration for comfort temperature, clothing items, and scoring parameters

## Testing

Run tests from the backend directory:
```bash
python -m pytest tests/
```




