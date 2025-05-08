#!/bin/bash
set -e

# PostgreSQL connection details from environment variables
PG_HOST=${PG_HOST:-db}
PG_PORT=${PG_PORT:-5432}
PG_USER=${PG_USER:-gameuser}
PG_DB=${PG_DB:-gamedb}

# Wait for PostgreSQL to be ready with a timeout (e.g., 30 seconds)
echo "Waiting for PostgreSQL to be ready at $PG_HOST:$PG_PORT..."
TIMEOUT=30
COUNT=0
until pg_isready -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB"; do
  echo "PostgreSQL is not ready yet, waiting..."
  sleep 2
  COUNT=$((COUNT + 2))
  if [ "$COUNT" -ge "$TIMEOUT" ]; then
    echo "Error: PostgreSQL did not become ready within $TIMEOUT seconds"
    exit 1
  fi
done
echo "PostgreSQL is ready!"

# Run Alembic migrations
echo "Running Alembic migrations..."
alembic upgrade head

# Start the FastAPI application
echo "Starting Uvicorn server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000