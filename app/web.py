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
import logging

# Add backend root to Python path to enable imports from app and src directories
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from datetime import datetime, timedelta, timezone

import pybreaker
from fastapi import APIRouter, BackgroundTasks, FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from typing import Optional

logger = logging.getLogger(__name__)

from app.config import APP_NAME, APP_VERSION
from app.database import get_db, Base, engine
from app.database.connection import SessionLocal
from app.database.models import WeatherCache
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
from src.clients.nws_client import get_current_conditions
from src.domain.models.weather import Weather
from src.services.scoring.weather_scoring import score_weather
from src.services.scoring.clothing_scoring import recommend_clothing

CACHE_TTL_MINUTES = 15


def _cache_lookup(db: Session, lat: float, lon: float):
    """Return a fresh WeatherCache row or None."""
    return (
        db.query(WeatherCache)
        .filter(
            WeatherCache.latitude == lat,
            WeatherCache.longitude == lon,
            WeatherCache.expires_at > datetime.now(timezone.utc),
        )
        .order_by(WeatherCache.cached_at.desc())
        .first()
    )


def _cache_upsert(db: Session, lat: float, lon: float, data: dict) -> None:
    """UPSERT weather data into cache with a 15-min TTL."""
    now = datetime.now(timezone.utc)
    stmt = (
        pg_insert(WeatherCache)
        .values(
            latitude=lat,
            longitude=lon,
            weather_data=data,
            cached_at=now,
            expires_at=now + timedelta(minutes=CACHE_TTL_MINUTES),
        )
        .on_conflict_do_update(
            constraint="uq_weather_cache_lat_lon",
            set_={
                "weather_data": data,
                "cached_at": now,
                "expires_at": now + timedelta(minutes=CACHE_TTL_MINUTES),
            },
        )
    )
    db.execute(stmt)
    db.commit()


def _save_recommendation(
    lat: float,
    lon: float,
    comfort_temp: float,
    weather_data: dict,
    comfort_score: float,
    clothing_items: list,
    user_id: Optional[int] = None,
) -> None:
    """A3 — persist a Recommendation row (history). Runs as a fire-and-forget
    BackgroundTask, so it opens its OWN session: by the time it executes, the
    request-scoped session has already been closed. Failures are logged and
    swallowed so history-write problems never surface to the user."""
    from app.database.models import Recommendation

    db = None
    try:
        db = SessionLocal()
        db.add(
            Recommendation(
                user_id=user_id,
                latitude=lat,
                longitude=lon,
                comfort_temperature=comfort_temp,
                weather_data=weather_data,
                comfort_score=comfort_score,
                clothing_recommendations=clothing_items,
            )
        )
        db.commit()
    except Exception:
        logger.exception("Failed to persist recommendation history for lat=%s lon=%s", lat, lon)
        if db is not None:
            db.rollback()
    finally:
        if db is not None:
            db.close()


# Create database tables (in production, use Alembic migrations)
# Wrap in try-except so server can start even if database isn't available
try:
    # Import models to register them on Base.metadata, then create tables.
    # NOTE: do NOT call Base.metadata.clear() here — models are already imported
    # (via app.database package init), so a clear() empties the registry and the
    # cached re-import does not re-populate it, leaving create_all() a silent no-op.
    from app.database.models import User, WeatherCache, Recommendation  # noqa: F401
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

# S3 — CORS locked to the deployed frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://khang2001.github.io"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# F2 — catch any unhandled exception; log server-side, return generic body
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# D3 — API versioning. Business routes attach to this router, which is mounted
# twice at the bottom of the file: legacy unprefixed (e.g. /score) AND under /v1
# (e.g. /v1/score). Health/root stay on `app` directly and are never versioned —
# load-balancer probes target a stable, unversioned path.
api_router = APIRouter()


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


# Score Endpoint — POST only (D1), canonical scoring route (D2), cache-first (A1, A2, A4)
@api_router.post("/score", response_model=RecommendationResponse)
async def get_score(
    background_tasks: BackgroundTasks,
    request: Optional[RecommendationRequest] = None,
    db: Session = Depends(get_db),
):
    # Coordinates come from the JSON body. A missing body is a client error.
    if request is None:
        raise HTTPException(status_code=400, detail="latitude and longitude are required")
    lat, lon, comfort_temp = request.latitude, request.longitude, request.comfort_temperature
    cold_penalty = request.cold_penalty_per_degree
    heat_penalty = request.heat_penalty_per_degree

    if comfort_temp is None:
        from src.config.common import COMFORT_TEMPERATURE
        comfort_temp = COMFORT_TEMPERATURE

    try:
        # A2 — cache lookup
        cached = _cache_lookup(db, lat, lon)
        if cached:
            weather_raw = cached.weather_data
        else:
            # A1 — async NWS fetch (A4: circuit breaker inside get_current_conditions)
            weather_raw = await get_current_conditions(lat, lon)
            _cache_upsert(db, lat, lon, weather_raw)

    except pybreaker.CircuitBreakerError:
        raise HTTPException(status_code=503, detail="Weather service temporarily unavailable")
    except Exception:
        logger.exception("NWS fetch failed for lat=%s lon=%s", lat, lon)
        raise HTTPException(status_code=503, detail="Weather service temporarily unavailable")

    weather = Weather.from_cache(weather_raw, lat, lon)
    if not weather.is_ready():
        raise HTTPException(status_code=404, detail="Weather data not available for this location")

    comfort_score = score_weather(
        weather,
        comfort_temperature=comfort_temp,
        cold_penalty_per_degree=cold_penalty,
        heat_penalty_per_degree=heat_penalty,
    )
    clothing_recs = recommend_clothing(
        comfort_temperature=comfort_temp,
        temperature=weather.get_temperature(),
        wind_speed=weather.get_wind_speed(),
    )
    clothing_items = [
        {
            "name": item["name"],
            "score": item["score"],
            "category": item["category"],
            "rainproof": item.get("rainproof"),
            "windproof": item.get("windproof"),
            "insulated": item.get("insulated"),
        }
        for item in clothing_recs
    ]

    # A3 — record history fire-and-forget; runs after the response, adds no latency.
    background_tasks.add_task(
        _save_recommendation,
        lat,
        lon,
        comfort_temp,
        weather_raw,
        comfort_score,
        clothing_items,
    )

    return RecommendationResponse(
        weather=WeatherResponse(
            temp_f=weather.get_temperature(),
            wind_mph=weather.get_wind_speed(),
            short_forecast=weather.get_short_forecast(),
            location=weather_raw.get("location", "Unknown"),
            period_start=weather.get_period_start(),
            source="weather.gov",
        ),
        comfort_score=comfort_score,
        clothing_recommendations=clothing_items,
        location={"latitude": lat, "longitude": lon},
    )


# Weather Endpoint — async (A1)
@api_router.get("/weather/current", response_model=WeatherResponse)
async def get_current_weather(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
):
    try:
        data = await get_current_conditions(latitude, longitude)
        return WeatherResponse(
            temp_f=data["temp_f"],
            wind_mph=data["wind_mph"],
            short_forecast=data["short_forecast"],
            location=data["location"],
            period_start=data["period_start"],
            source=data["source"],
        )
    except pybreaker.CircuitBreakerError:
        raise HTTPException(status_code=503, detail="Weather service temporarily unavailable")
    except Exception:
        logger.exception("Error in /weather/current for lat=%s lon=%s", latitude, longitude)
        raise HTTPException(status_code=500, detail="Internal server error")


# D2 — the legacy /recommendations duplicate was removed; /score is the single
# canonical scoring route. (History persistence will be a separate route under A3.)


# User Endpoints (optional - for future use)
@api_router.post("/users", response_model=UserResponse)
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
                logger.exception("Unexpected IntegrityError creating user %s", base_username)
                raise HTTPException(status_code=400, detail="User creation failed")
    
    # If we get here, all retries failed
    raise HTTPException(
        status_code=500,
        detail="Unable to create user after multiple attempts. Please try again."
    )


@api_router.get("/users/{user_id}", response_model=UserResponse)
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
@api_router.get("/db-test")
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


# D3 — Dual-mount every business route under both the legacy unprefixed path and
# /v1, so the frontend can migrate to /v1 without breaking the live deployment.
# Legacy mounts can be removed once nothing depends on them.
for _prefix in ("", "/v1"):
    app.include_router(api_router, prefix=_prefix)
    app.include_router(auth.router, prefix=_prefix)
    app.include_router(settings.router, prefix=_prefix)

