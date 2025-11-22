from django.urls import path
from sit import views
from sit.test_logging_view import test_logging_anonymous, test_logging_authenticated

app_name = 'sit'

urlpatterns = [
    path('informes-sit/', views.listar_informes_sit, name='listar_informes_sit'),
    path('mapa_ubicacion/', views.mapa_ubicacion, name='mapa_ubicacion'),
    path("ubicaciones_vehiculos_json/", views.ubicaciones_vehiculos_json, name="ubicaciones_vehiculos_json"),
    path("ubicacion_json/", views.ubicacion_json, name="ubicacion_json"),
    path('vehiculos/', views.ubicaciones_vehiculos, name='ubicaciones_vehiculos'),
    path("direccion/", views.direccion_por_coordenadas, name="direccion"),
    path("alarmas/", views.alarmas_view, name="alarmas"),
    path('api/security-photos-ajax/', views.get_security_photos_ajax, name='get_security_photos_ajax'), # ¡Nueva ruta!

    path('security-photos/', views.security_photos_form, name='security_photos_form'),
    path('security-photos/fetch/', views.fetch_security_photos, name='fetch_security_photos'),
    path('security-photos/progress/', views.security_photos_progress, name='security_photos_progress'),
    path('security-photos/check-progress/', views.check_download_progress, name='check_download_progress'),
    path('security-photos/view/', views.view_security_photos, name='view_security_photos'),
    path('security-photos/clear/', views.clear_security_photos_session, name='clear_security_photos_session'),

    # URLs de prueba para verificar logging con usuario
    path('test-logging/', test_logging_anonymous, name='test_logging_anonymous'),
    path('test-logging-auth/', test_logging_authenticated, name='test_logging_authenticated'),
]
