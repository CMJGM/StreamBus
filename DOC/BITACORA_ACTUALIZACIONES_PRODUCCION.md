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

### [2025-11-25] - Implementar Logging Correcto en Sit App
**Tipo:** Refactor
**Prioridad:** Alta
**Responsable:** TBD

**Descripción:**
Reemplazar todos los `print()` statements en `sit/` por logging apropiado para producción.

**Archivos Modificados:**
- sit/views.py (remover ~50 prints)
- sit/utils.py (remover ~20 prints)
- sit/gps_adapter.py (remover ~15 prints)
- sit/tasks.py (remover ~10 prints)

**Migraciones:**
- [x] No requiere migraciones

**Comandos Post-Deploy:**
```bash
# Verificar configuración de logging
python manage.py check

# Reiniciar servicios
sudo systemctl restart streambus
sudo systemctl restart celery-worker
```

**Testing:**
- [ ] Verificar logs en /var/log/streambus/ o stdout
- [ ] Confirmar que errores GPS se loggean correctamente
- [ ] Validar que Celery tasks loggean progreso

**Rollback Plan:**
```bash
# Revertir commit
git revert <commit-hash>
git push origin main
```

**Estado:** ⏳ Pendiente

**Notas:**
- Coordinar con Ops para verificar rotación de logs
- Considerar nivel de logging (DEBUG en dev, INFO en prod)

---

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

### [TBD] - Refactorizar sit/views.py (1786 líneas)
**Tipo:** Refactor
**Prioridad:** Media
**Responsable:** TBD

**Descripción:**
Dividir `sit/views.py` en módulos más pequeños y manejables.

**Estructura Propuesta:**
```
sit/
  views/
    __init__.py
    gps_views.py           # Tracking y GPS
    photo_download_views.py # Descarga de fotos
    api_views.py           # API endpoints
    admin_views.py         # Vistas admin
```

**Migraciones:**
- [x] No requiere migraciones

**Testing:**
- [ ] Todos los tests existentes pasan
- [ ] Imports actualizados en urls.py
- [ ] No hay regresiones funcionales

**Estado:** ⏳ Pendiente

**Notas:**
- Requiere tests antes de refactorizar
- Hacer en rama separada con PR review

---

## ✅ ACTUALIZACIONES COMPLETADAS

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
- **Features:** 3 completadas
- **BugFixes:** 1 completado
- **Refactors:** 0 completadas
- **Security:** 0 completadas
- **Hotfixes:** 0 completadas

### Por Prioridad
- **Crítica:** 0 completadas, 2 pendientes
- **Alta:** 1 completada, 1 pendiente
- **Media:** 2 completadas, 1 pendiente
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
