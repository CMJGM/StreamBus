# categorias/urls.py
from django.urls import path
from .views import (
    ListaCategoriasView,
    CrearCategoriaView,
    EditarCategoriaView,
    EliminarCategoriaView
)

urlpatterns = [
    path('', ListaCategoriasView.as_view(), name='lista_categorias'),  # Asegúrate de usar "" en la ruta base
    path('crear/', CrearCategoriaView.as_view(), name='crear_categoria'),
    path('editar/<int:pk>/', EditarCategoriaView.as_view(), name='editar_categoria'),
    path('eliminar/<int:pk>/', EliminarCategoriaView.as_view(), name='eliminar_categoria'),
]
