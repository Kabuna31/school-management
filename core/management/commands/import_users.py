# core/management/commands/import_users.py
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from core.models import User
from core.resources import UserResource
import csv
import os


class Command(BaseCommand):
    help = 'Import users from CSV with password hashing'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to CSV file')
        parser.add_argument('--default-password', type=str, default='password123', 
                          help='Default password for users without password')
        parser.add_argument('--dry-run', action='store_true', 
                          help='Preview import without saving')

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        default_password = options['default_password']
        dry_run = options['dry_run']
        
        if not os.path.exists(csv_file):
            self.stderr.write(f"Error: File '{csv_file}' not found")
            return
        
        self.stdout.write(f"Importing users from: {csv_file}")
        self.stdout.write(f"Default password: {default_password}")
        self.stdout.write(f"Dry run: {dry_run}")
        self.stdout.write("-" * 50)
        
        imported_count = 0
        error_count = 0
        
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                username = row.get('username')
                if not username:
                    self.stderr.write(f"⚠ Skipping row: missing username")
                    error_count += 1
                    continue
                
                # Check if user already exists
                if User.objects.filter(username=username).exists():
                    self.stdout.write(f"⚠ User '{username}' already exists - skipping")
                    error_count += 1
                    continue
                
                # Get password from row or use default
                password = row.get('password', default_password)
                if not password:
                    password = default_password
                
                try:
                    # Prepare user data
                    user_data = {
                        'username': username,
                        'password': make_password(password),
                        'email': row.get('email', ''),
                        'first_name': row.get('first_name', ''),
                        'last_name': row.get('last_name', ''),
                        'role': row.get('role', 'teacher'),
                        'is_active': row.get('is_active', 'True').lower() == 'true',
                        'is_staff': row.get('role', 'teacher') in ['system_admin', 'school_admin'],
                        'is_superuser': row.get('role', '') == 'system_admin',
                    }
                    
                    # Set school if provided
                    school_id = row.get('school')
                    if school_id:
                        try:
                            from core.models import School
                            user_data['school'] = School.objects.get(pk=int(school_id))
                        except (ValueError, School.DoesNotExist):
                            pass
                    
                    if dry_run:
                        self.stdout.write(f"  [DRY RUN] Would create: {username} ({password})")
                    else:
                        user = User.objects.create(**user_data)
                        imported_count += 1
                        self.stdout.write(f"✓ Created: {username} ({password})")
                    
                except Exception as e:
                    self.stderr.write(f"✗ Error creating user '{username}': {e}")
                    error_count += 1
        
        self.stdout.write("-" * 50)
        self.stdout.write(f"Summary: {imported_count} imported, {error_count} errors")