from django.contrib import admin
from .models import Informe, FotoInforme, VideoInforme, Origen

class OrigenAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo', 'orden')
    list_editable = ('activo', 'orden')
    search_fields = ('nombre', 'descripcion')
    list_filter = ('activo',)
    ordering = ('orden', 'nombre')

class FotoInformeInline(admin.TabularInline):
    model = FotoInforme
    extra = 1  # Número de formularios vacíos extra que se mostrarán en el formulario de informe

class VideoInformeInline(admin.TabularInline):
    model = VideoInforme
    extra = 1  # Número de formularios vacíos extra para los videos

class InformeAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'empleado', 'fecha_hora', 'sucursal', 'generado')
    search_fields = ('titulo', 'empleado__legajo', 'empleado__apellido', 'empleado__nombre', 'bus__ficha')
    list_filter = ('generado', 'sucursal')
    inlines = [FotoInformeInline, VideoInformeInline]  # Incluir las fotos y videos como formularios en la página de informe

class FotoInformeAdmin(admin.ModelAdmin):
    list_display = ('informe', 'imagen')
    search_fields = ('informe__titulo',)

class VideoInformeAdmin(admin.ModelAdmin):
    list_display = ('informe', 'video')
    search_fields = ('informe__titulo',)

# Registrar modelos en admin
admin.site.register(Origen, OrigenAdmin)
admin.site.register(Informe, InformeAdmin)
admin.site.register(FotoInforme, FotoInformeAdmin)
admin.site.register(VideoInforme, VideoInformeAdmin)

