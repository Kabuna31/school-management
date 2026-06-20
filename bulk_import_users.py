# bulk_import_users.py
import os
import django
import csv

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.hashers import make_password
from core.models import User, School

def import_users_from_csv(csv_file, default_password='password123', dry_run=False):
    """Import users from CSV with proper password hashing"""
    
    print("=" * 60)
    print("BULK USER IMPORT")
    print("=" * 60)
    print(f"File: {csv_file}")
    print(f"Default password: {default_password}")
    print(f"Dry run: {dry_run}")
    print("-" * 60)
    
    if not os.path.exists(csv_file):
        print(f"✗ File not found: {csv_file}")
        return
    
    imported = 0
    errors = 0
    skipped = 0
    
    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        # Show headers
        print(f"Headers: {', '.join(reader.fieldnames)}")
        print("-" * 60)
        
        for row in reader:
            username = row.get('username', '').strip()
            if not username:
                print(f"⚠ Skipping row: missing username")
                errors += 1
                continue
            
            # Check if user exists
            if User.objects.filter(username=username).exists():
                print(f"⚠ Skipping: {username} (already exists)")
                skipped += 1
                continue
            
            # Get password
            password = row.get('password', '').strip()
            if not password:
                password = default_password
            
            # Get or create school
            school = None
            school_name = row.get('school_name', '').strip()
            if school_name:
                school, _ = School.objects.get_or_create(
                    name=school_name,
                    defaults={'code': school_name[:10].upper()}
                )
            
            # Prepare user data
            user_data = {
                'username': username,
                'password': make_password(password),
                'email': row.get('email', '').strip(),
                'first_name': row.get('first_name', '').strip(),
                'last_name': row.get('last_name', '').strip(),
                'role': row.get('role', 'teacher').strip(),
                'school': school,
                'is_active': True,
                'is_staff': row.get('role', 'teacher').strip() in ['system_admin', 'school_admin'],
                'is_superuser': row.get('role', '').strip() == 'system_admin',
            }
            
            if dry_run:
                print(f"  [DRY RUN] Would create: {username} | Role: {user_data['role']} | School: {school_name or 'None'}")
            else:
                try:
                    user = User.objects.create(**user_data)
                    imported += 1
                    print(f"✓ Created: {username} | Role: {user_data['role']} | Password: {password}")
                except Exception as e:
                    print(f"✗ Error creating {username}: {e}")
                    errors += 1
    
    print("-" * 60)
    print(f"SUMMARY: Imported: {imported} | Skipped: {skipped} | Errors: {errors}")
    print("=" * 60)

if __name__ == '__main__':
    # Change these values
    CSV_FILE = 'users_import.csv'  # Path to your CSV file
    DEFAULT_PASSWORD = 'password123'  # Default password
    DRY_RUN = False  # Set to True to preview without importing
    
    import_users_from_csv(CSV_FILE, DEFAULT_PASSWORD, DRY_RUN)