from django.core.management.base import BaseCommand
from core.models import User

class Command(BaseCommand):
    help = 'Creates an admin user'

    def handle(self, *args, **options):
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123',
                role='admin',
                is_active=True,
                approval_status='approved'
            )
            self.stdout.write(self.style.SUCCESS('Successfully created admin user'))
