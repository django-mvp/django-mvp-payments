"""Create the accounts the demo signs in with.

Development only. The demo project is never deployed, and these passwords are
written here in plain sight precisely so nobody mistakes them for real ones.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

PASSWORD = "password"

ACCOUNTS = [
    {"username": "regular.user", "email": "regular.user@example.com"},
    {"username": "staff.user", "email": "staff.user@example.com", "is_staff": True},
    {
        "username": "super.user",
        "email": "super.user@example.com",
        "is_staff": True,
        "is_superuser": True,
    },
]


class Command(BaseCommand):
    """Seed the demo project with one account per role."""

    help = "Create the demo's sign-in accounts, one per role."

    def handle(self, *args, **options):
        """Create each account if it is missing, and reset its password either way."""
        user_model = get_user_model()
        for account in ACCOUNTS:
            username = account["username"]
            user, created = user_model.objects.get_or_create(
                username=username,
                defaults={k: v for k, v in account.items() if k != "username"},
            )
            user.set_password(PASSWORD)
            user.save()
            verb = "created" if created else "reset"
            self.stdout.write(f"{verb} {username} ({account['email']})")
