from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Sucursales
from .forms import SucursalesForm

class ListaSucursalesView(ListView):
    model = Sucursales
    template_name = 'sucursales/lista.html'
    context_object_name = 'sucursales'

class CrearSucursalView(CreateView):
    model = Sucursales
    form_class = SucursalesForm
    template_name = 'sucursales/formulario.html'
    success_url = reverse_lazy('lista_sucursales')

class EditarSucursalView(UpdateView):
    model = Sucursales
    form_class = SucursalesForm
    template_name = 'sucursales/formulario.html'
    success_url = reverse_lazy('lista_sucursales')

class EliminarSucursalView(DeleteView):
    model = Sucursales
    template_name = 'sucursales/eliminar.html'
    success_url = reverse_lazy('lista_sucursales')
