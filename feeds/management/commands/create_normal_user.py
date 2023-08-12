from django.core.management import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    # Show this when the user types help
    help = "Adds StartUp default feeds"

    def handle(self, *args, **options):
        user = User.objects.create_user('user', password='Sven')
        user.is_superuser = False
        user.is_staff = True
        user.save()