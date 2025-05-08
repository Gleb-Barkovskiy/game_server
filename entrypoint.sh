#!/bin/bash
set -e

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h db -p 5432 -U gameuser -d gamedb; do
  echo "PostgreSQL is not ready yet, waiting..."
  sleep 2
done
echo "PostgreSQL is ready!"

# Run Alembic migrations
echo "Running Alembic migrations..."
alembic upgrade head

# Start the FastAPI application
echo "Starting Uvicorn server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000