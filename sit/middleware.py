"""
Middleware básico para descargas de fotos de seguridad
Versión simplificada para resolver el error de importación
"""

import time
import logging
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse

logger = logging.getLogger(__name__)

class DownloadOptimizationMiddleware(MiddlewareMixin):
    """
    Middleware básico para optimizar requests de descarga
    Versión simplificada - implementaremos las optimizaciones gradualmente
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.download_paths = [
            '/sit/security-photos/check-progress/',
            '/sit/security-photos/begin-download/',
            '/sit/security-photos/fetch/',
        ]
        super().__init__(get_response)
    
    def __call__(self, request):
        # Por ahora, solo pasa el request sin modificaciones
        response = self.get_response(request)
        return response
    
    def process_request(self, request):
        """Procesar request entrante - versión básica"""
        
        # Solo log para requests de descarga
        if any(path in request.path for path in self.download_paths):
            logger.info(f"🔄 Request de descarga: {request.path}")
        
        return None  # Continuar procesamiento normal
    
    def process_response(self, request, response):
        """Procesar response - versión básica"""
        
        # Agregar headers básicos para requests de descarga
        if any(path in request.path for path in self.download_paths):
            if hasattr(response, '_headers'):
                response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response['Pragma'] = 'no-cache'
        
        return response
    
    def process_exception(self, request, exception):
        """Manejar excepciones básicas"""
        
        if any(path in request.path for path in self.download_paths):
            logger.error(f"❌ Error en descarga: {request.path} - {exception}")
            
            # Para requests AJAX, devolver JSON de error
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'error': 'Error del servidor',
                    'status': 'error',
                    'message': 'Ocurrió un error. Por favor, intente nuevamente.'
                }, status=500)
        
        return None  # Dejar que Django maneje otras excepciones