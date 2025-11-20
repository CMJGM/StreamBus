from django.urls import path
from .views import (
    ListaSucursalesView,
    CrearSucursalView,
    EditarSucursalView,
    EliminarSucursalView
)

urlpatterns = [
    path('', ListaSucursalesView.as_view(), name='lista_sucursales'),
    path('crear/', CrearSucursalView.as_view(), name='crear_sucursal'),
    path('editar/<int:pk>/', EditarSucursalView.as_view(), name='editar_sucursal'),
    path('eliminar/<int:pk>/', EliminarSucursalView.as_view(), name='eliminar_sucursal'),
]
