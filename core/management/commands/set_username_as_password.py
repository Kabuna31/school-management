from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

User = get_user_model()

class Command(BaseCommand):
    help = 'Set each user\'s password to their username'

    def handle(self, *args, **options):
        users = User.objects.all()
        count = 0
        
        self.stdout.write(f"Processing {users.count()} users...")
        self.stdout.write("-" * 50)
        
        for user in users:
            # Set password to username
            user.password = make_password(user.username)
            user.save()
            count += 1
            self.stdout.write(f"✅ {user.username} → password: {user.username}")
        
        self.stdout.write("-" * 50)
        self.stdout.write(self.style.SUCCESS(f"\n✅ Updated {count} users"))
        self.stdout.write("\n📋 Users and their passwords:")
        for user in User.objects.all():
            self.stdout.write(f"   - {user.username}: password = {user.username}")