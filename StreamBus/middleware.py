"""
Middleware personalizado para StreamBus
"""
from .logging_filters import set_current_request, clear_current_request
import logging

logger = logging.getLogger(__name__)


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
        try:
            set_current_request(request)
        except Exception as e:
            # Si falla guardar el request, continuar sin logging de usuario
            logger.warning(f"Error en LoggingMiddleware.set_current_request: {e}")

        try:
            response = self.get_response(request)
            return response
        except Exception as e:
            # Re-lanzar la excepción pero asegurar limpieza
            logger.error(f"Error en LoggingMiddleware durante request: {e}")
            raise
        finally:
            # SIEMPRE limpiar request después de la respuesta
            try:
                clear_current_request()
            except Exception as e:
                logger.warning(f"Error en LoggingMiddleware.clear_current_request: {e}")

