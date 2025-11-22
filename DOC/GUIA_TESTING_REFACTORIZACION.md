# 🧪 Guía de Testing - Refactorización y Logging

**Fecha:** 2025-11-22
**Objetivo:** Validar que las refactorizaciones y mejoras de logging funcionan correctamente sin afectar la funcionalidad existente.

---

## 📋 ÍNDICE

1. [Tests Básicos de Imports](#1-tests-básicos-de-imports)
2. [Tests de Logging con Usuario](#2-tests-de-logging-con-usuario)
3. [Tests Funcionales - GPS y Ubicaciones](#3-tests-funcionales---gps-y-ubicaciones)
4. [Tests Funcionales - Descarga de Fotos](#4-tests-funcionales---descarga-de-fotos)
5. [Tests Funcionales - Informes](#5-tests-funcionales---informes)
6. [Tests de Alarmas](#6-tests-de-alarmas)
7. [Verificación de Logs](#7-verificación-de-logs)
8. [Checklist Final](#8-checklist-final)

---

## 1. Tests Básicos de Imports

### 1.1 Verificar Imports de Python

Ejecuta estos comandos en el shell de Django para verificar que todos los módulos se importan correctamente:

```bash
python manage.py shell
```

Dentro del shell, ejecuta:

```python
# Test 1: Imports desde sit.views (backwards compatibility)
from sit.views import mapa_ubicacion, security_photos_form, alarmas_view
from sit.views import ubicacion_json, ubicaciones_vehiculos
from sit.views import fetch_security_photos, check_download_status
print("✓ Imports principales OK")

# Test 2: Imports directos desde módulos
from sit.views.gps_views import obtener_empresas_disponibles, actualizar_ubicacion_cache
from sit.views.photo_download_views import background_download_process
from sit.views.alarmas_views import query_security_photos
from sit.views.informes_views import listar_informes_sit
print("✓ Imports de módulos OK")

# Test 3: Imports de clases de estadísticas
from sit.views.stats import DownloadStatistics, BasicOptimizedStats
stats = DownloadStatistics()
print(f"✓ Estadísticas OK - Tipo: {type(stats)}")

# Test 4: Imports de informes (sin refactorizar)
from informes.views import InformesPorEmpleadoView, estadisticas_informes
from informes.views import InformeListView, InformeDetailView
print("✓ Imports de informes OK")

# Test 5: Verificar logging filters y middleware
from StreamBus.logging_filters import UserFilter, get_current_request
from StreamBus.middleware import LoggingMiddleware
print("✓ Logging components OK")

# Salir del shell
exit()
```

**Resultado esperado:** Todos los prints deben mostrar "✓ ... OK" sin errores.

---

## 2. Tests de Logging con Usuario

### 2.1 Verificar Configuración de Logging

```bash
python manage.py shell
```

```python
import logging
from django.conf import settings

# Verificar configuración
print("LOGGING configurado:", 'LOGGING' in dir(settings))
print("Handlers:", list(settings.LOGGING['handlers'].keys()))
print("Formatters:", list(settings.LOGGING['formatters'].keys()))
print("Filters:", list(settings.LOGGING['filters'].keys()))

# Verificar middleware
print("\nLoggingMiddleware presente:", 'StreamBus.middleware.LoggingMiddleware' in settings.MIDDLEWARE)

exit()
```

### 2.2 Test de Logging en Consola

Con el servidor ejecutándose (`python manage.py runserver`), observa los logs en la consola:

**Formato esperado:**
```
YYYY-MM-DD HH:MM:SS | username | LEVEL | logger_name | mensaje
```

**Ejemplos:**
```
2025-11-22 13:30:45 | system | INFO | sit.utils | Usando funciones GPS legacy
2025-11-22 13:31:20 | admin | INFO | sit.views.gps | Consultando ubicación de vehículo 123
2025-11-22 13:32:10 | AnonymousUser | DEBUG | sit.views.photos | Iniciando descarga de fotos
```

### 2.3 Verificar Archivo debug.log

```bash
# Ver últimas 20 líneas del log
tail -20 debug.log

# Monitorear logs en tiempo real
tail -f debug.log
```

**Verificar:**
- ✅ Cada línea tiene el formato: `timestamp | usuario | nivel | logger | mensaje`
- ✅ Usuarios autenticados muestran su username
- ✅ Usuarios no autenticados muestran "AnonymousUser"
- ✅ Tareas de Celery muestran "system"

---

## 3. Tests Funcionales - GPS y Ubicaciones

### 3.1 Vista de Mapa de Ubicación

**URL a probar:**
```
http://localhost:8000/sit/mapa-ubicacion/?ficha=<NUMERO_FICHA>
```

**Pasos:**
1. Inicia sesión en la aplicación
2. Navega a la URL del mapa con una ficha válida
3. Verifica que el mapa se muestra correctamente
4. Verifica que aparece el marcador del vehículo

**Logs esperados en debug.log:**
```
2025-11-22 13:35:10 | tu_usuario | INFO | sit.views.gps | Consultando ubicación para ficha: <NUMERO>
```

### 3.2 Vista de Ubicaciones de Vehículos

**URL a probar:**
```
http://localhost:8000/sit/ubicaciones-vehiculos/
```

**Pasos:**
1. Navega a la URL de ubicaciones
2. Selecciona una empresa del dropdown
3. Verifica que aparece la lista de vehículos
4. Verifica que cada vehículo muestra:
   - Ficha
   - Última ubicación
   - Tiempo transcurrido
   - Estado (activo/inactivo)

**Logs esperados:**
```
2025-11-22 13:36:30 | tu_usuario | INFO | sit.views.gps | Consultando ubicaciones para empresa: <ID>
```

### 3.3 API JSON de Ubicación

**URL a probar:**
```
http://localhost:8000/sit/ubicacion-json/?ficha=<NUMERO_FICHA>
```

**Pasos:**
1. Abre la URL en el navegador o usa curl:
```bash
curl "http://localhost:8000/sit/ubicacion-json/?ficha=123"
```

2. Verifica que la respuesta JSON contiene:
```json
{
    "lat": -31.xxxx,
    "lng": -60.xxxx,
    "timestamp": "2025-11-22T13:37:00",
    "vehiculo": "Ficha 123",
    "velocidad": 45
}
```

---

## 4. Tests Funcionales - Descarga de Fotos

### 4.1 Formulario de Descarga de Fotos de Seguridad

**URL a probar:**
```
http://localhost:8000/sit/security-photos-form/
```

**Pasos:**
1. Navega a la URL del formulario
2. Verifica que se muestra el formulario con:
   - Selector de empresa
   - Selector de vehículos
   - Campos de fecha inicio/fin
   - Opciones de descarga (fotos, alarmas, etc.)
3. **NO inicies una descarga todavía** (solo verifica que el formulario carga)

**Logs esperados:**
```
2025-11-22 13:40:00 | tu_usuario | INFO | sit.views.photos | Mostrando formulario de descarga de fotos
```

### 4.2 Proceso de Descarga (OPCIONAL - Solo si tienes datos reales)

**⚠️ ADVERTENCIA:** Esto iniciará una descarga real de fotos desde la API GPS.

**URL a probar:**
```
http://localhost:8000/sit/fetch-security-photos/
```

**Pasos:**
1. Completa el formulario con datos de prueba:
   - Selecciona una empresa
   - Selecciona 1-2 vehículos
   - Rango de fechas corto (ej: 1 hora)
2. Haz clic en "Descargar"
3. Verifica que aparece el modal de progreso
4. Observa los logs en tiempo real:

```bash
tail -f debug.log
```

**Logs esperados durante descarga:**
```
2025-11-22 13:45:00 | tu_usuario | INFO | sit.views.photos | Iniciando descarga para 2 vehículos
2025-11-22 13:45:01 | tu_usuario | INFO | sit.views.photos | Job ID: abc123 creado
2025-11-22 13:45:02 | system | INFO | sit.views.photos | Background download iniciado
2025-11-22 13:45:05 | system | INFO | sit.views.photos | Descargando foto 1/10
```

### 4.3 Verificar Estado de Descarga

**URL a probar:**
```
http://localhost:8000/sit/check-download-status/?job_id=<JOB_ID>
```

**Pasos:**
1. Copia el Job ID del paso anterior
2. Navega a la URL de status
3. Verifica que la respuesta JSON contiene:
```json
{
    "status": "in_progress",
    "progress": 50,
    "total": 100,
    "downloaded": 50,
    "errors": 0
}
```

---

## 5. Tests Funcionales - Informes

### 5.1 Listado de Informes

**URL a probar:**
```
http://localhost:8000/informes/
```

**Pasos:**
1. Navega a la URL de informes
2. Verifica que se muestra la lista de informes
3. Verifica paginación funciona
4. Verifica filtros funcionan (por fecha, empleado, etc.)

**Logs esperados:**
```
2025-11-22 13:50:00 | tu_usuario | INFO | informes.views | Listando informes - página 1
```

### 5.2 Detalle de Informe

**URL a probar:**
```
http://localhost:8000/informes/<ID>/
```

**Pasos:**
1. Selecciona un informe de la lista
2. Haz clic para ver detalle
3. Verifica que se muestra toda la información:
   - Datos del informe
   - Empleado asociado
   - Fotos adjuntas
   - Estado

**Logs esperados:**
```
2025-11-22 13:51:00 | tu_usuario | INFO | informes.views | Mostrando detalle de informe ID: <ID>
```

### 5.3 Crear/Editar Informe

**URL a probar:**
```
http://localhost:8000/informes/crear/
http://localhost:8000/informes/<ID>/editar/
```

**Pasos:**
1. Navega a crear nuevo informe
2. Completa el formulario (NO guardes todavía)
3. Verifica que todos los campos se muestran
4. Verifica validaciones funcionan
5. **Opcional:** Guarda y verifica que se crea correctamente

---

## 6. Tests de Alarmas

### 6.1 Vista de Alarmas

**URL a probar:**
```
http://localhost:8000/sit/alarmas/
```

**Pasos:**
1. Navega a la URL de alarmas
2. Completa el formulario de búsqueda:
   - Selecciona empresa
   - Selecciona vehículo
   - Define rango de fechas
3. Haz clic en "Buscar"
4. Verifica que se muestran resultados paginados

**Logs esperados:**
```
2025-11-22 13:55:00 | tu_usuario | INFO | sit.views.alarmas | Consultando alarmas para vehículo: <ID>
2025-11-22 13:55:01 | tu_usuario | INFO | sit.views.alarmas | Encontradas 25 alarmas
```

---

## 7. Verificación de Logs

### 7.1 Verificar Formato de Logs

Ejecuta estos comandos para validar el formato de los logs:

```bash
# Ver todas las entradas con usuario autenticado
grep -E "\| [a-zA-Z0-9_]+ \|" debug.log | tail -20

# Ver entradas del sistema (Celery, management commands)
grep "| system |" debug.log | tail -10

# Ver entradas de usuarios anónimos
grep "| AnonymousUser |" debug.log | tail -10

# Ver errores
grep "| ERROR |" debug.log | tail -10

# Ver logs de sit.views.gps específicamente
grep "sit.views.gps" debug.log | tail -10

# Ver logs de descarga de fotos
grep "sit.views.photos" debug.log | tail -20
```

### 7.2 Verificar Rotación de Logs

```bash
# Verificar tamaño del log actual
ls -lh debug.log

# Si el log supera 10MB, debería crear debug.log.1, debug.log.2, etc.
ls -lh debug.log*
```

### 7.3 Verificar Logs por Usuario

```bash
# Ver todas las acciones de un usuario específico
grep "| tu_usuario |" debug.log | tail -30

# Contar acciones por usuario
grep -oE "\| [a-zA-Z0-9_]+ \|" debug.log | sort | uniq -c | sort -rn
```

---

## 8. Checklist Final

### ✅ Tests de Imports
- [ ] Todos los imports de `sit.views` funcionan
- [ ] Imports directos de módulos funcionan
- [ ] Imports de `sit.views.stats` funcionan
- [ ] Imports de `informes.views` funcionan
- [ ] Logging components se importan sin error

### ✅ Tests de Logging
- [ ] Logs se escriben en `debug.log`
- [ ] Formato incluye: timestamp | usuario | nivel | logger | mensaje
- [ ] Usuarios autenticados muestran username correcto
- [ ] Usuarios anónimos muestran "AnonymousUser"
- [ ] Logs del sistema muestran "system"

### ✅ Tests Funcionales - Módulo SIT
- [ ] Mapa de ubicación carga correctamente
- [ ] Lista de ubicaciones de vehículos funciona
- [ ] API JSON de ubicación responde correctamente
- [ ] Formulario de descarga de fotos se muestra
- [ ] Proceso de descarga funciona (opcional)
- [ ] Vista de alarmas funciona y pagina correctamente

### ✅ Tests Funcionales - Módulo Informes
- [ ] Listado de informes se muestra correctamente
- [ ] Detalle de informe se muestra correctamente
- [ ] Filtros y búsqueda funcionan
- [ ] Paginación funciona
- [ ] Crear/editar informe funciona

### ✅ Verificación de Performance
- [ ] Las páginas cargan en tiempo razonable
- [ ] No hay errores 500 en ninguna vista
- [ ] No hay warnings en la consola de Django
- [ ] Los logs no muestran errores inesperados

---

## 📊 Reporte de Testing

Una vez completados los tests, documenta los resultados:

```markdown
## Reporte de Testing - Refactorización sit/views.py

**Fecha:** YYYY-MM-DD
**Tester:** [Tu nombre]
**Ambiente:** Desarrollo / Windows

### Tests Ejecutados
- Total: XX
- Exitosos: XX
- Fallidos: XX

### Bugs Encontrados
1. [Descripción del bug]
   - Severidad: Alta/Media/Baja
   - Pasos para reproducir: ...
   - Logs: ...

### Conclusión
[ ] ✅ Todos los tests pasaron - OK para deploy
[ ] ⚠️ Tests pasaron con warnings menores
[ ] ❌ Hay bugs críticos que requieren atención
```

---

## 🔧 Troubleshooting

### Problema: No se generan logs
**Solución:**
```bash
# Verificar que el archivo se puede crear
touch debug.log
chmod 644 debug.log

# Verificar configuración
python manage.py shell -c "from django.conf import settings; print(settings.LOGGING)"
```

### Problema: Logs sin usuario
**Solución:**
```python
# Verificar middleware está activo
python manage.py shell
from django.conf import settings
print('StreamBus.middleware.LoggingMiddleware' in settings.MIDDLEWARE)
```

### Problema: ImportError después de refactorización
**Solución:**
```bash
# Limpiar archivos .pyc
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +

# Reiniciar servidor
```

### Problema: Vista no carga
**Solución:**
```bash
# Ver traceback completo en consola
python manage.py runserver

# Ver logs con más detalle
tail -f debug.log | grep ERROR
```

---

## 📝 Notas Adicionales

### Performance
- Si notas lentitud, verifica que el nivel de logging en producción sea `INFO` no `DEBUG`
- La rotación de logs está configurada para 10MB, 5 backups

### Seguridad
- Los logs contienen usernames - proteger el archivo `debug.log`
- No commitear `debug.log` al repositorio (ya está en .gitignore)

### Próximos Pasos
Una vez validado todo en desarrollo:
1. Actualizar bitácora con resultados de testing
2. Preparar deploy a staging/producción
3. Coordinar ventana de mantenimiento si es necesario

---

**Última actualización:** 2025-11-22
**Versión:** 1.0
