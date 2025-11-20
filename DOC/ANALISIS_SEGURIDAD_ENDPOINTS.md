# Análisis de Seguridad - Endpoints Sin Autenticación

## Fecha: 2025-11-20

## Resumen Ejecutivo

**CRÍTICO:** Se identificaron **22 endpoints** sin autenticación en la app `informes`, permitiendo acceso no autorizado a funciones sensibles.

---

## ✅ Mixins de Seguridad Existentes

El proyecto ya tiene excelentes mixins de seguridad en `usuarios/mixins.py`:

### 1. **LoginRequiredMixin** (Django nativo)
- Requiere autenticación para acceder
- Redirige a login si no está autenticado

### 2. **SucursalFilterMixin** (LoginRequiredMixin)
- ✅ Requiere login
- Filtra automáticamente por sucursales del usuario
- Verifica permisos de usuario.profile

### 3. **SucursalAccessMixin** (LoginRequiredMixin)
- ✅ Requiere login
- Verifica acceso a objetos específicos por sucursal
- Bloquea edición/visualización de recursos de otras sucursales

### 4. **InformeFilterMixin** (SucursalFilterMixin)
- ✅ Requiere login (hereda de SucursalFilterMixin)
- Filtros específicos para informes
- Control de acceso por origen

### 5. **EmpleadoFilterMixin** (SucursalFilterMixin)
- ✅ Requiere login (hereda de SucursalFilterMixin)
- Filtros específicos para empleados

### 6. **SucursalFormMixin** ❌
- ⚠️ **NO requiere login**
- Solo pasa el usuario al formulario
- **VULNERABLE**

---

## 🚨 Endpoints Vulnerables Identificados

### Críticos (Manejo de archivos multimedia)

#### 1. `cargar_fotos(request, pk)` - Línea 547
```python
def cargar_fotos(request, pk):  # ❌ Sin @login_required
    informe = get_object_or_404(Informe, pk=pk)
    # Permite subir fotos sin autenticación
```
**Riesgo:** Cualquiera puede subir archivos al servidor

#### 2. `cargar_video(request, pk)` - Línea 581
```python
def cargar_video(request, pk):  # ❌ Sin @login_required
    # Permite subir videos sin autenticación
```
**Riesgo:** Subida de archivos grandes no autorizada → DoS

#### 3. `ver_foto(request, foto_id)` - Línea 614
```python
def ver_foto(request, foto_id):  # ❌ Sin @login_required
    foto = get_object_or_404(FotoInforme, id=foto_id)
```
**Riesgo:** Acceso a imágenes privadas/confidenciales

#### 4. Ver video (inferido, no revisado aún)
**Riesgo:** Acceso a videos privados

---

### Altos (Modificación de datos)

#### 5. `informes_asociar_sitinforme(request)` - Línea 692
```python
def informes_asociar_sitinforme(request):  # ❌ Sin @login_required
    if request.method == 'POST':
        # Modifica campo 'generado' de informes
        informe.generado = True
```
**Riesgo:** Modificación no autorizada de informes

#### 6. `informes_asociar_sitsiniestro(request)` - Línea 725
**Riesgo:** Modificación no autorizada de siniestros

#### 7. `informes_desestimar(request)` - Línea 758
**Riesgo:** Desestimar informes sin autorización

#### 8. `InformeBorrarView` (CBV)
**Riesgo:** Borrado de informes sin autenticación

---

### Medios (Visualización de datos sensibles)

#### 9. `lista_informes(request)` - Línea 471
```python
def lista_informes(request):  # ❌ Sin @login_required
    informes = Informe.objects.all()
```
**Riesgo:** Acceso a todos los informes sin autenticación

#### 10. `buscar_informes(request)` - Línea 476
**Riesgo:** Búsqueda sin autenticación

#### 11. `informes_sin_legajo(request)` - Línea 631
**Riesgo:** Acceso a datos de empleados

#### 12. `informes_no_enviados(request)` - Línea 669
**Riesgo:** Información sensible expuesta

#### 13. `estadisticas_informes(request)` - Línea 832
**Riesgo:** Estadísticas empresariales expuestas

#### 14. `informes_disciplinarios(request)` - Línea 882
**Riesgo:** Datos disciplinarios de empleados expuestos

#### 15. `InformesPorEmpleadoView` (CBV)
**Riesgo:** Historial completo de empleados

---

### Medios-Bajos (Creación sin control)

#### 16-20. Vistas de Creación (CBV con SucursalFormMixin)
- `InformeCreateSistemas` - Línea 71
- `InformeCreateGuardia` - Línea 117
- `InformeCreateSiniestros` - Línea 163
- `InformeCreateTaller` - Línea 207
- `InformeCreateView` - Línea 445
- `InformeCreateInspectores` - Línea 934

**Riesgo:** Creación de informes sin autenticación

#### 21. `EnviarInformeEmailView` (CBV)
**Riesgo:** Envío de emails no autorizado

#### 22. `ListaInformesBorrarView` (CBV)
**Riesgo:** Ver lista de informes a borrar

---

## ✅ Endpoints Protegidos Correctamente

### Function-Based Views con @login_required
1. `descargar_expediente_pdf` ✅
2. `buscar_empleados_ajax` ✅
3. `buscar_buses_ajax` ✅

### Class-Based Views con LoginRequiredMixin
1. `InformeListViewTaller` (InformeFilterMixin) ✅
2. `InformeListViewSiniestro` (InformeFilterMixin) ✅
3. `InformeListViewGuardia` (InformeFilterMixin) ✅
4. `InformeListView` (InformeFilterMixin) ✅
5. `InformeUpdateView` (SucursalAccessMixin) ✅

---

## 📋 Plan de Corrección P0.3

### Fase 1: Corregir SucursalFormMixin (15 min)

**Archivo:** `usuarios/mixins.py`

**Cambio:**
```python
# ANTES
class SucursalFormMixin:
    """Mixin para formularios..."""

# DESPUÉS
class SucursalFormMixin(LoginRequiredMixin):
    """Mixin para formularios..."""
```

**Impacto:** Protege automáticamente 6 vistas de creación

---

### Fase 2: Agregar @login_required a funciones (30 min)

**Archivo:** `informes/views.py`

**Funciones a proteger:**
```python
@login_required
def lista_informes(request):

@login_required
def buscar_informes(request):

@login_required
def cargar_fotos(request, pk):  # CRÍTICO

@login_required
def cargar_video(request, pk):  # CRÍTICO

@login_required
def ver_foto(request, foto_id):  # CRÍTICO

@login_required
def informes_sin_legajo(request):

@login_required
def informes_no_enviados(request):

@login_required
def informes_asociar_sitinforme(request):

@login_required
def informes_asociar_sitsiniestro(request):

@login_required
def informes_desestimar(request):

@login_required
def estadisticas_informes(request):

@login_required
def informes_disciplinarios(request):
```

---

### Fase 3: Agregar LoginRequiredMixin a CBVs (15 min)

**Archivo:** `informes/views.py`

**Vistas a proteger:**
```python
# ANTES
class ListaInformesBorrarView(View):

# DESPUÉS
class ListaInformesBorrarView(LoginRequiredMixin, View):

# Repetir para:
- EnviarInformeEmailView
- InformesPorEmpleadoView
- InformeBorrarView
```

---

### Fase 4: Agregar verificación de sucursal en endpoints críticos (1h)

**Para endpoints de archivos (cargar_fotos, cargar_video, ver_foto):**

```python
@login_required
def cargar_fotos(request, pk):
    informe = get_object_or_404(Informe, pk=pk)

    # ✅ NUEVO: Verificar acceso a sucursal
    if hasattr(request.user, 'profile'):
        profile = request.user.profile
        if not profile.puede_ver_todas:
            if not profile.tiene_acceso_sucursal(informe.sucursal):
                messages.error(request, "No tienes permisos para esta sucursal")
                return redirect('/')

    # ... resto del código
```

---

### Fase 5: Crear decorador de auditoría (30 min)

**Archivo:** `informes/decorators.py` (NUEVO)

```python
from functools import wraps
import logging

logger = logging.getLogger('informes.security')

def audit_file_access(action='view'):
    """
    Decorador para registrar accesos a archivos.

    Uso:
        @audit_file_access(action='upload')
        def cargar_fotos(request, pk):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            logger.info(
                f"File {action}: user={user.username}, "
                f"ip={request.META.get('REMOTE_ADDR')}, "
                f"args={args}"
            )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
```

**Aplicar:**
```python
@login_required
@audit_file_access(action='upload_photo')
def cargar_fotos(request, pk):
    ...

@login_required
@audit_file_access(action='view_photo')
def ver_foto(request, foto_id):
    ...
```

---

### Fase 6: Tests de seguridad (2h)

**Archivo:** `TEST/informes/test_security.py` (NUEVO)

```python
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

class SecurityTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', password='12345')

    def test_cargar_fotos_requires_login(self):
        """Verificar que cargar_fotos requiere autenticación"""
        response = self.client.get(reverse('informes:cargar_fotos', args=[1]))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        self.assertIn('/login/', response.url)

    def test_cargar_fotos_with_login(self):
        """Verificar acceso después de login"""
        self.client.login(username='testuser', password='12345')
        # ... crear informe y probar acceso

    # ... más tests
```

---

## 📊 Impacto Estimado

| Fase | Tiempo | Endpoints Protegidos | Prioridad |
|------|--------|----------------------|-----------|
| Fase 1 | 15 min | 6 vistas | Alta |
| Fase 2 | 30 min | 12 funciones | Crítica |
| Fase 3 | 15 min | 4 CBVs | Alta |
| Fase 4 | 1h | 3 endpoints críticos | Crítica |
| Fase 5 | 30 min | Auditoría | Media |
| Fase 6 | 2h | Tests | Media |
| **TOTAL** | **4.5h** | **22 endpoints** | - |

---

## 🎯 Orden de Ejecución Recomendado

### Implementación Inmediata (1h)
1. ✅ Fase 2: @login_required en funciones (30 min) - **CRÍTICO**
2. ✅ Fase 1: Corregir SucursalFormMixin (15 min) - **ALTA**
3. ✅ Fase 3: LoginRequiredMixin en CBVs (15 min) - **ALTA**

### Implementación Urgente (2h)
4. ✅ Fase 4: Verificación de sucursal (1h) - **CRÍTICO**
5. ✅ Fase 5: Decorador de auditoría (30 min) - **MEDIA**
6. ✅ Fase 6: Tests básicos (30 min de 2h) - **MEDIA**

### Implementación Normal (1.5h)
7. ✅ Fase 6: Tests completos (1.5h restantes) - **MEDIA**

---

## 🔒 Validación Post-Implementación

### Checklist de Seguridad
```bash
# 1. Verificar que ninguna función tiene acceso sin login
grep -E "^def [a-z_]+\(request" informes/views.py | \
  grep -B1 -v "@login_required" | \
  grep "^def"
# ✅ Debe retornar vacío

# 2. Verificar que todas las CBVs heredan de LoginRequiredMixin
grep -E "^class.*View.*\(.*View\)" informes/views.py | \
  grep -v "LoginRequiredMixin"
# ✅ Solo deben quedar las que tienen otro mixin que hereda de LoginRequiredMixin

# 3. Ejecutar tests de seguridad
python manage.py test TEST.informes.test_security
# ✅ Todos los tests deben pasar
```

---

## 📝 Notas Importantes

### ⚠️ Consideraciones

1. **Retrocompatibilidad:** Algunos endpoints públicos pueden ser intencionales
   - **Acción:** Revisar con el equipo antes de aplicar cambios
   - **Alternativa:** Crear settings para endpoints públicos

2. **Performance:** LoginRequiredMixin agrega overhead mínimo
   - **Impacto:** < 5ms por request
   - **Beneficio:** Seguridad >>> Performance

3. **UX:** Redireccionamiento a login puede confundir en AJAX
   - **Solución:** Agregar manejo de errores 401/403 en frontend
   - **Ejemplo:** Mostrar modal de "Sesión expirada"

---

## 🎓 Lecciones Aprendidas

### Buenas Prácticas Implementadas
1. ✅ Mixins reutilizables para control de acceso
2. ✅ Separación de concerns (autenticación, autorización, filtrado)
3. ✅ Logging de auditoría para trazabilidad

### Anti-Patrones Evitados
1. ❌ Vistas sin autenticación
2. ❌ Control de acceso manual en cada vista
3. ❌ Sin logging de acciones sensibles

---

## 📚 Referencias

- [Django LoginRequiredMixin](https://docs.djangoproject.com/en/5.0/topics/auth/default/#the-loginrequired-mixin)
- [Django @login_required](https://docs.djangoproject.com/en/5.0/topics/auth/default/#the-login-required-decorator)
- [OWASP - Broken Access Control](https://owasp.org/Top10/A01_2021-Broken_Access_Control/)

---

**Estado:** ⏳ PENDIENTE DE IMPLEMENTACIÓN
