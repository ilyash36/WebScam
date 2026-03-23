from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Ядро системы'

    def ready(self) -> None:
        """Подключает сигналы."""
        import apps.core.signals  # noqa: F401
