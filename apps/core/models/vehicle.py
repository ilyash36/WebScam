"""
Модель автомобиля клиента.
"""
from django.db import models
from django.core.validators import MinValueValidator
from .base import BaseModel
from .client import Client


class Vehicle(BaseModel):
    """Автомобиль клиента."""
    
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='vehicles',
        verbose_name="Клиент",
    )
    
    brand = models.CharField(
        max_length=100,
        verbose_name="Марка",
    )
    model = models.CharField(
        max_length=100,
        verbose_name="Модель",
    )
    year = models.IntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1900)],
        verbose_name="Год выпуска",
    )
    
    vin = models.CharField(
        max_length=17,
        blank=True,
        null=True,
        unique=True,
        verbose_name="VIN номер",
        help_text="17 символов",
    )
    license_plate = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Госномер",
    )
    
    mileage = models.IntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        verbose_name="Пробег (км)",
    )
    
    color = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Цвет",
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Заметки",
    )
    
    class Meta:
        """Метаданные модели."""
        
        verbose_name = "Автомобиль"
        verbose_name_plural = "Автомобили"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client']),
            models.Index(fields=['vin']),
            models.Index(fields=['license_plate']),
        ]
    
    def __str__(self) -> str:
        """Строковое представление объекта."""
        plate = self.license_plate or 'без номера'
        return f"{self.brand} {self.model} ({plate})"
