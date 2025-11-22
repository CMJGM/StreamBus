"""
Middleware personalizado para StreamBus
"""
from .logging_filters import set_current_request, clear_current_request


class LoggingMiddleware:
    """
    Middleware que captura el request actual para que esté disponible
    en los filtros de logging.

    Esto permite que los logs incluyan información del usuario autenticado.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Guardar request en thread-local storage
        set_current_request(request)

        try:
            response = self.get_response(request)
            return response
        finally:
            # Limpiar request después de la respuesta
            clear_current_request()
