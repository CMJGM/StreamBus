"""
Mixins y decoradores de logging para vistas CBV y FBV
Agregan logging automático a todas las peticiones
"""
import logging
from functools import wraps


class LoggingMixin:
    """
    Mixin que agrega logging automático a todas las vistas basadas en clases.

    Usage:
        class MyView(LoggingMixin, ListView):
            pass

    Logs generados:
        - GET requests: INFO level con usuario y acción
        - POST requests: INFO level con usuario y acción
        - Errores: ERROR level con detalles
    """

    def get_logger(self):
        """Obtiene el logger apropiado para este módulo"""
        module_name = self.__class__.__module__.split('.')[0]
        return logging.getLogger(f'{module_name}.views')

    def get_action_name(self):
        """
        Genera un nombre descriptivo de la acción basado en el nombre de la clase.

        Examples:
            InformeListView -> "accediendo a lista de informes"
            InformeCreateView -> "creando nuevo informe"
            BusUpdateView -> "editando bus"
        """
        class_name = self.__class__.__name__

        # Diccionario de acciones comunes
        actions = {
            'List': 'accediendo a lista',
            'Create': 'creando nuevo',
            'Update': 'editando',
            'Delete': 'eliminando',
            'Detail': 'viendo detalle',
        }

        # Buscar el tipo de acción en el nombre de la clase
        for key, action in actions.items():
            if key in class_name:
                # Extraer el modelo (ej: "Informe" de "InformeListView")
                model_name = class_name.replace('View', '').replace(key, '')
                if model_name:
                    return f"{action} de {model_name.lower()}"
                return action

        # Si no se encuentra, usar nombre de clase simplificado
        return f"accediendo a {class_name.replace('View', '').lower()}"

    def dispatch(self, request, *args, **kwargs):
        """Override dispatch para agregar logging antes de procesar request"""
        logger = self.get_logger()
        action = self.get_action_name()

        # Log de entrada
        if request.user.is_authenticated:
            username = request.user.username
        else:
            username = 'AnonymousUser'

        # Información adicional según el tipo de request
        extra_info = ""
        if 'pk' in kwargs:
            extra_info = f" [ID: {kwargs['pk']}]"
        elif 'slug' in kwargs:
            extra_info = f" [slug: {kwargs['slug']}]"

        logger.info(f"Usuario {username} {action}{extra_info}")

        try:
            response = super().dispatch(request, *args, **kwargs)

            # Log de éxito para POST/PUT/DELETE
            if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                logger.info(f"Usuario {username} completó: {action} [método: {request.method}]")

            return response

        except Exception as e:
            # Log de error
            logger.error(f"Error en {action} por usuario {username}: {str(e)}", exc_info=True)
            raise


class DetailedLoggingMixin(LoggingMixin):
    """
    Mixin con logging más detallado, incluyendo IP y user agent.
    Usar para vistas sensibles (edición, eliminación, etc.)
    """

    def dispatch(self, request, *args, **kwargs):
        logger = self.get_logger()
        action = self.get_action_name()

        # Información adicional
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')[:100]

        username = request.user.username if request.user.is_authenticated else 'AnonymousUser'

        logger.info(
            f"Usuario {username} {action} | IP: {ip} | Method: {request.method}"
        )
        logger.debug(
            f"User-Agent: {user_agent}"
        )

        try:
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(
                f"ERROR en {action} | Usuario: {username} | IP: {ip} | Error: {str(e)}",
                exc_info=True
            )
            raise


def log_view(func):
    """
    Decorador para funciones de vista (FBV - Function-Based Views).
    Agrega logging automático de acceso y errores.

    Usage:
        @log_view
        @login_required
        def mi_vista(request):
            pass

    Logs generados:
        - INFO: Usuario accediendo a la vista
        - ERROR: Errores durante la ejecución
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        # Obtener logger del módulo de la función
        module_name = func.__module__.split('.')[0]
        logger = logging.getLogger(f'{module_name}.views')

        # Obtener información del usuario
        username = request.user.username if request.user.is_authenticated else 'AnonymousUser'

        # Generar nombre descriptivo de la acción
        func_name = func.__name__.replace('_', ' ')

        # Información adicional
        extra_info = ""
        if kwargs:
            if 'pk' in kwargs:
                extra_info = f" [ID: {kwargs['pk']}]"
            elif 'slug' in kwargs:
                extra_info = f" [slug: {kwargs['slug']}]"

        # Log de acceso
        logger.info(f"Usuario {username} accediendo a: {func_name}{extra_info}")

        try:
            response = func(request, *args, **kwargs)

            # Log de POST/PUT/DELETE exitoso
            if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                logger.info(f"Usuario {username} completó: {func_name} [método: {request.method}]")

            return response

        except Exception as e:
            # Log de error
            logger.error(
                f"Error en {func_name} por usuario {username}: {str(e)}",
                exc_info=True
            )
            raise

    return wrapper


def log_view_detailed(func):
    """
    Decorador para funciones de vista con logging detallado (IP, user agent).
    Usar para vistas sensibles.

    Usage:
        @log_view_detailed
        @login_required
        def vista_sensible(request):
            pass
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        module_name = func.__module__.split('.')[0]
        logger = logging.getLogger(f'{module_name}.views')

        username = request.user.username if request.user.is_authenticated else 'AnonymousUser'
        func_name = func.__name__.replace('_', ' ')
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')[:100]

        logger.info(
            f"Usuario {username} accediendo a: {func_name} | IP: {ip} | Method: {request.method}"
        )
        logger.debug(f"User-Agent: {user_agent}")

        try:
            response = func(request, *args, **kwargs)

            if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                logger.info(
                    f"Usuario {username} completó: {func_name} | IP: {ip} | Method: {request.method}"
                )

            return response

        except Exception as e:
            logger.error(
                f"ERROR en {func_name} | Usuario: {username} | IP: {ip} | Error: {str(e)}",
                exc_info=True
            )
            raise

    return wrapper
