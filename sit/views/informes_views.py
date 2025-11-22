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

