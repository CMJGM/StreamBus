"""
Librería para API de GPS/Cámaras - Sistema de Monitoreo de Vehículos
================================================================

Esta librería proporciona una interfaz completa para interactuar con la API 
de sistemas GPS/Cámaras de monitoreo vehicular.

Autor: Sistema de Documentación API
Fecha: 2025
Versión: 1.0.0

Características principales:
- Autenticación y manejo de sesiones
- Gestión completa de vehículos y dispositivos
- Monitoreo en tiempo real de ubicaciones GPS
- Control de cámaras y videos en tiempo real
- Gestión de alarmas y eventos
- Reportes y análisis de datos
- Administración de usuarios y organizaciones


DOCUMENTACIÓN DE LA API
-- https://claude.ai/public/artifacts/f3d942ce-4d40-493b-aa59-9dc8c6cf448e

"""

import requests
import json
import hashlib
from typing import Dict, List, Optional, Union, Any
from urllib.parse import urlencode, quote
import logging
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class APIError(Exception):
    """Excepción personalizada para errores de la API"""
    def __init__(self, code: int, message: str, details: str = None):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(f"Error {code}: {message}")


class ErrorCodes(Enum):
    """Códigos de error definidos por la API"""
    SUCCESS = 0
    INVALID_CREDENTIALS = 1
    INCORRECT_PASSWORD = 2
    USER_DISABLED = 3
    USER_EXPIRED = 4
    SESSION_NOT_EXISTS = 5
    SYSTEM_EXCEPTION = 6
    INVALID_PARAMETERS = 7
    NO_OPERATION_AUTHORITY = 8
    INVALID_TIME_RANGE = 9
    TIME_RANGE_TOO_LONG = 10
    VIDEO_TASK_EXISTS = 11
    ACCOUNT_EXISTS = 12
    NO_AUTHORITY = 13
    DEVICE_LIMIT_REACHED = 14
    DEVICE_EXISTS = 15
    VEHICLE_EXISTS = 16
    DEVICE_IN_USE = 17
    VEHICLE_NOT_EXISTS = 18
    DEVICE_NOT_EXISTS = 19
    DEVICE_NOT_CURRENT_COMPANY = 20
    DEVICE_COUNT_MISMATCH = 21
    NETWORK_CONNECTION_EXCEPTION = 24
    RULE_NAME_EXISTS = 25
    RULE_NOT_EXISTS = 26
    INFORMATION_NOT_EXISTS = 27
    USER_SESSION_EXISTS = 28
    COMPANY_NOT_EXISTS = 29
    DEVICE_NOT_ONLINE = 32
    SINGLE_SIGN_ON_ALREADY_LOGGED = 34


@dataclass
class DeviceStatus:
    """Estructura para el estado de un dispositivo GPS"""
    device_id: str
    vehicle_id: Optional[str]
    longitude: float
    latitude: float
    speed: float
    online: bool
    gps_time: str
    direction: int
    mileage: int
    fuel: float
    temperature_sensors: List[float]
    status_flags: Dict[str, int]
    map_coordinates: Optional[Dict[str, str]] = None
    geographic_position: Optional[str] = None


@dataclass
class VehicleInfo:
    """Información básica de un vehículo"""
    id: int
    plate_number: str
    icon: int
    company_id: int
    company_name: str
    plate_type: str
    devices: List[Dict]
    vehicle_type: int = 0


@dataclass
class AlarmInfo:
    """Información de una alarma"""
    guid: str
    alarm_type: int
    device_id: str
    vehicle_id: Optional[str]
    company_id: int
    start_time: int
    end_time: Optional[int]
    description: str
    handled: bool
    parameters: Dict[str, Any]
    location_info: Dict[str, Any]


class GPSCameraAPI:
    """
    Cliente principal para la API de GPS/Cámaras
    
    Esta clase proporciona una interfaz completa para interactuar con todos
    los endpoints de la API de monitoreo vehicular.
    """
    
    def __init__(self, base_url: str = "http://190.183.254.253:8088", 
                 timeout: int = 30, verify_ssl: bool = True):
        """
        Inicializa el cliente de la API
        
        Args:
            base_url: URL base de la API
            timeout: Timeout para las requests en segundos
            verify_ssl: Si verificar certificados SSL
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.jsession = None
        self.account_name = None
        
        # Configurar logging
        self.logger = logging.getLogger(__name__)
        
        # Headers por defecto
        self.default_headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'User-Agent': 'Python-GPS-Camera-API/1.0.0'
        }
    
    def _encode_url_params(self, params: Dict[str, Any]) -> str:
        """
        Codifica parámetros para URL según RFC 1738
        
        Args:
            params: Diccionario de parámetros
            
        Returns:
            String de parámetros codificados
        """
        encoded_params = {}
        for key, value in params.items():
            if value is not None:
                if isinstance(value, str):
                    # Doble encoding para strings como especifica la API
                    encoded_params[key] = quote(quote(str(value), safe=''), safe='')
                else:
                    encoded_params[key] = str(value)
        
        return urlencode(encoded_params, safe=',')
    
    def _make_request(self, endpoint: str, method: str = 'GET', 
                     params: Dict[str, Any] = None, data: Dict[str, Any] = None,
                     require_session: bool = True) -> Dict[str, Any]:
        """
        Realiza una petición HTTP a la API
        
        Args:
            endpoint: Endpoint de la API (sin base_url)
            method: Método HTTP (GET, POST)
            params: Parámetros para la URL
            data: Datos para el cuerpo de la petición
            require_session: Si requiere jsession válido
            
        Returns:
            Respuesta de la API como diccionario
            
        Raises:
            APIError: Si hay error en la respuesta de la API
        """
        if require_session and not self.jsession:
            raise APIError(5, "No hay sesión activa. Debe hacer login primero.")
        
        # Preparar parámetros
        if params is None:
            params = {}
        
        if require_session and self.jsession:
            params['jsession'] = self.jsession
        
        # Construir URL
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        if params:
            url += '?' + self._encode_url_params(params)
        
        # Preparar headers
        headers = self.default_headers.copy()
        
        # Realizar petición
        try:
            if method.upper() == 'POST':
                if data:
                    response = requests.post(
                        url, json=data, headers=headers, 
                        timeout=self.timeout, verify=self.verify_ssl
                    )
                else:
                    response = requests.post(
                        url, headers=headers,
                        timeout=self.timeout, verify=self.verify_ssl
                    )
            else:
                response = requests.get(
                    url, headers=headers,
                    timeout=self.timeout, verify=self.verify_ssl
                )
            
            response.raise_for_status()
            
            # Parsear respuesta JSON
            try:
                result = response.json()
            except json.JSONDecodeError:
                raise APIError(6, "Respuesta inválida del servidor")
            
            # Verificar código de resultado
            if 'result' in result and result['result'] != 0:
                error_code = result['result']
                error_msg = self._get_error_message(error_code)
                raise APIError(error_code, error_msg)
            
            return result
            
        except requests.RequestException as e:
            self.logger.error(f"Error de conexión: {e}")
            raise APIError(24, f"Error de conexión: {str(e)}")
    
    def _get_error_message(self, code: int) -> str:
        """Obtiene el mensaje de error para un código específico"""
        error_messages = {
            1: "Nombre de usuario o contraseña incorrectos",
            2: "Nombre de usuario o contraseña incorrectos", 
            3: "El usuario está deshabilitado",
            4: "El usuario ha expirado",
            5: "La sesión no existe",
            6: "Excepción del sistema",
            7: "Parámetros de solicitud incorrectos",
            8: "Sin autoridad para operar el vehículo o dispositivo",
            9: "La hora de inicio no es mayor que la hora de fin",
            10: "El rango de tiempo es demasiado largo",
            11: "Las tareas de descarga de video ya existen",
            12: "La cuenta ya existe",
            13: "Sin autoridad de operación",
            14: "Se alcanzó el límite de dispositivos",
            15: "El dispositivo ya existe",
            16: "El vehículo ya existe",
            17: "El dispositivo está siendo utilizado",
            18: "El vehículo no existe",
            19: "El dispositivo no existe",
            20: "El dispositivo no es de la empresa actual",
            21: "El número de registros de dispositivos no coincide",
            24: "Excepción de conexión de red",
            25: "El nombre de la regla ya existe",
            26: "Las reglas no existen",
            27: "La información no existe",
            28: "La sesión de usuario ya existe",
            29: "La empresa no existe",
            32: "El equipo no está en línea",
            34: "Usuario de inicio de sesión único, ya conectado",
            111003: "Error de autenticación o sesión inválida",
        }
        return error_messages.get(code, f"Error desconocido: {code}")
    
    # =====================================================================
    # AUTENTICACIÓN Y GESTIÓN DE SESIONES
    # =====================================================================
    
    def login(self, account: str, password: str) -> Dict[str, Any]:
        """
        Inicia sesión en la API
        
        Args:
            account: Nombre de cuenta de usuario
            password: Contraseña (se aplicará hash MD5 automáticamente)
            
        Returns:
            Información de la sesión incluyendo jsession
            
        Raises:
            APIError: Si las credenciales son inválidas
        """
        # DEBUGGING - agregar estas líneas
        print(f"🔍 CITOS DEBUG: account recibida = '{account}'")
        print(f"🔍 CITOS DEBUG: password recibida = '{password}'")
        
        # Aplicar hash MD5 a la contraseña
        if len(password) != 32:  # No es un hash MD5 ya
            original_password = password
            password = hashlib.md5(password.encode('utf-8')).hexdigest()
            print(f"🔍 CITOS DEBUG: '{original_password}' -> MD5: {password}")
        else:
            print(f"🔍 CITOS DEBUG: Password ya es MD5: {password}")
        
        params = {
            'account': account,
            'password': password
        }
        
        result = self._make_request(
            'StandardApiAction_login.action',
            method='GET',
            params=params,
            require_session=False
        )
        
        # Guardar información de sesión
        self.jsession = result.get('jsession')
        self.account_name = result.get('account_name')
        
        self.logger.info(f"Login exitoso para usuario: {account}")
        return result
    
    def logout(self) -> Dict[str, Any]:
        """
        Cierra la sesión actual
        
        Returns:
            Confirmación de logout
        """
        if not self.jsession:
            return {'result': 0, 'message': 'No hay sesión activa'}
        
        result = self._make_request('StandardApiAction_logout.action')
        
        # Limpiar información de sesión
        self.jsession = None
        self.account_name = None
        
        self.logger.info("Logout exitoso")
        return result
    
    # =====================================================================
    # GESTIÓN DE VEHÍCULOS Y DISPOSITIVOS
    # =====================================================================
    
    def get_user_vehicles(self, language: str = 'zh') -> Dict[str, Any]:
        """
        Obtiene la lista de vehículos del usuario
        
        Args:
            language: Idioma ('zh' para chino, 'en' para inglés)
            
        Returns:
            Lista de vehículos con información detallada
        """
        params = {'language': language} if language else {}
        
        return self._make_request(
            'StandardApiAction_queryUserVehicle.action',
            params=params
        )
    
    def get_device_by_vehicle(self, vehicle_ids: Union[str, List[str]] = None) -> Dict[str, Any]:
        """
        Obtiene información de dispositivos por vehículo
        
        Args:
            vehicle_ids: ID(s) de vehículo (número de placa)
                        Puede ser string único o lista de strings
                        
        Returns:
            Información de dispositivos asociados
        """
        params = {}
        if vehicle_ids:
            if isinstance(vehicle_ids, list):
                params['vehiIdno'] = ','.join(vehicle_ids)
            else:
                params['vehiIdno'] = vehicle_ids
        
        return self._make_request(
            'StandardApiAction_getDeviceByVehicle.action',
            params=params
        )
    
    def get_device_online_status(self, device_ids: Union[str, List[str]] = None,
                                vehicle_ids: Union[str, List[str]] = None,
                                status: int = None) -> Dict[str, Any]:
        """
        Obtiene el estado en línea de dispositivos
        
        Args:
            device_ids: ID(s) de dispositivo
            vehicle_ids: ID(s) de vehículo (números de placa)
            status: Estado online (0=offline, 1=online, None=todos)
            
        Returns:
            Estado en línea de los dispositivos
        """
        params = {}
        
        if device_ids:
            if isinstance(device_ids, list):
                params['devIdno'] = ','.join(device_ids)
            else:
                params['devIdno'] = device_ids
        
        if vehicle_ids:
            if isinstance(vehicle_ids, list):
                params['vehiIdno'] = ','.join(vehicle_ids)
            else:
                params['vehiIdno'] = vehicle_ids
        
        if status is not None:
            params['status'] = status
        
        return self._make_request(
            'StandardApiAction_getDeviceOlStatus.action',
            params=params
        )
    
    def get_device_status(self, device_ids: Union[str, List[str]] = None,
                         vehicle_ids: Union[str, List[str]] = None,
                         geo_address: bool = False,
                         driver_info: bool = False,
                         map_type: int = None,
                         language: str = None) -> Dict[str, Any]:
        """
        Obtiene el estado GPS detallado de dispositivos
        
        Args:
            device_ids: ID(s) de dispositivo
            vehicle_ids: ID(s) de vehículo
            geo_address: Si resolver la posición geográfica
            driver_info: Si consultar información del conductor
            map_type: Conversión de coordenadas (1=Google, 2=Baidu)
            language: Idioma para resolución geográfica
            
        Returns:
            Estado GPS detallado de los dispositivos
        """
        params = {}
        
        if device_ids:
            if isinstance(device_ids, list):
                params['devIdno'] = ','.join(device_ids)
            else:
                params['devIdno'] = device_ids
        
        if vehicle_ids:
            if isinstance(vehicle_ids, list):
                params['vehiIdno'] = ','.join(vehicle_ids)
            else:
                params['vehiIdno'] = vehicle_ids
        
        if geo_address:
            params['geoaddress'] = 1
        
        if driver_info:
            params['driver'] = 1
        
        if map_type:
            params['toMap'] = map_type
        
        if language:
            params['language'] = language
        
        return self._make_request(
            'StandardApiAction_getDeviceStatus.action',
            params=params
        )
    
    # =====================================================================
    # GESTIÓN DE TRACKS Y RUTAS
    # =====================================================================
    
    def get_device_track(self, device_id: str, start_time: str, end_time: str,
                        distance: float = None, park_time: int = None,
                        geo_address: bool = False, map_type: int = None,
                        current_page: int = None, page_records: int = None) -> Dict[str, Any]:
        """
        Obtiene el track detallado de un dispositivo
        
        Args:
            device_id: ID del dispositivo
            start_time: Tiempo de inicio (formato: 'YYYY-MM-DD HH:MM:SS')
            end_time: Tiempo de fin (formato: 'YYYY-MM-DD HH:MM:SS')
            distance: Distancia mínima en KM
            park_time: Tiempo de estacionamiento mínimo en segundos
            geo_address: Si resolver posición geográfica
            map_type: Conversión de coordenadas (1=Google, 2=Baidu)
            current_page: Página actual para paginación
            page_records: Registros por página
            
        Returns:
            Track detallado del dispositivo
        """
        params = {
            'devIdno': device_id,
            'begintime': start_time,
            'endtime': end_time
        }
        
        if distance is not None:
            params['distance'] = distance
        
        if park_time is not None:
            params['parkTime'] = park_time
        
        if geo_address:
            params['geoaddress'] = 1
        
        if map_type:
            params['toMap'] = map_type
        
        if current_page is not None:
            params['currentPage'] = current_page
        
        if page_records is not None:
            params['pageRecords'] = page_records
        
        return self._make_request(
            'StandardApiAction_queryTrackDetail.action',
            params=params
        )
    
    # =====================================================================
    # GESTIÓN DE ALARMAS
    # =====================================================================
    
    def get_device_alarms(self, start_time: str, end_time: str,
                         alarm_types: Union[str, List[str]],
                         device_ids: Union[str, List[str]] = None,
                         vehicle_ids: Union[str, List[str]] = None,
                         handled: int = None,
                         geo_address: bool = False,
                         map_type: int = None,
                         current_page: int = 1,
                         page_records: int = 10) -> Dict[str, Any]:
        """
        Obtiene alarmas de dispositivos (con paginación)
        
        Args:
            start_time: Tiempo de inicio
            end_time: Tiempo de fin
            alarm_types: Tipos de alarma (lista o string separado por comas)
            device_ids: IDs de dispositivos
            vehicle_ids: IDs de vehículos
            handled: Estado de manejo (1=manejado, 0=no manejado, None=todos)
            geo_address: Si resolver posición geográfica
            map_type: Conversión de coordenadas
            current_page: Página actual
            page_records: Registros por página
            
        Returns:
            Lista paginada de alarmas
        """
        params = {
            'begintime': start_time,
            'endtime': end_time,
            'currentPage': current_page,
            'pageRecords': page_records
        }
        
        # Tipos de alarma
        if isinstance(alarm_types, list):
            params['armType'] = ','.join(map(str, alarm_types))
        else:
            params['armType'] = alarm_types
        
        # Dispositivos
        if device_ids:
            if isinstance(device_ids, list):
                params['devIdno'] = ','.join(device_ids)
            else:
                params['devIdno'] = device_ids
        
        # Vehículos
        if vehicle_ids:
            if isinstance(vehicle_ids, list):
                params['vehiIdno'] = ','.join(vehicle_ids)
            else:
                params['vehiIdno'] = vehicle_ids
        
        if handled is not None:
            params['handle'] = handled
        
        if geo_address:
            params['geoaddress'] = 1
        
        if map_type:
            params['toMap'] = map_type
        
        return self._make_request(
            'StandardApiAction_queryAlarmDetail.action',
            params=params
        )
    
    def get_realtime_alarms(self, device_id: str = None, 
                           map_type: int = None) -> Dict[str, Any]:
        """
        Obtiene alarmas en tiempo real
        
        Args:
            device_id: ID del dispositivo (debe estar online)
            map_type: Conversión de coordenadas
            
        Returns:
            Alarmas en tiempo real del dispositivo
        """
        params = {}
        
        if device_id:
            params['DevIDNO'] = device_id
        
        if map_type:
            params['toMap'] = map_type
        
        return self._make_request(
            'StandardApiAction_vehicleAlarm.action',
            params=params
        )
    
    # =====================================================================
    # GESTIÓN DE VIDEOS
    # =====================================================================
    
    def request_realtime_video(self, device_id: str, channels: Union[str, List[int]],
                              duration: int, label: str = "api_request") -> Dict[str, Any]:
        """
        Solicita grabación de video en tiempo real
        
        Args:
            device_id: ID del dispositivo (debe estar online)
            channels: Canales de video (string separado por comas o lista)
            duration: Duración en segundos (0-1800, 0 para detener)
            label: Etiqueta para el video
            
        Returns:
            Confirmación de la solicitud
        """
        params = {
            'DevIDNO': device_id,
            'Sec': duration,
            'Label': label
        }
        
        if isinstance(channels, list):
            params['Chn'] = ','.join(map(str, channels))
        else:
            params['Chn'] = channels
        
        return self._make_request(
            'StandardApiAction_realTimeVedio.action',
            params=params
        )
    
    def query_video_files(self, device_id: str, location: int, channel: int,
                         year: str, month: str, day: str,
                         record_type: int = -1, file_type: int = 2,
                         start_seconds: int = 0, end_seconds: int = 86399,
                         **kwargs) -> Dict[str, Any]:
        """
        Consulta archivos de video
        
        Args:
            device_id: ID del dispositivo
            location: Ubicación de búsqueda (1=dispositivo, 2=servidor, 4=descarga)
            channel: Canal (0=canal 1, 1=canal 2, -1=todos)
            year: Año de búsqueda
            month: Mes de búsqueda
            day: Día de búsqueda
            record_type: Tipo de grabación (0=general, 1=alarma, -1=todos)
            file_type: Tipo de archivo (1=imagen, 2=video)
            start_seconds: Segundos de inicio (0-86399)
            end_seconds: Segundos de fin (0-86399)
            **kwargs: Parámetros adicionales para dispositivos 1078
            
        Returns:
            Lista de archivos de video disponibles
        """
        params = {
            'DevIDNO': device_id,
            'LOC': location,
            'CHN': channel,
            'YEAR': year,
            'MON': month,
            'DAY': day,
            'RECTYPE': record_type,
            'FILEATTR': file_type,
            'BEG': start_seconds,
            'END': end_seconds
        }
        
        # Parámetros adicionales para 1078
        optional_params = ['ARM1', 'ARM2', 'RES', 'STREAM', 'STORE', 'LABEL']
        for param in optional_params:
            if param.lower() in kwargs:
                params[param] = kwargs[param.lower()]
        
        return self._make_request(
            'StandardApiAction_getVideoFileInfo.action',
            params=params
        )
    
    def capture_picture(self, device_id: str, channel: str, 
                       resolution: int = 1) -> Dict[str, Any]:
        """
        Captura una imagen del dispositivo
        
        Args:
            device_id: ID del dispositivo (debe estar online)
            channel: Canal del dispositivo (0=canal 1, 1=canal 2)
            resolution: Resolución (1=320x240, 2=640x480, etc.)
            
        Returns:
            Información de la imagen capturada
        """
        params = {
            'DevIDNO': device_id,
            'Chn': channel,
            'Type': 1,
            'Resolution': resolution
        }
        
        return self._make_request(
            'StandardApiAction_capturePicture.action',
            params=params
        )
    
    # =====================================================================
    # CONTROL DE VEHÍCULOS
    # =====================================================================
    
    def control_gps_reporting(self, device_id: str, interval: int) -> Dict[str, Any]:
        """
        Controla el intervalo de reporte GPS
        
        Args:
            device_id: ID del dispositivo
            interval: Intervalo en segundos (0-3600, 0=no reportar GPS)
            
        Returns:
            Confirmación del control
        """
        params = {
            'DevIDNO': device_id,
            'Time': interval
        }
        
        return self._make_request(
            'StandardApiAction_vehicleControlGPSReport.action',
            params=params
        )
    
    def control_vehicle(self, device_id: str, control_type: int,
                       username: str, password: str) -> Dict[str, Any]:
        """
        Controla funciones del vehículo
        
        Args:
            device_id: ID del dispositivo
            control_type: Tipo de control:
                1=Cortar combustible, 2=Recuperar combustible,
                3=Apagar energía, 4=Encender energía, 5=Reiniciar dispositivo,
                6=Restaurar configuración de fábrica, 7=Dormir, 8=Despertar,
                9=Iniciar grabación, 10=Detener grabación, etc.
            username: Nombre de usuario
            password: Contraseña (se aplicará MD5)
            
        Returns:
            Confirmación del control
        """
        # Aplicar hash MD5 a la contraseña si no es ya un hash
        if len(password) != 32:
            password = hashlib.md5(password.encode('utf-8')).hexdigest()
        
        params = {
            'DevIDNO': device_id,
            'CtrlType': control_type,
            'Usr': username,
            'Pwd': password
        }
        
        return self._make_request(
            'StandardApiAction_vehicleControlOthers.action',
            params=params
        )
    
    def send_tts_message(self, device_id: str, text: str, flag: int = 4) -> Dict[str, Any]:
        """
        Envía mensaje TTS al dispositivo
        
        Args:
            device_id: ID del dispositivo (debe estar online)
            text: Texto a reproducir (máximo 240 caracteres)
            flag: Banderas TTS:
                1=Emergencia, 4=Mostrar en terminal, 8=TTS broadcast,
                16=Mostrar en pantalla publicitaria
                Se pueden combinar sumando valores
                
        Returns:
            Confirmación del envío
        """
        params = {
            'DevIDNO': device_id,
            'Text': text,
            'Flag': flag
        }
        
        return self._make_request(
            'StandardApiAction_vehicleTTS.action',
            params=params
        )
    
    def control_ptz(self, device_id: str, channel: int, command: int,
                   speed: int = 1, param: int = 1) -> Dict[str, Any]:
        """
        Controla cámara PTZ
        
        Args:
            device_id: ID del dispositivo
            channel: Canal de la cámara
            command: Comando de control:
                0=izquierda, 1=derecha, 2=arriba, 3=abajo,
                4=izquierda arriba, 5=derecha arriba, etc.
            speed: Velocidad (0-255)
            param: Parámetro para operaciones de preset
            
        Returns:
            Confirmación del control PTZ
        """
        params = {
            'DevIDNO': device_id,
            'Chn': channel,
            'Command': command,
            'Speed': speed,
            'Param': param
        }
        
        return self._make_request(
            'StandardApiAction_sendPTZControl.action',
            params=params
        )
    
    # =====================================================================
    # GESTIÓN DE DISPOSITIVOS
    # =====================================================================
    
    def get_device_info(self, device_id: str) -> Dict[str, Any]:
        """
        Obtiene información detallada de un dispositivo
        
        Args:
            device_id: ID del dispositivo (debe estar online)
            
        Returns:
            Información detallada del dispositivo
        """
        params = {'devIdno': device_id}
        
        return self._make_request(
            'StandardApiAction_getLoadDeviceInfo.action',
            params=params
        )
    
    def add_device(self, device_id: str, protocol: str, device_type: str,
                  company_name: str, factory_type: int,
                  account: str = None, **kwargs) -> Dict[str, Any]:
        """
        Agrega un nuevo dispositivo
        
        Args:
            device_id: ID del dispositivo
            protocol: Protocolo (0=desconocido, 1=estándar 2011, 2=brújula, 3=1078)
            device_type: Tipo de dispositivo (7=video, 5=GPS, -7=terminal defensa)
            company_name: Nombre de la empresa
            factory_type: Tipo de fabricante
            account: Cuenta maestra (requerida si la empresa no existe)
            **kwargs: Parámetros opcionales adicionales
            
        Returns:
            Confirmación de la adición
        """
        params = {
            'devIdno': device_id,
            'protocol': protocol,
            'devType': device_type,
            'companyName': company_name,
            'factoryType': factory_type
        }
        
        if account:
            params['account'] = account
        
        # Parámetros opcionales
        optional_params = ['channelNum', 'model', 'factory', 'audioCodec']
        for param in optional_params:
            if param in kwargs:
                params[param] = kwargs[param]
        
        return self._make_request(
            'StandardApiAction_addDevice.action',
            params=params
        )
    
    def add_vehicle(self, vehicle_id: str, device_id: str, device_type: str,
                   company_name: str, factory_type: int,
                   account: str = None, **kwargs) -> Dict[str, Any]:
        """
        Agrega un nuevo vehículo
        
        Args:
            vehicle_id: ID del vehículo (número de placa)
            device_id: ID del dispositivo
            device_type: Tipo de dispositivo
            company_name: Nombre de la empresa
            factory_type: Tipo de fabricante
            account: Cuenta maestra
            **kwargs: Parámetros opcionales adicionales
            
        Returns:
            Confirmación de la adición
        """
        params = {
            'vehiIdno': vehicle_id,
            'devIdno': device_id,
            'devType': device_type,
            'companyName': company_name,
            'factoryType': factory_type
        }
        
        if account:
            params['account'] = account
        
        # Parámetros opcionales
        optional_params = ['name', 'area', 'fleetName', 'simCard', 'serialId']
        for param in optional_params:
            if param in kwargs:
                params[param] = kwargs[param]
        
        return self._make_request(
            'StandardApiAction_addVehicle.action',
            params=params
        )
    
    def delete_device(self, device_id: str) -> Dict[str, Any]:
        """
        Elimina un dispositivo
        
        Args:
            device_id: ID del dispositivo
            
        Returns:
            Confirmación de la eliminación
        """
        params = {'devIdno': device_id}
        
        return self._make_request(
            'StandardApiAction_deleteDevice.action',
            params=params
        )
    
    def delete_vehicle(self, vehicle_id: str, delete_device: bool = False) -> Dict[str, Any]:
        """
        Elimina un vehículo
        
        Args:
            vehicle_id: ID del vehículo
            delete_device: Si eliminar también el dispositivo asociado
            
        Returns:
            Confirmación de la eliminación
        """
        params = {'vehiIdno': vehicle_id}
        
        if delete_device:
            params['delDevice'] = '1'
        
        return self._make_request(
            'StandardApiAction_deleteVehicle.action',
            params=params
        )
    
    # =====================================================================
    # REPORTES Y ANÁLISIS
    # =====================================================================
    
    def get_vehicle_mileage(self, start_time: str, end_time: str,
                           vehicle_ids: Union[str, List[str]] = None,
                           current_page: int = None,
                           page_records: int = None) -> Dict[str, Any]:
        """
        Obtiene reporte de kilometraje de vehículos
        
        Args:
            start_time: Tiempo de inicio
            end_time: Tiempo de fin
            vehicle_ids: IDs de vehículos
            current_page: Página actual
            page_records: Registros por página
            
        Returns:
            Reporte de kilometraje
        """
        params = {
            'begintime': start_time,
            'endtime': end_time
        }
        
        if vehicle_ids:
            if isinstance(vehicle_ids, list):
                params['vehiIdno'] = ','.join(vehicle_ids)
            else:
                params['vehiIdno'] = vehicle_ids
        
        if current_page is not None:
            params['currentPage'] = current_page
        
        if page_records is not None:
            params['pageRecords'] = page_records
        
        return self._make_request(
            'StandardApiAction_runMileage.action',
            params=params
        )
    
    def get_parking_detail(self, start_time: str, end_time: str,
                          park_time: int, map_type: int,
                          vehicle_ids: Union[str, List[str]] = None,
                          geo_address: bool = False,
                          current_page: int = None,
                          page_records: int = None) -> Dict[str, Any]:
        """
        Obtiene detalles de estacionamiento
        
        Args:
            start_time: Tiempo de inicio
            end_time: Tiempo de fin
            park_time: Tiempo mínimo de estacionamiento en segundos
            map_type: Conversión de coordenadas
            vehicle_ids: IDs de vehículos
            geo_address: Si resolver posición geográfica
            current_page: Página actual
            page_records: Registros por página
            
        Returns:
            Detalles de estacionamiento
        """
        params = {
            'begintime': start_time,
            'endtime': end_time,
            'parkTime': park_time,
            'toMap': map_type
        }
        
        if vehicle_ids:
            if isinstance(vehicle_ids, list):
                params['vehiIdno'] = ','.join(vehicle_ids)
            else:
                params['vehiIdno'] = vehicle_ids
        
        if geo_address:
            params['geoaddress'] = 1
        
        if current_page is not None:
            params['currentPage'] = current_page
        
        if page_records is not None:
            params['pageRecords'] = page_records
        
        return self._make_request(
            'StandardApiAction_parkDetail.action',
            params=params
        )
    
    # =====================================================================
    # GESTIÓN DE ÁREAS
    # =====================================================================
    
    def get_user_areas(self) -> Dict[str, Any]:
        """
        Obtiene las áreas del usuario
        
        Returns:
            Lista de áreas definidas por el usuario
        """
        return self._make_request('StandardApiAction_getUserMarkers.action')
    
    def add_area(self, name: str, marker_type: int, longitude: str, latitude: str,
                map_type: int = None, radius: int = None, share: int = 0,
                area_type: int = None, color: str = 'FF0000',
                remark: str = None) -> Dict[str, Any]:
        """
        Agrega una nueva área
        
        Args:
            name: Nombre del área
            marker_type: Tipo de área (1=punto, 2=rectángulo, 3=polígono, 4=ruta, 10=círculo)
            longitude: Longitud (puede ser múltiple separado por comas)
            latitude: Latitud (puede ser múltiple separado por comas)
            map_type: Tipo de mapa (0=Google, 3=Baidu, 4=Gaode)
            radius: Radio en metros (requerido para círculos)
            share: Compartir área (0=no compartir, 1=compartir grupo, 2=compartir todo)
            area_type: Tipo de geografía (2=villa, 3=fábrica, etc.)
            color: Color en formato hexadecimal
            remark: Observaciones
            
        Returns:
            ID del área creada
        """
        params = {
            'name': name,
            'markerType': marker_type,
            'jingDu': longitude,
            'weiDu': latitude,
            'share': share,
            'color': color
        }
        
        if map_type is not None:
            params['mapType'] = map_type
        
        if radius is not None:
            params['radius'] = radius
        
        if area_type is not None:
            params['type'] = area_type
        
        if remark:
            params['remark'] = remark
        
        return self._make_request(
            'MapMarkerAction_addMark.action',
            params=params
        )
    
    def edit_area(self, area_id: int, **kwargs) -> Dict[str, Any]:
        """
        Edita un área existente
        
        Args:
            area_id: ID del área
            **kwargs: Parámetros a actualizar (mismos que add_area)
            
        Returns:
            Confirmación de la edición
        """
        params = {'id': area_id}
        params.update(kwargs)
        
        return self._make_request(
            'MapMarkerAction_editMark.action',
            params=params
        )
    
    def get_area(self, area_id: int) -> Dict[str, Any]:
        """
        Obtiene información de un área específica
        
        Args:
            area_id: ID del área
            
        Returns:
            Información detallada del área
        """
        params = {'id': area_id}
        
        return self._make_request(
            'MapMarkerAction_findMark.action',
            params=params
        )
    
    def delete_area(self, area_id: int) -> Dict[str, Any]:
        """
        Elimina un área
        
        Args:
            area_id: ID del área
            
        Returns:
            Confirmación de la eliminación
        """
        params = {'id': area_id}
        
        return self._make_request(
            'MapMarkerAction_deleteMark.action',
            params=params
        )
    
    # =====================================================================
    # MÉTODOS DE UTILIDAD
    # =====================================================================
    
    def is_session_valid(self) -> bool:
        """
        Verifica si la sesión actual es válida
        
        Returns:
            True si la sesión es válida, False en caso contrario
        """
        if not self.jsession:
            return False
        
        try:
            # Intentar una operación simple que requiera sesión
            self.get_user_vehicles()
            return True
        except APIError as e:
            if e.code == 5:  # Session does not exist
                return False
            # Si es otro error, la sesión podría ser válida
            return True
        except Exception:
            return False
    
    def get_session_info(self) -> Dict[str, Any]:
        """
        Obtiene información de la sesión actual
        
        Returns:
            Información de la sesión
        """
        return {
            'jsession': self.jsession,
            'account_name': self.account_name,
            'is_valid': self.is_session_valid()
        }
    
    def __enter__(self):
        """Soporte para context manager"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Limpieza al salir del context manager"""
        if self.jsession:
            try:
                self.logout()
            except Exception:
                pass  # Ignorar errores durante logout


# =====================================================================
# FUNCIONES DE UTILIDAD
# =====================================================================

def create_md5_password(password: str) -> str:
    """
    Crea un hash MD5 de una contraseña
    
    Args:
        password: Contraseña en texto plano
        
    Returns:
        Hash MD5 de la contraseña
    """
    return hashlib.md5(password.encode('utf-8')).hexdigest()


def parse_coordinates(lng: int, lat: int) -> tuple:
    """
    Convierte coordenadas del formato de la API al formato estándar
    
    Args:
        lng: Longitud en formato API (ej: 113231258)
        lat: Latitud en formato API (ej: 39231258)
        
    Returns:
        Tupla con (longitud, latitud) en formato decimal
    """
    return (lng / 1000000.0, lat / 1000000.0)


def format_speed(speed: int) -> float:
    """
    Convierte velocidad del formato API a km/h
    
    Args:
        speed: Velocidad en formato API
        
    Returns:
        Velocidad en km/h
    """
    return speed / 10.0


def format_fuel(fuel: int) -> float:
    """
    Convierte combustible del formato API a litros
    
    Args:
        fuel: Combustible en formato API
        
    Returns:
        Combustible en litros
    """
    return fuel / 100.0


