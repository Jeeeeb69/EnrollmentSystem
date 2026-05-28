import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or update the deployment admin account from ADMIN_EMAIL and ADMIN_PASSWORD."

    def handle(self, *args, **options):
        email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
        password = os.environ.get("ADMIN_PASSWORD", "")

        if not email or not password:
            self.stdout.write("ADMIN_EMAIL or ADMIN_PASSWORD not set; skipping admin seed.")
            return

        User = get_user_model()
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )

        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.clear_activation_code()
        user.save(update_fields=[
            "password",
            "is_staff",
            "is_superuser",
            "is_active",
            "activation_code",
            "activation_code_expires_at",
        ])

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} admin account: {email}"))
