"""
SQLAlchemy database models.

This module defines all database models (tables) for the application.
Models represent the structure of data stored in the PostgreSQL database.

Current models:
- User: Stores user preferences and profiles
- WeatherCache: Caches weather data to reduce API calls
- Recommendation: Stores recommendation history
"""
from sqlalchemy import Column, Integer, Float, String, DateTime, JSON, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base


class User(Base):
    """
    User model for storing user preferences and authentication.
    
    Represents a user in the system with authentication credentials and
    personal comfort temperature preference. Used for personalized recommendations.
    
    Attributes:
        id: Primary key, auto-incrementing integer
        username: Unique username (required)
        email: Email address (required, unique)
        password: Password (required, plain text for development only)
        name: User's display name (optional)
        comfort_temperature: Personal comfort temperature in Fahrenheit (default: 70.0)
        saved_latitude: Saved location latitude (optional)
        saved_longitude: Saved location longitude (optional)
        location_name: User-friendly location name (optional)
        clothing_list: List of user's clothing items with ratings (JSON, optional)
        created_at: Timestamp when user was created (auto-set)
        updated_at: Timestamp when user was last updated (auto-updated)
        recommendations: Relationship to Recommendation records (one-to-many)
    """
    __tablename__ = "users"

    # Primary key with auto-increment
    id = Column(Integer, primary_key=True, index=True)
    
    # Authentication fields
    username = Column(String, nullable=False, unique=True, index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    password = Column(String, nullable=False)  # Plain text - DEVELOPMENT ONLY
    
    # User information
    name = Column(String, nullable=True)  # Optional display name
    comfort_temperature = Column(Float, default=70.0, nullable=False)

    # SC3 — per-user asymmetric comfort. Penalty-per-°F on each side of the
    # comfort temperature (cold = below, heat = above). 0.5/0.5 = symmetric.
    cold_penalty_per_degree = Column(Float, default=0.5, nullable=False)
    heat_penalty_per_degree = Column(Float, default=0.5, nullable=False)
    
    # Location settings (optional - legacy single location)
    saved_latitude = Column(Float, nullable=True)  # User's saved location latitude
    saved_longitude = Column(Float, nullable=True)  # User's saved location longitude
    location_name = Column(String, nullable=True)  # User-friendly location name (e.g., "Home", "New York")
    
    # Multiple saved locations — DB1: normalized into the user_saved_locations
    # table (see SavedLocation, relationship `saved_location_rows`). This JSON
    # column is legacy/deprecated; kept only so the migration can read existing
    # data. Responses are now built from the normalized rows.
    saved_locations = Column(JSON, nullable=True, default=list)
    
    # Clothing preferences (stored as JSON)
    # Format: [{"name": "T-Shirt", "category": "base", "warmth_rating": 1}, ...]
    clothing_list = Column(JSON, nullable=True, default=list)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships: One user can have many recommendations
    recommendations = relationship("Recommendation", back_populates="user")

    # DB1: normalized saved locations (ordered by insertion id to preserve the
    # index-based API contract). Cascade so deleting a user removes their rows.
    saved_location_rows = relationship(
        "SavedLocation",
        back_populates="user",
        order_by="SavedLocation.id",
        cascade="all, delete-orphan",
    )


class WeatherCache(Base):
    """
    Cache for weather data to reduce API calls.

    DB2: UNIQUE(latitude, longitude) prevents stampede duplicates and enables UPSERT.
    DB3: Index on expires_at so expiry filter doesn't do a full scan.
    """
    __tablename__ = "weather_cache"
    __table_args__ = (
        UniqueConstraint("latitude", "longitude", name="uq_weather_cache_lat_lon"),
        Index("ix_weather_cache_expires_at", "expires_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    weather_data = Column(JSON, nullable=False)
    cached_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)


class Recommendation(Base):
    """
    Store recommendation history.
    
    Records each clothing recommendation request for analytics and history.
    Stores the location, weather conditions, comfort score, and recommended
    clothing items at the time of the request.
    
    Attributes:
        id: Primary key, auto-incrementing integer
        user_id: Foreign key to User (optional, for future user-specific history)
        latitude: Latitude coordinate of the request
        longitude: Longitude coordinate of the request
        comfort_temperature: Comfort temperature used for the calculation
        weather_data: Weather conditions at time of request (stored as JSON)
        comfort_score: Calculated comfort score
        clothing_recommendations: List of recommended clothing items (stored as JSON)
        created_at: Timestamp when recommendation was created (auto-set)
        user: Relationship to User model (many-to-one, optional)
    """
    __tablename__ = "recommendations"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Optional user association (for future user-specific recommendations)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Location and preferences
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    comfort_temperature = Column(Float, nullable=False)
    
    # Weather and recommendation data (stored as JSON for flexibility)
    weather_data = Column(JSON, nullable=False)  # Weather conditions at time of request
    comfort_score = Column(Float, nullable=False)
    clothing_recommendations = Column(JSON, nullable=False)  # List of recommended items
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships: Many recommendations can belong to one user (optional)
    user = relationship("User", back_populates="recommendations")


class SavedLocation(Base):
    """
    DB1 — a user's saved location, normalized out of the old JSON blob.

    One row per saved location. The B-tree index on (latitude, longitude) makes
    coordinate lookups indexed rather than a full JSON scan.

    Attributes:
        id: Primary key.
        user_id: Owning user (FK, indexed).
        name: User-facing label (unique per user, enforced in the router).
        latitude / longitude: Coordinates.
        color / icon: UI presentation hints (match the frontend's options).
        created_at: Insertion timestamp.
    """
    __tablename__ = "user_saved_locations"
    __table_args__ = (
        Index("ix_user_saved_locations_lat_lon", "latitude", "longitude"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    color = Column(String, nullable=False, default="primary")
    icon = Column(String, nullable=False, default="pin")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="saved_location_rows")

