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
from ..utils import obtener_informe_sit
from ..utils import obtener_ultima_ubicacion, verificar_archivo_existe
from ..utils import obtener_vehiculos, crear_nombre_archivo_foto
from ..utils import crear_nombre_carpeta_vehiculo
from ..utils import get_performance_report_photos, download_and_save_image
from ..utils import make_request, AlarmAPIError
from StreamBus.logging_mixins import LoggingMixin, DetailedLoggingMixin, log_view, log_view_detailed


BASE_URL = "http://190.183.254.253:8088"

@log_view
def alarmas_view(request):
    photos = []
    error_message = None
    
    # --- CAMBIO CLAVE AQUÍ ---
    # Inicializa pagination con valores por defecto para que siempre exista en el contexto.
    pagination = {
        'currentPage': 1,
        'totalPages': 1,
        'totalRecords': 0,
        'pageSize': 10,
    }
    # -------------------------

    # Calcular las fechas y horas por defecto (ayer 8 AM a hoy 8 AM)
    today = now().date()
    yesterday = today - timedelta(days=1)

    default_begin_datetime = datetime.combine(yesterday, datetime.min.time().replace(hour=8), tzinfo=timezone.utc)
    default_end_datetime = datetime.combine(today, datetime.min.time().replace(hour=8), tzinfo=timezone.utc)

    default_begin_date = default_begin_datetime.strftime("%Y-%m-%d")
    default_begin_time = default_begin_datetime.strftime("%H:%M:%S")
    default_end_date = default_end_datetime.strftime("%Y-%m-%d")
    default_end_time = default_end_datetime.strftime("%H:%M:%S")

    # Parámetros por defecto para el formulario
    default_alarm_type = 1
    default_file_type = 2 # Asumimos 2 para fotos
    default_current_page = 1
    default_page_records = 10

    if request.method == 'POST':
        # Retrieve form data
        begin_date = request.POST.get('begin_date')
        begin_time = request.POST.get('begin_time')
        end_date = request.POST.get('end_date')
        end_time = request.POST.get('end_time')
        current_page = request.POST.get('current_page', default_current_page)
        page_records = request.POST.get('page_records', default_page_records)

        begintime_str = f"{begin_date} {begin_time}"
        endtime_str = f"{end_date} {end_time}"
        
        try:
            current_page_int = int(current_page)
            page_records_int = int(page_records)

            response_data = query_security_photos(
                begintime=begintime_str,
                endtime=endtime_str,
                current_page=current_page_int,
                page_records=page_records_int
            )

            if response_data and response_data.get('result') == 0:
                photos = response_data.get('infos', [])
                # Si hay datos de paginación de la API, sobrescribe los valores por defecto
                pagination = response_data.get('pagination', pagination) 
                request.session['photo_query_params'] = {
                    'begintime': begintime_str,
                    'endtime': endtime_str,
                    'currentPage': current_page,
                    'pageRecords': page_records_int,
                }
            else:
                error_message = response_data.get('msg', 'No se encontraron fotos o hubo un error en la API.')
                # Si hay un error, resetea la paginación a valores por defecto o vacíos
                pagination = {
                    'currentPage': 1,
                    'totalPages': 1,
                    'totalRecords': 0,
                    'pageSize': page_records_int, # Mantiene el tamaño de página solicitado
                }


        except ValueError:
            error_message = "Por favor, asegúrese de que los campos numéricos sean válidos."
            # En caso de error de validación, también resetea la paginación
            pagination = {
                'currentPage': 1,
                'totalPages': 1,
                'totalRecords': 0,
                'pageSize': default_page_records,
            }
        except Exception as e:
            error_message = f"Ocurrió un error al procesar la solicitud: {e}"
            pagination = { # Resetea también la paginación en caso de excepción
                'currentPage': 1,
                'totalPages': 1,
                'totalRecords': 0,
                'pageSize': default_page_records,
            }

    context = {
        'photos': photos,
        'error_message': error_message,
        'default_begin_date': default_begin_date,
        'default_begin_time': default_begin_time,
        'default_end_date': default_end_date,
        'default_end_time': default_end_time,
        'default_alarm_type': default_alarm_type,
        'default_file_type': default_file_type,
        'default_current_page': default_current_page,
        'default_page_records': default_page_records,
        'pagination': pagination, # Aseguramos que pagination siempre está presente
    }
    return render(request, 'sit/detalle_alarmas.html', context)

# -----------------------------------------------------------------------------
# Nueva Vista AJAX para obtener fotos paginadas
# -----------------------------------------------------------------------------
@log_view
@require_GET
def get_security_photos_ajax(request):

    # Recuperar los parámetros base de la sesión
    query_params = request.session.get('photo_query_params')
    if not query_params:
        return JsonResponse({'error': 'Parámetros de búsqueda no encontrados. Realice una búsqueda inicial.', 'photos': []}, status=400)

    # Obtener la página solicitada del request AJAX
    current_page = request.GET.get('page', 1)
    
    try:
        current_page_int = int(current_page)
        
        # Combinar los parámetros base con la página actual
        params_for_api = query_params.copy()
        params_for_api['currentPage'] = current_page_int

        response_data = query_security_photos(            
            begintime=params_for_api['begintime'],
            endtime=params_for_api['endtime'],
            current_page=params_for_api['currentPage']
        )

        if response_data and response_data.get('result') == 0:
            photos = response_data.get('infos', [])
            pagination = response_data.get('pagination', {})
            return JsonResponse({'photos': photos, 'pagination': pagination})
        else:
            return JsonResponse({
                'error': response_data.get('msg', 'Error al obtener fotos desde la API.'), 
                'photos': []
            }, status=500)

    except ValueError:
        return JsonResponse({'error': 'Número de página inválido.', 'photos': []}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Error inesperado: {e}', 'photos': []}, status=500)

def query_security_photos(
    begintime: str,
    endtime: str,
    current_page: int = 1,
    page_records: int = 25,
    vehiIdnos: list = None,
    devIdnos: list = None
):
    """
    Consulta fotos de seguridad con filtrado PRE-API por empresa
    
    Args:
        begintime: Fecha inicio
        endtime: Fecha fin  
        current_page: Página actual
        page_records: Registros por página
        vehiIdnos: Lista de fichas de vehículos a incluir
        devIdnos: Lista de dispositivos a incluir
        
    Returns:
        dict: Respuesta de la API con fotos filtradas
    """
    endpoint = "StandardApiAction_queryPhoto.action"
    
    params = {
        "jsession": settings.JSESSION_GPS,
        "filetype": 2,
        "alarmType": 1,
        "begintime": begintime,
        "endtime": endtime,
        "currentPage": current_page,
        "pageRecords": page_records,
    }
    
    # INTENTAR FILTRADO PRE-API
    filtro_aplicado = False
    
    # Opción 1: Filtrar por vehículos (fichas)
    if vehiIdnos and len(vehiIdnos) > 0:
        # Limitar cantidad para evitar URLs muy largas
        max_vehicles = 50  # Ajustar según límites de la API
        vehicles_chunk = vehiIdnos[:max_vehicles]
        
        params["vehiIdno"] = ','.join(vehicles_chunk)
        filtro_aplicado = True
        logger.info(f"[🔍 FILTRO PRE-API] Aplicando filtro por vehículos: {len(vehicles_chunk)} fichas")
        
        if len(vehiIdnos) > max_vehicles:
            logger.info(f"[⚠️ ADVERTENCIA] Se truncaron {len(vehiIdnos) - max_vehicles} vehículos por límite de API")
    
    # Opción 2: Filtrar por dispositivos (como fallback)
    elif devIdnos and len(devIdnos) > 0:
        max_devices = 50
        devices_chunk = devIdnos[:max_devices]
        
        params["devIdno"] = ','.join(devices_chunk)
        filtro_aplicado = True
        logger.info(f"[🔍 FILTRO PRE-API] Aplicando filtro por dispositivos: {len(devices_chunk)} devices")
        
        if len(devIdnos) > max_devices:
            logger.info(f"[⚠️ ADVERTENCIA] Se truncaron {len(devIdnos) - max_devices} dispositivos por límite de API")
    
    try:
        response_data = make_request(endpoint, params)
        
        if filtro_aplicado and response_data:
            total_records = response_data.get('pagination', {}).get('totalRecords', 0)
            logger.info(f"[✅ FILTRO PRE-API] Exitoso - {total_records} fotos encontradas para la empresa")
        
        return response_data
        
    except AlarmAPIError as e:
        logger.info(f"[❌ ERROR FILTRO PRE-API] {e}")
        
        # FALLBACK: Intentar sin filtros si falla
        if filtro_aplicado:
            logger.info("[🔄 FALLBACK] Reintentando sin filtros de empresa...")
            
            # Remover filtros y reintentar
            params.pop("vehiIdno", None)
            params.pop("devIdno", None)
            
            try:
                response_data = make_request(endpoint, params)
                logger.info("[⚠️ FALLBACK] Descarga sin filtro empresarial - se aplicará filtrado POST-API")
                return response_data
            except Exception as fallback_error:
                logger.info(f"[💥 FALLBACK FAILED] {fallback_error}")
                return None
        
        return None
    except Exception as e:
        logger.info(f"[💥 ERROR INESPERADO] {e}")
        return None

