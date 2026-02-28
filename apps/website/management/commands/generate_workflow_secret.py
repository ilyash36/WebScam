"""Management command to generate WORKFLOW_OCR_SECRET token."""
import secrets

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Generate a secure random token for WORKFLOW_OCR_SECRET."""

    help = (
        "Генерирует токен для WORKFLOW_OCR_SECRET. "
        "Добавьте вывод в .env и в настройки workflow."
    )

    def handle(self, *args, **options):
        """Generate and print the token."""
        token = secrets.token_urlsafe(32)
        self.stdout.write(
            self.style.SUCCESS(f"WORKFLOW_OCR_SECRET={token}")
        )
        self.stdout.write(
            "\nДобавьте эту строку в .env и тот же токен в настройки "
            "проверки workflow (шаг проверки секрета)."
        )
