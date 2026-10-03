#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Loading terrain features..."
python backend/scripts/load_zone_terrain_features.py || echo "Terrain features script failed."

echo "Seeding demo data if database is empty..."
python backend/scripts/seed_demo_data.py || echo "Seeding script failed or skipped (may already be seeded)."

echo "Starting FastAPI server..."
exec uvicorn backend.src.interfaces.http.main:app --host 0.0.0.0 --port 8000
