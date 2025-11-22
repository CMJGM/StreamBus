from django.shortcuts import render
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth, TruncDate
from datetime import datetime, timedelta
from informes.models import Informe, Origen
from sucursales.models import Sucursales
import logging

logger = logging.getLogger('inicio.views')


def inicio(request):
    """Vista de inicio con dashboard para usuarios logueados."""

    # Si no está logueado, mostrar página pública
    if not request.user.is_authenticated:
        logger.debug("Usuario no autenticado accediendo a inicio")
        return render(request, 'inicio/inicio_publico.html')

    # Usuario logueado - mostrar dashboard con métricas
    logger.info(f"Usuario {request.user.username} accediendo a dashboard de inicio")
    grupos_usuario = list(request.user.groups.values_list('name', flat=True))

    # Obtener sucursales permitidas del usuario
    if hasattr(request.user, 'profile'):
        sucursales = request.user.profile.get_sucursales_permitidas()
    else:
        sucursales = Sucursales.objects.all()

    # Filtrar informes por sucursales del usuario
    informes_base = Informe.objects.filter(sucursal__in=sucursales)

    # === MÉTRICAS PRINCIPALES ===
    total_informes = informes_base.count()
    sin_empleado = informes_base.filter(empleado__isnull=True).count()
    no_enviados = informes_base.filter(historial_envios__isnull=True).count()
    sin_expediente = informes_base.filter(generado=False).count()

    # Informes de los últimos 30 días
    hace_30_dias = datetime.now() - timedelta(days=30)
    informes_mes = informes_base.filter(fecha_hora__gte=hace_30_dias).count()

    # Informes de hoy
    hoy = datetime.now().date()
    informes_hoy = informes_base.filter(fecha_hora__date=hoy).count()

    # === GRILLA: INFORMES POR ORIGEN Y SUCURSAL ===
    origenes = Origen.objects.all()

    # Matriz de datos para la grilla
    grilla_data = []
    totales_por_origen = {}

    for sucursal in sucursales:
        fila = {'sucursal': sucursal, 'valores': {}, 'total': 0}
        for origen in origenes:
            count = informes_base.filter(sucursal=sucursal, origen=origen).count()
            fila['valores'][origen.id] = count
            fila['total'] += count
            totales_por_origen[origen.id] = totales_por_origen.get(origen.id, 0) + count
        grilla_data.append(fila)

    # === DATOS PARA GRÁFICO DE BARRAS (últimos 7 días) ===
    hace_7_dias = datetime.now() - timedelta(days=7)
    informes_por_dia = (
        informes_base
        .filter(fecha_hora__gte=hace_7_dias)
        .annotate(dia=TruncDate('fecha_hora'))
        .values('dia')
        .annotate(cantidad=Count('id'))
        .order_by('dia')
    )

    # Preparar datos para Chart.js
    chart_labels = []
    chart_data = []
    for item in informes_por_dia:
        chart_labels.append(item['dia'].strftime('%d/%m'))
        chart_data.append(item['cantidad'])

    # === DATOS PARA GRÁFICO DE DONA (por origen) ===
    informes_por_origen = (
        informes_base
        .values('origen__nombre')
        .annotate(cantidad=Count('id'))
        .order_by('-cantidad')
    )

    dona_labels = []
    dona_data = []
    dona_colors = ['#667eea', '#f093fb', '#4facfe', '#fa709a', '#ff9a9e', '#a8edea']
    for idx, item in enumerate(informes_por_origen):
        if item['origen__nombre']:
            dona_labels.append(item['origen__nombre'])
            dona_data.append(item['cantidad'])

    # === TOP 5 BUSES CON MÁS INFORMES ===
    top_buses = (
        informes_base
        .values('bus__ficha')
        .annotate(cantidad=Count('id'))
        .order_by('-cantidad')[:5]
    )

    context = {
        'user_groups': grupos_usuario,
        'sucursales': sucursales,
        'origenes': origenes,
        # Métricas principales
        'total_informes': total_informes,
        'sin_empleado': sin_empleado,
        'no_enviados': no_enviados,
        'sin_expediente': sin_expediente,
        'informes_mes': informes_mes,
        'informes_hoy': informes_hoy,
        # Grilla
        'grilla_data': grilla_data,
        'totales_por_origen': totales_por_origen,
        # Gráficos
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        'dona_labels': dona_labels,
        'dona_data': dona_data,
        'dona_colors': dona_colors[:len(dona_labels)],
        # Top buses
        'top_buses': top_buses,
    }

    return render(request, 'inicio/inicio.html', context)
