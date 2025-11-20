from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static



urlpatterns = [
    path('', include('inicio.urls')), 
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/', include('registration.backends.default.urls')),
    path('admin/', admin.site.urls),    
    path('usuarios/', include('usuarios.urls')), 
    path("buses/", include("buses.urls")),
    path("categoria/", include("categoria.urls")),
    path("empleados/", include("empleados.urls")),
    path("sit/", include("sit.urls")),
    path("siniestros/", include("siniestros.urls")),
    path("sucursales/", include("sucursales.urls")),
    path("informes/", include("informes.urls", namespace="informes")),
]


if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [ path('__debug__/', include(debug_toolbar.urls)), ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)