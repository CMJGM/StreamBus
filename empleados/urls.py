from django.urls import path
from .views import EmpleadoListView, EmpleadoCreateView, EmpleadoUpdateView

urlpatterns = [
    path('', EmpleadoListView.as_view(), name='lista_empleados'),
    path('crear/', EmpleadoCreateView.as_view(), name='crear_empleado'),
    path('editar/<int:pk>/', EmpleadoUpdateView.as_view(), name='editar_empleado'),
]
