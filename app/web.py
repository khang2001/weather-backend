"""
FastAPI main application file.

This module contains the main FastAPI application with all API endpoints.
It handles:
- Health check endpoints
- Weather data retrieval
- Clothing recommendation generation
- User management (optional)

The application integrates with:
- National Weather Service API for weather data
- Scoring algorithms for comfort and clothing recommendations
- PostgreSQL database for data persistence (optional)
"""
import sys
import os

# Add backend root to Python path to enable imports from app and src directories
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional

from app.config import APP_NAME, APP_VERSION
from app.database import get_db, Base, engine
from app.api.schemas import (
    HealthResponse,
    WeatherResponse,
    RecommendationResponse,
    RecommendationRequest,
    CoordinatesRequest,
    UserCreate,
    UserResponse
)
from app.routers import auth, settings
from src.domain.models.weather import Weather
from src.services.scoring.weather_scoring import score_weather
from src.services.scoring.clothing_scoring import recommend_clothing

# Create database tables (in production, use Alembic migrations)
# Wrap in try-except so server can start even if database isn't available
try:
    # Clear metadata cache to ensure fresh table definitions
    Base.metadata.clear()
    # Import models to register them with Base
    from app.database.models import User, WeatherCache, Recommendation
    # Create tables
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created/verified")
except Exception as e:
    print(f"⚠ Warning: Could not create database tables: {e}")
    print("  Server will start, but database features may not work.")

# Initialize FastAPI app
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="API for weather-based clothing recommendations"
)

# CORS middleware (adjust origins for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(settings.router)


# Health Check Endpoint
@app.get("/", response_model=HealthResponse)
@app.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint.
    
    Checks the health status of the API and database connection.
    Useful for monitoring and load balancer health checks.
    
    Args:
        db: Database session dependency (injected by FastAPI)
        
    Returns:
        HealthResponse: Contains status, version, and database connection status
        
    Example:
        GET /health
        Response: {"status": "healthy", "version": "1.0.0", "database": "connected"}
    """
    try:
        # Test database connection with a simple query
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        # Database connection failed, but API is still healthy
        db_status = "disconnected"

    return HealthResponse(
        status="healthy",
        version=APP_VERSION,
        database=db_status
    )


# Score Endpoint (main endpoint for frontend)
@app.get("/score", response_model=RecommendationResponse)
@app.post("/score", response_model=RecommendationResponse)
def get_score(
    latitude: Optional[float] = Query(None, ge=-90, le=90),
    longitude: Optional[float] = Query(None, ge=-180, le=180),
    comfort_temperature: Optional[float] = Query(None, ge=50, le=90),
    request: Optional[RecommendationRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Get clothing recommendations based on weather conditions.
    
    This is the main endpoint used by the frontend. It fetches current weather
    data for the given coordinates, calculates a comfort score, and generates
    appropriate clothing recommendations.
    
    Can be called via GET (query params) or POST (JSON body).
    
    Args:
        latitude: Latitude coordinate (-90 to 90). Required for GET requests.
        longitude: Longitude coordinate (-180 to 180). Required for GET requests.
        comfort_temperature: Optional personal comfort temperature in Fahrenheit (50-90°F).
                           Defaults to 70°F if not provided.
        request: Optional RecommendationRequest object for POST requests.
        db: Database session dependency (injected by FastAPI).
        
    Returns:
        RecommendationResponse: Contains:
            - weather: Current weather conditions (temp, wind, forecast, location)
            - comfort_score: Calculated comfort score (higher = more comfortable)
            - clothing_recommendations: List of recommended clothing items
            - location: Input coordinates
            
    Raises:
        HTTPException 400: If latitude/longitude are missing
        HTTPException 404: If weather data is not available for the location
        HTTPException 500: If there's an error fetching weather or generating recommendations
        
    Example GET:
        GET /score?latitude=40.7128&longitude=-74.0060&comfort_temperature=70
        
    Example POST:
        POST /score
        Body: {"latitude": 40.7128, "longitude": -74.0060, "comfort_temperature": 70}
    """
    # Handle both GET (query params) and POST (body) request formats
    if request:
        lat = request.latitude
        lon = request.longitude
        comfort_temp = request.comfort_temperature
    else:
        if latitude is None or longitude is None:
            raise HTTPException(
                status_code=400,
                detail="latitude and longitude are required"
            )
        lat = latitude
        lon = longitude
        comfort_temp = comfort_temperature
    
    try:
        # Fetch current weather data from National Weather Service API
        weather = Weather(lat, lon)
        if not weather.is_ready():
            raise HTTPException(
                status_code=404,
                detail="Weather data not available for this location"
            )
        
        # Use default comfort temperature if not provided
        if comfort_temp is None:
            from src.config.common import COMFORT_TEMPERATURE
            comfort_temp = COMFORT_TEMPERATURE
        
        # Calculate comfort score based on temperature, wind, and forecast
        # The score considers deviation from comfort temperature and weather conditions
        comfort_score = score_weather(weather, comfort_temperature=comfort_temp)
        
        # Generate clothing recommendations based on temperature deviation and wind
        # Layers are calculated as: 1 + floor((comfort_temp - actual_temp) / 20) + wind_adjustment
        clothing_recs = recommend_clothing(
            comfort_temperature=comfort_temp,
            temperature=weather.get_temperature(),
            wind_speed=weather.get_wind_speed()
        )
        
        # Format clothing items for API response
        # Extract relevant properties from each clothing recommendation
        clothing_items = [
            {
                "name": item["name"],
                "score": item["score"],
                "category": item["category"],
                "rainproof": item.get("rainproof"),
                "windproof": item.get("windproof"),
                "insulated": item.get("insulated")
            }
            for item in clothing_recs
        ]
        
        # Build response
        return RecommendationResponse(
            weather=WeatherResponse(
                temp_f=weather.get_temperature(),
                wind_mph=weather.get_wind_speed(),
                short_forecast=weather.get_short_forecast(),
                location=weather.weather_data.get("location", "Unknown"),
                period_start=weather.get_period_start(),
                source="weather.gov"
            ),
            comfort_score=comfort_score,
            clothing_recommendations=clothing_items,
            location={"latitude": lat, "longitude": lon}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate recommendations: {str(e)}"
        )


# Weather Endpoint
@app.get("/weather/current", response_model=WeatherResponse)
def get_current_weather(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude")
):
    """
    Get current weather conditions for a location.
    
    Fetches raw weather data from the National Weather Service API without
    calculating recommendations. Useful for debugging or displaying weather
    information separately.
    
    Args:
        latitude: Latitude coordinate (-90 to 90). Required.
        longitude: Longitude coordinate (-180 to 180). Required.
        
    Returns:
        WeatherResponse: Contains:
            - temp_f: Temperature in Fahrenheit
            - wind_mph: Wind speed in miles per hour
            - short_forecast: Brief forecast description
            - location: City and state name
            - period_start: Timestamp of the weather period
            - source: Data source (always "weather.gov")
            
    Raises:
        HTTPException 500: If weather data cannot be fetched
        
    Example:
        GET /weather/current?latitude=40.7128&longitude=-74.0060
    """
    try:
        from src.clients.nws_client import get_current_conditions
        
        weather_data = get_current_conditions(latitude, longitude)
        
        return WeatherResponse(
            temp_f=weather_data["temp_f"],
            wind_mph=weather_data["wind_mph"],
            short_forecast=weather_data["short_forecast"],
            location=weather_data["location"],
            period_start=weather_data["period_start"],
            source=weather_data["source"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch weather data: {str(e)}"
        )


# Recommendations Endpoint (alias for /score)
@app.get("/recommendations", response_model=RecommendationResponse)
@app.post("/recommendations", response_model=RecommendationResponse)
def get_recommendations(
    latitude: Optional[float] = Query(None, ge=-90, le=90),
    longitude: Optional[float] = Query(None, ge=-180, le=180),
    comfort_temperature: Optional[float] = Query(None, ge=50, le=90),
    request: Optional[RecommendationRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Alias for /score endpoint.
    
    Provides an alternative endpoint name for getting clothing recommendations.
    Functionally identical to /score endpoint.
    
    Args:
        Same as get_score() function.
        
    Returns:
        Same as get_score() function.
    """
    return get_score(latitude, longitude, comfort_temperature, request, db)


# User Endpoints (optional - for future use)
@app.post("/users", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user.
    
    Creates a user record in the database with their name and comfort temperature.
    This endpoint is optional and reserved for future features like user profiles
    and personalized recommendations.
    
    Args:
        user: UserCreate schema containing name and comfort_temperature
        db: Database session dependency
        
    Returns:
        UserResponse: Created user object with ID and timestamps
        
    Raises:
        HTTPException 500: If database operation fails
        
    Example:
        POST /users
        Body: {"name": "John Doe", "comfort_temperature": 72.0}
    """
    from app.database.models import User
    from sqlalchemy.exc import IntegrityError
    import time
    
    # Ensure we're using the latest model definition
    # Generate username and email from name, making it unique if needed
    base_username = user.name.lower().replace(" ", "_").replace(".", "_")
    username = base_username
    email = f"{username}@example.com"
    
    # Check if username/email already exists and make it unique
    counter = 1
    while db.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first():
        username = f"{base_username}_{counter}"
        email = f"{username}@example.com"
        counter += 1
        # Safety limit to prevent infinite loop
        if counter > 1000:
            raise HTTPException(
                status_code=500,
                detail="Unable to generate unique username. Please try a different name."
            )
    
    # Create new user record with all required fields
    # Retry logic in case of race condition
    max_retries = 5
    for attempt in range(max_retries):
        try:
            db_user = User(
                username=username,
                email=email,
                password="",  # Empty password for non-auth users
                name=user.name,
                comfort_temperature=user.comfort_temperature
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            
            return db_user
        except IntegrityError as e:
            db.rollback()
            # Check if it's a unique constraint violation
            error_str = str(e.orig) if hasattr(e, 'orig') else str(e)
            if 'unique' in error_str.lower() or 'duplicate' in error_str.lower():
                # Try to find a unique username/email
                if attempt < max_retries - 1:
                    # Re-check and increment
                    counter = 1
                    while db.query(User).filter(
                        (User.username == username) | (User.email == email)
                    ).first():
                        username = f"{base_username}_{counter}"
                        email = f"{username}@example.com"
                        counter += 1
                        if counter > 1000:
                            break
                    continue
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Username or email already exists. Please try a different name."
                    )
            else:
                # Other integrity error
                raise HTTPException(
                    status_code=400,
                    detail=f"User creation failed: {error_str}"
                )
    
    # If we get here, all retries failed
    raise HTTPException(
        status_code=500,
        detail="Unable to create user after multiple attempts. Please try again."
    )


@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """
    Get user by ID.
    
    Retrieves a user record from the database by their unique ID.
    
    Args:
        user_id: Unique identifier for the user
        db: Database session dependency
        
    Returns:
        UserResponse: User object with all user information
        
    Raises:
        HTTPException 404: If user with given ID is not found
        
    Example:
        GET /users/1
    """
    from app.database.models import User
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


# Database Test Endpoint - Comprehensive CRUD Testing
@app.get("/db-test")
def test_database_operations(db: Session = Depends(get_db)):
    """
    Comprehensive database connection and CRUD operations test.
    
    This endpoint performs a full suite of database tests:
    1. Connection test (SELECT 1)
    2. CREATE operation (insert test user)
    3. READ operation (retrieve test user)
    4. UPDATE operation (modify test user)
    5. DELETE operation (remove test user)
    
    Based on FastAPI + PostgreSQL integration best practices.
    All operations are performed on temporary test data that is cleaned up.
    
    Returns:
        dict: Test results for each operation
        
    Example:
        GET /db-test
    """
    from app.database.models import User
    from sqlalchemy.exc import SQLAlchemyError
    import time
    
    test_results = {
        "connection": "not_tested",
        "create": "not_tested",
        "read": "not_tested",
        "update": "not_tested",
        "delete": "not_tested",
        "summary": "not_completed"
    }
    
    test_user_id = None
    
    try:
        # TEST 1: Connection Test
        try:
            db.execute(text("SELECT 1"))
            test_results["connection"] = "✅ PASSED - Database connection successful"
        except Exception as e:
            test_results["connection"] = f"❌ FAILED - {str(e)}"
            raise
        
        # TEST 2: CREATE - Insert test user
        try:
            timestamp = int(time.time())
            test_user = User(
                username=f"test_user_{timestamp}",
                email=f"test_{timestamp}@example.com",
                password="test_password",
                name="Test User",
                comfort_temperature=72.0
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
            test_user_id = test_user.id
            test_results["create"] = f"✅ PASSED - Created user with ID {test_user_id}"
        except Exception as e:
            db.rollback()
            test_results["create"] = f"❌ FAILED - {str(e)}"
            raise
        
        # TEST 3: READ - Retrieve test user
        try:
            retrieved_user = db.query(User).filter(User.id == test_user_id).first()
            if retrieved_user and retrieved_user.username == f"test_user_{timestamp}":
                test_results["read"] = f"✅ PASSED - Retrieved user {retrieved_user.username}"
            else:
                test_results["read"] = "❌ FAILED - User data mismatch"
                raise Exception("Retrieved user data does not match")
        except Exception as e:
            test_results["read"] = f"❌ FAILED - {str(e)}"
            raise
        
        # TEST 4: UPDATE - Modify test user
        try:
            retrieved_user.comfort_temperature = 68.0
            retrieved_user.name = "Updated Test User"
            db.commit()
            db.refresh(retrieved_user)
            if retrieved_user.comfort_temperature == 68.0:
                test_results["update"] = "✅ PASSED - Updated user comfort temperature to 68.0"
            else:
                test_results["update"] = "❌ FAILED - Update did not persist"
                raise Exception("Update operation failed to persist")
        except Exception as e:
            db.rollback()
            test_results["update"] = f"❌ FAILED - {str(e)}"
            raise
        
        # TEST 5: DELETE - Remove test user
        try:
            db.delete(retrieved_user)
            db.commit()
            
            # Verify deletion
            deleted_check = db.query(User).filter(User.id == test_user_id).first()
            if deleted_check is None:
                test_results["delete"] = f"✅ PASSED - Deleted user ID {test_user_id}"
            else:
                test_results["delete"] = "❌ FAILED - User still exists after delete"
                raise Exception("Delete operation failed")
        except Exception as e:
            db.rollback()
            test_results["delete"] = f"❌ FAILED - {str(e)}"
            raise
        
        # All tests passed
        test_results["summary"] = "✅ ALL TESTS PASSED - Database is fully operational"
        
    except Exception as e:
        # Cleanup: Try to delete test user if it exists
        try:
            if test_user_id:
                test_user = db.query(User).filter(User.id == test_user_id).first()
                if test_user:
                    db.delete(test_user)
                    db.commit()
        except:
            pass
        
        test_results["summary"] = f"❌ SOME TESTS FAILED - {str(e)}"
    
    finally:
        # Additional database info
        try:
            user_count = db.query(User).count()
            test_results["database_info"] = {
                "total_users": user_count,
                "database_url": "postgresql://postgres:***@localhost:1234/weather_cloth_rec"
            }
        except:
            pass
    
    return test_results




