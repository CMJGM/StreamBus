import logging
import os
import re
import requests
import time
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
from django.db import connections
from django.conf import settings
from django.core.cache import cache
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from urllib.parse import urlencode
from .models import informe_sit
from .citos_library import GPSCameraAPI, APIError

logger = logging.getLogger(__name__)

# =========================================================================
# SISTEMA DE MIGRACIÓN GRADUAL A CITOS
# =========================================================================

# Importar adapter si está habilitado
if getattr(settings, 'USE_CITOS_LIBRARY', False):
    try:
        from .gps_adapter import get_gps_adapter
        _use_citos = True
        _adapter = get_gps_adapter()
        logger.info("Citos library activada - usando funciones avanzadas")
    except ImportError as e:
        logger.info(f"Error importando citos adapter: {e}")
        _use_citos = False
        _adapter = None
else:
    _use_citos = False
    _adapter = None
    logger.info("Usando funciones GPS legacy")

def _should_use_citos(function_name: str) -> bool:
    """Decide si usar citos para una función específica"""
    if not _use_citos or not _adapter:
        return False
    
    enabled_functions = getattr(settings, 'CITOS_ENABLED_FUNCTIONS', {})
    return enabled_functions.get(function_name, False)



BASE_URL = "http://190.183.254.253:8088"
DEFAULT_TIMEOUT = 50

def gps_login(account: str, password: str) -> str:
    payload = {
        "account": account,
        "password": password
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json,text/html"
    }

    try:
        gps_url_login = BASE_URL+"/StandardApiAction_login.action"
        response = requests.post(gps_url_login, data=payload, headers=headers)        

        if response.headers.get("Content-Type", "").startswith("application/json"):
            data = response.json()
            if data.get("result") == 0:
                return data["jsession"]
            else:
                raise Exception(f"Error en login: {data.get('msg')}")
        else:
            raise Exception("Respuesta no es JSON. Puede que el login haya fallado.")
    except Exception as e:
        logger.info(f"Excepción al intentar hacer login: {e}")
        return None
    
def logout_api(jsession):    
    endpoint = "/StandardApiAction_logout.action"
    url = f"{BASE_URL}{endpoint}"
    
    params = {"jsession": jsession}
    
    try:
        response = requests.get(url, params=params)      
        response.raise_for_status()        
        return response.json()
    
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error al realizar la solicitud: {str(e)}")
    except ValueError as e:
        raise Exception(f"Error al procesar la respuesta JSON: {str(e)}")

def obtener_informe_sit(idinforme):
    with connections['SIT'].cursor() as cursor:
        cursor.execute("SELECT * FROM SIT.dbo.PerInformeDetalladoByIdInforme(%s)", [idinforme])
        columnas = [col[0] for col in cursor.description]
        resultados = [
            informe_sit(**dict(zip(columnas, fila)))
            for fila in cursor.fetchall()
        ]
    return resultados

def obtener_ultima_ubicacion(vehi_idno=None, to_map=2, geoaddress=0, current_page=1, page_records=50): 
    # Decidir qué implementación usar
    if _should_use_citos('obtener_ultima_ubicacion'):
        try:
            return _adapter.obtener_ultima_ubicacion(vehi_idno, to_map, geoaddress, current_page, page_records)
        except Exception as e:
            logger.info(f"⚠️ Citos falló, usando legacy: {e}")
            # IMPORTANTE: Llamar directamente a legacy SIN pasar por esta función
            return obtener_ultima_ubicacion_legacy(vehi_idno, to_map, geoaddress, current_page, page_records)
    
    # Si no usamos citos, usar legacy directamente
    return obtener_ultima_ubicacion_legacy(vehi_idno, to_map, geoaddress, current_page, page_records)

def obtener_ultima_ubicacion_legacy(vehi_idno=None, to_map=2, geoaddress=0, current_page=1, page_records=50):
    """Función legacy original - NUNCA MODIFICAR"""
    url = BASE_URL+"/StandardApiAction_vehicleStatus.action"
    
    params = {
        "jsession": settings.JSESSION_GPS,
        "toMap": to_map,
        "geoaddress": geoaddress,
        "currentPage": current_page,
        "pageRecords": page_records,
    }

    if vehi_idno:
        params["vehiIdno"] = vehi_idno

    try:
        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        if data.get("result") == 0 and data.get("infos"):
            info = data["infos"][0]
            longitud = info.get("jd") / 1000000.0 if info.get("jd") else None
            latitud = info.get("wd") / 1000000.0 if info.get("wd") else None
            timestamp = info.get("tm")  # milisegundos       
            direccion = info.get("pos", "") # No se carga, parametro siempre en nulo por que la cantidad de coches hace la busqueda muy lenta
            velocidad = None  # No se encuentra en la respuesta

            return latitud, longitud, velocidad, timestamp, direccion
        else:
            logger.info(f"Error en respuesta: {data}")
            return None, None, None, None, None
    except requests.RequestException as e:
        logger.info(f"Error de conexión: {e}")
        return None, None, None, None, None

def obtener_vehiculos():
    url = BASE_URL+"/StandardApiAction_queryUserVehicle.action"
    params = {
        "jsession": settings.JSESSION_GPS,
        "language": "en"
    }

    try:
        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        logger.info("------------------>>>", data)
        # Verificar si estamos desconectados o la sesión expiró
        if data.get("result") in [2, 4, 5] or 'error' in data.get("errmsg", "").lower() or 'expired' in data.get("errmsg", "").lower():
            logger.info("Sesión expirada o desconectada. Intentando reconexión...")
            
            # Intentar desconectar la sesión actual primero (por si acaso)
            try:
                logout_api(settings.JSESSION_GPS)
            except Exception as e:
                logger.info(f"Error al desconectar la sesión anterior: {e}")
                
            # Realizar un nuevo login
            new_jsession = gps_login(settings.GPS_ACCOUNT, settings.GPS_PASSWORD)
            
            if new_jsession:
                # Actualizar la sesión en settings
                settings.JSESSION_GPS = new_jsession
                logger.info(f"Reconexión exitosa. Nueva jsession: {new_jsession[:10]}...")
                
                # Volver a intentar obtener los vehículos con la nueva sesión
                params["jsession"] = new_jsession
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
        
        vehicles = data.get("vehicles", [])
        return vehicles

    except Exception as e:
        logger.info(f"Error al obtener vehículos: {e}")
        
        # Intentar reconexión en caso de cualquier error
        try:
            logger.info("Intentando reconexión debido a error...")
            new_jsession = gps_login(settings.GPS_ACCOUNT, settings.GPS_PASSWORD)
            
            if new_jsession:
                # Actualizar la sesión en settings
                settings.JSESSION_GPS = new_jsession
                logger.info(f"Reconexión exitosa. Nueva jsession: {new_jsession[:10]}...")
                
                # Volver a intentar obtener los vehículos con la nueva sesión
                params["jsession"] = new_jsession
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                vehicles = data.get("vehicles", [])
                logger.info(f"Cantidad de vehículos obtenidos tras reconexión: {len(vehicles)}")
                return vehicles
        except Exception as reconnect_error:
            logger.info(f"Error en reconexión: {reconnect_error}")
        
        return []

def obtener_estado_dispositivo(vehi_idno=None, dev_idno=None, to_map=2, geoaddress=1, driver=0, language="es"):
    url = BASE_URL+"/StandardApiAction_getDeviceStatus.action"

    params = {
        "jsession": settings.JSESSION_GPS,
        "toMap": to_map,
        "geoaddress": geoaddress,
        "driver": driver,
        "language": language
    }

    # Priorizar devIdno si está disponible, de lo contrario usar vehiIdno
    if dev_idno:
        params["devIdno"] = dev_idno
    elif vehi_idno:
        params["vehiIdno"] = vehi_idno
    else:
        return None, None, None, None, None, None

    try:
        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        if data.get("result") == 0 and data.get("status"):
            info = data["status"][0]
            longitud = info.get("lng") / 1000000.0 if info.get("lng") else None
            latitud = info.get("lat") / 1000000.0 if info.get("lat") else None
            timestamp = info.get("gt")  # formato de fecha como string
            
            # Obtener velocidad y convertirla (dividir por 10)
            velocidad = info.get("sp") / 10.0 if info.get("sp") is not None else None
            direccion = info.get("ps", "")  # Obtener la dirección
            
            # Detectar posibles alertas de velocidad
            alertas = []
            
            # Alerta de ADAS nivel 1 - sobre límite de señales viales
            if info.get("adas1") is not None and (info.get("adas1") & (1 << 5)):
                alertas.append("Alerta de límite de velocidad (señal vial)")
                
            # Alerta de ADAS nivel 2 - sobre límite de señales viales
            if info.get("adas2") is not None and (info.get("adas2") & (1 << 5)):
                alertas.append("Alerta grave de límite de velocidad (señal vial)")
                
            # Alerta de velocidad en curvas
            if info.get("adas1") is not None and (info.get("adas1") & (1 << 7)):
                alertas.append("Advertencia de velocidad en curva")
            
            # Dirección de movimiento
            direccion_movimiento = info.get("hx")  # Dirección en grados (0=Norte, aumenta en sentido horario)
            
            return latitud, longitud, velocidad, timestamp, direccion, alertas, direccion_movimiento
        else:
            logger.info(f"Error en respuesta: {data}")
            return None, None, None, None, None, None, None
    except requests.RequestException as e:
        logger.info(f"Error de conexión: {e}")
        return None, None, None, None, None, None, None
    except ValueError as e:
        logger.info(f"Error al procesar la respuesta JSON: {e}")
        return None, None, None, None, None, None, None
    
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#  ALARMAS
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

class AlarmAPIError(Exception):
    pass

# Es una función auxiliar que hace la petición HTTP al servidor usando requests. 
# Envía los parámetros, verifica errores y devuelve la respuesta en formato dict.
def make_request(endpoint, params, method="GET"):
    url = f"{BASE_URL}/{endpoint}"    
    try:
        if method.upper() == "POST":
            response = requests.post(url, data=params, timeout=DEFAULT_TIMEOUT)
        else:
            response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)

        response.raise_for_status()
        data = response.json()
        if data.get("result") != 0:
            raise AlarmAPIError(f"API error: {data}")
        return data
    except (requests.RequestException, ValueError) as e:
        raise AlarmAPIError(f"Request failed: {e}")

# 1. Security Evidence Inquiry
# Consulta evidencias de seguridad. Devuelve una lista de eventos con fotos captadas por el sistema en un rango de tiempo determinado.
#📥 Parámetros importantes:
#       jsession: token de sesión.
#       vehiIdno: identificador del vehículo.
#       begintime, endtime: rango de fechas (formato "YYYY-MM-DD HH:MM:SS").
#       alarmType: tipo de alarma (ej. 72 = ADAS, 78 = DMS).
#       mediaType: 0 para fotos, 1 para video.
#       📤 Devuelve una lista de eventos que contienen URLs de imágenes o videos.
def get_performance_report_photos(vehi_idno, begintime, endtime, alarm_type,media_type=0, to_map=None, current_page=None, page_records=None
):
    params = {
        "jsession": settings.JSESSION_GPS,
        "vehiIdno": vehi_idno,
        "begintime": begintime,
        "endtime": endtime,
        "alarmType": alarm_type,
    }
    if media_type is not None:
        params["mediaType"] = media_type
    if to_map is not None:
        params["toMap"] = to_map
    if current_page is not None:
        params["currentPage"] = current_page
    if page_records is not None:
        params["pageRecords"] = page_records

    return make_request("StandardApiAction_performanceReportPhotoListSafe.action", params)



# 2. Evidence Query
# Consulta detalles de una evidencia específica (con guid), incluyendo posibles fotos relacionadas.
def get_alarm_evidence(dev_idno, begintime, alarm_type, guid, to_map=None, md5=None):
    params = {
        "jsession": settings.JSESSION_GPS,
        "devIdno": dev_idno,
        "begintime": begintime,
        "alarmType": alarm_type,
        "guid": guid
    }
    if to_map is not None:
        params["toMap"] = to_map
    if md5 is not None:
        params["md5"] = md5

    return make_request("StandardApiAction_alarmEvidence.action", params)


# 3. Security Alarm Inquiry (básico)
# Lista alarmas de seguridad detectadas por los dispositivos.
def get_device_alarm(current_page=None, page_records=None):
    params = {
        "jsession": settings.JSESSION_GPS
    }
    if current_page is not None:
        params["currentPage"] = current_page
    if page_records is not None:
        params["pageRecords"] = page_records

    return make_request("StandardApiAction_queryAlarmList.action", params)


# 4. Download Evidence
# Devuelve la URL para descargar un archivo .zip con las evidencias asociadas a un evento.
def get_zip_alarm_evidence_url(extra_params: dict):
    params = {"jsession": settings.JSESSION_GPS}
    params.update(extra_params)
    query_string = urlencode(params)
    return f"{BASE_URL}/StandardApiAction_zipAlarmEvidence.action?{query_string}"

#url = 'http://190.183.254.253:6603/3/5?DownType=2&LOC=2&CHN=1&YEAR=2025&MON=05&DAY=20&RECTYPE=-1&FILEATTR=1&BEG=0&END=86399&ARM1=0&ARM2=0&RES=0&STREAM=-1&STORE=0&host=190.183.254.253&jsession='+settings.JSESSION_GPS+'&YEARE=202525&MONE=05&DAYE=20&COMPANYID=11&USERID=25'

def old_download_and_save_image(url, filename):

    save_path = os.path.join(settings.MEDIA_ROOT, 'security_photos')
    os.makedirs(save_path, exist_ok=True)
    file_path = os.path.join(save_path, filename)

    if os.path.exists(file_path):
        return True
    
    try:
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()  # Para detectar errores HTTP
    except requests.RequestException as e:
        logger.info(f"Error descargando {url}: {e}")
        return False
    
    with open(file_path, 'wb') as f:
        f.write(response.content)    
    return True


def crear_nombre_carpeta_vehiculo(vehiIdno, devIdno=None):
    """
    Crea nombre de carpeta híbrido para organizar fotos por vehículo
    
    Args:
        vehiIdno: Ficha del vehículo (puede ser None o vacío)
        devIdno: ID del dispositivo GPS
        
    Returns:
        str: Nombre de carpeta sanitizado
        
    Ejemplos:
        - vehiIdno="001", devIdno="10041" → "vehiculo_001_device_10041"
        - vehiIdno=None, devIdno="10041" → "device_10041"
        - vehiIdno="", devIdno="10041" → "device_10041"
    """
    # Sanitizar vehiIdno
    vehiculo_clean = None
    if vehiIdno and str(vehiIdno).strip():
        vehiculo_clean = sanitizar_nombre_archivo(str(vehiIdno).strip())
    
    # Sanitizar devIdno
    device_clean = "unknown"
    if devIdno:
        device_clean = sanitizar_nombre_archivo(str(devIdno).replace('C', '').replace('c', ''))
    
    # Crear nombre híbrido
    if vehiculo_clean:
        folder_name = f"ficha_{vehiculo_clean}_mdvr_{device_clean}"
    else:
        folder_name = f"mdvr_{device_clean}"
    
    # Validar longitud (límite de 100 caracteres para compatibilidad)
    if len(folder_name) > 100:
        # Truncar manteniendo parte importante
        folder_name = f"ficha_trunc_mdvr_{device_clean}"[:100]
    
    return folder_name


def sanitizar_nombre_archivo(nombre):
    """
    Sanitiza nombres de archivo/carpeta removiendo caracteres problemáticos
    
    Args:
        nombre: Nombre a sanitizar
        
    Returns:
        str: Nombre sanitizado seguro para sistema de archivos
    """
    if not nombre:
        return "unknown"
    
    # Remover caracteres especiales, mantener solo alfanuméricos, guiones y underscores
    sanitized = re.sub(r'[^\w\-_.]', '_', str(nombre))
    
    # Remover múltiples underscores consecutivos
    sanitized = re.sub(r'_+', '_', sanitized)
    
    # Remover underscores al inicio y final
    sanitized = sanitized.strip('_')
    
    # Si queda vacío, usar default
    if not sanitized:
        sanitized = "unknown"
    
    return sanitized


def verificar_archivo_existe(file_path):
    """
    Verifica si un archivo ya existe y tiene tamaño válido
    
    Args:
        file_path: Ruta completa al archivo
        
    Returns:
        bool: True si existe y es válido, False si necesita descarga
    """
    try:
        if os.path.exists(file_path):
            # Verificar que el archivo no esté corrupto (tamaño > 0)
            size = os.path.getsize(file_path)
            if size > 0:
                logger.info(f"[⏭️ EXISTE] Archivo ya existe: {os.path.basename(file_path)} ({size} bytes)")
                return True
            else:
                logger.info(f"[🗑️ CORRUPTO] Archivo existe pero está vacío: {file_path}")
                # Eliminar archivo corrupto
                os.remove(file_path)
                return False
        return False
    except (OSError, IOError) as e:
        logger.info(f"[⚠️ ERROR] Error verificando archivo {file_path}: {e}")
        return False


def crear_nombre_archivo_foto(vehiIdno, devIdno, fileTimeStr):
    """
    Crea nombre de archivo para foto sin incluir el vehículo (ya está en carpeta)
    
    Args:
        vehiIdno: Ficha del vehículo
        devIdno: ID del dispositivo  
        fileTimeStr: Timestamp de la foto
        
    Returns:
        str: Nombre de archivo sanitizado
    """
    # Sanitizar timestamp
    date_str = fileTimeStr or 'sin_fecha'
    date_clean = date_str.replace(' ', '_').replace(':', '-').replace('/', '-')
    date_clean = sanitizar_nombre_archivo(date_clean)
    
    # Crear nombre más simple (sin vehículo porque ya está en la carpeta)
    device_clean = sanitizar_nombre_archivo(str(devIdno).replace('C', '').replace('c', ''))
    file_name = f"{date_clean}_dev_{device_clean}.jpg"
    
    return file_name

def download_and_save_image(url, full_file_path):
    """
    Descarga y guarda una imagen desde URL a ruta específica
    VERSIÓN MEJORADA: Maneja rutas completas con carpetas
    
    Args:
        url: URL de descarga
        full_file_path: Ruta completa incluyendo directorio y nombre de archivo
        
    Returns:
        bool: True si fue exitoso, False si falló
    """
    # Crear directorio padre si no existe
    os.makedirs(os.path.dirname(full_file_path), exist_ok=True)
    
    # Verificar si ya existe
    if os.path.exists(full_file_path):
        file_size = os.path.getsize(full_file_path)
        if file_size > 0:
            logger.info(f"[⏭️ SKIP] Archivo ya existe: {os.path.basename(full_file_path)}")
            return True
        else:
            # Eliminar archivo corrupto
            os.remove(full_file_path)
    
    try:
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        
        # Escribir archivo
        with open(full_file_path, 'wb') as f:
            f.write(response.content)
        
        # Verificar que se escribió correctamente
        if os.path.getsize(full_file_path) > 0:
            return True
        else:
            logger.info(f"[❌ ERROR] Archivo descargado está vacío: {full_file_path}")
            os.remove(full_file_path)
            return False
            
    except requests.RequestException as e:
        logger.info(f"[🌐 ERROR] Error descargando {url}: {e}")
        return False
    except IOError as e:
        logger.info(f"[💾 ERROR] Error escribiendo archivo {full_file_path}: {e}")
        return False

def test_folder_creation():
    """
    Función de testing para verificar creación de nombres de carpeta
    """
    test_cases = [
        ("001", "10041"),
        ("002", "10042"),
        (None, "10041"),
        ("", "10041"),
        ("ABC-123", "10041"),
        ("Veh/ículo:especial*", "10041"),
        ("123456789012345678901234567890", "10041")  # Nombre muy largo
    ]
    
    logger.info("🧪 TESTING - Creación de nombres de carpeta:")
    for vehiIdno, devIdno in test_cases:
        folder_name = crear_nombre_carpeta_vehiculo(vehiIdno, devIdno)
        logger.info(f"  Input: vehiIdno='{vehiIdno}', devIdno='{devIdno}'")
        logger.info(f"  Output: '{folder_name}'")
        logger.info(f"  Longitud: {len(folder_name)} caracteres")
        logger.debug("")



