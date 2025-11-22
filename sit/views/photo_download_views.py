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


BASE_URL = "http://190.183.254.253:8088"

logger = logging.getLogger('sit.views.photos')

from .stats import DownloadStatistics, BasicOptimizedStats

#Para la descarga de imagenes
download_jobs = {}

def security_photos_progress(request):
    """
    Vista para mostrar el progreso de descarga de fotos.
    """
    job_info = request.session.get('security_photos_job', {})
    
    if job_info.get('status') == 'pending':
        # Primera vez que se carga esta vista - iniciar la descarga real
        job_info['status'] = 'processing'
        request.session['security_photos_job'] = job_info
        request.session.modified = True
        
        # Renderizar la página de progreso
        return render(request, 'sit\security_photos_progress.html', {'job_info': job_info})
    
    elif job_info.get('status') == 'completed':
        # Si la descarga ya está completa, redirigir al visor
        photo_ids = job_info.get('photo_ids', [])
        if photo_ids:
            return redirect('sit:view_security_photos')
        else:
            messages.warning(request, "No se encontraron fotos en el rango seleccionado.")
            return redirect('sit:security_photos_form')
    
    # Si está en proceso o cualquier otro estado, mostrar la página de progreso
    return render(request, 'sit\security_photos_progress.html', {'job_info': job_info})

def view_security_photos(request):
    job_id = 'default_job'
    job_info = download_jobs.get(job_id, {})
    photos_data = job_info.get('all_photos', [])

    if not photos_data:
        messages.warning(request, "No hay fotos disponibles para mostrar.")
        return redirect('sit:security_photos_form')

    current_index = int(request.GET.get('idx', 0))
    if current_index < 0 or current_index >= len(photos_data):
        current_index = 0

    current_photo = photos_data[current_index]    
    context = {
        'current_photo': current_photo,
        'current_index': current_index,
        'total_photos': len(photos_data),
        'prev_index': max(0, current_index - 1),
        'next_index': min(len(photos_data) - 1, current_index + 1),
        'has_prev': current_index > 0,
        'has_next': current_index < len(photos_data) - 1,
        'MEDIA_URL': settings.MEDIA_URL,
    }
    return render(request, 'sit/view_security_photos.html', context)

def clear_security_photos_session(request):
    job_id = 'default_job'
    if job_id in download_jobs:
        del download_jobs[job_id]

    if 'security_photos_data' in request.session:
        del request.session['security_photos_data']
    if 'security_photos_job' in request.session:
        del request.session['security_photos_job']

    messages.success(request, "Datos de fotos de seguridad eliminados correctamente.")
    return redirect('sit:security_photos_form')

def check_download_progress(request):
    job_id = 'default_job'
    job_info = download_jobs.get(job_id, request.session.get('security_photos_job', {}))

    if job_info.get('status') == 'processing' and not job_info.get('thread_started', False):
        job_info['thread_started'] = True
        download_jobs[job_id] = job_info

        thread = threading.Thread(target=background_download_process, args=(job_id, job_info))
        thread.daemon = True
        thread.start()

    request.session['security_photos_job'] = job_info
    request.session.modified = True

    return JsonResponse({
        'status': job_info.get('status', 'unknown'),
        'progress': job_info.get('progress', 0),
        'message': job_info.get('message', ''),
        'total_photos': job_info.get('total_photos', 0),
        'downloaded_photos': job_info.get('downloaded_photos', 0)
    })

def security_photos_form(request):

    """
    Vista para mostrar el formulario de selección con empresas disponibles
    """
    # Establecer fechas predeterminadas (hoy y ayer)
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    
    # Obtener empresas disponibles
    empresas, vehiculos = obtener_empresas_disponibles()
    
    context = {
        'default_start_date': yesterday.strftime('%Y-%m-%d'),
        'default_start_time': '00:00',
        'default_end_date': today.strftime('%Y-%m-%d'),
        'default_end_time': '23:59',
        'empresas': empresas,  # NUEVO
        'total_vehiculos': len(vehiculos)  # NUEVO
    }
    
    return render(request, 'sit/security_photos_form.html', context)

def process_photos_page(page_result, photos_dir, all_photos, global_stats=None):
    """
    VERSIÓN DINÁMICA CON FILTRADO POR EMPRESA SELECCIONADA
    """
    prephotos = page_result.get('infos', [])
    photos = []
    
    page_stats = {
        'total_procesadas': 0,
        'incluidas': 0,
        'excluidas_empresa': 0,
        'ya_existen': 0,
        'descargadas': 0,
        'errores': 0,
        'vehiculos': set(),
        'dispositivos': set()
    }
    
    # OBTENER FILTRO DE EMPRESA desde variable global
    empresa_filter = getattr(process_photos_page, 'empresa_filter', None)
    
    if empresa_filter:
        fichas_validas = empresa_filter.get('vehiIdnos', [])
        devices_validos = [str(d) for d in empresa_filter.get('devIdnos', [])]
        empresa_nombre = empresa_filter['empresa_info']['nombre']
        
        logger.info(f"[🏢 APLICANDO FILTRO] {empresa_nombre}")
        logger.info(f"├── Fichas válidas: {fichas_validas}")
        logger.info(f"└── Devices válidos: {devices_validos}")
    else:
        logger.info("[🌐 SIN FILTRO] Procesando todas las empresas")
        fichas_validas = None
        devices_validos = None
        empresa_nombre = "Todas"
    
    # PROCESAR CADA FOTO
    for photo in prephotos:
        page_stats['total_procesadas'] += 1
        
        try:
            devIdno_raw = photo.get('devIdno', '0')
            devIdno = int(str(devIdno_raw).replace('C', '').replace('c', ''))
            vehiIdno = str(photo.get('vehiIdno', ''))
            
            # SI HAY FILTRO DE EMPRESA, APLICARLO
            if empresa_filter:
                # Verificar si la ficha está en la empresa
                ficha_valida = vehiIdno in fichas_validas
                
                # Verificar si el device está en la empresa
                device_valido = str(devIdno) in devices_validos
                
                # Debe cumplir al menos uno de los criterios
                if not (ficha_valida or device_valido):
                    page_stats['excluidas_empresa'] += 1
                    logger.info(f"[🚫 EXCLUIDA] Ficha {vehiIdno} / Device {devIdno} → NO pertenece a {empresa_nombre}")
                    continue
                else:
                    logger.info(f"[✅ INCLUIDA] Ficha {vehiIdno} / Device {devIdno} → SÍ pertenece a {empresa_nombre}")
            
            # Si llega aquí, la foto pasa el filtro (o no hay filtro)
            photos.append(photo)
            page_stats['incluidas'] += 1
            page_stats['vehiculos'].add(vehiIdno)
            page_stats['dispositivos'].add(str(devIdno))
                
        except ValueError:
            page_stats['errores'] += 1
            logger.info(f"[ERROR] No se pudo interpretar devIdno: {photo.get('devIdno')}")
            continue

    # RESTO DE LA LÓGICA DE DESCARGA (sin cambios)
    def download_photo(photo_info):        
        vehiIdno = photo_info.get('vehiIdno')
        devIdno = photo_info.get('devIdno')
        fileTimeStr = photo_info.get('fileTimeStr')
        
        try:
            vehicle_folder = crear_nombre_carpeta_vehiculo(vehiIdno, devIdno)
            vehicle_dir = os.path.join(photos_dir, vehicle_folder)
            os.makedirs(vehicle_dir, exist_ok=True)
            
            file_name = crear_nombre_archivo_foto(vehiIdno, devIdno, fileTimeStr)
            file_path = os.path.join(vehicle_dir, file_name)
            
            if verificar_archivo_existe(file_path):
                page_stats['ya_existen'] += 1
                photo_info['local_path'] = f"security_photos/{vehicle_folder}/{file_name}"
                return photo_info
            
            download_url = photo_info.get('downloadUrl')
            if not download_url:
                file_path_api = photo_info.get('FPATH')
                if file_path_api:
                    download_url = f"{BASE_URL}/StandardApiAction_downloadFile.action?jsession={settings.JSESSION_GPS}&filePath={file_path_api}"
                else:
                    page_stats['errores'] += 1
                    return None
            
            if download_and_save_image(download_url, file_path):
                page_stats['descargadas'] += 1
                photo_info['local_path'] = f"security_photos/{vehicle_folder}/{file_name}"
                return photo_info
            else:
                page_stats['errores'] += 1
                return None
                
        except Exception as e:
            page_stats['errores'] += 1
            logger.info(f"[💥 ERROR] {vehiIdno}-{devIdno}: {e}")
            return None

    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(download_photo, photo): photo for photo in photos}
        for future in as_completed(futures):
            result = future.result()
            if result:
                all_photos.append(result)

    logger.info(f"""
[📊 ESTADÍSTICAS - {empresa_nombre}]
├── Total procesadas: {page_stats['total_procesadas']}
├── ✅ Incluidas: {page_stats['incluidas']}
├── 🚫 Excluidas por empresa: {page_stats['excluidas_empresa']}
├── ⏭️ Ya existían: {page_stats['ya_existen']}
├── 📥 Descargadas nuevas: {page_stats['descargadas']}
├── 🚌 Vehículos únicos: {len(page_stats['vehiculos'])}
└── 💥 Errores: {page_stats['errores']}
""")
    
    if global_stats:
        global_stats.add_page_stats(page_stats)
    
    return page_stats

def begin_download_process(request):
    """
    VERSIÓN CORREGIDA - Pasa filtro directamente a process_photos_page
    """
    job_info = request.session.get('security_photos_job', {})
    query_params = request.session.get('photo_query_params', {})
    
    begin_time = job_info.get('begin_time')
    end_time = job_info.get('end_time')
    empresa_filter = query_params.get('empresa_filter')  # OBTENER AQUÍ
    
    # ⭐ DEBUGGING: Verificar si llega el filtro
    if empresa_filter:
        logger.info(f"[🎯 FILTRO RECIBIDO] {empresa_filter['empresa_info']['nombre']} - {len(empresa_filter.get('vehiIdnos', []))} vehículos")
    else:
        logger.info("[❌ FILTRO FALTANTE] No se recibió filtro de empresa")
    
    # Inicializar estadísticas consolidadas
    global_stats = DownloadStatistics()
    
    # Iniciar con la primera página para obtener el total de registros
    first_page_result = query_security_photos(begin_time, end_time, 1)
    
    if not first_page_result or first_page_result.get('result') != 0:
        job_info['status'] = 'error'
        job_info['message'] = 'Error al obtener las fotos de seguridad'
        request.session['security_photos_job'] = job_info
        request.session.modified = True
        return
    
    # Obtener información de paginación
    pagination = first_page_result.get('pagination', {})
    total_records = pagination.get('totalRecords', 0)
    total_pages = pagination.get('totalPages', 0)
    
    if total_records == 0:
        job_info['status'] = 'completed'
        job_info['total_photos'] = 0
        job_info['photo_ids'] = []
        request.session['security_photos_job'] = job_info
        request.session.modified = True
        return
    
    # Actualizar información del trabajo
    job_info['total_photos'] = total_records
    if empresa_filter:
        job_info['message'] = f'Descargando {total_records} fotos de {empresa_filter["empresa_info"]["nombre"]}...'
    else:
        job_info['message'] = f'Descargando {total_records} fotos de todas las empresas...'
        
    request.session['security_photos_job'] = job_info
    request.session.modified = True
    
    # Crear directorio para guardar las fotos si no existe
    photos_dir = os.path.join(settings.MEDIA_ROOT, 'security_photos')
    os.makedirs(photos_dir, exist_ok=True)
    
    # Lista para almacenar todos los datos de las fotos
    all_photos = []
    
    logger.info(f"🚀 INICIANDO DESCARGA: {total_pages} páginas, {total_records} fotos estimadas")
    
    # ⭐ PASAR FILTRO DIRECTAMENTE A process_photos_page
    process_photos_page_with_filter(first_page_result, photos_dir, all_photos, global_stats, empresa_filter)
    
    # Actualizar progreso
    job_info['downloaded_photos'] = len(all_photos)
    job_info['progress'] = int((len(all_photos) / total_records) * 100)
    request.session['security_photos_job'] = job_info
    request.session.modified = True
    
    # Descargar las páginas restantes
    for page in range(2, total_pages + 1):
        logger.info(f"📄 Procesando página {page}/{total_pages}...")
        
        page_result = query_security_photos(begin_time, end_time, page)
        if not page_result or page_result.get('result') != 0:
            continue
        
        # ⭐ PASAR FILTRO DIRECTAMENTE
        process_photos_page_with_filter(page_result, photos_dir, all_photos, global_stats, empresa_filter)
        
        # Actualizar progreso
        job_info['downloaded_photos'] = len(all_photos)
        job_info['progress'] = min(99, int((len(all_photos) / total_records) * 100))
        request.session['security_photos_job'] = job_info
        request.session.modified = True
    
    # Finalizar estadísticas
    global_stats.finalize()
    final_report = global_stats.get_final_report()
    logger.info(final_report)
    
    # Guardar los datos de las fotos en la sesión
    request.session['security_photos_data'] = all_photos
    
    # Marcar como completado
    job_info['status'] = 'completed'
    job_info['progress'] = 100
    
    if empresa_filter:
        job_info['message'] = f'✅ COMPLETADO: {len(all_photos)} fotos de {empresa_filter["empresa_info"]["nombre"]}'
    else:
        job_info['message'] = f'✅ COMPLETADO: {len(all_photos)} fotos de todas las empresas'
    
    job_info['photo_ids'] = list(range(len(all_photos)))
    request.session['security_photos_job'] = job_info
    request.session.modified = True

def process_photos_page_with_filter(page_result, photos_dir, all_photos, global_stats, empresa_filter):
    """
    VERSIÓN QUE RECIBE EL FILTRO DIRECTAMENTE COMO PARÁMETRO
    """
    prephotos = page_result.get('infos', [])
    photos = []
    
    page_stats = {
        'total_procesadas': 0,
        'incluidas': 0,
        'excluidas_empresa': 0,
        'ya_existen': 0,
        'descargadas': 0,
        'errores': 0,
        'vehiculos': set(),
        'dispositivos': set()
    }
    
    if empresa_filter:
        fichas_validas = empresa_filter.get('vehiIdnos', [])
        devices_validos = [str(d) for d in empresa_filter.get('devIdnos', [])]
        empresa_nombre = empresa_filter['empresa_info']['nombre']
        
        logger.info(f"[🏢 APLICANDO FILTRO] {empresa_nombre}")
        logger.info(f"├── Fichas válidas: {fichas_validas}")
        logger.info(f"└── Devices válidos: {devices_validos}")
    else:
        logger.info("[🌐 SIN FILTRO] Procesando todas las empresas")
        fichas_validas = None
        devices_validos = None
        empresa_nombre = "Todas"
    
    # PROCESAR CADA FOTO
    for photo in prephotos:
        page_stats['total_procesadas'] += 1
        
        try:
            devIdno_raw = photo.get('devIdno', '0')
            devIdno = int(str(devIdno_raw).replace('C', '').replace('c', ''))
            vehiIdno = str(photo.get('vehiIdno', ''))
            
            # SI HAY FILTRO DE EMPRESA, APLICARLO
            if empresa_filter:
                # Verificar si la ficha está en la empresa
                ficha_valida = vehiIdno in fichas_validas
                
                # Verificar si el device está en la empresa
                device_valido = str(devIdno) in devices_validos
                
                # Debe cumplir al menos uno de los criterios
                if not (ficha_valida or device_valido):
                    page_stats['excluidas_empresa'] += 1
                    logger.info(f"[🚫 EXCLUIDA] Ficha {vehiIdno} / Device {devIdno} → NO pertenece a {empresa_nombre}")
                    continue
                else:
                    logger.info(f"[✅ INCLUIDA] Ficha {vehiIdno} / Device {devIdno} → SÍ pertenece a {empresa_nombre}")
            
            # Si llega aquí, la foto pasa el filtro (o no hay filtro)
            photos.append(photo)
            page_stats['incluidas'] += 1
            page_stats['vehiculos'].add(vehiIdno)
            page_stats['dispositivos'].add(str(devIdno))
                
        except ValueError:
            page_stats['errores'] += 1
            logger.info(f"[ERROR] No se pudo interpretar devIdno: {photo.get('devIdno')}")
            continue

    # DESCARGA (mismo código que antes)
    def download_photo(photo_info):        
        vehiIdno = photo_info.get('vehiIdno')
        devIdno = photo_info.get('devIdno')
        fileTimeStr = photo_info.get('fileTimeStr')
        
        try:
            vehicle_folder = crear_nombre_carpeta_vehiculo(vehiIdno, devIdno)
            vehicle_dir = os.path.join(photos_dir, vehicle_folder)
            os.makedirs(vehicle_dir, exist_ok=True)
            
            file_name = crear_nombre_archivo_foto(vehiIdno, devIdno, fileTimeStr)
            file_path = os.path.join(vehicle_dir, file_name)
            
            if verificar_archivo_existe(file_path):
                page_stats['ya_existen'] += 1
                photo_info['local_path'] = f"security_photos/{vehicle_folder}/{file_name}"
                return photo_info
            
            download_url = photo_info.get('downloadUrl')
            if not download_url:
                file_path_api = photo_info.get('FPATH')
                if file_path_api:
                    download_url = f"{BASE_URL}/StandardApiAction_downloadFile.action?jsession={settings.JSESSION_GPS}&filePath={file_path_api}"
                else:
                    page_stats['errores'] += 1
                    return None
            
            if download_and_save_image(download_url, file_path):
                page_stats['descargadas'] += 1
                photo_info['local_path'] = f"security_photos/{vehicle_folder}/{file_name}"
                return photo_info
            else:
                page_stats['errores'] += 1
                return None
                
        except Exception as e:
            page_stats['errores'] += 1
            logger.info(f"[💥 ERROR] {vehiIdno}-{devIdno}: {e}")
            return None

    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(download_photo, photo): photo for photo in photos}
        for future in as_completed(futures):
            result = future.result()
            if result:
                all_photos.append(result)

    logger.info(f"""
[📊 ESTADÍSTICAS - {empresa_nombre}]
├── Total procesadas: {page_stats['total_procesadas']}
├── ✅ Incluidas: {page_stats['incluidas']}
├── 🚫 Excluidas por empresa: {page_stats['excluidas_empresa']}
├── ⏭️ Ya existían: {page_stats['ya_existen']}
├── 📥 Descargadas nuevas: {page_stats['descargadas']}
└── 💥 Errores: {page_stats['errores']}
""")
    
    if global_stats:
        global_stats.add_page_stats(page_stats)
    
    return page_stats

def background_download_process(job_id, job_info):
    """
    Proceso de descarga en background con estadísticas consolidadas
    VERSIÓN CORREGIDA CON FILTRO DE EMPRESA
    """
    begin_time = job_info.get('begin_time')
    end_time = job_info.get('end_time')
    
    # ⭐ OBTENER FILTRO DE EMPRESA DESDE job_info
    empresa_filter = job_info.get('empresa_filter')  # NUEVO
    
    # ⭐ DEBUG: Verificar si llega el filtro
    if empresa_filter:
        logger.info(f"[🎯 FILTRO EN BACKGROUND] {empresa_filter['empresa_info']['nombre']} - {len(empresa_filter.get('vehiIdnos', []))} vehículos")
    else:
        logger.info("[❌ FILTRO FALTANTE EN BACKGROUND] No se recibió filtro de empresa")
    
    # Inicializar estadísticas consolidadas
    global_stats = DownloadStatistics()

    photos_dir = os.path.join(settings.MEDIA_ROOT, 'security_photos')
    os.makedirs(photos_dir, exist_ok=True)

    first_page_result = query_security_photos(begin_time, end_time, 1)
    if not first_page_result or first_page_result.get('result') != 0:
        job_info['status'] = 'error'
        job_info['message'] = 'Error al obtener las fotos de seguridad'
        download_jobs[job_id] = job_info
        return

    pagination = first_page_result.get('pagination', {})
    total_records = pagination.get('totalRecords', 0)
    total_pages = pagination.get('totalPages', 0)

    if total_records == 0:
        job_info['status'] = 'completed'
        job_info['total_photos'] = 0
        job_info['photo_ids'] = []
        download_jobs[job_id] = job_info
        return

    job_info['total_photos'] = total_records
    job_info['message'] = f'Descargando {total_records} fotos...'
    job_info['start_time'] = time.time()
    download_jobs[job_id] = job_info

    all_photos = []
    
    # ⭐ PROCESAR PRIMERA PÁGINA CON FILTRO
    process_photos_page_with_filter(first_page_result, photos_dir, all_photos, global_stats, empresa_filter)
    job_info['downloaded_photos'] = len(all_photos)

    # Procesar páginas restantes
    for page in range(2, total_pages + 1):
        page_result = query_security_photos(begin_time, end_time, page)
        if not page_result or page_result.get('result') != 0:
            continue
            
        # ⭐ PROCESAR PÁGINA CON FILTRO
        process_photos_page_with_filter(page_result, photos_dir, all_photos, global_stats, empresa_filter)
        job_info['downloaded_photos'] = len(all_photos)

        elapsed = time.time() - job_info['start_time']
        estimated_total_time = (elapsed / page) * total_pages
        remaining = max(0, estimated_total_time - elapsed)

        job_info['message'] = (
            f"Página {page}/{total_pages} - "
            f"{global_stats.descargadas + global_stats.ya_existen} fotos - "
            f"Restante: {timedelta(seconds=int(remaining))}"
        )
        job_info['progress'] = min(99, int((len(all_photos) / total_records) * 100))
        download_jobs[job_id] = job_info

    # Finalizar con estadísticas completas
    global_stats.finalize()
    logger.info(global_stats.get_final_report())
    
    all_photos.sort(key=lambda x: (int(x.get('vehiIdno', 0)), x.get('fileTimeStr', '')))
    job_info['photo_ids'] = list(range(len(all_photos)))
    job_info['all_photos'] = all_photos

    elapsed = time.time() - job_info['start_time']
    job_info['message'] = (
        f"✅ COMPLETADO: {global_stats.descargadas + global_stats.ya_existen} fotos disponibles "
        f"({global_stats.descargadas} nuevas) - {str(timedelta(seconds=int(elapsed)))}"
    )
    job_info['progress'] = 100
    job_info['status'] = 'completed'
    download_jobs[job_id] = job_info

@require_POST

def fetch_security_photos(request):
    """
    VERSIÓN CORREGIDA - Pasa filtro al job_info para background process
    """
    start_date = request.POST.get('start_date')
    start_time = request.POST.get('start_time')
    end_date = request.POST.get('end_date')
    end_time = request.POST.get('end_time')
    empresa_id = request.POST.get('empresa_id')

    if not all([start_date, start_time, end_date, end_time]):
        messages.error(request, "Todos los campos de fecha y hora son obligatorios.")
        return redirect('sit:security_photos_form')

    begin_time = f"{start_date} {start_time}:00"
    end_time = f"{end_date} {end_time}:59"

    try:
        # Obtener filtro de empresa
        empresa_filter = None
        if empresa_id and empresa_id.strip():
            logger.info(f"[🏢 EMPRESA] Aplicando filtro por empresa ID: {empresa_id}")
            empresa_filter = obtener_vehiculos_por_empresa(empresa_id)
            
            if not empresa_filter:
                messages.error(request, f"No se pudo obtener información de la empresa {empresa_id}")
                return redirect('sit:security_photos_form')
            
            if empresa_filter['empresa_info']['total_vehiculos'] == 0:
                messages.warning(request, f"La empresa seleccionada no tiene vehículos activos.")
                return redirect('sit:security_photos_form')
        else:
            logger.info("[🌐 TODAS LAS EMPRESAS] Sin filtro de empresa")

        # Guardar parámetros para uso posterior
        request.session['photo_query_params'] = {
            'begintime': begin_time,
            'endtime': end_time,
            'pageRecords': 10,
            'empresa_filter': empresa_filter
        }

        # ⭐ INICIAR JOB CON FILTRO DE EMPRESA
        job_info = {
            'begin_time': begin_time,
            'end_time': end_time,
            'status': 'pending',
            'progress': 0,
            'total_photos': 0,
            'downloaded_photos': 0,
            'empresa_filter': empresa_filter  # ⭐ NUEVO: Pasar filtro al background process
        }
        
        if empresa_filter:
            job_info['empresa_info'] = empresa_filter['empresa_info']
            job_info['message'] = f"Preparando descarga para empresa: {empresa_filter['empresa_info']['nombre']}"
        else:
            job_info['message'] = "Preparando descarga para todas las empresas"
        
        request.session['security_photos_job'] = job_info

        return redirect('sit:security_photos_progress')

    except Exception as e:
        messages.error(request, f"Error al iniciar la descarga: {str(e)}")
        return redirect('sit:security_photos_form')


# VERSIONES BÁSICAS OPTIMIZADAS para agregar a views.py
# Reemplaza gradualmente las funciones existentes

def basic_optimized_check_progress(request):
    """
    Versión básica optimizada del check progress
    Reduce el polling innecesario con cache
    """
    job_id = 'default_job'
    job_info = download_jobs.get(job_id, request.session.get('security_photos_job', {}))
    
    # Cache para evitar requests demasiado frecuentes
    cache_key = f"progress_{request.session.session_key}"
    cached_data = cache.get(cache_key)
    
    current_time = time.time()
    
    # Si hay datos en cache y son recientes (menos de 1 segundo), devolverlos
    if cached_data and (current_time - cached_data.get('timestamp', 0)) < 1.0:
        return JsonResponse(cached_data['data'])
    
    # Verificar si necesita iniciar el proceso
    if (job_info.get('status') == 'processing' and 
        not job_info.get('thread_started', False) and 
        job_id not in download_jobs):
        
        job_info['thread_started'] = True
        download_jobs[job_id] = job_info
        
        # Usar versión optimizada básica
        basic_optimized_begin_download(request)
    
    # Preparar respuesta
    response_data = {
        'status': job_info.get('status', 'unknown'),
        'progress': job_info.get('progress', 0),
        'message': job_info.get('message', ''),
        'total_photos': job_info.get('total_photos', 0),
        'downloaded_photos': job_info.get('downloaded_photos', 0),
        'final_stats': job_info.get('final_stats', {})
    }
    
    # Guardar en cache por 1 segundo
    cache_data = {
        'data': response_data,
        'timestamp': current_time
    }
    cache.set(cache_key, cache_data, timeout=2)
    
    # Actualizar sesión con menos frecuencia (cada 3 segundos)
    last_session_update = job_info.get('last_session_update', 0)
    if current_time - last_session_update > 3:
        request.session['security_photos_job'] = job_info
        request.session.modified = True
        job_info['last_session_update'] = current_time
    
    return JsonResponse(response_data)

def basic_optimized_begin_download(request):
    """
    Versión básica optimizada del proceso de descarga
    Usa ThreadPoolExecutor mejorado y procesamiento por lotes
    """
    job_info = request.session.get('security_photos_job', {})
    query_params = request.session.get('photo_query_params', {})
    
    begin_time = job_info.get('begin_time')
    end_time = job_info.get('end_time')
    empresa_filter = query_params.get('empresa_filter')
    
    def run_optimized_download():
        try:
            # Obtener configuración optimizada
            config = getattr(settings, 'DOWNLOAD_OPTIMIZATION', {})
            max_workers = config.get('MAX_DOWNLOAD_WORKERS', 15)
            batch_size = config.get('API_BATCH_SIZE', 30)
            
            logger.info(f"🚀 [BASIC OPTIMIZED] Iniciando con {max_workers} workers, batch size {batch_size}")
            
            # Usar la función de stats optimizada básica
            stats = BasicOptimizedStats()
            
            # Obtener fotos por lotes más grandes
            first_page_result = basic_optimized_query_photos(
                begin_time, end_time, 1, batch_size, empresa_filter
            )
            
            if not first_page_result or first_page_result.get('result') != 0:
                job_info['status'] = 'error'
                job_info['message'] = 'Error al obtener las fotos de seguridad'
                download_jobs['default_job'] = job_info
                return
            
            pagination = first_page_result.get('pagination', {})
            total_records = pagination.get('totalRecords', 0)
            total_pages = pagination.get('totalPages', 0)
            
            if total_records == 0:
                job_info['status'] = 'completed'
                job_info['total_photos'] = 0
                job_info['photo_ids'] = []
                download_jobs['default_job'] = job_info
                return
            
            job_info['total_photos'] = total_records
            job_info['status'] = 'downloading'
            download_jobs['default_job'] = job_info
            
            photos_dir = os.path.join(settings.MEDIA_ROOT, 'security_photos')
            os.makedirs(photos_dir, exist_ok=True)
            
            all_photos = []
            
            # Procesar páginas con ThreadPoolExecutor optimizado
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                
                # Procesar primera página
                process_photos_page_optimized(
                    first_page_result, photos_dir, all_photos, stats, empresa_filter, executor
                )
                
                # Procesar páginas restantes
                for page in range(2, total_pages + 1):
                    page_result = basic_optimized_query_photos(
                        begin_time, end_time, page, batch_size, empresa_filter
                    )
                    
                    if page_result and page_result.get('result') == 0:
                        process_photos_page_optimized(
                            page_result, photos_dir, all_photos, stats, empresa_filter, executor
                        )
                    
                    # Actualizar progreso
                    job_info['downloaded_photos'] = len(all_photos)
                    job_info['progress'] = min(99, int((len(all_photos) / total_records) * 100))
                    job_info['message'] = f"Página {page}/{total_pages} - {len(all_photos)} fotos procesadas"
                    download_jobs['default_job'] = job_info
            
            # Finalizar
            stats.finalize()
            all_photos.sort(key=lambda x: (int(x.get('vehiIdno', 0)), x.get('fileTimeStr', '')))
            
            job_info['status'] = 'completed'
            job_info['progress'] = 100
            job_info['all_photos'] = all_photos
            job_info['photo_ids'] = list(range(len(all_photos)))
            job_info['final_stats'] = stats.get_summary()
            job_info['message'] = f'✅ COMPLETADO: {len(all_photos)} fotos en {stats.get_duration():.1f}s'
            
            download_jobs['default_job'] = job_info
            
            logger.info(f"✅ [BASIC OPTIMIZED] Descarga completada: {len(all_photos)} fotos")
            
        except Exception as e:
            job_info['status'] = 'error'
            job_info['message'] = f'Error en descarga: {str(e)}'
            download_jobs['default_job'] = job_info
            logger.info(f"❌ [BASIC OPTIMIZED] Error: {e}")
    
    # Ejecutar en thread separado
    import threading
    thread = threading.Thread(target=run_optimized_download, daemon=True)
    thread.start()
    
    request.session['security_photos_job'] = job_info
    request.session.modified = True

def basic_optimized_query_photos(begintime, endtime, current_page, page_records, empresa_filter=None):
    """
    Versión básica optimizada de consulta de fotos
    Aplica filtrado PRE-API cuando es posible
    """
    params = {
        "jsession": settings.JSESSION_GPS,
        "filetype": 2,
        "alarmType": 1,
        "begintime": begintime,
        "endtime": endtime,
        "currentPage": current_page,
        "pageRecords": page_records,
    }
    
    # Aplicar filtro PRE-API si hay empresa seleccionada
    if empresa_filter:
        vehiIdnos = empresa_filter.get('vehiIdnos', [])
        if vehiIdnos and len(vehiIdnos) <= 30:  # Límite conservador
            params["vehiIdno"] = ','.join(vehiIdnos[:30])
            logger.info(f"[🎯 FILTRO PRE-API] Aplicando para {len(vehiIdnos[:30])} vehículos")
    
    try:
        return make_request("StandardApiAction_queryPhoto.action", params)
    except Exception as e:
        logger.info(f"[❌ ERROR API] {e}")
        return None

def process_photos_page_optimized(page_result, photos_dir, all_photos, stats, empresa_filter, executor):
    """
    Versión optimizada básica del procesamiento de páginas
    Usa ThreadPoolExecutor y filtrado mejorado
    """
    prephotos = page_result.get('infos', [])
    photos_to_download = []
    
    # Aplicar filtros POST-API si es necesario
    for photo in prephotos:
        try:
            vehiIdno = str(photo.get('vehiIdno', ''))
            devIdno_raw = photo.get('devIdno', '0')
            devIdno = str(int(str(devIdno_raw).replace('C', '').replace('c', '')))
            
            # Si hay filtro de empresa, verificar
            if empresa_filter:
                fichas_validas = empresa_filter.get('vehiIdnos', [])
                devices_validos = [str(d) for d in empresa_filter.get('devIdnos', [])]
                
                if not (vehiIdno in fichas_validas or devIdno in devices_validos):
                    stats.update('excluidas', 1)
                    continue
            
            photos_to_download.append(photo)
            stats.update('incluidas', 1)
            
        except Exception as e:
            stats.update('errores', 1)
            continue
    
    # Descargar fotos en paralelo con el executor proporcionado
    def download_single_photo(photo_info):
        return download_photo_basic_optimized(photo_info, photos_dir, stats)
    
    # Enviar tareas al executor
    futures = [executor.submit(download_single_photo, photo) for photo in photos_to_download]
    
    # Recoger resultados
    for future in futures:
        try:
            result = future.result(timeout=30)  # Timeout de 30 segundos por foto
            if result:
                all_photos.append(result)
        except Exception as e:
            stats.update('errores', 1)
            logger.info(f"[❌ DOWNLOAD ERROR] {e}")

def download_photo_basic_optimized(photo_info, photos_dir, stats):
    """
    Versión básica optimizada de descarga individual
    Manejo mejorado de errores y paths
    """
    try:
        vehiIdno = photo_info.get('vehiIdno')
        devIdno = photo_info.get('devIdno')
        fileTimeStr = photo_info.get('fileTimeStr')
        
        # Crear directorio del vehículo
        vehicle_folder = crear_nombre_carpeta_vehiculo(vehiIdno, devIdno)
        vehicle_dir = os.path.join(photos_dir, vehicle_folder)
        os.makedirs(vehicle_dir, exist_ok=True)
        
        # Generar nombre de archivo
        file_name = crear_nombre_archivo_foto(vehiIdno, devIdno, fileTimeStr)
        file_path = os.path.join(vehicle_dir, file_name)
        
        # Verificar si ya existe
        if verificar_archivo_existe(file_path):
            stats.update('ya_existen', 1)
            photo_info['local_path'] = f"security_photos/{vehicle_folder}/{file_name}"
            return photo_info
        
        # Obtener URL de descarga
        download_url = photo_info.get('downloadUrl')
        if not download_url:
            file_path_api = photo_info.get('FPATH')
            if file_path_api:
                download_url = f"{BASE_URL}/StandardApiAction_downloadFile.action?jsession={settings.JSESSION_GPS}&filePath={file_path_api}"
            else:
                stats.update('errores', 1)
                return None
        
        # Descargar con timeout optimizado
        if download_and_save_image(download_url, file_path):
            stats.update('descargadas', 1)
            photo_info['local_path'] = f"security_photos/{vehicle_folder}/{file_name}"
            return photo_info
        else:
            stats.update('errores', 1)
            return None
            
    except Exception as e:
        stats.update('errores', 1)
        logger.info(f"[❌ ERROR INDIVIDUAL] {vehiIdno}-{devIdno}: {e}")
        return None

