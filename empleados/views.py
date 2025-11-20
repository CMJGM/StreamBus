from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from .models import Empleado
from .forms import EmpleadoForm

class EmpleadoListView(ListView):
    model = Empleado
    template_name = 'empleados/lista_empleados.html'
    context_object_name = 'empleados'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        filtro = self.request.GET.get('filtro', '').strip()
        orden = self.request.GET.get('orden', '')

        if filtro:
            queryset = queryset.filter(apellido__icontains=filtro)

        if orden == 'apellido_asc':
            queryset = queryset.order_by('apellido')
        elif orden == 'apellido_desc':
            queryset = queryset.order_by('-apellido')
        else:
            queryset = queryset.order_by("apellido")

        return queryset


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filtro = self.request.GET.get('filtro', '')
        orden = self.request.GET.get('orden', '')

        context['filtro'] = filtro
        context['orden'] = orden
        context['hay_filtro'] = bool(filtro)
        return context


class EmpleadoCreateView(SuccessMessageMixin, CreateView):
    model = Empleado
    form_class = EmpleadoForm
    template_name = 'empleados/form_empleado.html'
    success_url = reverse_lazy('lista_empleados')
    success_message = "El empleado %(nombre)s %(apellido)s fue creado exitosamente."
    
    def get_success_message(self, cleaned_data):
        return self.success_message % dict(
            cleaned_data,
            nombre=self.object.nombre,
            apellido=self.object.apellido,
        )
    
    def form_valid(self, form):
        """Método llamado cuando el formulario es válido"""
        # Puedes agregar lógica adicional aquí si es necesario
        response = super().form_valid(form)
        messages.success(
            self.request, 
            f'Empleado {self.object.nombre} {self.object.apellido} (Legajo: {self.object.legajo}) creado correctamente.'
        )
        return response
    
    def form_invalid(self, form):
        """Método llamado cuando el formulario tiene errores"""
        messages.error(self.request, 'Por favor corrija los errores en el formulario.')
        return super().form_invalid(form)


class EmpleadoUpdateView(SuccessMessageMixin, UpdateView):
    model = Empleado
    form_class = EmpleadoForm
    template_name = 'empleados/form_empleado.html'
    success_url = reverse_lazy('lista_empleados')
    success_message = "El empleado %(nombre)s %(apellido)s fue actualizado exitosamente."
    
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
            f'Empleado {self.object.nombre} {self.object.apellido} actualizado correctamente.'
        )
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        print(f"Fecha Ingreso: {context['form'].fields['fecha_ingreso'].initial}")
        return context