"""
core/management/commands/ensure_superuser.py

Runs migrations, then creates superuser if none exists.
Works on both PostgreSQL (Render) and SQLite (local).
"""
import os
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection


class Command(BaseCommand):
    help = 'Ensures database is migrated and superuser exists.'

    def handle(self, *args, **kwargs):
        self._fix_migration_state()
        self.stdout.write('Running migrations...')
        call_command('migrate', '--noinput', verbosity=1)
        self._ensure_superuser()

    def _table_exists(self, table_name):
        """Check if a table exists — works on both SQLite and PostgreSQL."""
        db_engine = connection.vendor  # 'sqlite' or 'postgresql'
        with connection.cursor() as cursor:
            if db_engine == 'postgresql':
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = %s
                    )
                """, [table_name])
                return cursor.fetchone()[0]
            else:
                # SQLite
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=%s",
                    [table_name]
                )
                return cursor.fetchone() is not None

    def _fix_migration_state(self):
        """
        If django_migrations exists but core_user doesn't,
        delete core migration records so migrate reruns them.
        """
        if not self._table_exists('django_migrations'):
            self.stdout.write('Fresh database — running all migrations.')
            return

        if not self._table_exists('core_user'):
            self.stdout.write(
                self.style.WARNING(
                    'Broken migration state detected — '
                    'core_user table missing. Clearing core records...'
                )
            )
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM django_migrations WHERE app = 'core'"
                )
            self.stdout.write(self.style.SUCCESS('Cleared. Will re-run core migrations.'))
        else:
            self.stdout.write('Database state OK.')

    def _ensure_superuser(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        username = os.environ.get('SUPERUSER_USERNAME', 'admin')
        email    = os.environ.get('SUPERUSER_EMAIL',    'admin@school.com')
        password = os.environ.get('SUPERUSER_PASSWORD', 'changeme123')

        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(self.style.WARNING('Superuser already exists — skipping.'))
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(
            self.style.SUCCESS(f'Superuser "{username}" created. Change the password after first login.')
        )
