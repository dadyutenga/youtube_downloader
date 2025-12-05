#!/bin/bash
set -e

# Ensure data directory exists and has correct permissions
echo "Setting up data directories..."
mkdir -p /app/data /app/downloads /app/logs
chown -R appuser:appgroup /app/data /app/downloads /app/logs 2>/dev/null || true

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Start cron daemon for cleanup job
echo "Starting cron daemon..."
service cron start

# Execute the main command as appuser
echo "Starting Gunicorn server on port 8090..."
exec "$@"
