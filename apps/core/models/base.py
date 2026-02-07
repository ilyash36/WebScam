"""
Базовые модели для проекта.
"""
from django.db import models


class BaseModel(models.Model):
    """Абстрактная базовая модель с полями created_at и updated_at."""
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления",
    )
    
    class Meta:
        """Метаданные модели."""
        
        abstract = True
        ordering = ['-created_at']
