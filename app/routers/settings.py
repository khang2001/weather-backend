"""
User settings router.

Handles user profile settings including:
- Comfort temperature
- Saved location
- Clothing list management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from app.database.connection import get_db
from app.database.models import User, SavedLocation as SavedLocationModel
from app.security import get_current_user

# Create router for settings endpoints
router = APIRouter(prefix="/settings", tags=["Settings"])


# Schemas
class ClothingItem(BaseModel):
    """Schema for a clothing item."""
    name: str
    category: str  # base, mid, outer, bottom, accessory
    warmth_rating: int = Field(ge=0, le=10, description="Warmth rating 0-10")
    color: Optional[str] = None
    windproof: Optional[bool] = False
    rainproof: Optional[bool] = False
    insulated: Optional[bool] = False


class UserSettingsUpdate(BaseModel):
    """Schema for updating user settings."""
    comfort_temperature: Optional[float] = Field(None, ge=0, le=100)
    cold_penalty_per_degree: Optional[float] = Field(None, ge=0, le=2)  # SC3
    heat_penalty_per_degree: Optional[float] = Field(None, ge=0, le=2)  # SC3
    saved_latitude: Optional[float] = Field(None, ge=-90, le=90)
    saved_longitude: Optional[float] = Field(None, ge=-180, le=180)
    location_name: Optional[str] = None
    clothing_list: Optional[List[Dict[str, Any]]] = None


class UserSettingsResponse(BaseModel):
    """Schema for user settings response."""
    id: int
    username: str
    email: str
    name: Optional[str]
    comfort_temperature: float
    cold_penalty_per_degree: float  # SC3
    heat_penalty_per_degree: float  # SC3
    saved_latitude: Optional[float]
    saved_longitude: Optional[float]
    location_name: Optional[str]
    saved_locations: Optional[List[Dict[str, Any]]]
    clothing_list: Optional[List[Dict[str, Any]]]
    
    class Config:
        from_attributes = True


def _require_owner(user_id: int, current_user: User) -> None:
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def _settings_response(user: User) -> "UserSettingsResponse":
    """Build the settings response, sourcing saved_locations from the normalized
    user_saved_locations rows (DB1) rather than the legacy JSON column. Keeps the
    response shape identical so the frontend is unaffected."""
    return UserSettingsResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        name=user.name,
        comfort_temperature=user.comfort_temperature,
        cold_penalty_per_degree=user.cold_penalty_per_degree,
        heat_penalty_per_degree=user.heat_penalty_per_degree,
        saved_latitude=user.saved_latitude,
        saved_longitude=user.saved_longitude,
        location_name=user.location_name,
        saved_locations=[
            {
                "name": r.name,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "color": r.color,
                "icon": r.icon,
            }
            for r in user.saved_location_rows
        ],
        clothing_list=user.clothing_list or [],
    )


@router.get("/{user_id}", response_model=UserSettingsResponse)
def get_user_settings(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user settings — caller must be the owner."""
    _require_owner(user_id, current_user)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _settings_response(user)


@router.put("/{user_id}", response_model=UserSettingsResponse)
def update_user_settings(
    user_id: int,
    settings: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update user settings — caller must be the owner."""
    _require_owner(user_id, current_user)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Update fields if provided
    if settings.comfort_temperature is not None:
        user.comfort_temperature = settings.comfort_temperature

    if settings.cold_penalty_per_degree is not None:
        user.cold_penalty_per_degree = settings.cold_penalty_per_degree

    if settings.heat_penalty_per_degree is not None:
        user.heat_penalty_per_degree = settings.heat_penalty_per_degree

    if settings.saved_latitude is not None:
        user.saved_latitude = settings.saved_latitude
    
    if settings.saved_longitude is not None:
        user.saved_longitude = settings.saved_longitude
    
    if settings.location_name is not None:
        user.location_name = settings.location_name
    
    if settings.clothing_list is not None:
        user.clothing_list = settings.clothing_list
    
    db.commit()
    db.refresh(user)
    
    return _settings_response(user)


@router.post("/{user_id}/clothing", response_model=UserSettingsResponse)
def add_clothing_item(
    user_id: int,
    item: ClothingItem,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a clothing item — caller must be the owner."""
    _require_owner(user_id, current_user)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Initialize clothing_list if None
    if user.clothing_list is None:
        user.clothing_list = []
    
    # Add new item
    clothing_list = list(user.clothing_list)  # Create a copy
    clothing_list.append(item.dict())
    user.clothing_list = clothing_list
    
    db.commit()
    db.refresh(user)
    
    return _settings_response(user)


@router.delete("/{user_id}/clothing/{item_index}", response_model=UserSettingsResponse)
def delete_clothing_item(
    user_id: int,
    item_index: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a clothing item — caller must be the owner."""
    _require_owner(user_id, current_user)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if user.clothing_list is None or item_index >= len(user.clothing_list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid item index"
        )
    
    # Remove item
    clothing_list = list(user.clothing_list)
    clothing_list.pop(item_index)
    user.clothing_list = clothing_list
    
    db.commit()
    db.refresh(user)
    
    return _settings_response(user)


# Saved Locations Endpoints
class SavedLocation(BaseModel):
    """Schema for a saved location."""
    name: str = Field(..., min_length=1, max_length=50)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    color: str = Field(default="primary")  # primary, success, warning, danger, secondary
    icon: str = Field(default="pin")  # pin, home, work, beach, city, mountain, airport, star, map


@router.post("/{user_id}/locations", response_model=UserSettingsResponse)
def add_saved_location(
    user_id: int,
    location: SavedLocation,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a saved location — caller must be the owner."""
    _require_owner(user_id, current_user)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Names are unique per user (matches the old JSON behavior).
    if any(r.name == location.name for r in user.saved_location_rows):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location with this name already exists"
        )

    db.add(SavedLocationModel(
        user_id=user.id,
        name=location.name,
        latitude=location.latitude,
        longitude=location.longitude,
        color=location.color,
        icon=location.icon,
    ))
    db.commit()
    db.refresh(user)

    return _settings_response(user)


@router.put("/{user_id}/locations/{location_index}", response_model=UserSettingsResponse)
def update_saved_location(
    user_id: int,
    location_index: int,
    location: SavedLocation,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a saved location — caller must be the owner."""
    _require_owner(user_id, current_user)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    rows = user.saved_location_rows  # ordered by id (relationship order_by)
    if location_index < 0 or location_index >= len(rows):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid location index"
        )

    row = rows[location_index]
    row.name = location.name
    row.latitude = location.latitude
    row.longitude = location.longitude
    row.color = location.color
    row.icon = location.icon

    db.commit()
    db.refresh(user)

    return _settings_response(user)


@router.delete("/{user_id}/locations/{location_index}", response_model=UserSettingsResponse)
def delete_saved_location(
    user_id: int,
    location_index: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a saved location — caller must be the owner."""
    _require_owner(user_id, current_user)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    rows = user.saved_location_rows  # ordered by id (relationship order_by)
    if location_index < 0 or location_index >= len(rows):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid location index"
        )

    db.delete(rows[location_index])
    db.commit()
    db.refresh(user)

    return _settings_response(user)

