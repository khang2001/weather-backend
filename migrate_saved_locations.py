"""
One-time migration (DB1): normalize users.saved_locations (JSON) into the
user_saved_locations table.

Run once after deploying the SavedLocation model:
  python migrate_saved_locations.py

What it does:
  1. Creates the user_saved_locations table + (latitude, longitude) index if missing
     (via Base.metadata.create_all — only creates what doesn't exist).
  2. Copies each user's JSON saved_locations entries into normalized rows,
     skipping users that already have rows (so it's safe to re-run).

The legacy users.saved_locations JSON column is left in place (now unused by the
API) so this migration stays reversible; drop it in a later cleanup once you're
confident nothing reads it.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.database.connection import engine, SessionLocal, Base
from app.database.models import User, SavedLocation  # noqa: F401  (register tables)


def main():
    # 1. Create the new table + index (no-op if they already exist).
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    migrated_users = 0
    migrated_rows = 0
    try:
        users = db.query(User).all()
        for user in users:
            legacy = user.saved_locations or []
            if not legacy:
                continue
            # Idempotent: skip users that already have normalized rows.
            if user.saved_location_rows:
                continue
            for loc in legacy:
                if not isinstance(loc, dict):
                    continue
                lat, lon = loc.get("latitude"), loc.get("longitude")
                if lat is None or lon is None:
                    continue
                db.add(SavedLocation(
                    user_id=user.id,
                    name=loc.get("name") or "Saved location",
                    latitude=lat,
                    longitude=lon,
                    color=loc.get("color") or "primary",
                    icon=loc.get("icon") or "pin",
                ))
                migrated_rows += 1
            migrated_users += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(f"Done: migrated {migrated_rows} location(s) for {migrated_users} user(s) "
          f"into user_saved_locations.")


if __name__ == "__main__":
    main()
