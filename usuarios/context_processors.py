def user_groups(request):
    """
    Context processor que proporciona información de grupos y sucursales del usuario.

    Añade al contexto de todos los templates:
    - user_groups: Lista de nombres de grupos del usuario
    - user_sucursales: Lista de sucursales asignadas al usuario
    - puede_ver_todas_sucursales: Boolean indicando si puede ver todas las sucursales
    - sucursales_count: Número de sucursales asignadas
    """
    if request.user.is_authenticated:
        groups = request.user.groups.values_list('name', flat=True)

        # Obtener información de sucursales si el usuario tiene perfil
        sucursales_info = []
        puede_ver_todas = False
        sucursales_count = 0

        try:
            if hasattr(request.user, 'profile'):
                user_profile = request.user.profile
                puede_ver_todas = user_profile.puede_ver_todas

                # Obtener sucursales permitidas
                sucursales_qs = user_profile.get_sucursales_permitidas()
                sucursales_count = sucursales_qs.count()

                # Convertir a lista de diccionarios para usar en templates
                sucursales_info = list(
                    sucursales_qs.values('id', 'descripcion', 'abreviatura')
                )
        except Exception as e:
            # Si hay algún error, loguear pero no romper el template
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error al obtener sucursales del usuario {request.user.username}: {e}")

        return {
            'user_groups': groups,
            'user_sucursales': sucursales_info,
            'puede_ver_todas_sucursales': puede_ver_todas,
            'sucursales_count': sucursales_count,
        }

    return {
        'user_groups': [],
        'user_sucursales': [],
        'puede_ver_todas_sucursales': False,
        'sucursales_count': 0,
    }
