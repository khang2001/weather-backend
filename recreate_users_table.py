"""
Script to recreate the users table with the updated schema.
This will DROP the existing users table and recreate it with the new structure.

WARNING: This will delete all existing user data!
"""
import sys
import os

# Add backend root to Python path
backend_root = os.path.abspath(os.path.dirname(__file__))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from sqlalchemy import text
from app.database.connection import engine, Base
from app.database.models import User

def recreate_users_table():
    """Drop and recreate the users table."""
    with engine.connect() as conn:
        # Start a transaction
        trans = conn.begin()
        try:
            # Drop the table if it exists (CASCADE to handle foreign keys)
            print("Dropping existing users table...")
            conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
            
            # Recreate the table using SQLAlchemy metadata
            print("Creating new users table...")
            Base.metadata.create_all(bind=engine, tables=[User.__table__])
            
            # Commit the transaction
            trans.commit()
            print("✓ Users table recreated successfully!")
        except Exception as e:
            trans.rollback()
            print(f"✗ Error recreating table: {e}")
            raise

if __name__ == "__main__":
    print("=" * 60)
    print("RECREATING USERS TABLE")
    print("=" * 60)
    print("WARNING: This will delete all existing user data!")
    print()
    
    # Check for --yes flag to skip confirmation
    if "--yes" not in sys.argv:
        try:
            response = input("Are you sure you want to continue? (yes/no): ")
            if response.lower() != "yes":
                print("Cancelled.")
                sys.exit(0)
        except EOFError:
            # If running non-interactively, require --yes flag
            print("Error: Running non-interactively. Use --yes flag to proceed.")
            sys.exit(1)
    
    recreate_users_table()

