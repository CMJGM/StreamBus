"""
Filtros personalizados para logging de StreamBus
Agrega información del usuario autenticado a los logs
"""
import logging
from threading import local

# Thread-local storage para request actual
_thread_locals = local()


def get_current_request():
    """Obtiene el request actual del thread-local storage"""
    return getattr(_thread_locals, 'request', None)


def set_current_request(request):
    """Guarda el request actual en thread-local storage"""
    _thread_locals.request = request


def clear_current_request():
    """Limpia el request del thread-local storage"""
    if hasattr(_thread_locals, 'request'):
        del _thread_locals.request


class UserFilter(logging.Filter):
    """
    Filtro de logging que agrega el nombre de usuario al log record.

    Formato de salida:
    YYYY-MM-DD HH:MM:SS | username | LEVEL | logger.name | mensaje

    Ejemplo:
    2025-11-22 15:30:45 | admin | INFO | sit.views | Descargando fotos...
    2025-11-22 15:30:46 | AnonymousUser | WARNING | informes.views | Sin permisos
    """

    def filter(self, record):
        """
        Agrega el atributo 'user' al log record.

        Args:
            record: LogRecord object

        Returns:
            bool: True para permitir el log
        """
        request = get_current_request()

        if request and hasattr(request, 'user'):
            # Si hay request y tiene usuario
            if request.user.is_authenticated:
                record.user = request.user.username
            else:
                record.user = 'AnonymousUser'
        else:
            # Sin request (Celery tasks, management commands, etc.)
            record.user = 'system'

        return True
