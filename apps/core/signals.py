"""
Сигналы для моделей core.
"""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.core.models import BookingRequest, Client

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Client)
def sync_booking_requests_when_email_verified(sender, instance, **kwargs):
    """
    Переводит заявки в «Подтверждена», когда email клиента считается подтверждённым.

    Дублирует шаг из verify_email_view для случая ручной установки
    «Email подтверждён» в админ-панели (без перехода по ссылке).
    """
    if not instance.is_verified:
        return
    updated = (
        BookingRequest.objects.filter(
            client_id=instance.pk,
            status='pending_confirmation',
        ).update(status='confirmed')
    )
    if updated:
        logger.info(
            'Заявки переведены в confirmed после is_verified: '
            'client_id=%s, count=%s',
            instance.pk,
            updated,
        )
