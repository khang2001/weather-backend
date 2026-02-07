"""
Add new columns to users table for settings functionality.

Adds:
- saved_latitude (FLOAT)
- saved_longitude (FLOAT)
- location_name (VARCHAR)
- clothing_list (JSON)
"""
import sys
import os

backend_root = os.path.abspath(os.path.dirname(__file__))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from app.database.connection import engine
from sqlalchemy import text

def migrate_user_table():
    """Add new columns to users table."""
    with engine.connect() as conn:
        try:
            print("Adding new columns to users table...")
            
            # Add saved_latitude column
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN saved_latitude FLOAT"))
                conn.commit()
                print("✅ Added saved_latitude column")
            except Exception as e:
                if "already exists" in str(e):
                    print("⚠️  saved_latitude column already exists")
                else:
                    raise
            
            # Add saved_longitude column
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN saved_longitude FLOAT"))
                conn.commit()
                print("✅ Added saved_longitude column")
            except Exception as e:
                if "already exists" in str(e):
                    print("⚠️  saved_longitude column already exists")
                else:
                    raise
            
            # Add location_name column
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN location_name VARCHAR"))
                conn.commit()
                print("✅ Added location_name column")
            except Exception as e:
                if "already exists" in str(e):
                    print("⚠️  location_name column already exists")
                else:
                    raise
            
            # Add clothing_list column (JSON)
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN clothing_list JSON"))
                conn.commit()
                print("✅ Added clothing_list column")
            except Exception as e:
                if "already exists" in str(e):
                    print("⚠️  clothing_list column already exists")
                else:
                    raise
            
            print("\n✅ Migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    migrate_user_table()

