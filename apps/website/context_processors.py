"""
Context processors для публичного сайта.
"""


def client_context(request):
    """
    Добавляет client в контекст шаблонов.

    Использует request.client, установленный ClientAuthMiddleware.
    """
    return {'client': getattr(request, 'client', None)}
