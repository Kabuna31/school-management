# check_db.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from django.contrib.auth import get_user_model

User = get_user_model()

print("=== DATABASE CHECK ===")

# Check if tables exist
with connection.cursor() as cursor:
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    tables = cursor.fetchall()
    print(f"Tables found: {len(tables)}")
    for table in tables:
        print(f"  - {table[0]}")

# Check if users exist
users = User.objects.all()
print(f"\nUsers found: {users.count()}")
for user in users:
    print(f"  - {user.username} (superuser: {user.is_superuser})")

if users.count() == 0:
    print("\n⚠️ No users found! Creating superuser...")
    User.objects.create_superuser(
        username='admin',
        email='admin@school.com',
        password='admin123456'
    )
    print("✅ Superuser created: admin / admin123456")