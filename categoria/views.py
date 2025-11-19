# categorias/views.py
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Categorias

class ListaCategoriasView(ListView):
    model = Categorias
    template_name = 'categoria/lista.html'
    context_object_name = 'categorias'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtro por búsqueda
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(descripcion__icontains=search)

        # Ordenar por descripción
        order = self.request.GET.get('order')
        if order == 'desc':
            queryset = queryset.order_by('-descripcion')
        else:
            queryset = queryset.order_by('descripcion')
        
        return queryset

class CrearCategoriaView(CreateView):
    model = Categorias
    fields = ['descripcion']
    template_name = 'categoria/form_categoria.html'
    success_url = reverse_lazy('lista_categorias')

class EditarCategoriaView(UpdateView):
    model = Categorias
    fields = ['descripcion']
    template_name = 'categoria/form_categoria.html'
    success_url = reverse_lazy('lista_categorias')

class EliminarCategoriaView(DeleteView):
    model = Categorias
    template_name = 'categoria/confirmar_eliminar.html'
    success_url = reverse_lazy('lista_categorias')
