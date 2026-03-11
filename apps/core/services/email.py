"""
Email-сервис: отправка писем клиентам.

В development: console.EmailBackend (письма выводятся в терминал).
В production: SMTP через настройки EMAIL_* в .env.
"""
import logging
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

if TYPE_CHECKING:
    from apps.core.models import Client

logger = logging.getLogger(__name__)

DEFAULT_FROM_EMAIL = getattr(
    settings, 'DEFAULT_FROM_EMAIL', 'noreply@chernyavskiy-atech.ru'
)


def _send(
    subject: str,
    html_body: str,
    recipient: str,
) -> bool:
    """
    Отправляет email. Возвращает True при успехе.

    Args:
        subject: Тема письма.
        html_body: HTML-содержимое письма.
        recipient: Email получателя.

    Returns:
        True если письмо отправлено, False при ошибке.
    """
    try:
        send_mail(
            subject=subject,
            message=strip_tags(html_body),
            from_email=DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            html_message=html_body,
            fail_silently=False,
        )
        return True
    except Exception:
        logger.error(
            "Ошибка отправки email на %s",
            recipient,
            exc_info=True,
        )
        return False


def send_verification_email(
    client: 'Client',
    request=None,
) -> bool:
    """
    Отправляет письмо с ссылкой подтверждения email.

    Генерирует токен, сохраняет в Client и отправляет письмо.

    Args:
        client: Клиент, которому нужно подтвердить email.
        request: HTTP-запрос (для построения абсолютного URL).

    Returns:
        True если письмо отправлено.
    """
    if not client.email:
        return False

    token = client.generate_verification_token()

    if request:
        base_url = request.build_absolute_uri('/')[:-1]
    else:
        base_url = getattr(
            settings, 'SITE_URL', 'http://127.0.0.1:8000'
        )

    verify_url = f"{base_url}/verify-email/{token}/"

    html_body = render_to_string('email/verify_email.html', {
        'client': client,
        'verify_url': verify_url,
    })

    logger.info(
        "Отправка письма подтверждения на %s (client=%s)",
        client.email, client.pk,
    )
    return _send(
        subject="Подтвердите вашу электронную почту — Chernyavskiy A-Tech",
        html_body=html_body,
        recipient=client.email,
    )


def send_auth_code(client: 'Client') -> bool:
    """
    Генерирует 6-значный код и отправляет на email клиента.

    Args:
        client: Верифицированный клиент.

    Returns:
        True если письмо отправлено.
    """
    if not client.email:
        return False

    code = client.generate_auth_code()

    html_body = render_to_string('email/auth_code.html', {
        'client': client,
        'code': code,
    })

    logger.info(
        "Отправка кода авторизации на %s (client=%s)",
        client.email, client.pk,
    )
    return _send(
        subject="Код для входа — Chernyavskiy A-Tech",
        html_body=html_body,
        recipient=client.email,
    )
