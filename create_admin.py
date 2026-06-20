# create_admin.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(
        username='Admin',
        email='kabunaivan@gmail.com',
        password='admin123'
    )
    print("✅ Superuser created: admin / admin123456")
else:
    print("✅ Superuser already exists")