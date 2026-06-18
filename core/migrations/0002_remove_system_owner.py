"""
core/migrations/0002_remove_system_owner.py

Migrates any existing users with role='system_owner' to role='system_admin',
then updates the role field choices to remove system_owner.

Run with: python manage.py migrate
"""
from django.db import migrations, models


def merge_system_owner_into_admin(apps, schema_editor):
    User = apps.get_model('core', 'User')
    updated = User.objects.filter(role='system_owner').update(role='system_admin')
    if updated:
        print(f"  Migrated {updated} system_owner user(s) to system_admin.")


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        # Step 1: convert any existing system_owner rows to system_admin
        migrations.RunPython(
            merge_system_owner_into_admin,
            reverse_code=migrations.RunPython.noop,
        ),
        # Step 2: update the field choices (no DB column change needed —
        # choices are only enforced at the Django form/validation level)
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('system_admin',   'System Admin'),
                    ('headteacher',    'School Administrator'),
                    ('bursar',         'School Bursar'),
                    ('nurse',          'School Nurse'),
                    ('librarian',      'School Librarian'),
                    ('lab_technician', 'Lab Technician'),
                    ('dos',            'Director of Studies'),
                    ('class_teacher',  'Class Teacher'),
                    ('teacher',        'Teacher'),
                    ('parent',         'Parent'),
                    ('student',        'Student'),
                ],
                default='teacher',
                max_length=20,
            ),
        ),
    ]
