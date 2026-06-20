from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Create admin user'

    def handle(self, *args, **options):
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@school.com',
                password='admin123456'
            )
            self.stdout.write(self.style.SUCCESS('✅ Admin created'))
        else:
            self.stdout.write(self.style.WARNING('⚠️ Admin exists'))