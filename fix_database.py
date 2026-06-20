# fix_database.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

def fix_schema():
    with connection.cursor() as cursor:
        try:
            cursor.execute("ALTER TABLE core_mark ADD COLUMN term VARCHAR(10) NOT NULL DEFAULT 'Term 1'")
            print("✓ Added column: term")
        except Exception as e:
            print(f"⚠ Column term: {e}")

        try:
            cursor.execute("ALTER TABLE core_mark ADD COLUMN exam VARCHAR(15) NOT NULL DEFAULT 'Mid Term'")
            print("✓ Added column: exam")
        except Exception as e:
            print(f"⚠ Column exam: {e}")

        try:
            cursor.execute("ALTER TABLE core_mark ADD COLUMN mid_term DECIMAL(5,2) DEFAULT 0.00")
            print("✓ Added column: mid_term")
        except Exception as e:
            print(f"⚠ Column mid_term: {e}")

        try:
            cursor.execute("ALTER TABLE core_mark ADD COLUMN end_term DECIMAL(5,2) DEFAULT 0.00")
            print("✓ Added column: end_term")
        except Exception as e:
            print(f"⚠ Column end_term: {e}")

if __name__ == '__main__':
    fix_schema()