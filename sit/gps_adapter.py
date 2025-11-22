"""
StreamBus GPS Adapter - Integración con Citos Library
====================================================

Este módulo proporciona una capa de compatibilidad entre las funciones
actuales de StreamBus y la nueva librería citos, manteniendo la misma
interfaz de salida pero aprovechando las capacidades avanzadas de citos.

Archivo: sit/gps_adapter.py
Autor: StreamBus Development Team
Fecha: Mayo 2025
Versión: 1.0.0
"""

import logging
from typing import Dict, List, Optional, Union, Any, Tuple
from django.conf import settings
from django.core.cache import cache
from .citos_library import GPSCameraAPI, APIError

logger = logging.getLogger(__name__)


class StreamBusGPSAdapter:
    """
    Adapter que proporciona compatibilidad con las funciones existentes
    de StreamBus utilizando la librería citos internamente.
    """
    
    def __init__(self):
        """Inicializa el adapter con configuración de StreamBus"""
        self.api = GPSCameraAPI(
            base_url=getattr(settings, 'GPS_BASE_URL', 'http://190.183.254.253:8088'),
            timeout=getattr(settings, 'GPS_TIMEOUT', 30),
            verify_ssl=getattr(settings, 'GPS_VERIFY_SSL', True)
        )
        self._session_cache_key = 'streambus_gps_session'
        self._login_credentials = {
            'account': getattr(settings, 'GPS_ACCOUNT', None),
            'password': getattr(settings, 'GPS_PASSWORD', None)
        }
    
    def _ensure_session(self) -> bool:
        """
        Asegura que tenemos una sesión válida, creando una nueva si es necesario
        
        Returns:
            True si la sesión es válida, False en caso contrario
        """
        try:
            # Verificar si ya tenemos una sesión válida
            if self.api.jsession and self.api.is_session_valid():
                return True
            
            # Intentar restaurar sesión desde cache
            cached_session = cache.get(self._session_cache_key)
            if cached_session:
                self.api.jsession = cached_session
                if self.api.is_session_valid():
                    return True
            
            # Crear nueva sesión
            if self._login_credentials['account'] and self._login_credentials['password']:
                result = self.api.login(
                    self._login_credentials['account'],
                    self._login_credentials['password']
                )
                
                # Guardar sesión en cache por 30 minutos
                cache.set(self._session_cache_key, self.api.jsession, 1800)
                
                # Actualizar settings global para compatibilidad
                settings.JSESSION_GPS = self.api.jsession
                
                logger.info("Nueva sesión GPS creada exitosamente")
                return True
            else:
                logger.error("Credenciales GPS no configuradas")
                return False
                
        except APIError as e:
            logger.error(f"Error de API GPS: {e.code} - {e.message}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado en sesión GPS: {e}")
            return False
    
    def _fallback_to_legacy(self, func_name: str, *args, **kwargs):
        """Fallback a funciones legacy en caso de error con citos"""
        logger.info(f"🔄 Usando fallback legacy para {func_name}")
        
        # IMPORTANTE: Llamar directamente a función legacy, no a la modificada
        from . import utils as legacy_utils
        
        legacy_function_name = func_name + '_legacy'
        
        if hasattr(legacy_utils, legacy_function_name):
            return getattr(legacy_utils, legacy_function_name)(*args, **kwargs)
        else:
            logger.info(f"❌ Función legacy {legacy_function_name} no encontrada")
            return None
    
    # =========================================================================
    # FUNCIONES DE COMPATIBILIDAD CON STREAMBUS
    # =========================================================================
    
    def obtener_ultima_ubicacion(self, vehi_idno: str = None, to_map: int = 2, 
                                geoaddress: int = 0, current_page: int = 1, 
                                page_records: int = 50) -> Tuple[Optional[float], Optional[float], 
                                                               Optional[float], Optional[int], Optional[str]]:
        """
        Obtiene la última ubicación de un vehículo (compatible con función actual)
        
        Args:
            vehi_idno: ID del vehículo (ficha)
            to_map: Tipo de mapa (1=Google, 2=Baidu)
            geoaddress: Si resolver dirección (0=no, 1=sí)
            current_page: Página actual (para compatibilidad)
            page_records: Registros por página (para compatibilidad)
            
        Returns:
            Tupla: (latitud, longitud, velocidad, timestamp, dirección)
        """
        try:
            if not self._ensure_session():
                return self._fallback_to_legacy('obtener_ultima_ubicacion', 
                                               vehi_idno, to_map, geoaddress, 
                                               current_page, page_records)
            
            # Usar la nueva API de citos
            result = self.api.get_device_status(
                vehicle_ids=vehi_idno,
                geo_address=bool(geoaddress),
                map_type=to_map
            )
            
            if result.get('status') and len(result['status']) > 0:
                info = result['status'][0]
                
                # Convertir al formato esperado por StreamBus
                latitud = info.get('lat') / 1000000.0 if info.get('lat') else None
                longitud = info.get('lng') / 1000000.0 if info.get('lng') else None
                velocidad = info.get('sp') / 10.0 if info.get('sp') is not None else None
                timestamp = info.get('gt')  # Timestamp en milisegundos
                direccion = info.get('ps', '')  # Dirección
                
                logger.debug(f"Ubicación obtenida para vehículo {vehi_idno}: "
                           f"lat={latitud}, lng={longitud}")
                
                return latitud, longitud, velocidad, timestamp, direccion
            else:
                logger.warning(f"No se encontró información para vehículo {vehi_idno}")
                return None, None, None, None, None
                
        except APIError as e:
            logger.error(f"Error API citos en obtener_ultima_ubicacion: {e}")
            return self._fallback_to_legacy('obtener_ultima_ubicacion', 
                                           vehi_idno, to_map, geoaddress, 
                                           current_page, page_records)
        except Exception as e:
            logger.error(f"Error inesperado en obtener_ultima_ubicacion: {e}")
            return self._fallback_to_legacy('obtener_ultima_ubicacion', 
                                           vehi_idno, to_map, geoaddress, 
                                           current_page, page_records)
    
    def obtener_vehiculos(self, language: str = 'es') -> List[Dict[str, Any]]:
        """
        Obtiene la lista de vehículos del usuario (compatible con función actual)
        
        Args:
            language: Idioma ('es' para español, 'en' para inglés)
            
        Returns:
            Lista de vehículos con información detallada
        """
        try:
            if not self._ensure_session():
                return self._fallback_to_legacy('obtener_vehiculos')
            
            # Mapear idioma a formato de API
            api_language = 'en' if language == 'es' else language
            
            result = self.api.get_user_vehicles(language=api_language)
            
            if result.get('vehicles'):
                logger.info(f"Obtenidos {len(result['vehicles'])} vehículos")
                return result['vehicles']
            else:
                logger.warning("No se encontraron vehículos")
                return []
                
        except APIError as e:
            logger.error(f"Error API citos en obtener_vehiculos: {e}")
            return self._fallback_to_legacy('obtener_vehiculos')
        except Exception as e:
            logger.error(f"Error inesperado en obtener_vehiculos: {e}")
            return self._fallback_to_legacy('obtener_vehiculos')
    
    def query_security_photos(self, begintime: str, endtime: str, 
                             current_page: int = 1, page_records: int = 50) -> Optional[Dict[str, Any]]:
        """
        Consulta fotos de seguridad (compatible con función actual)
        
        Args:
            begintime: Fecha inicio en formato "YYYY-MM-DD HH:MM:SS"
            endtime: Fecha fin en formato "YYYY-MM-DD HH:MM:SS"
            current_page: Página actual
            page_records: Registros por página
            
        Returns:
            Respuesta de la API con fotos de seguridad
        """
        
        page_records = 50

        try:
            if not self._ensure_session():
                return self._fallback_to_legacy('query_security_photos', 
                                               begintime, endtime, 
                                               current_page, page_records)
            
            # Usar get_device_alarms para obtener eventos con fotos
            result = self.api.get_device_alarms(
                start_time=begintime,
                end_time=endtime,
                alarm_types=[1, 72, 78],  # Tipos de alarma que generan fotos
                current_page=current_page,
                page_records=page_records,
                geo_address=True
            )
            
            # Adaptar formato de respuesta para compatibilidad
            if 'infos' in result:
                # Convertir alarmas a formato de fotos de seguridad
                adapted_result = {
                    'result': 0,
                    'infos': [],
                    'pagination': result.get('pagination', {})
                }
                
                for alarm in result['infos']:
                    # Convertir alarma a formato foto
                    photo_info = {
                        'devIdno': alarm.get('devIdno'),
                        'vehiIdno': alarm.get('vehiIdno'), 
                        'fileTimeStr': alarm.get('startTime'),
                        'position': alarm.get('position', ''),
                        # Agregar más campos según necesidad
                    }
                    adapted_result['infos'].append(photo_info)
                
                return adapted_result
            
            return result
            
        except APIError as e:
            logger.error(f"Error API citos en query_security_photos: {e}")
            return self._fallback_to_legacy('query_security_photos', 
                                           begintime, endtime, 
                                           current_page, page_records)
        except Exception as e:
            logger.error(f"Error inesperado en query_security_photos: {e}")
            return self._fallback_to_legacy('query_security_photos', 
                                           begintime, endtime, 
                                           current_page, page_records)
    
    def gps_login(self, account: str, password: str) -> Optional[str]:
        """
        Login GPS (compatible con función actual)
        
        Args:
            account: Cuenta de usuario
            password: Contraseña
            
        Returns:
            Jsession string o None si falla
        """
        try:
            result = self.api.login(account, password)
            
            if result.get('jsession'):
                # Guardar en cache y settings global
                cache.set(self._session_cache_key, result['jsession'], 1800)
                settings.JSESSION_GPS = result['jsession']
                
                logger.info(f"Login GPS exitoso para usuario: {account}")
                return result['jsession']
            else:
                logger.error("Login GPS falló: no se obtuvo jsession")
                return None
                
        except APIError as e:
            logger.error(f"Error en login GPS: {e.code} - {e.message}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado en login GPS: {e}")
            return None
    
    def logout_api(self, jsession: str = None) -> Dict[str, Any]:
        """
        Logout GPS (compatible con función actual)
        
        Args:
            jsession: Sesión a cerrar (opcional)
            
        Returns:
            Resultado del logout
        """
        try:
            result = self.api.logout()
            
            # Limpiar cache y settings
            cache.delete(self._session_cache_key)
            if hasattr(settings, 'JSESSION_GPS'):
                settings.JSESSION_GPS = None
            
            logger.info("Logout GPS exitoso")
            return result
            
        except Exception as e:
            logger.error(f"Error en logout GPS: {e}")
            return {'result': 1, 'error': str(e)}


# =========================================================================
# INSTANCIA GLOBAL DEL ADAPTER
# =========================================================================

# Crear instancia global para usar en todo el proyecto
_adapter_instance = None

def get_gps_adapter() -> StreamBusGPSAdapter:
    """
    Obtiene la instancia global del adapter
    
    Returns:
        Instancia del StreamBusGPSAdapter
    """
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = StreamBusGPSAdapter()
    return _adapter_instance