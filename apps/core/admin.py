"""
Админ-панель для моделей core.
"""
from django.contrib import admin
from .models import Client, Vehicle, BookingRequest


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    """Админка для клиентов."""

    list_display = [
        'full_name',
        'phone',
        'email',
        'is_verified',
        'is_active',
        'attraction_channel',
        'created_at',
    ]
    list_filter = [
        'is_active',
        'is_verified',
        'attraction_channel',
        'created_at',
    ]
    search_fields = [
        'first_name',
        'last_name',
        'phone',
        'email',
    ]
    readonly_fields = ['created_at', 'updated_at']
    actions = ['deactivate_clients', 'activate_clients']

    fieldsets = (
        ('Основная информация', {
            'fields': (
                'first_name',
                'last_name',
                'middle_name',
                'phone',
                'email',
            ),
        }),
        ('Канал привлечения', {
            'fields': ('attraction_channel',),
        }),
        ('Согласия', {
            'fields': ('consent_personal_data',),
        }),
        ('Статус', {
            'fields': ('is_active', 'is_verified'),
        }),
        ('Дополнительно', {
            'fields': ('notes', 'created_at', 'updated_at'),
        }),
    )

    @admin.action(description="Деактивировать выбранных клиентов")
    def deactivate_clients(self, request, queryset):
        """Мягкая деактивация без удаления данных."""
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f"Деактивировано клиентов: {updated}",
        )

    @admin.action(description="Активировать выбранных клиентов")
    def activate_clients(self, request, queryset):
        """Повторная активация клиентов."""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f"Активировано клиентов: {updated}",
        )


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    """Админка для автомобилей."""
    
    list_display = [
        '__str__',
        'client',
        'year',
        'mileage',
        'created_at',
    ]
    list_filter = ['brand', 'year', 'created_at']
    search_fields = [
        'brand',
        'model',
        'vin',
        'license_plate',
        'client__phone',
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Владелец', {
            'fields': ('client',),
        }),
        ('Основная информация', {
            'fields': ('brand', 'model', 'year', 'color'),
        }),
        ('Идентификация', {
            'fields': ('vin', 'license_plate'),
        }),
        ('Дополнительно', {
            'fields': (
                'mileage',
                'notes',
                'created_at',
                'updated_at',
            ),
        }),
    )


@admin.register(BookingRequest)
class BookingRequestAdmin(admin.ModelAdmin):
    """Админка для заявок на запись."""

    list_display = [
        '__str__',
        'status',
        'client',
        'vehicle',
        'created_at',
    ]
    list_filter = ['status', 'created_at']
    search_fields = [
        'client__first_name',
        'client__phone',
        'vehicle__brand',
        'vehicle__vin',
    ]
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Заявка', {
            'fields': ('client', 'vehicle', 'status'),
        }),
        ('Описание', {
            'fields': ('message',),
        }),
        ('Данные ТС', {
            'fields': (
                'vehicle_passport_number',
                'vehicle_engine_volume',
                'vehicle_engine_power',
            ),
        }),
        ('Мастер', {
            'fields': ('notes',),
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
        }),
    )
