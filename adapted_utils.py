"""
StreamBus GPS Utils - Standalone Version
Adaptado del código Django original para uso independiente
"""

import json
import logging
import os
import re
import requests
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from urllib.parse import urlencode
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuración global (reemplaza Django settings)
global_config = {}
simple_cache = {}  # Reemplaza Django cache
current_session = None  # Reemplaza settings.JSESSION_GPS

# Logger
logger = logging.getLogger(__name__)

def load_config(config_path="config.json"):
    """Cargar configuración desde archivo JSON"""
    global global_config
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            global_config = json.load(f)
        logger.info("✅ Configuración cargada correctamente")
        return True
    except Exception as e:
        logger.error(f"❌ Error cargando configuración: {e}")
        return False

def save_config(config_path="config.json"):
    """Guardar configuración en archivo JSON"""
    global global_config
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(global_config, f, indent=2, ensure_ascii=False)
        logger.info("✅ Configuración guardada correctamente")
        return True
    except Exception as e:
        logger.error(f"❌ Error guardando configuración: {e}")
        return False

def get_config(key_path, default=None):
    """Obtener valor de configuración usando path con puntos"""
    global global_config
    keys = key_path.split('.')
    value = global_config
    try:
        for key in keys:
            value = value[key]
        return value
    except (KeyError, TypeError):
        return default

def set_config(key_path, value):
    """Establecer valor de configuración usando path con puntos"""
    global global_config
    keys = key_path.split('.')
    config_ref = global_config
    for key in keys[:-1]:
        if key not in config_ref:
            config_ref[key] = {}
        config_ref = config_ref[key]
    config_ref[keys[-1]] = value

# =========================================================================
# FUNCIONES GPS ORIGINALES ADAPTADAS
# =========================================================================

def gps_login(account: str = None, password: str = None) -> str:
    """Login GPS adaptado para standalone"""
    global current_session
    
    if not account:
        account = get_config('gps.account')
    if not password:
        password = get_config('gps.password')
    
    if not account or not password:
        logger.error("❌ Credenciales GPS no configuradas")
        return None

    base_url = get_config('gps.base_url', 'http://190.183.254.253:8088')
    timeout = get_config('gps.timeout', 30)
    
    payload = {
        "account": account,
        "password": password
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json,text/html"
    }

    try:
        gps_url_login = f"{base_url}/StandardApiAction_login.action"
        response = requests.post(gps_url_login, data=payload, headers=headers, timeout=timeout)        

        if response.headers.get("Content-Type", "").startswith("application/json"):
            data = response.json()
            if data.get("result") == 0:
                current_session = data["jsession"]
                set_config('gps.current_session', current_session)
                logger.info(f"✅ Login GPS exitoso: {current_session[:10]}...")
                return current_session
            else:
                logger.error(f"❌ Error en login GPS: {data.get('msg')}")
                return None
        else:
            logger.error("❌ Respuesta no es JSON. Login GPS falló.")
            return None
    except Exception as e:
        logger.error(f"❌ Excepción en login GPS: {e}")
        return None

def logout_api(jsession=None):
    """Logout GPS adaptado"""
    global current_session
    
    if not jsession:
        jsession = current_session
    
    if not jsession:
        return {"result": 0, "message": "No hay sesión activa"}
    
    base_url = get_config('gps.base_url', 'http://190.183.254.253:8088')
    timeout = get_config('gps.timeout', 30)
    
    endpoint = "/StandardApiAction_logout.action"
    url = f"{base_url}{endpoint}"
    
    params = {"jsession": jsession}
    
    try:
        response = requests.get(url, params=params, timeout=timeout)      
        response.raise_for_status()
        result = response.json()
        
        # Limpiar sesión local
        current_session = None
        set_config('gps.current_session', None)
        
        logger.info("✅ Logout GPS exitoso")
        return result
    
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error en logout GPS: {str(e)}")
        return {"result": 1, "error": str(e)}

def ensure_gps_session():
    """Asegurar que tenemos una sesión GPS válida"""
    global current_session
    
    # Intentar cargar sesión desde config
    if not current_session:
        current_session = get_config('gps.current_session')
    
    # Si no hay sesión, hacer login
    if not current_session:
        current_session = gps_login()
    
    return current_session is not None

def obtener_vehiculos():
    """Obtener vehículos adaptado para standalone"""
    global current_session
    
    if not ensure_gps_session():
        logger.error("❌ No se pudo establecer sesión GPS")
        return []
    
    base_url = get_config('gps.base_url', 'http://190.183.254.253:8088')
    timeout = get_config('gps.timeout', 30)
    
    url = f"{base_url}/StandardApiAction_queryUserVehicle.action"
    params = {
        "jsession": current_session,
        "language": "en"
    }

    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        
        # Verificar si estamos desconectados o la sesión expiró
        if data.get("result") in [2, 4, 5] or 'error' in data.get("errmsg", "").lower():
            logger.warning("⚠️ Sesión GPS expirada. Intentando reconexión...")
            
            # Intentar nuevo login
            current_session = gps_login()
            if current_session:
                params["jsession"] = current_session
                response = requests.get(url, params=params, timeout=timeout)
                response.raise_for_status()
                data = response.json()
        
        vehicles = data.get("vehicles", [])
        logger.info(f"✅ Obtenidos {len(vehicles)} vehículos")
        return vehicles

    except Exception as e:
        logger.error(f"❌ Error obteniendo vehículos: {e}")
        
        # Intentar reconexión en caso de error
        try:
            logger.info("🔄 Intentando reconexión debido a error...")
            current_session = gps_login()
            
            if current_session:
                params["jsession"] = current_session
                response = requests.get(url, params=params, timeout=timeout)
                response.raise_for_status()
                data = response.json()
                
                vehicles = data.get("vehicles", [])
                logger.info(f"✅ Obtenidos {len(vehicles)} vehículos tras reconexión")
                return vehicles
        except Exception as reconnect_error:
            logger.error(f"❌ Error en reconexión: {reconnect_error}")
        
        return []

def obtener_empresas_disponibles():
    """Obtener lista de empresas disponibles"""
    try:
        base_url = get_config('gps.base_url', 'http://190.183.254.253:8088')
        timeout = get_config('gps.timeout', 30)
        
        if not ensure_gps_session():
            return [], []
        
        response = requests.get(
            f"{base_url}/StandardApiAction_queryUserVehicle.action",
            params={"jsession": current_session, "language": "es"},
            timeout=timeout
        )
        response.raise_for_status()
        data = response.json()

        companys = data.get("companys", [])
        vehiculos_data = data.get("vehicles", [])
        
        # Obtener solo empresas principales (pId == 0)
        empresas_principales = [e for e in companys if e.get("pId") == 0]
        
        # Calcular conteo de vehículos por empresa
        for empresa in empresas_principales:
            empresa_id = empresa.get("id")
            
            # Obtener sub-empresas
            sub_empresas = [e for e in companys if e.get("pId") == empresa_id]
            empresa_ids = [e.get("id") for e in sub_empresas]
            empresa_ids.append(empresa_id)
            
            # Contar vehículos
            vehiculos_empresa = [v for v in vehiculos_data if v.get("pid") in empresa_ids]
            empresa['vehicle_count'] = len(vehiculos_empresa)
        
        logger.info(f"✅ Obtenidas {len(empresas_principales)} empresas")
        return empresas_principales, vehiculos_data

    except Exception as e:
        logger.error(f"❌ Error obteniendo empresas: {e}")
        return [], []

def obtener_vehiculos_por_empresa(empresa_id):
    """Obtener vehículos de una empresa específica"""
    try:
        empresas, vehiculos_data = obtener_empresas_disponibles()
        
        if not empresas:
            return None
        
        companys = []
        # Reconstruir lista de companys de empresas
        for empresa in empresas:
            companys.append(empresa)
        
        # Encontrar empresa principal
        empresa_principal = next((e for e in companys if e.get("id") == int(empresa_id)), None)
        if not empresa_principal:
            return None
        
        # Obtener sub-empresas
        sub_empresas = [e for e in companys if e.get("pId") == int(empresa_id)]
        empresa_ids = [e.get("id") for e in sub_empresas]
        empresa_ids.append(int(empresa_id))
        
        # Filtrar vehículos
        vehiculos_empresa = [v for v in vehiculos_data if v.get("pid") in empresa_ids]
        
        # Extraer listas para filtrado
        vehiIdnos = []
        devIdnos = []
        
        for vehiculo in vehiculos_empresa:
            ficha = vehiculo.get("nm")
            if ficha:
                vehiIdnos.append(str(ficha))
            
            devices = vehiculo.get("dl", [])
            if devices and len(devices) > 0:
                device_id = devices[0].get("id")
                if device_id:
                    devIdnos.append(str(device_id))
        
        resultado = {
            'vehiculos': vehiculos_empresa,
            'vehiIdnos': vehiIdnos,
            'devIdnos': devIdnos,
            'empresa_info': {
                'id': empresa_principal.get('id'),
                'nombre': empresa_principal.get('nm'),
                'total_vehiculos': len(vehiculos_empresa),
                'sub_empresas': len(sub_empresas)
            }
        }
        
        logger.info(f"✅ Empresa {resultado['empresa_info']['nombre']}: {len(vehiculos_empresa)} vehículos")
        return resultado

    except Exception as e:
        logger.error(f"❌ Error obteniendo vehículos de empresa {empresa_id}: {e}")
        return None

# =========================================================================
# FUNCIONES DE UTILIDAD PARA ARCHIVOS (ADAPTADAS)
# =========================================================================

def crear_nombre_carpeta_vehiculo(vehiIdno, devIdno=None):
    """Crear nombre de carpeta para organizar fotos por vehículo"""
    vehiculo_clean = None
    if vehiIdno and str(vehiIdno).strip():
        vehiculo_clean = sanitizar_nombre_archivo(str(vehiIdno).strip())
    
    device_clean = "unknown"
    if devIdno:
        device_clean = sanitizar_nombre_archivo(str(devIdno).replace('C', '').replace('c', ''))
    
    if vehiculo_clean:
        folder_name = f"ficha_{vehiculo_clean}_mdvr_{device_clean}"
    else:
        folder_name = f"mdvr_{device_clean}"
    
    if len(folder_name) > 100:
        folder_name = f"ficha_trunc_mdvr_{device_clean}"[:100]
    
    return folder_name

def sanitizar_nombre_archivo(nombre):
    """Sanitizar nombres de archivo/carpeta"""
    if not nombre:
        return "unknown"
    
    sanitized = re.sub(r'[^\w\-_.]', '_', str(nombre))
    sanitized = re.sub(r'_+', '_', sanitized)
    sanitized = sanitized.strip('_')
    
    if not sanitized:
        sanitized = "unknown"
    
    return sanitized

def verificar_archivo_existe(file_path):
    """Verificar si un archivo ya existe y tiene tamaño válido"""
    try:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            if size > 0:
                logger.debug(f"⏭️ Archivo ya existe: {os.path.basename(file_path)} ({size} bytes)")
                return True
            else:
                logger.warning(f"🗑️ Archivo corrupto (vacío): {file_path}")
                os.remove(file_path)
                return False
        return False
    except (OSError, IOError) as e:
        logger.error(f"⚠️ Error verificando archivo {file_path}: {e}")
        return False

def crear_nombre_archivo_foto(vehiIdno, devIdno, fileTimeStr):
    """Crear nombre de archivo para foto"""
    date_str = fileTimeStr or 'sin_fecha'
    date_clean = date_str.replace(' ', '_').replace(':', '-').replace('/', '-')
    date_clean = sanitizar_nombre_archivo(date_clean)
    
    device_clean = sanitizar_nombre_archivo(str(devIdno).replace('C', '').replace('c', ''))
    file_name = f"{date_clean}_dev_{device_clean}.jpg"
    
    return file_name

def download_and_save_image(url, full_file_path):
    """Descargar y guardar una imagen desde URL"""
    os.makedirs(os.path.dirname(full_file_path), exist_ok=True)
    
    if os.path.exists(full_file_path):
        file_size = os.path.getsize(full_file_path)
        if file_size > 0:
            logger.debug(f"⏭️ Archivo ya existe: {os.path.basename(full_file_path)}")
            return True
        else:
            os.remove(full_file_path)
    
    timeout = get_config('download.timeout', 50)
    
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        
        with open(full_file_path, 'wb') as f:
            f.write(response.content)
        
        if os.path.getsize(full_file_path) > 0:
            logger.debug(f"✅ Descargado: {os.path.basename(full_file_path)}")
            return True
        else:
            logger.error(f"❌ Archivo descargado está vacío: {full_file_path}")
            os.remove(full_file_path)
            return False
            
    except requests.RequestException as e:
        logger.error(f"🌐 Error descargando {url}: {e}")
        return False
    except IOError as e:
        logger.error(f"💾 Error escribiendo archivo {full_file_path}: {e}")
        return False

# =========================================================================
# FUNCIONES DE ALARMAS Y FOTOS (ADAPTADAS)
# =========================================================================

class AlarmAPIError(Exception):
    pass

def make_request(endpoint, params, method="GET"):
    """Hacer petición HTTP al servidor GPS"""
    base_url = get_config('gps.base_url', 'http://190.183.254.253:8088')
    timeout = get_config('gps.timeout', 30)
    
    url = f"{base_url}/{endpoint}"
    
    try:
        if method.upper() == "POST":
            response = requests.post(url, data=params, timeout=timeout)
        else:
            response = requests.get(url, params=params, timeout=timeout)

        response.raise_for_status()
        data = response.json()
        
        if data.get("result") != 0:
            raise AlarmAPIError(f"API error: {data}")
            
        return data
        
    except (requests.RequestException, ValueError) as e:
        raise AlarmAPIError(f"Request failed: {e}")

def query_security_photos(
    begintime: str,
    endtime: str,
    current_page: int = 1,
    page_records: int = 50,
    vehiIdnos: list = None,
    devIdnos: list = None
):
    """Consulta fotos de seguridad con filtrado PRE-API"""
    global current_session
    
    if not ensure_gps_session():
        logger.error("❌ No se pudo establecer sesión GPS")
        return None
    
    endpoint = "StandardApiAction_queryPhoto.action"
    
    params = {
        "jsession": current_session,
        "filetype": 2,
        "alarmType": 1,
        "begintime": begintime,
        "endtime": endtime,
        "currentPage": current_page,
        "pageRecords": page_records,
    }
    
    # Filtrado PRE-API
    filtro_aplicado = False
    
    if vehiIdnos and len(vehiIdnos) > 0:
        max_vehicles = 50
        vehicles_chunk = vehiIdnos[:max_vehicles]
        params["vehiIdno"] = ','.join(vehicles_chunk)
        filtro_aplicado = True
        logger.info(f"🔍 Filtro PRE-API por vehículos: {len(vehicles_chunk)} fichas")
        
        if len(vehiIdnos) > max_vehicles:
            logger.warning(f"⚠️ Truncados {len(vehiIdnos) - max_vehicles} vehículos por límite de API")
    
    elif devIdnos and len(devIdnos) > 0:
        max_devices = 50
        devices_chunk = devIdnos[:max_devices]
        params["devIdno"] = ','.join(devices_chunk)
        filtro_aplicado = True
        logger.info(f"🔍 Filtro PRE-API por dispositivos: {len(devices_chunk)} devices")
    
    try:
        response_data = make_request(endpoint, params)
        
        if filtro_aplicado and response_data:
            total_records = response_data.get('pagination', {}).get('totalRecords', 0)
            logger.info(f"✅ Filtro PRE-API exitoso - {total_records} fotos encontradas")
        
        return response_data
        
    except AlarmAPIError as e:
        logger.error(f"❌ Error en query_security_photos: {e}")
        
        if filtro_aplicado:
            logger.info("🔄 Reintentando sin filtros...")
            params.pop("vehiIdno", None)
            params.pop("devIdno", None)
            
            try:
                response_data = make_request(endpoint, params)
                logger.warning("⚠️ Descarga sin filtro empresarial")
                return response_data
            except Exception as fallback_error:
                logger.error(f"💥 Fallback falló: {fallback_error}")
                return None
        
        return None
    except Exception as e:
        logger.error(f"💥 Error inesperado: {e}")
        return None