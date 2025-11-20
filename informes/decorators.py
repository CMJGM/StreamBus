"""
Decoradores de seguridad para vistas de informes.

Estos decoradores se encargan de:
- Registrar acciones sensibles en logs de auditoría
- Verificar permisos de acceso a sucursales
"""

from functools import wraps
import logging
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from .models import Informe, FotoInforme, VideoInforme

logger = logging.getLogger('informes.security')


def check_sucursal_access(view_func):
    """
    Decorador para verificar que el usuario tenga acceso a la sucursal del informe.

    Requiere que la vista reciba 'pk' (para Informe) o 'foto_id'/'video_id'.
    El usuario debe estar autenticado (@login_required).

    Uso:
        @login_required
        @check_sucursal_access
        def cargar_fotos(request, pk):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = request.user
        informe = None

        # Determinar el informe según el parámetro
        if 'pk' in kwargs:
            informe = get_object_or_404(Informe, pk=kwargs['pk'])
        elif 'foto_id' in kwargs:
            foto = get_object_or_404(FotoInforme, id=kwargs['foto_id'])
            informe = foto.informe
        elif 'video_id' in kwargs:
            video = get_object_or_404(VideoInforme, id=kwargs['video_id'])
            informe = video.informe

        if not informe:
            logger.warning(
                f"check_sucursal_access: No informe found. "
                f"user={user.username}, kwargs={kwargs}"
            )
            messages.error(request, "Informe no encontrado")
            return redirect('/')

        # Verificar acceso a sucursal
        if hasattr(user, 'profile'):
            profile = user.profile

            # Si puede ver todas las sucursales, permitir acceso
            if profile.puede_ver_todas:
                return view_func(request, *args, **kwargs)

            # Verificar si tiene acceso a esta sucursal específica
            if not profile.tiene_acceso_sucursal(informe.sucursal):
                logger.warning(
                    f"Acceso denegado a sucursal: user={user.username}, "
                    f"sucursal={informe.sucursal.descripcion}, informe_id={informe.id}"
                )
                messages.error(
                    request,
                    f"No tienes permisos para acceder a elementos de la sucursal {informe.sucursal.descripcion}"
                )
                return redirect('/')
        else:
            logger.error(
                f"Usuario sin perfil: user={user.username}"
            )
            messages.error(request, "No tienes un perfil configurado. Contacta al administrador.")
            return redirect('/')

        # Todo OK, ejecutar vista
        return view_func(request, *args, **kwargs)

    return wrapper


def audit_file_access(action='view'):
    """
    Decorador para registrar accesos a archivos en logs de auditoría.

    Args:
        action (str): Tipo de acción ('upload_photo', 'view_photo', 'upload_video', 'view_video')

    Uso:
        @login_required
        @check_sucursal_access
        @audit_file_access(action='upload_photo')
        def cargar_fotos(request, pk):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            ip = request.META.get('REMOTE_ADDR', 'unknown')
            user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')

            logger.info(
                f"File {action}: "
                f"user={user.username}, "
                f"ip={ip}, "
                f"method={request.method}, "
                f"args={args}, "
                f"kwargs={kwargs}, "
                f"user_agent={user_agent[:50]}"
            )

            # Ejecutar vista
            response = view_func(request, *args, **kwargs)

            # Log de resultado
            status = 'success' if response.status_code < 400 else 'error'
            logger.info(
                f"File {action} result: "
                f"user={user.username}, "
                f"status={status}, "
                f"status_code={response.status_code}"
            )

            return response

        return wrapper
    return decorator


def require_origin_permission(view_func):
    """
    Decorador para verificar que el usuario tenga permiso para el origen del informe.

    Uso:
        @login_required
        @check_sucursal_access
        @require_origin_permission
        def vista(request, pk):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = request.user

        if 'pk' in kwargs:
            informe = get_object_or_404(Informe, pk=kwargs['pk'])

            if hasattr(user, 'profile'):
                profile = user.profile

                # Si puede usar todos los orígenes, permitir
                if profile.puede_usar_todos_origenes:
                    return view_func(request, *args, **kwargs)

                # Verificar si tiene acceso a este origen
                if not profile.tiene_acceso_origen(informe.origen):
                    logger.warning(
                        f"Acceso denegado a origen: user={user.username}, "
                        f"origen={informe.origen.nombre}, informe_id={informe.id}"
                    )
                    messages.error(
                        request,
                        f"No tienes permisos para acceder a informes de origen {informe.origen.nombre}"
                    )
                    return redirect('/')

        return view_func(request, *args, **kwargs)

    return wrapper
