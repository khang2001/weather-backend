"""
Update test user with sample settings including clothing list.

This script adds:
- Saved location (New York City)
- Sample clothing list with realistic warmth ratings
"""
import sys
import os

backend_root = os.path.abspath(os.path.dirname(__file__))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from app.database.connection import SessionLocal
from app.database.models import User

def update_test_user():
    """Update test user with sample settings."""
    db = SessionLocal()
    
    try:
        # Find test user
        user = db.query(User).filter(User.email == "test@example.com").first()
        
        if not user:
            print("❌ Test user not found. Run create_test_user.py first.")
            return
        
        # Sample clothing list with realistic warmth ratings
        # Rating scale: 1 (very light) to 10 (very warm)
        sample_clothing = [
            # Base layers (1-3)
            {"name": "Tank Top", "category": "base", "warmth_rating": 1, "color": "white"},
            {"name": "T-Shirt", "category": "base", "warmth_rating": 2, "color": "blue"},
            {"name": "Long Sleeve Shirt", "category": "base", "warmth_rating": 3, "color": "gray"},
            {"name": "Thermal Underwear", "category": "base", "warmth_rating": 4, "color": "black"},
            
            # Mid layers (4-6)
            {"name": "Light Sweater", "category": "mid", "warmth_rating": 4, "color": "beige"},
            {"name": "Hoodie", "category": "mid", "warmth_rating": 5, "color": "navy"},
            {"name": "Fleece Jacket", "category": "mid", "warmth_rating": 6, "color": "red"},
            {"name": "Heavy Sweater", "category": "mid", "warmth_rating": 7, "color": "green"},
            
            # Outer layers (7-10)
            {"name": "Light Jacket", "category": "outer", "warmth_rating": 5, "color": "khaki"},
            {"name": "Windbreaker", "category": "outer", "warmth_rating": 4, "color": "yellow", "windproof": True},
            {"name": "Rain Jacket", "category": "outer", "warmth_rating": 3, "color": "black", "rainproof": True},
            {"name": "Winter Coat", "category": "outer", "warmth_rating": 9, "color": "black", "insulated": True},
            {"name": "Parka", "category": "outer", "warmth_rating": 10, "color": "olive", "insulated": True, "windproof": True},
            
            # Bottoms (2-8)
            {"name": "Shorts", "category": "bottom", "warmth_rating": 1, "color": "khaki"},
            {"name": "Light Pants", "category": "bottom", "warmth_rating": 3, "color": "blue"},
            {"name": "Jeans", "category": "bottom", "warmth_rating": 4, "color": "denim"},
            {"name": "Thermal Pants", "category": "bottom", "warmth_rating": 6, "color": "black"},
            {"name": "Winter Pants", "category": "bottom", "warmth_rating": 7, "color": "black", "insulated": True},
            
            # Accessories (1-5)
            {"name": "Baseball Cap", "category": "accessory", "warmth_rating": 1, "color": "blue"},
            {"name": "Sunglasses", "category": "accessory", "warmth_rating": 0, "color": "black"},
            {"name": "Light Scarf", "category": "accessory", "warmth_rating": 2, "color": "gray"},
            {"name": "Beanie", "category": "accessory", "warmth_rating": 3, "color": "black"},
            {"name": "Winter Scarf", "category": "accessory", "warmth_rating": 4, "color": "red"},
            {"name": "Gloves", "category": "accessory", "warmth_rating": 4, "color": "black"},
            {"name": "Winter Gloves", "category": "accessory", "warmth_rating": 5, "color": "black", "insulated": True},
        ]
        
        # Update user settings
        user.saved_latitude = 40.7128  # New York City
        user.saved_longitude = -74.0060
        user.location_name = "New York, NY"
        user.clothing_list = sample_clothing
        
        db.commit()
        db.refresh(user)
        
        print("✅ Test user settings updated successfully!")
        print(f"\n📍 Location:")
        print(f"   Name: {user.location_name}")
        print(f"   Coordinates: {user.saved_latitude}, {user.saved_longitude}")
        print(f"\n👕 Clothing Items: {len(user.clothing_list)}")
        print(f"\n   Categories:")
        categories = {}
        for item in user.clothing_list:
            cat = item['category']
            categories[cat] = categories.get(cat, 0) + 1
        for cat, count in categories.items():
            print(f"   - {cat.capitalize()}: {count} items")
        
        print(f"\n🌡️ Comfort Temperature: {user.comfort_temperature}°F")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error updating test user: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    print("Updating test user settings...")
    update_test_user()

