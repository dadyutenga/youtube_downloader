#!/bin/bash
set -e

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Start cron daemon for cleanup job
echo "Starting cron daemon..."
service cron start

# Execute the main command
echo "Starting Gunicorn server on port 8090..."
exec "$@"
