"""
Mixins para control de acceso por sucursal.

Estos mixins se pueden usar en cualquier vista basada en clases (ListView, DetailView, etc.)
para filtrar automáticamente los resultados por las sucursales asignadas al usuario.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages


class SucursalFilterMixin(LoginRequiredMixin):
    """
    Mixin base para filtrar resultados por sucursal del usuario.

    Uso:
        class MiVista(SucursalFilterMixin, ListView):
            model = MiModelo
            # El queryset se filtrará automáticamente por sucursal
    """

    def get_queryset(self):
        """
        Filtra el queryset por las sucursales permitidas del usuario.
        Solo aplica si el modelo tiene un campo 'sucursal'.
        """
        queryset = super().get_queryset()

        # Verificar si el usuario tiene perfil
        if not hasattr(self.request.user, 'profile'):
            return queryset.none()  # Sin perfil, no muestra nada

        user_profile = self.request.user.profile

        # Si puede ver todas las sucursales, no filtrar
        if user_profile.puede_ver_todas:
            return queryset

        # Verificar si el modelo tiene campo sucursal
        if hasattr(queryset.model, 'sucursal'):
            sucursales_permitidas = user_profile.get_sucursales_permitidas()
            return queryset.filter(sucursal__in=sucursales_permitidas)

        return queryset

    def get_context_data(self, **kwargs):
        """
        Agrega las sucursales permitidas al contexto del template.
        """
        context = super().get_context_data(**kwargs)

        if hasattr(self.request.user, 'profile'):
            context['sucursales'] = self.request.user.profile.get_sucursales_permitidas()
            context['puede_ver_todas'] = self.request.user.profile.puede_ver_todas
        else:
            context['sucursales'] = []
            context['puede_ver_todas'] = False

        return context


class SucursalAccessMixin(LoginRequiredMixin):
    """
    Mixin para verificar acceso a un objeto específico basado en sucursal.

    Uso:
        class EditarInformeView(SucursalAccessMixin, UpdateView):
            model = Informe
            # Verificará automáticamente si el usuario tiene acceso a la sucursal del informe
    """

    def dispatch(self, request, *args, **kwargs):
        """
        Verifica que el usuario tenga acceso a la sucursal del objeto.
        """
        # Obtener el objeto si existe un pk en kwargs
        if 'pk' in kwargs and hasattr(self, 'model'):
            try:
                obj = self.model.objects.get(pk=kwargs['pk'])

                # Verificar si el objeto tiene sucursal
                if hasattr(obj, 'sucursal'):
                    # Verificar acceso
                    if not hasattr(request.user, 'profile'):
                        messages.error(request, "No tienes un perfil configurado. Contacta al administrador.")
                        return redirect('/')

                    user_profile = request.user.profile

                    # Si puede ver todas, permitir acceso
                    if not user_profile.puede_ver_todas:
                        # Verificar si tiene acceso a esta sucursal
                        if not user_profile.tiene_acceso_sucursal(obj.sucursal):
                            messages.error(
                                request,
                                f"No tienes permisos para acceder a elementos de la sucursal {obj.sucursal.descripcion}"
                            )
                            return redirect('/')

            except self.model.DoesNotExist:
                pass  # Dejar que la vista maneje el 404

        return super().dispatch(request, *args, **kwargs)


class InformeFilterMixin(SucursalFilterMixin):
    """
    Mixin específico para filtrar informes con opciones adicionales.

    Incluye filtros comunes de informes:
    - Por título
    - Por fecha
    - Por origen
    - Por sucursal
    """

    def get_queryset(self):
        """
        Filtra informes por sucursal y parámetros adicionales.
        """
        queryset = super().get_queryset()

        # Aplicar select_related para optimizar consultas
        queryset = queryset.select_related('bus', 'sucursal', 'empleado', 'origen')

        # Filtrar por orígenes permitidos del usuario (siempre)
        if hasattr(self.request.user, 'profile'):
            user_profile = self.request.user.profile
            # Si no puede usar todos los orígenes, filtrar por los permitidos
            if not user_profile.puede_usar_todos_origenes:
                origenes_permitidos = user_profile.get_origenes_permitidos()
                queryset = queryset.filter(origen__in=origenes_permitidos)

        # Filtros adicionales de la URL
        filtro_titulo = self.request.GET.get('filtro', '')
        fecha_desde = self.request.GET.get('fecha_desde')
        fecha_hasta = self.request.GET.get('fecha_hasta')
        origen_filtro = self.request.GET.get('origen')
        sucursal_filtro = self.request.GET.get('sucursal')

        if filtro_titulo:
            queryset = queryset.filter(titulo__icontains=filtro_titulo)

        if fecha_desde:
            queryset = queryset.filter(fecha_hora__gte=fecha_desde)

        if fecha_hasta:
            queryset = queryset.filter(fecha_hora__lte=fecha_hasta)

        if origen_filtro:
            # Verificar que el usuario tenga acceso a este origen
            if hasattr(self.request.user, 'profile'):
                user_profile = self.request.user.profile
                # Si puede usar todos los orígenes o tiene acceso a este origen específico
                if user_profile.puede_usar_todos_origenes or user_profile.tiene_acceso_origen(int(origen_filtro)):
                    queryset = queryset.filter(origen_id=origen_filtro)

        if sucursal_filtro:
            # Solo permitir filtrar por sucursales a las que tiene acceso
            if hasattr(self.request.user, 'profile'):
                user_profile = self.request.user.profile
                if user_profile.puede_ver_todas or user_profile.tiene_acceso_sucursal(int(sucursal_filtro)):
                    queryset = queryset.filter(sucursal_id=sucursal_filtro)

        return queryset.order_by('-fecha_hora')


class EmpleadoFilterMixin(SucursalFilterMixin):
    """
    Mixin específico para filtrar empleados.

    Incluye filtros comunes de empleados:
    - Por apellido/nombre
    - Por legajo
    - Por sucursal
    """

    def get_queryset(self):
        """
        Filtra empleados por sucursal y parámetros adicionales.
        """
        queryset = super().get_queryset()

        # Aplicar select_related para optimizar consultas
        queryset = queryset.select_related('categoria', 'sucursal')

        # Filtros adicionales
        filtro_apellido = self.request.GET.get('filtro', '')
        sucursal_filtro = self.request.GET.get('sucursal')

        if filtro_apellido:
            queryset = queryset.filter(apellido__icontains=filtro_apellido)

        if sucursal_filtro:
            # Solo permitir filtrar por sucursales a las que tiene acceso
            if hasattr(self.request.user, 'profile'):
                user_profile = self.request.user.profile
                if user_profile.puede_ver_todas or user_profile.tiene_acceso_sucursal(int(sucursal_filtro)):
                    queryset = queryset.filter(sucursal_id=sucursal_filtro)

        return queryset.order_by('apellido', 'nombre')


class SucursalFormMixin:
    """
    Mixin para formularios que necesitan filtrar opciones de sucursal.

    Uso:
        class MiFormView(SucursalFormMixin, CreateView):
            # El formulario filtrará automáticamente las sucursales disponibles
    """

    def get_form_kwargs(self):
        """
        Agrega el usuario actual a los kwargs del formulario.
        """
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
