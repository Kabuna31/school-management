#!/bin/bash
set -e

echo "=== Installing dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Collecting static files ==="
python manage.py collectstatic --noinput

echo "=== Running migrations ==="
python manage.py makemigrations
python manage.py migrate --verbosity 3

echo "=== Checking migration status ==="
python manage.py showmigrations

echo "=== Creating superuser ==="
python -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@school.com', 'admin123456') if not User.objects.filter(username='admin').exists() else None"

echo "=== Build completed successfully ==="