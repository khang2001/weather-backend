"""
Database connection and session management.

This module sets up SQLAlchemy database connection and provides a session factory
for use with FastAPI dependency injection. It handles:
- Database engine creation with connection pooling
- Session factory for database operations
- Dependency function for FastAPI route handlers
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import DATABASE_URL

# Base class for all database models
# All models should inherit from this Base class
# Must be defined before models import it
Base = declarative_base()

# Create database engine with connection pooling
# pool_pre_ping: Verifies connections are alive before using them (prevents stale connections)
# echo: Set to True to log all SQL queries (useful for debugging)
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using
    echo=False  # Set to True for SQL query logging
)

# Create session factory for database operations
# autocommit=False: Changes require explicit commit
# autoflush=False: Changes are not automatically flushed to database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency function for FastAPI to get database session.
    Use this in route handlers to get a database session.
    
    Usage:
        from fastapi import Depends
        from sqlalchemy.orm import Session
        
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

