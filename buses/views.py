from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy
from .models import Buses, Modelo, Marca
from .forms import BusesForm, ModeloForm, MarcaForm
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator

from django.db.models import Q
from django.utils.functional import cached_property
from StreamBus.logging_mixins import LoggingMixin, DetailedLoggingMixin, log_view, log_view_detailed

class BusListView(LoggingMixin, ListView):
    model = Buses
    template_name = 'buses/lista_buses.html'
    context_object_name = 'buses'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().select_related('modelo__marca')
        filtro = self.request.GET.get('filtro', '').strip()
        orden = self.request.GET.get('orden', '')
        estado = self.request.GET.get('estado', 'True')  # Por defecto solo buses activos

        # Filtrado por estado
        if estado == 'False':
            queryset = queryset.filter(estado=False)
        else:
            queryset = queryset.filter(estado=True)

        # Filtro por marca o modelo
        if filtro:
            queryset = queryset.filter(
                Q(modelo__nombre__icontains=filtro) |
                Q(modelo__marca__nombre__icontains=filtro)
            )

        # Ordenamiento
        if orden == 'ano_asc':
            queryset = queryset.order_by('ano')
        elif orden == 'ano_desc':
            queryset = queryset.order_by('-ano')
        elif orden == 'dominio_asc':
            queryset = queryset.order_by('dominio')
        elif orden == 'dominio_desc':
            queryset = queryset.order_by('-dominio')
        elif orden == 'ficha_asc':
            queryset = queryset.order_by('ficha')
        elif orden == 'ficha_desc':
            queryset = queryset.order_by('-ficha')
        else:        
            queryset = queryset.order_by('ficha')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filtro'] = self.request.GET.get('filtro', '')
        context['orden'] = self.request.GET.get('orden', '')
        context['estado'] = self.request.GET.get('estado', 'True')
        context['hay_filtro'] = bool(context['filtro'])

        # Asegurar paginación
        if 'page_obj' not in context:
            context['page_obj'] = context['buses']
            context['is_paginated'] = context['buses'].paginator.num_pages > 1

        return context




class BusCreateView(LoggingMixin, CreateView):
    model = Buses
    form_class = BusesForm
    template_name = 'buses/form_buses.html'
    success_url = reverse_lazy('lista_buses')

    def form_valid(self, form):
        messages.success(self.request, 'Bus creado exitosamente.')
        return super().form_valid(form)

class BusUpdateView(DetailedLoggingMixin, UpdateView):
    model = Buses
    form_class = BusesForm
    template_name = 'buses/form_buses.html'
    success_url = reverse_lazy('lista_buses')

    def form_valid(self, form):
        messages.success(self.request, 'Bus actualizado correctamente.')
        return super().form_valid(form)

# --- MARCAS ---
class MarcaCreateView(LoggingMixin, CreateView):
    model = Marca
    form_class = MarcaForm
    template_name = 'buses/form_marca.html'
    success_url = reverse_lazy('crear_modelo')

class MarcaUpdateView(DetailedLoggingMixin, UpdateView):  # ← esta es la que está faltando
    model = Marca
    form_class = MarcaForm
    template_name = 'buses/form_marca.html'
    success_url = reverse_lazy('lista_buses')

# --- MODELOS ---
class ModeloCreateView(LoggingMixin, CreateView):
    model = Modelo
    form_class = ModeloForm
    template_name = 'buses/form_modelo.html'
    success_url = reverse_lazy('crear_bus')

class ModeloUpdateView(DetailedLoggingMixin, UpdateView):
    model = Modelo
    form_class = ModeloForm
    template_name = 'buses/form_modelo.html'
    success_url = reverse_lazy('lista_buses')
