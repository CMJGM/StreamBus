# Configuración de Variables de Entorno - StreamBus

## Fecha de Implementación
**2025-11-20**

## Cambios Implementados

### ✅ P0.1 - Secrets Management (COMPLETADO)

Se ha migrado toda la configuración sensible a variables de entorno usando `python-decouple`.

## Archivos Modificados

### 1. Nuevo: `.env`
**Ubicación:** `/StreamBus/.env`
**Estado:** ⚠️ NUNCA SUBIR A GIT

Contiene todas las credenciales y configuración sensible:
- `DJANGO_SECRET_KEY` - Nueva clave secreta generada
- `DEBUG` - Control de modo debug
- `ALLOWED_HOSTS` - Hosts permitidos
- Credenciales de base de datos (default y SIT)
- Credenciales de email
- Credenciales GPS/Citos
- Configuración de Celery/Redis

### 2. Nuevo: `.env.example`
**Ubicación:** `/StreamBus/.env.example`
**Estado:** ✅ Subir a git como plantilla

Plantilla con valores de ejemplo para que otros desarrolladores sepan qué variables configurar.

### 3. Modificado: `StreamBus/settings.py`
**Cambios principales:**
- Importa `from decouple import config, Csv`
- Todas las credenciales ahora usan `config()`
- Valores por defecto seguros configurados

**Antes:**
```python
SECRET_KEY = 'django-insecure-@oic64r!trv^3_eydz6@4p0svih5_v-y)@!w%cq)22_=t^7mzh'
DEBUG = True
```

**Después:**
```python
SECRET_KEY = config('DJANGO_SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
```

### 4. Modificado: `sit/apps.py`
**Cambio:**
- Removida contraseña hardcoded `'Buses2024'`
- Ahora usa `settings.GPS_ACCOUNT` y `settings.GPS_PASSWORD`

### 5. Actualizado: `.gitignore`
**Agregados:**
- `.env` y variantes
- Mejor organización por categorías
- Protección de archivos sensibles

### 6. Actualizado: `requirements.txt`
**Agregado:**
- `python-decouple==3.8`

## Archivos Organizados

### Carpeta DOC/
Se movieron archivos de documentación:
- `MIGRACION_ORIGEN.md`
- `RESOLVER_CONFLICTO_MIGRACIONES.md`
- `settings.py.old` (backup del settings.py antiguo de la raíz)
- Este archivo

### Carpeta TEST/
Se reorganizaron todos los tests:
```
TEST/
├── buses/tests.py
├── categoria/tests.py
├── empleados/tests.py
├── informes/tests.py
├── inicio/tests.py
├── siniestros/tests.py
├── sit/tests.py
├── sucursales/tests.py
└── usuarios/tests.py
```

## Configuración para Desarrollo

### Primera vez (Setup inicial)

```bash
# 1. Clonar repositorio
git clone <repo-url>
cd StreamBus

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Copiar y configurar .env
cp .env.example .env
# Editar .env con tus credenciales reales

# 5. Generar nueva SECRET_KEY (recomendado)
python -c "import secrets; print('DJANGO_SECRET_KEY=' + ''.join(secrets.choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(50)))"
# Copiar el resultado a tu .env

# 6. Migrar base de datos
python manage.py migrate

# 7. Crear superusuario
python manage.py createsuperuser

# 8. Ejecutar servidor
python manage.py runserver
```

### Variables de Entorno Requeridas

#### Mínimas para desarrollo:
```env
DJANGO_SECRET_KEY=tu-key-aqui
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

DB_NAME=streambus
DB_USER=sa
DB_PASSWORD=tu-password
DB_HOST=localhost
DB_PORT=1433
```

#### Completas para producción:
Ver archivo `.env.example` para lista completa.

## Configuración para Producción

### Servidor de Producción

1. **NUNCA** subir el archivo `.env` al repositorio
2. Configurar variables de entorno directamente en el servidor:

```bash
# Opción 1: Archivo .env en el servidor
scp .env user@server:/path/to/StreamBus/.env

# Opción 2: Variables de entorno del sistema
export DJANGO_SECRET_KEY="..."
export DEBUG="False"
# ... etc

# Opción 3: Usando systemd (recomendado)
# Editar: /etc/systemd/system/streambus.service
[Service]
Environment="DJANGO_SECRET_KEY=..."
Environment="DEBUG=False"
```

3. Configurar valores de producción:
```env
DEBUG=False
ALLOWED_HOSTS=tudominio.com,www.tudominio.com
```

## Seguridad

### ✅ Implementado
- [x] SECRET_KEY ya no está en código
- [x] Credenciales de BD protegidas
- [x] Contraseñas de email protegidas
- [x] Credenciales GPS protegidas
- [x] .env en .gitignore
- [x] DEBUG=False por defecto

### ⚠️ Importante
- **NUNCA** hacer commit de `.env`
- Rotar credenciales si se committeó accidentalmente
- Usar SECRET_KEY diferente en cada entorno
- Mantener `.env.example` actualizado (sin valores reales)

## Verificación

### Verificar que no hay secrets en código:
```bash
# Buscar passwords
grep -r "password.*=" --include="*.py" | grep -v "config\|settings"

# Buscar SECRET_KEY hardcoded
grep -r "django-insecure" --include="*.py"

# Verificar .env en .gitignore
git check-ignore .env  # Debe retornar: .env
```

### Verificar que la app funciona:
```bash
# Verificar configuración
python manage.py check

# Verificar conexión a BD
python manage.py migrate --check

# Ejecutar tests
python manage.py test TEST
```

## Troubleshooting

### Error: "DJANGO_SECRET_KEY not found"
**Solución:** Crear archivo `.env` basándote en `.env.example`

### Error: "Database connection failed"
**Solución:** Verificar credenciales en `.env`:
- `DB_HOST`, `DB_USER`, `DB_PASSWORD`
- Probar conexión directa a la BD

### Error: "ModuleNotFoundError: No module named 'decouple'"
**Solución:**
```bash
pip install python-decouple
```

## Próximos Pasos

Ver archivo `../PLAN_SEGURIDAD.md` para los siguientes items a implementar:
- P0.2 - DEBUG=False en producción
- P0.3 - Autenticación en endpoints
- P0.4 - Validación MIME types
- etc.

## Referencias

- [python-decouple docs](https://github.com/HBNetwork/python-decouple)
- [Django deployment checklist](https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/)
- [12 Factor App - Config](https://12factor.net/config)
