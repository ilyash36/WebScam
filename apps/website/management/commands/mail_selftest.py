"""
Тест текущего EMAIL_BACKEND: при console — письмо в терминал этого же процесса.
"""
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Вызывает send_mail и печатает активный EMAIL_BACKEND."""

    help = (
        'Проверка почты: показывает EMAIL_BACKEND и вызывает send_mail. '
        'При console backend текст письма появится в этом же терминале (stdout).'
    )

    def handle(self, *args, **options):
        self.stdout.write(f'EMAIL_BACKEND = {settings.EMAIL_BACKEND}')
        self.stdout.write(
            'Если backend — console, ниже должен появиться блок «Content-Type: ...»\n',
        )
        send_mail(
            subject='[Chernyavskiy A-Tech] Тест почты',
            message='Тестовое тело письма. Console backend работает.',
            from_email=getattr(
                settings, 'DEFAULT_FROM_EMAIL', 'test@example.com',
            ),
            recipient_list=['test@example.local'],
            fail_silently=False,
        )
        self.stdout.write(
            self.style.SUCCESS(
                'Готово. Если письма не видно — проверьте .env: '
                'закомментируйте EMAIL_BACKEND=smtp или укажите вручную '
                'EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend',
            ),
        )
