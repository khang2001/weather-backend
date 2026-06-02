"""
Authentication router.

Endpoints:
  POST /auth/register  — create account (password stored as bcrypt hash)
  POST /auth/login     — verify credentials, set httpOnly JWT cookie
  POST /auth/logout    — clear the JWT cookie
  GET  /auth/users     — list users (requires auth)
  GET  /auth/users/{id} — get user by ID (requires auth)
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from typing import List

from app.database.connection import get_db
from app.database.models import User
from app.api.schemas import UserRegister, LoginRequest, UserResponse
from app.security import create_access_token, get_current_user, hash_password, verify_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Cookie settings — keep in one place so login and logout agree
_COOKIE_NAME = "access_token"
_COOKIE_OPTS = dict(httponly=True, secure=True, samesite="none", path="/")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: UserRegister, db: Session = Depends(get_db)):
    """Create a new account. Password is stored as a bcrypt hash."""
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    new_user = User(
        username=user.username,
        email=user.email,
        password=hash_password(user.password),
        comfort_temperature=user.comfort_temperature,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login")
def login(request: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """
    Verify credentials. On success, sets an httpOnly JWT cookie and returns
    non-sensitive user metadata in the body.
    """
    user = db.query(User).filter(User.email == request.email).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found. Please register first.")
    if not verify_password(request.password, user.password):
        raise HTTPException(status_code=401, detail="Incorrect password")

    token = create_access_token(user.id)
    response.set_cookie(key=_COOKIE_NAME, value=token, **_COOKIE_OPTS)

    return {
        "message": "Login successful",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "name": user.name,
            "comfort_temperature": user.comfort_temperature,
        },
    }


@router.post("/logout")
def logout(response: Response):
    """Clear the JWT cookie."""
    response.delete_cookie(key=_COOKIE_NAME, **_COOKIE_OPTS)
    return {"message": "Logged out"}


@router.get("/users", response_model=List[UserResponse])
def get_all_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all users — requires auth."""
    return db.query(User).all()


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user by ID — requires auth."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
