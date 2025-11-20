from django.views.generic import ListView, CreateView, UpdateView, FormView
from django.views import View
from django.urls import reverse_lazy, reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Empleado
from .forms import EmpleadoForm
from usuarios.mixins import EmpleadoFilterMixin, SucursalAccessMixin
from sucursales.models import Sucursales
from django import forms


class SeleccionarSucursalEmpleadosView(LoginRequiredMixin, View):
    """Vista para seleccionar la sucursal antes de ver empleados"""
    template_name = 'empleados/seleccionar_sucursal.html'

    def get(self, request):
        # Obtener sucursales permitidas para el usuario
        if hasattr(request.user, 'profile'):
            sucursales = request.user.profile.get_sucursales_permitidas()
        else:
            sucursales = Sucursales.objects.none()

        # Si solo tiene una sucursal, redirigir directamente
        if sucursales.count() == 1:
            return redirect('lista_empleados_sucursal', sucursal_id=sucursales.first().id)

        context = {
            'sucursales': sucursales
        }
        return render(request, self.template_name, context)


class EmpleadoListView(LoginRequiredMixin, ListView):
    model = Empleado
    template_name = 'empleados/lista_empleados.html'
    context_object_name = 'empleados'
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        # Verificar que el usuario tenga acceso a la sucursal
        sucursal_id = kwargs.get('sucursal_id')
        if sucursal_id:
            self.sucursal = get_object_or_404(Sucursales, id=sucursal_id)

            # Verificar acceso del usuario a esta sucursal
            if hasattr(request.user, 'profile'):
                if not request.user.profile.tiene_acceso_sucursal(self.sucursal):
                    messages.error(request, 'No tiene permisos para ver empleados de esta sucursal.')
                    return redirect('seleccionar_sucursal_empleados')
        else:
            # Si no hay sucursal_id, redirigir a selección
            return redirect('seleccionar_sucursal_empleados')

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Empleado.objects.filter(sucursal=self.sucursal).select_related('categoria', 'sucursal')

        # Filtro por apellido
        filtro = self.request.GET.get('filtro', '').strip()
        if filtro:
            queryset = queryset.filter(apellido__icontains=filtro)

        # Ordenamiento
        orden = self.request.GET.get('orden', '')
        if orden == 'apellido_asc':
            queryset = queryset.order_by('apellido')
        elif orden == 'apellido_desc':
            queryset = queryset.order_by('-apellido')
        else:
            queryset = queryset.order_by('apellido', 'nombre')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filtro = self.request.GET.get('filtro', '')
        orden = self.request.GET.get('orden', '')

        context['filtro'] = filtro
        context['orden'] = orden
        context['hay_filtro'] = bool(filtro)
        context['sucursal'] = self.sucursal
        context['total_empleados'] = self.get_queryset().count()
        return context


class EmpleadoCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Empleado
    form_class = EmpleadoForm
    template_name = 'empleados/form_empleado.html'
    success_message = "El empleado %(nombre)s %(apellido)s fue creado exitosamente."

    def get_form_kwargs(self):
        """Pasar el usuario al formulario"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_initial(self):
        """Pre-seleccionar la sucursal si viene de la lista"""
        initial = super().get_initial()
        sucursal_id = self.request.GET.get('sucursal')
        if sucursal_id:
            try:
                sucursal = Sucursales.objects.get(id=sucursal_id)
                # Verificar que el usuario tenga acceso
                if hasattr(self.request.user, 'profile'):
                    if self.request.user.profile.tiene_acceso_sucursal(sucursal):
                        initial['sucursal'] = sucursal
            except Sucursales.DoesNotExist:
                pass
        return initial

    def get_success_url(self):
        """Redirigir a la lista de empleados de la sucursal"""
        if self.object.sucursal:
            return reverse('lista_empleados_sucursal', kwargs={'sucursal_id': self.object.sucursal.id})
        return reverse('seleccionar_sucursal_empleados')

    def get_success_message(self, cleaned_data):
        return self.success_message % dict(
            cleaned_data,
            nombre=self.object.nombre,
            apellido=self.object.apellido,
        )

    def form_valid(self, form):
        """Método llamado cuando el formulario es válido"""
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'✅ Empleado {self.object.nombre} {self.object.apellido} (Legajo: {self.object.legajo}) creado correctamente.'
        )
        return response

    def form_invalid(self, form):
        """Método llamado cuando el formulario tiene errores"""
        messages.error(self.request, '❌ Por favor corrija los errores en el formulario.')
        return super().form_invalid(form)


class EmpleadoUpdateView(SucursalAccessMixin, SuccessMessageMixin, UpdateView):
    model = Empleado
    form_class = EmpleadoForm
    template_name = 'empleados/form_empleado.html'
    success_message = "El empleado %(nombre)s %(apellido)s fue actualizado exitosamente."

    def get_form_kwargs(self):
        """Pasar el usuario al formulario"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        """Redirigir a la lista de empleados de la sucursal"""
        if self.object.sucursal:
            return reverse('lista_empleados_sucursal', kwargs={'sucursal_id': self.object.sucursal.id})
        return reverse('seleccionar_sucursal_empleados')

    def get_success_message(self, cleaned_data):
        return self.success_message % dict(
            cleaned_data,
            nombre=self.object.nombre,
            apellido=self.object.apellido,
        )

    def form_valid(self, form):
        """Método llamado cuando el formulario es válido"""
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'✅ Empleado {self.object.nombre} {self.object.apellido} actualizado correctamente.'
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['es_edicion'] = True
        return context