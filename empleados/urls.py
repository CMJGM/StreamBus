from django.urls import path
from .views import (
    SeleccionarSucursalEmpleadosView,
    EmpleadoListView,
    EmpleadoCreateView,
    EmpleadoUpdateView
)

urlpatterns = [
    # Selección de sucursal
    path('', SeleccionarSucursalEmpleadosView.as_view(), name='seleccionar_sucursal_empleados'),
    path('seleccionar/', SeleccionarSucursalEmpleadosView.as_view(), name='empleados_seleccionar_sucursal'),

    # Lista de empleados por sucursal
    path('sucursal/<int:sucursal_id>/', EmpleadoListView.as_view(), name='lista_empleados_sucursal'),

    # CRUD de empleados
    path('crear/', EmpleadoCreateView.as_view(), name='crear_empleado'),
    path('editar/<int:pk>/', EmpleadoUpdateView.as_view(), name='editar_empleado'),

    # Compatibilidad con ruta anterior (redirige a selección)
    path('lista/', SeleccionarSucursalEmpleadosView.as_view(), name='lista_empleados'),
]
