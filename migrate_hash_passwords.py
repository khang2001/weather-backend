"""
One-time migration: hash all plaintext passwords with bcrypt.

Run once after deploying the S1 auth changes:
  python migrate_hash_passwords.py

Safe to re-run — already-hashed passwords are detected and skipped.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.database.connection import SessionLocal
from app.database.models import User
from app.security import hash_password


def already_hashed(pw: str) -> bool:
    return pw.startswith("$2b$") or pw.startswith("$2a$")


def main():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        migrated = 0
        skipped = 0
        for user in users:
            if already_hashed(user.password):
                skipped += 1
                continue
            user.password = hash_password(user.password)
            migrated += 1
        db.commit()
        print(f"Done: {migrated} passwords hashed, {skipped} already hashed.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
