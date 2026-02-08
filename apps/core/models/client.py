"""
Модель клиента автосервиса.
"""
from django.db import models
from django.core.validators import RegexValidator
from .base import BaseModel


class Client(BaseModel):
    """Клиент автосервиса."""
    
    phone_validator = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Телефон должен быть в формате: '+79991234567'",
    )
    
    first_name = models.CharField(
        max_length=100,
        verbose_name="Имя",
    )
    last_name = models.CharField(
        max_length=100,
        verbose_name="Фамилия",
    )
    middle_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Отчество",
    )
    phone = models.CharField(
        max_length=20,
        unique=True,
        validators=[phone_validator],
        verbose_name="Телефон",
        help_text="Формат: +79991234567",
        error_messages={
            'unique': 'Клиент с таким телефоном уже существует.',
        },
    )
    email = models.EmailField(
        blank=True,
        null=True,
        verbose_name="Email",
    )
    
    # Канал привлечения
    ATTRACTION_CHOICES = [
        ('website', 'Сайт'),
        ('recommendation', 'Рекомендация'),
        ('advertising', 'Реклама'),
        ('walk_in', 'Проходящий мимо'),
        ('other', 'Другое'),
    ]
    
    attraction_channel = models.CharField(
        max_length=50,
        choices=ATTRACTION_CHOICES,
        default='website',
        verbose_name="Канал привлечения",
    )
    
    # Согласия на коммуникацию
    consent_sms = models.BooleanField(
        default=False,
        verbose_name="Согласие на SMS",
    )
    consent_email = models.BooleanField(
        default=False,
        verbose_name="Согласие на Email",
    )
    consent_phone = models.BooleanField(
        default=True,
        verbose_name="Согласие на звонки",
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Заметки",
    )
    
    class Meta:
        """Метаданные модели."""
        
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone']),
            models.Index(fields=['last_name', 'first_name']),
        ]
    
    def __str__(self) -> str:
        """Строковое представление объекта."""
        name = f"{self.first_name} {self.last_name}".strip()
        return f"{name} ({self.phone})"
    
    @property
    def full_name(self) -> str:
        """Полное имя клиента."""
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return " ".join(parts)
