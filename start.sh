#!/usr/bin/env bash
# start.sh — runs on every Render deploy before gunicorn starts

set -e  # exit immediately if any command fails

echo "==> Running migrations..."
python manage.py migrate --noinput

echo "==> Ensuring superuser exists..."
python manage.py ensure_superuser

echo "==> Starting gunicorn..."
exec gunicorn config.wsgi:application \
    --workers 1 \
    --timeout 120 \
    --bind 0.0.0.0:$PORT \
    --log-level info
