"""
Админ-панель для моделей core.
"""
from django.contrib import admin
from .models import Client, Vehicle


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    """Админка для клиентов."""
    
    list_display = [
        'full_name',
        'phone',
        'email',
        'attraction_channel',
        'created_at',
    ]
    list_filter = ['attraction_channel', 'created_at']
    search_fields = [
        'first_name',
        'last_name',
        'phone',
        'email',
    ]
    readonly_fields = ['created_at', 'updated_at']
    
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
        ('Согласия на коммуникацию', {
            'fields': (
                'consent_sms',
                'consent_email',
                'consent_phone',
            ),
        }),
        ('Дополнительно', {
            'fields': ('notes', 'created_at', 'updated_at'),
        }),
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
