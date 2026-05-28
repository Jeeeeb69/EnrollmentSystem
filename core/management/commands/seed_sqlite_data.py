import json
import os

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import Enrollment, Section, Student, Subject, User


class Command(BaseCommand):
    help = "Load sqlite_data.json into an empty deployed database."

    def handle(self, *args, **options):
        fixture_path = settings.BASE_DIR / "sqlite_data.json"

        if not fixture_path.exists():
            raise CommandError(f"Fixture not found: {fixture_path}")

        has_school_data = any([
            Subject.objects.exists(),
            Section.objects.exists(),
            Student.objects.exists(),
            Enrollment.objects.exists(),
        ])
        force = os.environ.get("SEED_SQLITE_DATA_FORCE", "false").lower() == "true"

        if has_school_data and not force:
            self.stdout.write("School data already exists; skipping sqlite_data.json seed.")
            return

        with fixture_path.open(encoding="utf-8") as fixture_file:
            fixture_data = json.load(fixture_file)

        fixture_emails = [
            item["fields"]["email"].lower()
            for item in fixture_data
            if item.get("model") == "core.user" and item.get("fields", {}).get("email")
        ]

        with transaction.atomic():
            if not has_school_data:
                User.objects.filter(email__in=fixture_emails).delete()

            call_command("loaddata", str(fixture_path), verbosity=1)
            User.objects.filter(is_active=True).update(email_verified=True)

        self.stdout.write(self.style.SUCCESS("Loaded sqlite_data.json into the database."))
