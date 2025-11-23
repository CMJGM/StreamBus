from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Sucursales
from .forms import SucursalesForm
from StreamBus.logging_mixins import LoggingMixin, DetailedLoggingMixin, log_view, log_view_detailed

class ListaSucursalesView(LoggingMixin, ListView):
    model = Sucursales
    template_name = 'sucursales/lista.html'
    context_object_name = 'sucursales'

class CrearSucursalView(LoggingMixin, CreateView):
    model = Sucursales
    form_class = SucursalesForm
    template_name = 'sucursales/formulario.html'
    success_url = reverse_lazy('lista_sucursales')

class EditarSucursalView(DetailedLoggingMixin, UpdateView):
    model = Sucursales
    form_class = SucursalesForm
    template_name = 'sucursales/formulario.html'
    success_url = reverse_lazy('lista_sucursales')

class EliminarSucursalView(DetailedLoggingMixin, DeleteView):
    model = Sucursales
    template_name = 'sucursales/eliminar.html'
    success_url = reverse_lazy('lista_sucursales')
