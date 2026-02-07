"""
Simple authentication router - no complex hashing.

WARNING: This is for DEVELOPMENT ONLY. Passwords are stored in plain text.
DO NOT use this in production!
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.connection import get_db
from app.database.models import User
from app.api.schemas import UserRegister, LoginRequest, UserResponse

# Create router for authentication endpoints
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user (simple version - no password hashing).
    
    WARNING: Stores passwords in plain text for development only!
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username already exists
    existing_username = db.query(User).filter(User.username == user.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create new user with plain text password
    new_user = User(
        username=user.username,
        email=user.email,
        password=user.password,  # Plain text - DEVELOPMENT ONLY
        comfort_temperature=user.comfort_temperature
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Simple login - check email and password match.
    
    Returns user info if credentials are correct.
    Shows specific error messages:
    - "User not found" if email doesn't exist
    - "Incorrect password" if password is wrong
    """
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please register first."
        )
    
    # Check password (plain text comparison)
    if user.password != request.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )
    
    # Return user info on successful login
    return {
        "message": "Login successful",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "name": user.name,
            "comfort_temperature": user.comfort_temperature
        }
    }


@router.get("/users", response_model=List[UserResponse])
def get_all_users(db: Session = Depends(get_db)):
    """
    Get all registered users.
    """
    users = db.query(User).all()
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """
    Get user by ID.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user

