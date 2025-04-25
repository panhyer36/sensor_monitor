from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import UserProfile


class Command(BaseCommand):
    help = 'Create UserProfile for all users who don\'t have a profile'

    def handle(self, *args, **kwargs):
        users_without_profile = []
        profiles_created = 0
        
        for user in User.objects.all():
            try:
                # Try to access profile to check if it exists
                user.profile
            except UserProfile.DoesNotExist:
                # If it doesn't exist, create a profile for the user
                UserProfile.objects.create(user=user)
                users_without_profile.append(user.username)
                profiles_created += 1
        
        if profiles_created:
            self.stdout.write(self.style.SUCCESS(f'Successfully created UserProfile for {profiles_created} users: {", ".join(users_without_profile)}'))
        else:
            self.stdout.write(self.style.SUCCESS('All users already have UserProfile, no need to create')) 