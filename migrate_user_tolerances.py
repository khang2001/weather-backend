"""
One-time migration (SC3 per-user): add the asymmetric-comfort columns to users.

Adds (idempotent — skips if already present):
- cold_penalty_per_degree (FLOAT, default 0.5, NOT NULL)
- heat_penalty_per_degree (FLOAT, default 0.5, NOT NULL)

The DEFAULT backfills existing rows to the symmetric 0.5/0.5 behavior, so no
user's scores change until they pick a tolerance.

Run once after deploying the model change:
  python migrate_user_tolerances.py
"""
import sys
import os

backend_root = os.path.abspath(os.path.dirname(__file__))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from sqlalchemy import text
from app.database.connection import engine

STATEMENTS = [
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS cold_penalty_per_degree FLOAT NOT NULL DEFAULT 0.5",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS heat_penalty_per_degree FLOAT NOT NULL DEFAULT 0.5",
]


def main():
    with engine.connect() as conn:
        for stmt in STATEMENTS:
            conn.execute(text(stmt))
        conn.commit()
    print("Done: users.cold_penalty_per_degree + heat_penalty_per_degree added (default 0.5).")


if __name__ == "__main__":
    main()
