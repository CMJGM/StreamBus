# 📝 Bitácora de Actualizaciones a Producción

**Proyecto:** StreamBus
**Ambiente:** Producción
**Responsable:** Equipo Desarrollo

---

## 🎯 PROPÓSITO

Este documento registra TODAS las actualizaciones planificadas y realizadas en el ambiente de producción.

**⚠️ IMPORTANTE:** Antes de cualquier deploy a producción:
1. Revisar este documento
2. Crear entrada en sección "Pendientes"
3. Realizar pruebas en ambiente de desarrollo/staging
4. Crear backup de base de datos
5. Ejecutar deploy
6. Mover entrada a sección "Completadas"

---

## 📋 TEMPLATE DE ENTRADA

```markdown
### [YYYY-MM-DD] - Título del Cambio
**Tipo:** [BugFix | Feature | Refactor | Security | Hotfix]
**Prioridad:** [Crítica | Alta | Media | Baja]
**Responsable:** Nombre

**Descripción:**
Breve descripción del cambio

**Archivos Modificados:**
- path/to/file1.py
- path/to/file2.py

**Migraciones:**
- [ ] No requiere migraciones
- [ ] Requiere: python manage.py migrate

**Comandos Post-Deploy:**
```bash
# Comandos necesarios después del deploy
python manage.py collectstatic --noinput
systemctl restart celery
```

**Testing:**
- [ ] Tests unitarios pasaron
- [ ] Tests manuales en desarrollo
- [ ] Validado por QA/Usuario

**Rollback Plan:**
```bash
# En caso de fallar, ejecutar:
git checkout <commit-anterior>
python manage.py migrate <app> <migration-anterior>
```

**Estado:** ⏳ Pendiente | ✅ Completado | ❌ Rollback

**Notas:**
Observaciones adicionales
```

---

## ⏳ ACTUALIZACIONES PENDIENTES



### [2025-11-30] - Agregar Tests Unitarios Apps Críticas
**Tipo:** Testing
**Prioridad:** Crítica
**Responsable:** TBD

**Descripción:**
Crear suite de tests básica para apps `informes`, `sit`, y `usuarios`.

**Archivos Nuevos:**
- informes/tests/test_models.py
- informes/tests/test_views.py
- informes/tests/test_forms.py
- sit/tests/test_gps_adapter.py
- sit/tests/test_download_tasks.py
- usuarios/tests/test_permissions.py

**Migraciones:**
- [x] No requiere migraciones

**Comandos Post-Deploy:**
```bash
# Ejecutar tests
pytest --cov=informes --cov=sit --cov=usuarios
```

**Testing:**
- [ ] Coverage mínimo 40% en apps críticas
- [ ] Tests de modelos (creación, validaciones)
- [ ] Tests de permisos (sucursal access)
- [ ] Tests de GPS API (con mocks)

**Rollback Plan:**
No aplica (solo agrega tests, no modifica funcionalidad)

**Estado:** ⏳ Pendiente

**Notas:**
- Usar pytest-django y factory_boy para fixtures
- Mockear llamadas a API GPS externa

---

### [2025-12-05] - Auditoría de Seguridad en Producción
**Tipo:** Security
**Prioridad:** Crítica
**Responsable:** TBD

**Descripción:**
Verificar y corregir configuraciones de seguridad en ambiente de producción.

**Checklist:**
- [ ] DEBUG=False
- [ ] ALLOWED_HOSTS específico (no '*')
- [ ] SECRET_KEY único (diferente a dev)
- [ ] SECURE_SSL_REDIRECT=True (si HTTPS)
- [ ] SESSION_COOKIE_SECURE=True
- [ ] CSRF_COOKIE_SECURE=True
- [ ] SECURE_HSTS_SECONDS=31536000
- [ ] Passwords DB no hardcodeados
- [ ] Permisos archivos .env (600)

**Comandos:**
```bash
# Verificar configuración Django
python manage.py check --deploy

# Auditar dependencias
pip install pip-audit
pip-audit
```

**Testing:**
- [ ] SSL Labs test (A+ rating)
- [ ] Verificar headers seguridad (SecurityHeaders.com)
- [ ] Probar CSRF protection funciona
- [ ] Validar sesiones expiradas correctamente

**Estado:** ⏳ Pendiente

**Notas:**
- Coordinar downtime mínimo si requiere cambios
- Documentar cualquier finding crítico

---

---

## ✅ ACTUALIZACIONES COMPLETADAS

### [2025-11-22] - Implementar Logging en Lugar de print()
**Tipo:** Refactor
**Prioridad:** Alta
**Responsable:** Claude Agent

**Descripción:**
Reemplazados 87 `print()` statements por logging apropiado en apps `sit` e `informes` para mejorar trazabilidad en producción.

**Archivos Modificados:**
- sit/views.py (52 prints → 52 logger statements)
- sit/utils.py (32 prints → 32 logger statements)
- sit/gps_adapter.py (2 prints → 22 logger statements)
- informes/views.py (1 print → 29 logger statements adicionales)
- sit/views/stats.py (nuevo - clases de estadísticas)

**Migraciones:**
- [x] No requiere migraciones

**Comandos Post-Deploy:**
```bash
# Crear directorio de logs
mkdir -p /var/www/streambus/logs
chmod 755 /var/www/streambus/logs

# Verificar sintaxis
python -m py_compile sit/views.py sit/utils.py sit/gps_adapter.py informes/views.py

# Reiniciar servicios
sudo systemctl restart streambus
sudo systemctl restart celery-worker
```

**Testing:**
- [x] Sintaxis Python verificada correctamente
- [x] No quedan print() statements (verificado con grep)
- [x] 135 logger statements agregados
- [ ] Verificar logs en producción después de deploy

**Rollback Plan:**
```bash
# Revertir commit
git revert 92d732f
git push origin claude/project-analysis-improvements-01RNexvQDpVfeuowaWtPP99K
systemctl restart streambus
```

**Estado:** ✅ Completado (2025-11-22)

**Commit:** 92d732f - refactor: Reemplazar print() por logging en apps sit e informes

**Beneficios:**
- ✅ Logs visibles en producción (gunicorn/uwsgi)
- ✅ Niveles configurables (DEBUG, INFO, WARNING, ERROR)
- ✅ Trazabilidad para debugging
- ✅ Integración con herramientas de monitoreo

**Documentación:**
- Ver DOC/CAMBIOS_LOGGING.md para detalles completos
- Relacionado con DOC/ANALISIS_PROYECTO_Y_MEJORAS.md (Problema #3)

**Notas:**
- ⚠️ IMPORTANTE: Configurar rotación de logs en producción
- Ajustar LOG_LEVEL=INFO en .env de producción (no DEBUG)
- Verificar permisos del directorio de logs

---

### [2025-11-22] - Logging con Formato Personalizado (Timestamp + Usuario)
**Tipo:** Feature
**Prioridad:** Alta
**Responsable:** Claude Agent

**Descripción:**
Implementación de sistema de logging con formato personalizado que incluye timestamp y usuario autenticado.
Formato: `YYYY-MM-DD HH:MM:SS | username | LEVEL | logger | mensaje`

**Archivos Nuevos:**
- StreamBus/logging_filters.py (UserFilter class + thread-local storage)
- StreamBus/middleware.py (LoggingMiddleware para capturar request)

**Archivos Modificados:**
- StreamBus/settings.py (LOGGING config + middleware)

**Migraciones:**
- [x] No requiere migraciones

**Comandos Post-Deploy:**
```bash
# Crear directorio de logs
mkdir -p /var/www/streambus/logs
chmod 755 /var/www/streambus/logs
chown www-data:www-data /var/www/streambus/logs

# Verificar sintaxis
python -m py_compile StreamBus/logging_filters.py StreamBus/middleware.py

# Configurar logrotate
cat > /etc/logrotate.d/streambus <<'EOF'
/var/www/streambus/debug.log {
    daily
    missingok
    rotate 14
    compress
    notifempty
    create 0644 www-data www-data
    sharedscripts
    postrotate
        systemctl reload streambus > /dev/null 2>&1 || true
    endscript
}
EOF

# Reiniciar servicios
systemctl restart streambus
systemctl restart celery-worker
```

**Testing:**
- [x] Sintaxis Python verificada
- [x] RotatingFileHandler configurado (10MB, 5 backups)
- [x] UserFilter agrega username correctamente
- [x] LoggingMiddleware captura request
- [ ] Verificar formato en producción después de deploy

**Rollback Plan:**
```bash
# Revertir commits de logging
git revert 100d585  # docs
git revert b90c91a  # logging implementation
systemctl restart streambus
```

**Estado:** ✅ Completado (2025-11-22)

**Commits:**
- 100d585 - docs: Agregar documentación de cambios de logging
- b90c91a - refactor: Dividir sit/views.py en módulos y agregar logging con usuario

**Beneficios:**
- ✅ Logs muestran usuario autenticado (auditoría)
- ✅ Timestamp en formato legible
- ✅ Celery tasks muestran "system" como usuario
- ✅ Rotación automática de logs (evita llenado de disco)
- ✅ Niveles configurables por ambiente (DEBUG en dev, INFO en prod)

**Documentación:**
- Ver DOC/CAMBIOS_LOGGING.md para detalles de implementación
- Ver DOC/REFACTORIZACION_MODULOS.md sección logging

**Notas:**
- ⚠️ CRÍTICO: Verificar que LoggingMiddleware esté en MIDDLEWARE settings
- Logs de usuarios autenticados: `username`
- Logs anónimos: `AnonymousUser`
- Logs de Celery/management commands: `system`

---

### [2025-11-22] - Refactorización de sit/views.py en Módulos
**Tipo:** Refactor
**Prioridad:** Alta
**Responsable:** Claude Agent

**Descripción:**
División de `sit/views.py` (1,786 líneas) en 5 módulos organizados por dominio funcional.
Reducción de 72% en tamaño del archivo más grande.

**Estructura Implementada:**
```
sit/views/
├── __init__.py (exports para backwards compatibility)
├── gps_views.py (16 KB, ~200 líneas) - GPS tracking y ubicaciones
├── photo_download_views.py (39 KB, ~500 líneas) - Descarga masiva de fotos
├── alarmas_views.py (11 KB, ~150 líneas) - Consultas de alarmas
├── informes_views.py (2.5 KB, ~40 líneas) - Informes PDF
└── stats.py (6.5 KB, ~150 líneas) - Clases de estadísticas
```

**Archivos Nuevos:**
- sit/views/__init__.py (backwards compatibility - todos los imports siguen funcionando)
- sit/views/gps_views.py (9 funciones GPS)
- sit/views/photo_download_views.py (15 funciones descarga)
- sit/views/alarmas_views.py (3 funciones alarmas)
- sit/views/informes_views.py (2 funciones PDF)
- sit/views/stats.py (2 clases estadísticas)
- informes/views/__init__.py (placeholder para futura refactorización)

**Archivos Eliminados:**
- sit/views.py (dividido en módulos, backup en sit/views_old.py localmente)

**Archivos Modificados:**
- .gitignore (agregado *_old.py para backups)

**Migraciones:**
- [x] No requiere migraciones

**Comandos Post-Deploy:**
```bash
# Verificar sintaxis de todos los módulos
python -m py_compile sit/views/*.py

# Verificar imports funcionan (backwards compatibility)
python manage.py shell <<EOF
from sit.views import mapa_ubicacion
from sit.views import security_photos_form
from sit.views.gps_views import obtener_empresas_disponibles
print("✅ Imports OK")
EOF

# Reiniciar servicios
systemctl restart streambus
systemctl restart celery-worker

# Verificar logs
tail -f /var/www/streambus/debug.log | grep "sit.views"
```

**Testing:**
- [x] Sintaxis Python verificada (py_compile)
- [x] Backwards compatibility mantenida (__init__.py exports)
- [x] Backups creados (sit/views_old.py)
- [ ] Tests funcionales en desarrollo
- [ ] Validar todas las URLs funcionan
- [ ] Verificar descarga de fotos funciona
- [ ] Verificar GPS tracking funciona

**Rollback Plan:**
```bash
# Revertir a archivo monolítico
git revert 989a1a2  # Completar migración
git revert b90c91a  # División en módulos
systemctl restart streambus
```

**Estado:** ✅ Completado (2025-11-22)

**Commits:**
- b90c91a - refactor: Dividir sit/views.py en módulos y agregar logging con usuario
- 989a1a2 - refactor: Completar migración de sit/views.py a módulos
- 9d288f9 - docs: Documentar refactorización de módulos y logging con usuario

**Métricas de Mejora:**
- **Archivo más grande:** 1,786 líneas → 500 líneas (-72%)
- **Módulos creados:** 1 archivo → 5 módulos organizados
- **Facilidad de localización:** Código organizado por dominio
- **Mantenibilidad:** Cada módulo tiene responsabilidad única

**Documentación:**
- Ver DOC/REFACTORIZACION_MODULOS.md para documentación completa
- Ver DOC/ANALISIS_PROYECTO_Y_MEJORAS.md (Problema #2 resuelto)

**Notas:**
- ✅ Todos los imports existentes siguen funcionando (sit.views.*)
- ✅ No se requieren cambios en urls.py ni templates
- ⚠️ informes/views.py (1,497 líneas) pendiente de refactorizar (requiere tests primero)
- ⚠️ IMPORTANTE: Hacer testing exhaustivo en desarrollo antes de deploy a producción

---

### [2025-11-22] - Mejoras Estéticas del Menú de Navegación
**Tipo:** Feature
**Prioridad:** Baja
**Responsable:** Claude Agent

**Descripción:**
Modernización del navbar con Bootstrap 5, corrección de estilos y eliminación de errores JavaScript de Popper.js.

**Archivos Modificados:**
- templates/base.html
- static_dev/css/custom.css
- Múltiples commits (ver historial)

**Migraciones:**
- [x] No requiere migraciones

**Comandos Post-Deploy:**
```bash
python manage.py collectstatic --noinput
```

**Testing:**
- [x] Menú desplegable funciona correctamente
- [x] Sin errores en consola JavaScript
- [x] Responsive en móviles

**Estado:** ✅ Completado (2025-11-22)

**Commits:**
- 95cb1ec: Merge estilos menu
- f5141f2: Estilos con ID selector
- 4dede96: Alta especificidad items
- 0ac32b6: Eliminar ES modules
- 4a5440e: Corregir Popper.js

**Notas:**
Deploy exitoso sin incidentes.

---

### [2025-11-20] - Dashboard de Métricas en Página Inicio
**Tipo:** Feature
**Prioridad:** Media
**Responsable:** Claude Agent

**Descripción:**
Agregado dashboard con métricas en tiempo real: total informes, pendientes, sin empleado, últimos 30 días, hoy.
Gráficos con Chart.js (barras por día, donut por origen).

**Archivos Modificados:**
- inicio/views.py
- templates/inicio/home.html
- static_dev/js/dashboard.js (nuevo)

**Migraciones:**
- [x] No requiere migraciones

**Testing:**
- [x] Métricas calculan correctamente
- [x] Gráficos renderizan bien
- [x] Links a filtros funcionan

**Estado:** ✅ Completado (2025-11-20)

**Commits:**
- cb8339e: Dashboard con métricas
- 11a6d87: Reducir tamaño gráficos

**Notas:**
Feedback positivo de usuarios.

---

### [2025-11-18] - Validación de Expediente Obligatorio
**Tipo:** Feature + BugFix
**Prioridad:** Alta
**Responsable:** Claude Agent

**Descripción:**
Agregar validación: expediente obligatorio solo cuando checkbox "Generado" está marcado.
Botón de confirmación rápida en formulario.

**Archivos Modificados:**
- informes/forms.py
- informes/views.py
- templates/informes/informe_form.html

**Migraciones:**
- [x] No requiere migraciones

**Testing:**
- [x] Validación funciona correctamente
- [x] Mensajes de error claros
- [x] Botón confirmación rápida OK

**Estado:** ✅ Completado (2025-11-18)

**Commits:**
- 8f65782: Corregir validación expediente
- 6c85519: Agregar validación + botón

**Notas:**
Resuelve problema reportado por usuarios (error 500 al editar).

---

## 📊 ESTADÍSTICAS

### Por Tipo (Últimos 3 meses)
- **Features:** 4 completadas
- **BugFixes:** 1 completado
- **Refactors:** 2 completadas
- **Security:** 0 completadas
- **Hotfixes:** 0 completadas

### Por Prioridad
- **Crítica:** 0 completadas, 2 pendientes
- **Alta:** 3 completadas, 0 pendientes
- **Media:** 2 completadas, 0 pendientes
- **Baja:** 1 completada, 0 pendientes

### Tiempo Promedio Deploy
- **Estimado:** ~30 minutos (incluyendo testing)

---

## 🚨 INCIDENTES EN PRODUCCIÓN

### Template de Incidente
```markdown
### [YYYY-MM-DD HH:MM] - Título del Incidente
**Severidad:** [P0-Crítico | P1-Alto | P2-Medio | P3-Bajo]
**Duración:** HH:MM
**Usuarios Afectados:** N usuarios / % del total

**Descripción:**
Qué pasó

**Root Cause:**
Por qué pasó

**Resolución:**
Cómo se resolvió

**Prevención:**
Qué haremos para que no vuelva a pasar

**Timeline:**
- HH:MM - Detectado
- HH:MM - Investigación iniciada
- HH:MM - Fix aplicado
- HH:MM - Validado resuelto
```

### Historial de Incidentes
*(No hay incidentes registrados aún)*

---

## 📖 PROCESOS

### Proceso de Deploy Estándar

```bash
# 1. PREPARACIÓN (Desarrollo)
git checkout main
git pull origin main
git checkout -b feature/nombre-cambio

# [... hacer cambios ...]

# 2. TESTING LOCAL
python manage.py test
pytest --cov=.
python manage.py check --deploy

# 3. COMMIT Y PUSH
git add .
git commit -m "feat: descripción del cambio"
git push origin feature/nombre-cambio

# 4. CODE REVIEW
# Crear Pull Request en GitHub
# Esperar aprobación

# 5. MERGE A MAIN
git checkout main
git merge feature/nombre-cambio
git push origin main

# 6. BACKUP PRODUCCIÓN
ssh user@produccion
cd /var/backups/streambus/
pg_dump streambus > streambus_$(date +%Y%m%d_%H%M%S).sql

# 7. DEPLOY
cd /var/www/streambus
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput

# 8. RESTART SERVICES
sudo systemctl restart streambus
sudo systemctl restart celery-worker
sudo systemctl restart nginx

# 9. VERIFICACIÓN
curl -I https://streambus.com/health/
# Verificar logs
tail -f /var/log/streambus/app.log

# 10. ACTUALIZAR BITÁCORA
# Mover entrada de Pendiente a Completada
```

### Proceso de Rollback

```bash
# 1. IDENTIFICAR COMMIT ANTERIOR ESTABLE
git log --oneline -10

# 2. REVERTIR
git revert <commit-hash-problemático>
git push origin main

# 3. DEPLOY REVERT
cd /var/www/streambus
git pull origin main

# 4. MIGRACIONES (si aplicaron)
python manage.py migrate <app> <migration-anterior>

# 5. RESTART
sudo systemctl restart streambus
sudo systemctl restart celery-worker

# 6. VERIFICAR
curl -I https://streambus.com/health/

# 7. POST-MORTEM
# Documentar en sección Incidentes
# Actualizar bitácora
```

---

## 🔗 RECURSOS

### Ambientes
- **Producción:** https://streambus.autobusessantafe.com.ar (TBD)
- **Staging:** N/A (crear recomendado)
- **Desarrollo:** http://localhost:8000

### Contactos
- **Responsable Técnico:** [Nombre]
- **Responsable Ops:** [Nombre]
- **On-Call:** [Rotación/Nombre]

### Documentación
- [ANALISIS_PROYECTO_Y_MEJORAS.md](./ANALISIS_PROYECTO_Y_MEJORAS.md)
- [CONFIGURACION_ENV.md](./CONFIGURACION_ENV.md)
- [DEPLOYMENT.md](./DEPLOYMENT.md) (pendiente crear)

---

**Última actualización:** 2025-11-22
**Próxima revisión:** Semanal (cada lunes)
