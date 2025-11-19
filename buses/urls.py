from django.urls import path
from .views import (
    BusListView, BusCreateView, BusUpdateView,
    MarcaCreateView, MarcaUpdateView,
    ModeloCreateView, ModeloUpdateView
)


urlpatterns = [
    # Buses
    path('', BusListView.as_view(), name='lista_buses'),
    path('nuevo/', BusCreateView.as_view(), name='crear_bus'),
    path('editar/<int:pk>/', BusUpdateView.as_view(), name='editar_bus'),

    # Modelos
    path('modelo/nuevo/', ModeloCreateView.as_view(), name='crear_modelo'),
    path('modelo/editar/<int:pk>/', ModeloUpdateView.as_view(), name='editar_modelo'),

    # Marcas
    path('marca/nuevo/', MarcaCreateView.as_view(), name='crear_marca'),
    path('marca/editar/<int:pk>/', MarcaUpdateView.as_view(), name='editar_marca'),
]
