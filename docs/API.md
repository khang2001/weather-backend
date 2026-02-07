# API Documentation

## Endpoints

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected"
}
```

### GET /score
Get clothing recommendations based on weather conditions.

**Query Parameters:**
- `latitude` (required): Latitude coordinate (-90 to 90)
- `longitude` (required): Longitude coordinate (-180 to 180)
- `comfort_temperature` (optional): Personal comfort temperature in Fahrenheit (default: 70)

**Response:**
See `shared/schemas/recommendation.json` for the full schema.

### POST /score
Get clothing recommendations via POST request.

**Request Body:**
```json
{
  "latitude": 40.7128,
  "longitude": -74.0060,
  "comfort_temperature": 70
}
```

**Response:**
See `shared/schemas/recommendation.json` for the full schema.

### GET /weather/current
Get current weather conditions for a location.

**Query Parameters:**
- `latitude` (required): Latitude coordinate (-90 to 90)
- `longitude` (required): Longitude coordinate (-180 to 180)

**Response:**
```json
{
  "temp_f": 72.5,
  "wind_mph": 5.0,
  "short_forecast": "sunny",
  "location": "New York, NY",
  "period_start": "12:00 PM EST on October 27, 2025",
  "source": "weather.gov"
}
```








