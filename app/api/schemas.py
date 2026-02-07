"""
Pydantic schemas for request/response validation.

This module defines all Pydantic models used for API request/response validation.
These schemas ensure type safety and data validation for incoming requests
and outgoing responses.

Schemas include:
- Request schemas: CoordinatesRequest, RecommendationRequest, UserCreate
- Response schemas: WeatherResponse, RecommendationResponse, UserResponse, HealthResponse
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# Request Schemas
class CoordinatesRequest(BaseModel):
    """
    Request schema for latitude/longitude coordinates.
    
    Used for endpoints that require geographic coordinates.
    Validates that coordinates are within valid ranges.
    
    Attributes:
        latitude: Latitude coordinate (-90 to 90 degrees)
        longitude: Longitude coordinate (-180 to 180 degrees)
    """
    latitude: float = Field(..., ge=-90, le=90, description="Latitude (-90 to 90)")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude (-180 to 180)")

    @validator("latitude", "longitude")
    def validate_coordinates(cls, v):
        """Validate that coordinates are within valid range."""
        if abs(v) > 180:
            raise ValueError("Coordinate out of valid range")
        return v


class RecommendationRequest(CoordinatesRequest):
    """
    Request schema for recommendations with optional comfort temperature.
    
    Extends CoordinatesRequest to include optional comfort temperature preference.
    Used by the /score and /recommendations endpoints.
    
    Attributes:
        latitude: Latitude coordinate (-90 to 90 degrees)
        longitude: Longitude coordinate (-180 to 180 degrees)
        comfort_temperature: Optional personal comfort temperature (0-100°F, default: 70)
    """
    comfort_temperature: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
        description="Personal comfort temperature in Fahrenheit (default: 70)"
    )


class UserCreate(BaseModel):
    """
    Schema for creating a user.
    
    Used by POST /users endpoint to create new user records.
    Only name and comfort_temperature are required in the request body.
    Username and email are automatically generated from the name.
    
    Attributes:
        name: User's name (1-100 characters)
        comfort_temperature: Personal comfort temperature (0-100°F, default: 70.0)
    """
    name: str = Field(..., min_length=1, max_length=100, description="User's display name")
    comfort_temperature: float = Field(default=70.0, ge=0, le=100, description="Preferred comfort temperature in Fahrenheit")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "comfort_temperature": 72.0
            }
        }


# Simple Authentication Schemas
class UserRegister(BaseModel):
    """
    Schema for user registration (simple - no hashing).
    
    Attributes:
        username: Unique username (3-50 characters)
        email: Email address (unique)
        password: Password (minimum 3 characters)
        comfort_temperature: Personal comfort temperature (default: 70.0)
    """
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=3)
    comfort_temperature: float = Field(default=70.0, ge=0, le=100)


class LoginRequest(BaseModel):
    """
    Schema for user login.
    
    Attributes:
        email: User's email address
        password: User's password
    """
    email: str
    password: str


# Response Schemas
class WeatherResponse(BaseModel):
    """
    Weather data response schema.
    
    Contains current weather conditions for a location.
    Returned by /weather/current and included in RecommendationResponse.
    
    Attributes:
        temp_f: Temperature in Fahrenheit
        wind_mph: Wind speed in miles per hour
        short_forecast: Brief forecast description (e.g., "mostly sunny")
        location: City and state name (e.g., "New York, NY")
        period_start: Timestamp of the weather period
        source: Data source (always "weather.gov")
    """
    temp_f: float
    wind_mph: float
    short_forecast: str
    location: str
    period_start: str
    source: str = "weather.gov"

    class Config:
        from_attributes = True


class ClothingItem(BaseModel):
    """
    Individual clothing item in recommendations.
    
    Represents a single recommended clothing item with its properties.
    
    Attributes:
        name: Item name (e.g., "tee", "sweater", "light_jacket")
        score: Warmth score (integer)
        category: Layer category ("base", "mid", "outer", "shell", "accessory")
        rainproof: Whether item is rainproof (optional)
        windproof: Whether item is windproof (optional)
        insulated: Whether item is insulated (optional)
    """
    name: str
    score: int
    category: str
    rainproof: Optional[bool] = None
    windproof: Optional[bool] = None
    insulated: Optional[bool] = None


class ComfortScoreBreakdown(BaseModel):
    """
    Breakdown of comfort score components.
    
    Provides detailed breakdown of how the comfort score was calculated.
    Currently not used but reserved for future detailed score reporting.
    
    Attributes:
        temperature_score: Base temperature score
        wind_multiplier: Wind multiplier applied
        forecast_score: Forecast bonus/penalty
        final_score: Final combined comfort score
    """
    temperature_score: float
    wind_multiplier: float
    forecast_score: float
    final_score: float


class RecommendationResponse(BaseModel):
    """
    Full recommendation response schema.
    
    Main response schema for /score and /recommendations endpoints.
    Contains weather data, comfort score, and clothing recommendations.
    
    Attributes:
        weather: Current weather conditions (WeatherResponse)
        comfort_score: Calculated comfort score (float, higher = more comfortable)
        score_breakdown: Optional detailed breakdown of score components
        clothing_recommendations: List of recommended clothing items
        location: Input coordinates as dict {"latitude": float, "longitude": float}
    """
    weather: WeatherResponse
    comfort_score: float
    score_breakdown: Optional[ComfortScoreBreakdown] = None
    clothing_recommendations: List[ClothingItem]
    location: Dict[str, float]  # {"latitude": float, "longitude": float}


class UserResponse(BaseModel):
    """
    User response schema.
    
    Returned by user endpoints (GET /users/{id}, POST /users).
    
    Attributes:
        id: User's unique identifier
        username: User's username
        email: User's email address
        name: User's display name (optional)
        comfort_temperature: User's preferred comfort temperature
        created_at: Timestamp when user was created
    """
    id: int
    username: str
    email: str
    name: Optional[str] = None
    comfort_temperature: float
    created_at: datetime

    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    """
    Health check response schema.
    
    Returned by /health endpoint to indicate API and database status.
    
    Attributes:
        status: API status (typically "healthy")
        version: Application version string
        database: Database connection status ("connected" or "disconnected")
    """
    status: str = "healthy"
    version: str
    database: str = "connected"

