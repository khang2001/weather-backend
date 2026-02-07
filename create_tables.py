"""
Create all database tables.

This script creates all database tables defined in the models.
Run this script after setting up the database for the first time.

Usage:
    python create_tables.py
"""
import sys
import os

# Add backend root to Python path
backend_root = os.path.abspath(os.path.dirname(__file__))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from app.database.connection import Base, engine

# Import models explicitly to register them with Base
from app.database.models import User, WeatherCache, Recommendation

def create_tables():
    """Create all database tables."""
    try:
        print("Creating database tables...")
        print(f"Database URL: {os.getenv('DATABASE_URL', 'postgresql://postgres:pukan2001@localhost:1234/weather_cloth_rec')}")
        
        # Don't clear metadata - we need the models registered
        print(f"\nModels registered in Base.metadata: {len(Base.metadata.tables)}")
        for table_name in Base.metadata.tables.keys():
            print(f"  - {table_name}")
        
        # Create all tables
        print("\nCreating tables...")
        Base.metadata.create_all(bind=engine)
        
        print("✅ Database tables created successfully!")
        print("\nVerifying tables in database...")
        
        # Verify tables exist in database
        from sqlalchemy import inspect
        inspector = inspect(engine)
        db_tables = inspector.get_table_names()
        print(f"Tables in database: {db_tables}")
            
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    create_tables()

