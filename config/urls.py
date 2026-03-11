"""
URL configuration for автосервис project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Брендинг админ-панели Chernyavskiy A-Tech
admin.site.site_header = "Chernyavskiy A-Tech"
admin.site.site_title = "Chernyavskiy A-Tech"
admin.site.index_title = "Панель управления"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.website.urls')),
]

# Статические и медиа файлы для разработки
if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT
    )
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
