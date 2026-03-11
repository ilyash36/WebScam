"""
Middleware для публичного сайта.
"""
from apps.core.models import Client


class ClientAuthMiddleware:
    """
    Добавляет request.client для авторизованных клиентов.

    Загружает Client по session['client_id'] при is_active=True,
    is_verified=True. Очищает session при невалидном client_id.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.client = None
        client_id = request.session.get('client_id')
        if client_id:
            try:
                request.client = Client.objects.get(
                    pk=client_id,
                    is_active=True,
                    is_verified=True,
                )
            except Client.DoesNotExist:
                request.session.pop('client_id', None)
        return self.get_response(request)
