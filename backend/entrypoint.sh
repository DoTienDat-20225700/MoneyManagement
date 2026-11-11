#!/bin/sh
set -e

echo "[MoneyManagement] Applying database migrations..."
python manage.py migrate --noinput

if [ "${SEED_DEMO:-false}" = "true" ]; then
    echo "[MoneyManagement] Seeding demo data..."
    if [ "${SEED_DEMO_FORCE:-false}" = "true" ]; then
        python manage.py seed_demo --force
    else
        python manage.py seed_demo
    fi
fi

PORT="${PORT:-8008}"
echo "[MoneyManagement] Starting Gunicorn on port ${PORT}..."
exec gunicorn hubSettings.wsgi:application --bind "0.0.0.0:${PORT}" --workers 2

