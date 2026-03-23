"""
Email-сервис: отправка писем клиентам.

В development: по умолчанию console.EmailBackend (письма в консоль).
Для реальной отправки: EMAIL_BACKEND=smtp + EMAIL_* в .env.
В production: SMTP через настройки EMAIL_* и DEFAULT_FROM_EMAIL в .env.
"""
import logging
from typing import TYPE_CHECKING, Optional

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


def _base_url_for_email(request: Optional[object]) -> str:
    """
    Базовый URL для ссылок в письмах.

    Приоритет: SITE_URL из настроек (reverse-proxy), иначе request, иначе localhost.

    Args:
        request: HTTP-запрос или None.

    Returns:
        URL без завершающего слэша.
    """
    site = getattr(settings, 'SITE_URL', '') or ''
    site = site.strip().rstrip('/')
    if site:
        return site
    if request is not None:
        try:
            return request.build_absolute_uri('/')[:-1]
        except Exception:
            pass
    return 'http://127.0.0.1:8000'


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

    base_url = _base_url_for_email(request)
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
