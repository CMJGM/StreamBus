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

logger = logging.getLogger('sit.views')

#Para la descarga de imagenes
download_jobs = {}

def listar_informes_sit(request):
    informe = obtener_informe_sit(5)  
    return render(request, 'sit/lista_informes.html', {'informe': informe})

def descargar_expediente_pdf(request):
    parametros = {
        'rs:Format': 'PDF',
        'rs:Command': 'Render',
        'pBase': 1,
        'pEmpresa': 1,
        'pExpediente': 463080,
    }

    # URL del ReportViewer
    base_url = "http://190.183.254.254:82/ReportesSIT/Pages/ReportViewer.aspx"
    reporte = "/Personal/ExpedienteInforme"  # nombre del path al reporte
    full_url = f"{base_url}?{urlencode({'%2f' + reporte: ''})}&{urlencode(parametros)}"

    # Realiza la petición autenticada
    auth = HTTPBasicAuth("reporte.mail", "autobuses")
    response = requests.get(full_url, auth=auth)

    if response.status_code == 200:
        return HttpResponse(
            response.content,
            content_type='application/pdf',
            headers={'Content-Disposition': 'inline; filename="ExpedienteInforme.pdf"'}
        )
    else:
        return HttpResponse(
            f"Error al generar el reporte: {response.status_code}",
            status=500
        )

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

class DownloadStatistics:
    """
    Clase para manejar estadísticas consolidadas de descarga de fotos
    """
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reinicia todas las estadísticas"""
        self.total_procesadas = 0
        self.incluidas = 0
        self.excluidas = 0
        self.ya_existen = 0
        self.descargadas = 0
        self.errores = 0
        self.paginas_procesadas = 0
        self.vehiculos_unicos = set()
        self.dispositivos_unicos = set()
        self.start_time = time.time()
        self.end_time = None
    
    def add_page_stats(self, page_stats):
        """
        Agrega estadísticas de una página al total consolidado
        
        Args:
            page_stats: Diccionario con estadísticas de la página
        """
        self.total_procesadas += page_stats.get('total_procesadas', 0)
        self.incluidas += page_stats.get('incluidas', 0)
        self.excluidas += page_stats.get('excluidas', 0)
        self.ya_existen += page_stats.get('ya_existen', 0)
        self.descargadas += page_stats.get('descargadas', 0)
        self.errores += page_stats.get('errores', 0)
        self.paginas_procesadas += 1
        
        # Agregar vehículos y dispositivos únicos si están disponibles
        if 'vehiculos' in page_stats:
            self.vehiculos_unicos.update(page_stats['vehiculos'])
        if 'dispositivos' in page_stats:
            self.dispositivos_unicos.update(page_stats['dispositivos'])
    
    def finalize(self):
        """Finaliza el conteo y calcula métricas finales"""
        self.end_time = time.time()
    
    def get_duration(self):
        """Retorna duración total del proceso"""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    def get_final_report(self):
        """
        Genera reporte final consolidado
        
        Returns:
            str: Reporte formateado para mostrar en logs
        """
        duration = self.get_duration()
        duration_str = str(timedelta(seconds=int(duration)))
        
        # Calcular porcentajes
        total_intentos = self.incluidas
        porcentaje_exito = (self.descargadas / total_intentos * 100) if total_intentos > 0 else 0
        porcentaje_ya_existian = (self.ya_existen / total_intentos * 100) if total_intentos > 0 else 0
        porcentaje_errores = (self.errores / total_intentos * 100) if total_intentos > 0 else 0
        
        # Velocidad de descarga
        velocidad = self.descargadas / duration if duration > 0 else 0
        
        report = f"""
╔═══════════════════════════════════════════════════════════════════════╗
║                    📊 ESTADÍSTICAS FINALES DE DESCARGA                ║
╠═══════════════════════════════════════════════════════════════════════╣
║                                                                       ║
║  📈 RESUMEN GENERAL:                                                  ║
║  ├── Total de fotos procesadas: {self.total_procesadas:,}                             ║
║  ├── ✅ Incluidas en filtrado: {self.incluidas:,}                               ║
║  ├── ❌ Excluidas por filtro: {self.excluidas:,}                                ║
║  └── 📄 Páginas procesadas: {self.paginas_procesadas}                                    ║
║                                                                       ║
║  🎯 RESULTADOS DE DESCARGA:                                           ║
║  ├── 📥 Descargadas nuevas: {self.descargadas:,} ({porcentaje_exito:.1f}%)                    ║
║  ├── ⏭️ Ya existían: {self.ya_existen:,} ({porcentaje_ya_existian:.1f}%)                         ║
║  ├── 💥 Errores: {self.errores:,} ({porcentaje_errores:.1f}%)                                   ║
║  └── ✅ Total disponibles: {self.ya_existen + self.descargadas:,}                         ║
║                                                                       ║
║  🚗 COBERTURA:                                                        ║
║  ├── 🚌 Vehículos únicos: {len(self.vehiculos_unicos)}                                  ║
║  └── 📱 Dispositivos únicos: {len(self.dispositivos_unicos)}                            ║
║                                                                       ║
║  ⏱️ RENDIMIENTO:                                                       ║
║  ├── 🕐 Tiempo total: {duration_str}                                  ║
║  ├── 🚀 Velocidad: {velocidad:.1f} fotos/segundo                            ║
║  └── 📊 Promedio por página: {self.incluidas/self.paginas_procesadas:.1f} fotos        ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
"""
        return report
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

class BasicOptimizedStats:
    """Clase básica para manejar estadísticas de descarga"""
    
    def __init__(self):
        self.stats = {
            'incluidas': 0,
            'excluidas': 0,
            'ya_existen': 0,
            'descargadas': 0,
            'errores': 0
        }
        self.start_time = time.time()
        self.end_time = None
    
    def update(self, key, value):
        """Actualizar estadística"""
        if key in self.stats:
            self.stats[key] += value
    
    def finalize(self):
        """Finalizar conteo"""
        self.end_time = time.time()
    
    def get_duration(self):
        """Obtener duración"""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    def get_summary(self):
        """Obtener resumen de estadísticas"""
        return {
            **self.stats,
            'duration': self.get_duration(),
            'total_disponibles': self.stats['descargadas'] + self.stats['ya_existen']
        }

# Para usar estas funciones, actualiza tus URLs:
# urls.py
# path('security-photos/check-progress/', basic_optimized_check_progress, name='check_download_progress'),