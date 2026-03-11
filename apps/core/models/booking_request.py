"""
Модель заявки на запись в автосервис.
"""
from django.db import models

from .base import BaseModel
from .client import Client
from .vehicle import Vehicle


class BookingRequest(BaseModel):
    """Заявка на запись в автосервис."""

    STATUS_CHOICES = [
        ('pending_confirmation', 'Ожидает подтверждения email'),
        ('confirmed', 'Подтверждена'),
        ('in_progress', 'В работе'),
        ('completed', 'Завершена'),
        ('cancelled', 'Отменена'),
    ]

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='booking_requests',
        verbose_name="Клиент",
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='booking_requests',
        verbose_name="Автомобиль",
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='pending_confirmation',
        verbose_name="Статус",
    )

    message = models.TextField(
        blank=True,
        default='',
        verbose_name="Описание проблемы / желаемая услуга",
    )

    vehicle_passport_number = models.CharField(
        max_length=30,
        blank=True,
        default='',
        verbose_name="Паспорт ТС №",
    )
    vehicle_engine_volume = models.CharField(
        max_length=10,
        blank=True,
        default='',
        verbose_name="Объём двигателя, куб.см",
    )
    vehicle_engine_power = models.CharField(
        max_length=30,
        blank=True,
        default='',
        verbose_name="Мощность двигателя, л.с.",
    )

    notes = models.TextField(
        blank=True,
        default='',
        verbose_name="Заметки мастера",
    )

    class Meta:
        """Метаданные модели."""

        verbose_name = "Заявка на запись"
        verbose_name_plural = "Заявки на запись"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client']),
            models.Index(fields=['status']),
        ]

    def __str__(self) -> str:
        """Строковое представление объекта."""
        return (
            f"Заявка #{self.pk} — {self.client.first_name} "
            f"({self.vehicle.brand} {self.vehicle.model})"
        )
