"""
core/management/commands/ensure_superuser.py

Runs migrations, then creates superuser if none exists.
Handles broken partial database states gracefully.
"""
import os
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Ensures database is migrated and superuser exists.'

    def handle(self, *args, **kwargs):
        # Step 1: Check and fix broken migration state
        self._fix_migration_state()

        # Step 2: Run migrations
        self.stdout.write('Running migrations...')
        from django.core.management import call_command
        call_command('migrate', '--noinput', verbosity=1)

        # Step 3: Create superuser if none exists
        self._ensure_superuser()

    def _fix_migration_state(self):
        """
        If django_migrations table exists but core tables don't,
        remove the core migration records so migrate runs them fresh.
        """
        with connection.cursor() as cursor:
            # Check if django_migrations table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'django_migrations'
                )
            """)
            has_migrations_table = cursor.fetchone()[0]

            if not has_migrations_table:
                self.stdout.write('Fresh database — no fix needed.')
                return

            # Check if core_user table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'core_user'
                )
            """)
            has_core_user = cursor.fetchone()[0]

            if not has_core_user:
                self.stdout.write(
                    self.style.WARNING(
                        'Detected broken migration state — '
                        'core tables missing. Clearing core migration records...'
                    )
                )
                # Delete core migration records so migrate reruns them
                cursor.execute(
                    "DELETE FROM django_migrations WHERE app = 'core'"
                )
                self.stdout.write(
                    self.style.SUCCESS('Migration state cleared. Will re-run core migrations.')
                )

    def _ensure_superuser(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        username = os.environ.get('SUPERUSER_USERNAME', 'admin')
        email    = os.environ.get('SUPERUSER_EMAIL',    'admin@school.com')
        password = os.environ.get('SUPERUSER_PASSWORD', 'changeme123')

        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(
                self.style.WARNING(f'Superuser already exists — skipping.')
            )
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'Superuser "{username}" created. Please change the password after first login.'
            )
        )
