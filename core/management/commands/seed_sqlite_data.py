import json
import os

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from core.models import Enrollment, Section, Student, Subject, User


class Command(BaseCommand):
    help = "Load sqlite_data.json into an empty deployed database."

    def handle(self, *args, **options):
        fixture_path = settings.BASE_DIR / "sqlite_data.json"

        if not fixture_path.exists():
            raise CommandError(f"Fixture not found: {fixture_path}")

        with fixture_path.open(encoding="utf-8") as fixture_file:
            fixture_data = json.load(fixture_file)

        expected_counts = {
            "core.subject": 0,
            "core.section": 0,
            "core.student": 0,
            "core.enrollment": 0,
        }

        for item in fixture_data:
            model_name = item.get("model")

            if model_name in expected_counts:
                expected_counts[model_name] += 1

        current_counts = {
            "core.subject": Subject.objects.count(),
            "core.section": Section.objects.count(),
            "core.student": Student.objects.count(),
            "core.enrollment": Enrollment.objects.count(),
        }
        force = os.environ.get("SEED_SQLITE_DATA_FORCE", "false").lower() == "true"
        has_full_school_data = all(
            current_counts[model_name] >= expected_count
            for model_name, expected_count in expected_counts.items()
        )

        if has_full_school_data and not force:
            self.stdout.write("School data already matches or exceeds sqlite_data.json; skipping seed.")
            return

        with transaction.atomic():
            self.stdout.write("Loading sqlite_data.json into the database.")
            with connection.constraint_checks_disabled():
                Enrollment.objects.all().delete()
                Student.objects.all().delete()
                Section.objects.all().delete()
                Subject.objects.all().delete()
                User.objects.all().delete()

            call_command("loaddata", str(fixture_path), verbosity=1)
            User.objects.filter(is_active=True).update(email_verified=True)

        self.stdout.write(self.style.SUCCESS("Loaded sqlite_data.json into the database."))
