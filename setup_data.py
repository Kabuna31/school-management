# setup_data.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import School

User = get_user_model()

print("=== SETTING UP DATA ON RENDER ===")

# 1. Create superuser
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(
        username='Admin',
        email='kabunaivan@gmail.com',
        password='admin123'
    )
    print("✅ Superuser created: admin / admin123456")
else:
    print("✅ Superuser already exists")

# 2. Create a default school (optional)
if not School.objects.exists():
    school = School.objects.create(
        name='Default School',
        code='DS001',
        address='123 School Street',
        phone='+1234567890',
        email='school@example.com'
    )
    print(f"✅ School created: {school.name}")
else:
    print("✅ School already exists")

print("=== SETUP COMPLETE ===")