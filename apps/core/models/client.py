"""
Модель клиента автосервиса.
"""
import secrets
import uuid

from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone

from .base import BaseModel

AUTH_CODE_TTL_SECONDS = 600  # 10 минут
VERIFICATION_TOKEN_TTL_HOURS = 48

AUTH_CODE_SEND_LIMIT = 3
AUTH_CODE_SEND_WINDOW_SECONDS = 900  # 15 минут
AUTH_CODE_FAIL_LIMIT = 5
AUTH_CODE_FAIL_BLOCK_SECONDS = 900  # 15 минут


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
        blank=True,
        default='',
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

    # Согласия
    consent_personal_data = models.BooleanField(
        default=False,
        verbose_name="Согласие на обработку ПДн",
    )

    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Заметки",
    )

    # --- Авторизация (passwordless) ---
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Email подтверждён",
    )
    verification_token = models.CharField(
        max_length=64,
        blank=True,
        default='',
        verbose_name="Токен подтверждения",
    )
    verification_token_created_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Токен создан",
    )
    auth_code = models.CharField(
        max_length=6,
        blank=True,
        default='',
        verbose_name="Код авторизации",
    )
    auth_code_created_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Код создан",
    )

    # Rate limiting
    auth_code_send_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Отправок кода",
    )
    auth_code_last_send_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Последняя отправка кода",
    )
    auth_code_failed_attempts = models.PositiveIntegerField(
        default=0,
        verbose_name="Неверных попыток кода",
    )
    auth_code_failed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Последний неверный ввод",
    )

    # Мягкая деактивация (только вручную через админ-панель)
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен",
        help_text="Деактивированный клиент не может войти.",
    )

    class Meta:
        """Метаданные модели."""

        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone']),
            models.Index(fields=['email']),
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['is_active', 'email']),
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

    # --- Helpers ---

    @property
    def masked_email(self) -> str:
        """Маскированный email: первая буква + звёздочки + домен."""
        if not self.email or '@' not in self.email:
            return ''
        local, domain = self.email.split('@', 1)
        if len(local) <= 1:
            masked_local = local
        else:
            masked_local = local[0] + '*' * (len(local) - 1)
        return f"{masked_local}@{domain}"

    def can_send_auth_code(self) -> bool:
        """Проверяет, не превышен ли лимит отправок кода."""
        if not self.auth_code_last_send_at:
            return True
        window_start = (
            timezone.now()
            - timezone.timedelta(
                seconds=AUTH_CODE_SEND_WINDOW_SECONDS,
            )
        )
        if self.auth_code_last_send_at < window_start:
            return True
        return self.auth_code_send_count < AUTH_CODE_SEND_LIMIT

    def record_auth_code_send(self) -> None:
        """Фиксирует факт отправки кода."""
        now = timezone.now()
        window_start = (
            now
            - timezone.timedelta(
                seconds=AUTH_CODE_SEND_WINDOW_SECONDS,
            )
        )
        if (
            not self.auth_code_last_send_at
            or self.auth_code_last_send_at < window_start
        ):
            self.auth_code_send_count = 1
        else:
            self.auth_code_send_count += 1
        self.auth_code_last_send_at = now
        self.save(update_fields=[
            'auth_code_send_count',
            'auth_code_last_send_at',
        ])

    def is_auth_code_blocked(self) -> bool:
        """Проверяет, заблокирован ли ввод кода после ошибок."""
        if (
            self.auth_code_failed_attempts < AUTH_CODE_FAIL_LIMIT
        ):
            return False
        if not self.auth_code_failed_at:
            return False
        block_end = (
            self.auth_code_failed_at
            + timezone.timedelta(
                seconds=AUTH_CODE_FAIL_BLOCK_SECONDS,
            )
        )
        return timezone.now() < block_end

    def record_auth_code_failure(self) -> None:
        """Фиксирует неудачную попытку ввода кода."""
        self.auth_code_failed_attempts += 1
        self.auth_code_failed_at = timezone.now()
        self.save(update_fields=[
            'auth_code_failed_attempts',
            'auth_code_failed_at',
        ])

    def reset_auth_code_failures(self) -> None:
        """Сбрасывает счётчик неудачных попыток."""
        self.auth_code_failed_attempts = 0
        self.auth_code_failed_at = None
        self.save(update_fields=[
            'auth_code_failed_attempts',
            'auth_code_failed_at',
        ])

    def generate_verification_token(self) -> str:
        """Создаёт UUID-токен для подтверждения email."""
        token = uuid.uuid4().hex
        self.verification_token = token
        self.verification_token_created_at = timezone.now()
        self.save(update_fields=[
            'verification_token',
            'verification_token_created_at',
        ])
        return token

    def is_verification_token_valid(self) -> bool:
        """Проверяет, не истёк ли токен подтверждения."""
        if not self.verification_token or not self.verification_token_created_at:
            return False
        age = timezone.now() - self.verification_token_created_at
        return age.total_seconds() < VERIFICATION_TOKEN_TTL_HOURS * 3600

    def generate_auth_code(self) -> str:
        """Создаёт 6-значный код для входа."""
        code = f"{secrets.randbelow(1_000_000):06d}"
        self.auth_code = code
        self.auth_code_created_at = timezone.now()
        self.save(update_fields=['auth_code', 'auth_code_created_at'])
        return code

    def verify_auth_code(self, code: str) -> bool:
        """Проверяет код и TTL, учитывая brute-force блокировку."""
        if self.is_auth_code_blocked():
            return False
        if not self.auth_code or not self.auth_code_created_at:
            return False
        if self.auth_code != code:
            self.record_auth_code_failure()
            return False
        age = timezone.now() - self.auth_code_created_at
        if age.total_seconds() > AUTH_CODE_TTL_SECONDS:
            return False
        self.auth_code = ''
        self.auth_code_created_at = None
        self.auth_code_failed_attempts = 0
        self.auth_code_failed_at = None
        self.auth_code_send_count = 0
        self.auth_code_last_send_at = None
        self.save(update_fields=[
            'auth_code', 'auth_code_created_at',
            'auth_code_failed_attempts', 'auth_code_failed_at',
            'auth_code_send_count', 'auth_code_last_send_at',
        ])
        return True
