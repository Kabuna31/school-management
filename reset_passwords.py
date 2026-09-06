import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import User

# Define passwords for each user
passwords = {
    'mwanika': 'mwanika123',
    'ikoona': 'ikoona123', 
    'kasadha': 'kasadha123',
    'gloria': 'gloria123',
    'isaac': 'isaac123',
    'tabingwa': 'tabingwa123',
    'ngobi': 'ngobi123',
    'nangobi': 'nangobi123',
    'Admin': 'admin123',
}

print("\n" + "="*50)
print("RESETTING PASSWORDS")
print("="*50)

for username, password in passwords.items():
    try:
        user = User.objects.get(username=username)
        user.set_password(password)
        user.save()
        print(f"✅ {username:12} -> {password}")
    except User.DoesNotExist:
        print(f"❌ {username:12} -> User not found")

print("\n" + "="*50)
print("Login Credentials:")
print("-"*50)
for username, password in passwords.items():
    print(f"  {username:12} / {password}")
print("="*50)