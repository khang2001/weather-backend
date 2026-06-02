"""
One-time migration (DB2 + DB3): add UNIQUE(latitude, longitude) and
an index on expires_at to the weather_cache table.

Run once before deploying Phase 2:
  python migrate_cache_constraints.py

Safe to re-run — each statement is guarded with IF NOT EXISTS.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text
from app.database.connection import engine


STATEMENTS = [
    # DB2 — remove duplicate rows first (keep newest per coordinate pair)
    """
    DELETE FROM weather_cache
    WHERE id NOT IN (
        SELECT DISTINCT ON (latitude, longitude) id
        FROM weather_cache
        ORDER BY latitude, longitude, cached_at DESC
    )
    """,
    # DB2 — add unique constraint (idempotent via DO NOTHING)
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'uq_weather_cache_lat_lon'
        ) THEN
            ALTER TABLE weather_cache
            ADD CONSTRAINT uq_weather_cache_lat_lon UNIQUE (latitude, longitude);
        END IF;
    END $$
    """,
    # DB3 — add index on expires_at
    """
    CREATE INDEX IF NOT EXISTS ix_weather_cache_expires_at
    ON weather_cache (expires_at)
    """,
]


def main():
    with engine.connect() as conn:
        for stmt in STATEMENTS:
            conn.execute(text(stmt.strip()))
        conn.commit()
    print("Done: weather_cache UNIQUE(lat, lon) + expires_at index applied.")


if __name__ == "__main__":
    main()
