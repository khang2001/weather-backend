"""
Create a test user in the database for login testing.

This script creates a test user with:
- Email: test@example.com
- Password: password123
- Username: testuser
- Comfort Temperature: 70°F

Usage:
    python create_test_user.py
"""
import sys
import os

# Add backend root to Python path
backend_root = os.path.abspath(os.path.dirname(__file__))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from app.database.connection import SessionLocal
from app.database.models import User
from sqlalchemy.exc import IntegrityError

def create_test_user():
    """Create a test user in the database."""
    db = SessionLocal()
    
    try:
        # Check if test user already exists
        existing_user = db.query(User).filter(User.email == "test@example.com").first()
        
        if existing_user:
            print("✅ Test user already exists:")
            print(f"   Email: {existing_user.email}")
            print(f"   Username: {existing_user.username}")
            print(f"   Password: password123")
            print(f"   Comfort Temperature: {existing_user.comfort_temperature}°F")
            return
        
        # Create test user
        test_user = User(
            username="testuser",
            email="test@example.com",
            password="password123",  # Plain text for demo
            name="Test User",
            comfort_temperature=70.0
        )
        
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        
        print("✅ Test user created successfully!")
        print(f"   ID: {test_user.id}")
        print(f"   Email: {test_user.email}")
        print(f"   Username: {test_user.username}")
        print(f"   Password: password123")
        print(f"   Name: {test_user.name}")
        print(f"   Comfort Temperature: {test_user.comfort_temperature}°F")
        print("\n🔐 You can now login with these credentials:")
        print("   Email: test@example.com")
        print("   Password: password123")
        
    except IntegrityError as e:
        db.rollback()
        print(f"❌ Error: User with this email or username already exists")
        print(f"   Details: {e}")
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating test user: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    print("Creating test user...")
    create_test_user()

