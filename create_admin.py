# create_admin.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

print("=== CREATING ADMIN USER ===")

try:
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser(
            username='admin',
            email='admin@school.com',
            password='admin123456'
        )
        print("✅ Superuser created successfully!")
        print("   Username: admin")
        print("   Password: admin123456")
    else:
        print("✅ Superuser already exists")
        
    # Verify
    admin = User.objects.get(username='admin')
    print(f"✅ Verified: {admin.username} (superuser: {admin.is_superuser})")
    
except Exception as e:
    print(f"❌ Error: {e}")