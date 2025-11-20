from django.urls import path
from .views import InformesPorEmpleadoView, estadisticas_informes
from . import views

app_name = 'informes'

urlpatterns = [
    path('', views.InformeListView.as_view(), name='lista_informes'),
    path('lista', views.InformeListView.as_view(), name='lista'),
    path('lista_guardia', views.InformeListViewGuardia.as_view(), name='lista_guardia'),
    path('lista_siniestro', views.InformeListViewSiniestro.as_view(), name='lista_siniestro'),
    path('lista_taller/', views.InformeListViewTaller.as_view(), name='lista_taller'),
    path('crear/', views.InformeCreateView.as_view(), name='crear_informe'),
    path('editar/<int:pk>/', views.InformeUpdateView.as_view(), name='editar_informe'),
    path('informes/<int:pk>/foto/', views.cargar_fotos, name='cargar_fotos'),
    path('informes/<int:pk>/video/', views.cargar_video, name='cargar_video'),
    path('foto/<int:foto_id>/ver/', views.ver_foto, name='ver_foto'),
    path('informes/sin-legajo/', views.informes_sin_legajo, name='informes_sin_legajo'),
    path('informes/<int:pk>/enviar/', views.EnviarInformeEmailView.as_view(), name='enviar_informe_email'),
    path('informes/no_enviados/', views.informes_no_enviados, name="informes_no_enviados"),
    path('informes/sit_informe/', views.informes_asociar_sitinforme, name='sit_informe'),
    path('informes/sit_siniestro/', views.informes_asociar_sitsiniestro, name='sit_siniestro'),
    path('informes/informe_guardia/', views.InformeCreateGuardia.as_view(), name='informe_guardia'),
    path('informes/informe_sistemas/', views.InformeCreateSistemas.as_view(), name='informe_sistemas'),
    path('informes/informe_siniestro/', views.InformeCreateSiniestros.as_view(), name='informe_siniestro'),
    path('informes/informe_taller/', views.InformeCreateTaller.as_view(), name='informe_taller'),
    path('informes/por_empleado/', InformesPorEmpleadoView.as_view(), name='informes_por_empleado'),
    path('informes/borrar/<int:pk>/', views.InformeBorrarView.as_view(), name='borrar_informe'),
    path('informes/lista_borrar', views.ListaInformesBorrarView.as_view(), name='lista_borrar'),
    path('informes/dashboard/', views.estadisticas_informes, name='dashboard'),
    path('informes/desestimar/', views.informes_desestimar, name='desestimar'),
    path('informes-disciplinarios/', views.informes_disciplinarios, name='informes_disciplinarios'),
    path('reporte-pdf/<int:expediente_id>/', views.descargar_expediente_pdf, name='reporte_pdf'),

    # Ajax endpoints
    path('ajax/buscar-empleados/', views.buscar_empleados_ajax, name='buscar_empleados_ajax'),
    path('ajax/buscar-buses/', views.buscar_buses_ajax, name='buscar_buses_ajax'),
]
