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
from app.database.models import User

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
    saved_latitude: Optional[float]
    saved_longitude: Optional[float]
    location_name: Optional[str]
    saved_locations: Optional[List[Dict[str, Any]]]
    clothing_list: Optional[List[Dict[str, Any]]]
    
    class Config:
        from_attributes = True


@router.get("/{user_id}", response_model=UserSettingsResponse)
def get_user_settings(user_id: int, db: Session = Depends(get_db)):
    """
    Get user settings by user ID.
    
    Returns all user settings including location and clothing list.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.put("/{user_id}", response_model=UserSettingsResponse)
def update_user_settings(
    user_id: int,
    settings: UserSettingsUpdate,
    db: Session = Depends(get_db)
):
    """
    Update user settings.
    
    Allows updating:
    - comfort_temperature
    - saved_latitude, saved_longitude, location_name
    - clothing_list
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields if provided
    if settings.comfort_temperature is not None:
        user.comfort_temperature = settings.comfort_temperature
    
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
    
    return user


@router.post("/{user_id}/clothing", response_model=UserSettingsResponse)
def add_clothing_item(
    user_id: int,
    item: ClothingItem,
    db: Session = Depends(get_db)
):
    """
    Add a clothing item to user's wardrobe.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Initialize clothing_list if None
    if user.clothing_list is None:
        user.clothing_list = []
    
    # Add new item
    clothing_list = list(user.clothing_list)  # Create a copy
    clothing_list.append(item.dict())
    user.clothing_list = clothing_list
    
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/{user_id}/clothing/{item_index}", response_model=UserSettingsResponse)
def delete_clothing_item(
    user_id: int,
    item_index: int,
    db: Session = Depends(get_db)
):
    """
    Delete a clothing item from user's wardrobe by index.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
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
    
    return user


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
    db: Session = Depends(get_db)
):
    """
    Add a saved location to user's quick-access list.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Initialize saved_locations if None
    if user.saved_locations is None:
        user.saved_locations = []
    
    # Check if location with same name already exists
    locations = list(user.saved_locations)
    if any(loc.get('name') == location.name for loc in locations):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location with this name already exists"
        )
    
    # Add new location
    locations.append(location.dict())
    user.saved_locations = locations
    
    db.commit()
    db.refresh(user)
    
    return user


@router.put("/{user_id}/locations/{location_index}", response_model=UserSettingsResponse)
def update_saved_location(
    user_id: int,
    location_index: int,
    location: SavedLocation,
    db: Session = Depends(get_db)
):
    """
    Update a saved location by index.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.saved_locations is None or location_index >= len(user.saved_locations):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid location index"
        )
    
    # Update location
    locations = list(user.saved_locations)
    locations[location_index] = location.dict()
    user.saved_locations = locations
    
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/{user_id}/locations/{location_index}", response_model=UserSettingsResponse)
def delete_saved_location(
    user_id: int,
    location_index: int,
    db: Session = Depends(get_db)
):
    """
    Delete a saved location by index.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.saved_locations is None or location_index >= len(user.saved_locations):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid location index"
        )
    
    # Remove location
    locations = list(user.saved_locations)
    locations.pop(location_index)
    user.saved_locations = locations
    
    db.commit()
    db.refresh(user)
    
    return user

