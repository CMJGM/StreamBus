import requests
import logging
import json
import threading
import datetime
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from django.conf import settings
from django.contrib import messages
from django.core.serializers.json import DjangoJSONEncoder
from django.core.paginator import Paginator
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.utils.timesince import timesince
from django.utils.timezone import now
from django.urls import reverse
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST
from requests.auth import HTTPBasicAuth
from buses.models import Buses
from urllib.parse import urlencode
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from .utils import obtener_informe_sit
from .utils import obtener_ultima_ubicacion, verificar_archivo_existe
from .utils import obtener_vehiculos, crear_nombre_archivo_foto
from .utils import crear_nombre_carpeta_vehiculo
from .utils import get_performance_report_photos, download_and_save_image
from .utils import make_request, AlarmAPIError


BASE_URL = "http://190.183.254.253:8088"

def mapa_ubicacion(request):
    ficha = request.GET.get('ficha')
    
    if ficha:        
        
        latitud, longitud = obtener_ultima_ubicacion(vehi_idno=ficha)
        
        if latitud is not None and longitud is not None:
            try:
                latitud = float(latitud)
                longitud = float(longitud)
                
                if not (-90 <= latitud <= 90 and -180 <= longitud <= 180):
                    raise ValueError("Coordenadas fuera del rango válido")
                
                coordinates = {'lat': latitud, 'lng': longitud}
                logger.debug("Coordenadas en la función mapa_ubicaciones", coordinates)
                
                return render(request, 'sit/mapa_ubicacion.html', {
                    'coordinates': json.dumps({'lat': coordinates['lat'], 'lng': coordinates['lng']})
                })
            except (ValueError, TypeError):
                return render(request, 'sit/mapa_ubicacion.html', {
                    'error': 'Coordenadas no válidas recibidas para esta ficha.',
                    'coordinates': json.dumps({'lat': -34.6037, 'lng': -58.3816})  # Valor predeterminado
                })
        else:
            return render(request, 'sit/mapa_ubicacion.html', {
                'error': 'No se encontró ubicación para esta ficha.',
                'coordinates': json.dumps({'lat': -34.6037, 'lng': -58.3816})  # Valor predeterminado
            })
    else:
        return render(request, 'sit/mapa_ubicacion.html', {
            'coordinates': json.dumps({'lat': -34.6037, 'lng': -58.3816})  # Valor predeterminado
        })

def ubicacion_json(request):

    ficha = request.GET.get('ficha')
        
    lat, lon = obtener_ultima_ubicacion(vehi_idno=ficha)

    return JsonResponse({
        'latitud': lat,
        'longitud': lon
    })

def ubicaciones_vehiculos(request):
    selected_company_id = request.GET.get("empresa")
    try:
        response = requests.get(
            "http://190.183.254.253:8088/StandardApiAction_queryUserVehicle.action",
            params={"jsession": settings.JSESSION_GPS},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        companys = data.get("companys", [])
        vehiculos_data = data.get("vehicles", [])
        empresas = [e for e in companys if e.get("pId") == 0]

        # Filtrado seguro
        empresas_bus = []
        empresa_ids = []
        if selected_company_id and selected_company_id.strip().isdigit():
            selected_id = int(selected_company_id)
            empresas_bus = [e for e in companys if e.get("pId") == selected_id]
            empresa_ids = [e.get("id") for e in empresas_bus]
            empresa_ids.append(selected_id)
            vehiculos_data = [v for v in vehiculos_data if v.get("pid") in empresa_ids]

        vehiculos = []
        for veh in vehiculos_data:
            try:
                ficha = veh.get("nm")
                dispositivo = veh.get("dl", [{}])[0].get("id")
                posicion = obtener_ultima_ubicacion(ficha)

                if posicion and len(posicion) == 5:
                    lat, lon, velocidad, gps_timestamp, direccion = posicion
                    if gps_timestamp is not None:
                        ultima_fecha = datetime.fromtimestamp(gps_timestamp / 1000, tz=timezone.utc)
                        tiempo_conectado = calcular_tiempo(ultima_fecha)
                        vehiculos.append({
                            "ficha": ficha,
                            "dispositivo": dispositivo,
                            "tiempo_conectado": tiempo_conectado,
                            "lat": lat,
                            "lon": lon,
                            "segundos_desde_reporte": int((now() - ultima_fecha).total_seconds()),
                            "direccion": direccion,
                        })
            except Exception as err:
                logger.info(f"Error procesando vehículo {veh.get('nm')}: {err}")
                continue

    except Exception as e:
        return render(request, 'sit/ubicaciones_vehiculos.html', {
            "error": str(e),
            "vehiculos": [],
            "empresas": [],
            "empresa_seleccionada": selected_company_id,
            "vehiculos_json": "[]",
        })

    return render(request, 'sit/ubicaciones_vehiculos.html', {
        "vehiculos": vehiculos,
        "empresas": empresas,
        "empresa_seleccionada": selected_company_id,
        "vehiculos_json": json.dumps(vehiculos),
    })

@require_GET

def ubicaciones_vehiculos_json(request):
    selected_company_id = request.GET.get("empresa")
    filtro = request.GET.get("filtro", "").strip().lower()

    try:
        response = requests.get(
            "http://190.183.254.253:8088/StandardApiAction_queryUserVehicle.action",
            params={"jsession": settings.JSESSION_GPS},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        companys = data.get("companys", [])
        vehiculos_data = data.get("vehicles", [])

        # Filtrado por empresa
        empresa_ids = []
        if selected_company_id and selected_company_id.strip().isdigit():
            selected_id = int(selected_company_id)
            sub_empresas = [e for e in companys if e.get("pId") == selected_id]
            empresa_ids = [e.get("id") for e in sub_empresas]
            empresa_ids.append(selected_id)
            vehiculos_data = [v for v in vehiculos_data if v.get("pid") in empresa_ids]

        # Filtrado por texto (ficha o dispositivo)
        if filtro:
            vehiculos_data = [
                v for v in vehiculos_data
                if filtro in str(v.get("nm", "")).lower() or
                   filtro in str(v.get("dl", [{}])[0].get("id", "")).lower()
            ]

        vehiculos = []
        for veh in vehiculos_data:
            try:
                ficha = veh.get("nm")
                dispositivo = veh.get("dl", [{}])[0].get("id")

                posicion = obtener_ultima_ubicacion(ficha)
                if posicion and len(posicion) == 5:
                    lat, lon, velocidad, gps_timestamp, direccion = posicion
                    if gps_timestamp:
                        ultima_fecha = datetime.fromtimestamp(gps_timestamp / 1000, tz=timezone.utc)
                        tiempo_conectado = calcular_tiempo(ultima_fecha)

                        vehiculos.append({
                            "ficha": ficha,
                            "dispositivo": dispositivo,
                            "tiempo_conectado": tiempo_conectado,
                            "lat": lat,
                            "lon": lon,
                            "segundos_desde_reporte": int((now() - ultima_fecha).total_seconds()),
                            "direccion": direccion,
                        })
            except Exception as err:
                logger.info(f"Error procesando vehículo {veh.get('nm')}: {err}")
                continue

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(vehiculos, safe=False)

def direccion_por_coordenadas(request):    

    lat = request.GET.get("lat")
    lon = request.GET.get("lon")
    
    if not lat or not lon:
        return JsonResponse({'error': 'Latitud y longitud son requeridas'}, status=400)

   
    try:
        geolocator = Nominatim(user_agent="streambus")  # Cambiá el nombre por el de tu app si querés
        location = geolocator.reverse(f"{lat}, {lon}", language='es')
        address = location.raw["address"]
        calle = address.get("road", "")
        numero = address.get("house_number", "")
        barrio = address.get("neighbourhood", "") or address.get("suburb", "")
        ciudad = address.get("postcode", "") + "-" + address.get("city", "") if "city" in address else address.get("town", "")
        provincia = address.get("state", "")
        return JsonResponse({"direccion": f"{calle} {numero}".strip(),
                            "barrio": barrio,
                            "ciudad": ciudad,
                            "provincia": provincia
                            })

    
    except (GeocoderTimedOut, GeocoderUnavailable):
        return JsonResponse({"direccion": "Error localizacion",
                                "barrio": "",
                                "ciudad": "",
                                "provincia": ""
                                }, status=503)

def calcular_tiempo(fecha):
    if not fecha:
        return "Sin datos"
    diferencia = now() - fecha
    segundos = int(diferencia.total_seconds())
    minutos, segundos = divmod(segundos, 60)
    horas, minutos = divmod(minutos, 60)
    return f"{horas}h {minutos}m {segundos}s"

def obtener_empresas_y_vehiculos(jsession, empresa_id=None):
    try:
        response = requests.get(
            "http://190.183.254.253:8088/StandardApiAction_queryUserVehicle.action",
            params={"jsession": jsession},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        companys = data.get("companys", [])
        vehiculos_data = data.get("vehicles", [])
        empresas = [e for e in companys if e.get("pId") == 0]

        empresas_bus = []
        empresa_ids = []
        if empresa_id and str(empresa_id).isdigit():
            selected_id = int(empresa_id)
            empresas_bus = [e for e in companys if e.get("pId") == selected_id]
            empresa_ids = [e.get("id") for e in empresas_bus]
            empresa_ids.append(selected_id)
            vehiculos_data = [v for v in vehiculos_data if v.get("pid") in empresa_ids]

        vehiculos = []
        for veh in vehiculos_data:
            ficha = veh.get("nm")
            dispositivo = veh.get("dl", [{}])[0].get("id")
            vehiculos.append({
                "ficha": ficha,
                "dispositivo": dispositivo,
            })

        return empresas, vehiculos

    except Exception as e:
        logger.info(f"Error al obtener empresas/vehículos: {e}")
        return [], []

def obtener_empresas_disponibles():
    """
    Obtiene lista de empresas disponibles para el selector
    
    Returns:
        tuple: (empresas_principales, vehiculos_totales) 
    """
    try:
        response = requests.get(
            "http://190.183.254.253:8088/StandardApiAction_queryUserVehicle.action",
            params={"jsession": settings.JSESSION_GPS, "language": "es"},
            timeout=10
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
            empresa_ids.append(empresa_id)  # Incluir empresa principal
            
            # Contar vehículos de esta empresa (incluye sub-empresas)
            vehiculos_empresa = [v for v in vehiculos_data if v.get("pid") in empresa_ids]
            empresa['vehicle_count'] = len(vehiculos_empresa)
        
        return empresas_principales, vehiculos_data

    except Exception as e:
        logger.info(f"Error obteniendo empresas: {e}")
        return [], []

def obtener_vehiculos_por_empresa(empresa_id):
    """
    Obtiene todos los vehículos de una empresa (incluye sub-empresas)
    
    Args:
        empresa_id: ID de la empresa principal
        
    Returns:
        dict: {
            'vehiculos': [lista de vehículos],
            'vehiIdnos': [lista de fichas],
            'devIdnos': [lista de dispositivos],
            'empresa_info': {info de la empresa}
        }
    """
    try:
        response = requests.get(
            "http://190.183.254.253:8088/StandardApiAction_queryUserVehicle.action",
            params={"jsession": settings.JSESSION_GPS, "language": "es"},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        companys = data.get("companys", [])
        vehiculos_data = data.get("vehicles", [])
        
        # Encontrar empresa principal
        empresa_principal = next((e for e in companys if e.get("id") == int(empresa_id)), None)
        if not empresa_principal:
            return None
        
        # LÓGICA REUTILIZADA de ubicaciones_vehiculos()
        # Obtener sub-empresas de la empresa seleccionada
        sub_empresas = [e for e in companys if e.get("pId") == int(empresa_id)]
        empresa_ids = [e.get("id") for e in sub_empresas]
        empresa_ids.append(int(empresa_id))  # Incluir empresa principal
        
        # Filtrar vehículos que pertenecen a esta empresa o sus sub-empresas
        vehiculos_empresa = [v for v in vehiculos_data if v.get("pid") in empresa_ids]
        
        # Extraer listas para filtrado
        vehiIdnos = []
        devIdnos = []
        
        for vehiculo in vehiculos_empresa:
            ficha = vehiculo.get("nm")
            if ficha:
                vehiIdnos.append(str(ficha))
            
            # Obtener device del vehículo
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
        
        logger.info(f"""
[🏢 EMPRESA SELECCIONADA]
├── Nombre: {resultado['empresa_info']['nombre']}
├── ID: {resultado['empresa_info']['id']}
├── Sub-empresas: {resultado['empresa_info']['sub_empresas']}
├── Total vehículos: {resultado['empresa_info']['total_vehiculos']}
├── Fichas: {', '.join(vehiIdnos[:5])}{'...' if len(vehiIdnos) > 5 else ''}
└── Dispositivos: {', '.join(devIdnos[:5])}{'...' if len(devIdnos) > 5 else ''}
""")
        
        return resultado

    except Exception as e:
        logger.info(f"Error obteniendo vehículos de empresa {empresa_id}: {e}")
        return None

