# core/management/commands/reset_passwords.py
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from core.models import User


class Command(BaseCommand):
    help = 'Reset passwords for users'

    def add_arguments(self, parser):
        parser.add_argument('--password', type=str, default='password123',
                          help='New password for users')
        parser.add_argument('--users', nargs='+', help='Specific usernames to reset')
        parser.add_argument('--role', type=str, help='Reset passwords for a specific role')
        parser.add_argument('--dry-run', action='store_true', help='Preview without saving')

    def handle(self, *args, **options):
        new_password = options['password']
        specific_users = options.get('users', [])
        role_filter = options.get('role')
        dry_run = options['dry_run']
        
        # Build queryset
        users = User.objects.all()
        
        if specific_users:
            users = users.filter(username__in=specific_users)
        
        if role_filter:
            users = users.filter(role=role_filter)
        
        count = users.count()
        
        if count == 0:
            self.stdout.write("No users found matching criteria")
            return
        
        self.stdout.write(f"Found {count} users to update")
        self.stdout.write(f"New password: {new_password}")
        self.stdout.write(f"Dry run: {dry_run}")
        self.stdout.write("-" * 50)
        
        updated = 0
        for user in users:
            if dry_run:
                self.stdout.write(f"  [DRY RUN] Would reset: {user.username} ({user.role})")
            else:
                user.password = make_password(new_password)
                user.save()
                updated += 1
                self.stdout.write(f"✓ Reset: {user.username} ({user.role})")
        
        self.stdout.write("-" * 50)
        self.stdout.write(f"Updated {updated} users")