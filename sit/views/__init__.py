"""
Vistas de la aplicación SIT (Sistema de Información de Transporte)

Este módulo ha sido refactorizado para mejor organización y mantenibilidad.
Todas las vistas están disponibles directamente desde sit.views para mantener
compatibilidad con código existente.

Estructura:
- gps_views.py: Tracking GPS, ubicaciones, mapas
- alarmas_views.py: Consultas de alarmas y fotos de seguridad
- photo_download_views.py: Descarga de fotos de seguridad
- informes_views.py: Informes y reportes PDF
- stats.py: Clases de estadísticas
"""

# Importar todas las vistas de GPS
from .gps_views import (
    mapa_ubicacion,
    ubicacion_json,
    ubicaciones_vehiculos,
    ubicaciones_vehiculos_json,
    direccion_por_coordenadas,
    calcular_tiempo,
    obtener_empresas_y_vehiculos,
    obtener_empresas_disponibles,
    obtener_vehiculos_por_empresa,
)

# Importar vistas de alarmas
from .alarmas_views import (
    alarmas_view,
    get_security_photos_ajax,
    query_security_photos,
)

# Importar vistas de descarga de fotos
from .photo_download_views import (
    security_photos_progress,
    view_security_photos,
    clear_security_photos_session,
    check_download_progress,
    security_photos_form,
    process_photos_page,
    begin_download_process,
    process_photos_page_with_filter,
    background_download_process,
    fetch_security_photos,
    basic_optimized_check_progress,
    basic_optimized_begin_download,
    basic_optimized_query_photos,
    process_photos_page_optimized,
    download_photo_basic_optimized,
)

# Importar vistas de informes
from .informes_views import (
    listar_informes_sit,
    descargar_expediente_pdf,
)

# Importar clases de estadísticas
from .stats import (
    DownloadStatistics,
    BasicOptimizedStats,
)

# Exportar todo para que sit.views funcione como antes
__all__ = [
    # GPS Views
    'mapa_ubicacion',
    'ubicacion_json',
    'ubicaciones_vehiculos',
    'ubicaciones_vehiculos_json',
    'direccion_por_coordenadas',
    'calcular_tiempo',
    'obtener_empresas_y_vehiculos',
    'obtener_empresas_disponibles',
    'obtener_vehiculos_por_empresa',
    # Alarmas Views
    'alarmas_view',
    'get_security_photos_ajax',
    'query_security_photos',
    # Photo Download Views
    'security_photos_progress',
    'view_security_photos',
    'clear_security_photos_session',
    'check_download_progress',
    'security_photos_form',
    'process_photos_page',
    'begin_download_process',
    'process_photos_page_with_filter',
    'background_download_process',
    'fetch_security_photos',
    'basic_optimized_check_progress',
    'basic_optimized_begin_download',
    'basic_optimized_query_photos',
    'process_photos_page_optimized',
    'download_photo_basic_optimized',
    # Informes Views
    'listar_informes_sit',
    'descargar_expediente_pdf',
    # Stats Classes
    'DownloadStatistics',
    'BasicOptimizedStats',
]
