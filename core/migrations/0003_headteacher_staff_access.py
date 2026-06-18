"""
core/migrations/0003_headteacher_staff_access.py

Gives all headteacher users is_staff=True so they can
access the Django admin panel.
"""
from django.db import migrations


def grant_headteacher_staff_access(apps, schema_editor):
    User = apps.get_model('core', 'User')
    updated = User.objects.filter(role='headteacher', is_staff=False).update(is_staff=True)
    if updated:
        print(f"  Granted is_staff=True to {updated} headteacher(s).")


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_remove_system_owner'),
    ]

    operations = [
        migrations.RunPython(
            grant_headteacher_staff_access,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
