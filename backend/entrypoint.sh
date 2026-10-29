#!/bin/sh
set -e

echo "[MoneyManagement] Applying database migrations..."
python manage.py migrate --noinput

echo "[MoneyManagement] Seeding demo data..."
python manage.py seed_demo --force

PORT="${PORT:-8008}"
echo "[MoneyManagement] Starting Gunicorn on port ${PORT}..."
exec gunicorn hubSettings.wsgi:application --bind "0.0.0.0:${PORT}" --workers 2

