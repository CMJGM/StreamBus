# Guía de Migración: Sistema de Permisos de Origen

## Resumen de Cambios

Se implementó un **sistema de permisos por usuario para el campo Origen** en los informes, reemplazando el sistema hardcodeado anterior.

### Cambios Principales:

1. **Nuevo Modelo `Origen`**: Gestiona los diferentes orígenes de informes de forma dinámica
2. **Permisos por Usuario**: Cada usuario puede tener asignados orígenes específicos
3. **Filtrado Automático**: Los formularios solo muestran orígenes permitidos para cada usuario

---

## ⚠️ IMPORTANTE: Eliminar Migraciones Incorrectas

Si ejecutaste `makemigrations` y obtuviste el error:
```
Error al convertir el tipo de datos nvarchar a bigint
```

**Debes eliminar las migraciones incorrectas antes de continuar:**

### En tu entorno local (Windows):

```bash
# 1. Eliminar las migraciones auto-generadas incorrectas
del informes\migrations\0014_origen_alter_informe_origen.py
del usuarios\migrations\0002_userprofile_origenes_and_more.py

# 2. Si hay archivos __pycache__, eliminarlos también
del informes\migrations\__pycache__\0014_*.pyc
del usuarios\migrations\__pycache__\0002_*.pyc
```

### En Linux/Mac:

```bash
# 1. Eliminar las migraciones auto-generadas incorrectas
rm informes/migrations/0014_origen_alter_informe_origen.py
rm usuarios/migrations/0002_userprofile_origenes_and_more.py

# 2. Si hay archivos __pycache__, eliminarlos también
rm informes/migrations/__pycache__/0014_*.pyc
rm usuarios/migrations/__pycache__/0002_*.pyc
```

---

## Pasos para Migrar la Base de Datos

### 1. Asegúrate de tener las últimas migraciones

Las migraciones correctas ya están incluidas en el repositorio:

**Migraciones de Informes:**
- `0014_crear_modelo_origen.py` - Crea el modelo Origen
- `0015_poblar_origenes.py` - Crea los 6 orígenes predefinidos
- `0016_agregar_campo_origen_nuevo.py` - Agrega campo temporal origen_new
- `0017_migrar_datos_origen.py` - Migra los datos del campo antiguo al nuevo
- `0018_finalizar_migracion_origen.py` - Elimina campo antiguo y renombra

**Migraciones de Usuarios:**
- `0002_agregar_permisos_origenes.py` - Agrega campos de permisos de origen

### 2. Ejecutar las Migraciones

```bash
# Ejecutar todas las migraciones en orden
python manage.py migrate
```

Las migraciones se ejecutarán automáticamente en el orden correcto y:
1. ✅ Crearán el modelo `Origen`
2. ✅ Crearán los 6 orígenes: Sistemas, Guardia, RRHH, Taller, Siniestros, Inspectores
3. ✅ Migrarán todos los datos existentes del campo antiguo al nuevo
4. ✅ Agregarán los campos de permisos de origen en `UserProfile`

### 3. Verificar que las migraciones se aplicaron correctamente

```bash
# Ver el estado de las migraciones
python manage.py showmigrations informes usuarios
```

Deberías ver todas las migraciones marcadas con `[X]`:

```
informes
 [X] 0001_initial
 ...
 [X] 0014_crear_modelo_origen
 [X] 0015_poblar_origenes
 [X] 0016_agregar_campo_origen_nuevo
 [X] 0017_migrar_datos_origen
 [X] 0018_finalizar_migracion_origen

usuarios
 [X] 0001_initial
 [X] 0002_agregar_permisos_origenes
```

---

## Configuración Post-Migración

### 1. Asignar Orígenes a TODOS los Usuarios Existentes

**⚠️ MUY IMPORTANTE:** Después de migrar, **TODOS los usuarios necesitan tener al menos un origen asignado**.

#### Opción A - Asignar todos los orígenes a todos los usuarios (Recomendado para inicio):

```python
# Ejecutar en Django shell
python manage.py shell
```

```python
from usuarios.models import UserProfile
from informes.models import Origen

# Opción 1: Dar acceso a todos los orígenes a todos los usuarios
for profile in UserProfile.objects.all():
    profile.puede_usar_todos_origenes = True
    profile.save()
    print(f"✅ {profile.user.username} puede usar todos los orígenes")
```

#### Opción B - Asignar orígenes específicos por usuario:

```python
from usuarios.models import UserProfile
from informes.models import Origen
from django.contrib.auth.models import User

# Ejemplo: Asignar 'Guardia' a usuarios de guardia
guardia_origen = Origen.objects.get(nombre='Guardia')
user = User.objects.get(username='nombre_usuario')
user.profile.origenes.add(guardia_origen)
print(f"✅ Usuario {user.username} ahora puede usar 'Guardia'")
```

#### Opción C - Desde el Admin de Django:

1. Ve a `/admin/auth/user/`
2. Selecciona un usuario
3. En la sección **"Permisos de Orígenes"**:
   - Marca **"¿Puede usar todos los orígenes?"** para acceso total
   - O selecciona orígenes específicos de la lista

### 2. Verificar Orígenes Creados

```python
python manage.py shell
```

```python
from informes.models import Origen

# Ver todos los orígenes
for origen in Origen.objects.all():
    print(f"{origen.orden}. {origen.nombre} (activo: {origen.activo})")
```

Deberías ver:
```
1. Sistemas (activo: True)
2. Guardia (activo: True)
3. RRHH (activo: True)
4. Taller (activo: True)
5. Siniestros (activo: True)
6. Inspectores (activo: True)
```

---

## Funcionalidad Nueva

### En los Formularios:

**Antes:**
- Todos los usuarios veían los mismos 6 orígenes hardcodeados

**Ahora:**
- Cada usuario solo ve los orígenes que tiene permitidos
- Se puede configurar desde el admin de Django
- Fácil agregar nuevos orígenes sin cambiar código

### Administrar Orígenes

Accede al **Django Admin** → **Orígenes**:

- ✏️ Crear nuevos orígenes
- ✅ Activar/desactivar orígenes existentes
- 🔢 Cambiar orden de visualización
- 📝 Editar descripciones

### Métodos Disponibles en UserProfile:

```python
# Obtener orígenes permitidos para un usuario
origenes = user.profile.get_origenes_permitidos()

# Verificar si tiene acceso a un origen específico
tiene_acceso = user.profile.tiene_acceso_origen(origen_id)
```

---

## Solución de Problemas

### ❌ Error: "Informe.origen must be a Origen instance"

**Causa:** Las migraciones no se ejecutaron correctamente o hay datos sin migrar

**Solución:**
1. Verifica que todas las migraciones se hayan aplicado: `python manage.py showmigrations`
2. Si falta alguna, ejecuta: `python manage.py migrate`
3. Si el problema persiste, revisa que no haya migraciones incorrectas aplicadas

### ❌ Los usuarios no ven ningún origen al crear/editar informes

**Causa:** Los usuarios no tienen orígenes asignados en su perfil

**Solución:**
1. Opción rápida: Ejecuta el script de la sección "Opción A" arriba
2. O ve al admin de Django → Usuarios → Edita cada usuario → Asigna orígenes

### ❌ Error al crear nuevo informe: "origen cannot be null"

**Causa:** El formulario requiere que el usuario tenga al menos un origen permitido

**Solución:**
1. Asigna al menos un origen activo al usuario en el admin
2. O marca "¿Puede usar todos los orígenes?" en su perfil

### ❌ Error: "django.db.utils.ProgrammingError: nvarchar a bigint"

**Causa:** Intentaste ejecutar migraciones auto-generadas incorrectas

**Solución:**
1. Elimina las migraciones incorrectas (ver sección arriba)
2. Haz git pull para obtener las migraciones correctas
3. Ejecuta `python manage.py migrate` nuevamente

---

## Reversión (si es necesario)

Si necesitas revertir los cambios:

```bash
# Revertir migraciones de informes (antes de 0014)
python manage.py migrate informes 0013_alter_informe_origen_alter_informe_sucursal

# Revertir migraciones de usuarios (antes de 0002)
python manage.py migrate usuarios 0001_initial

# Luego restaurar el código anterior desde git
git revert <commit_hash>
```

⚠️ **ADVERTENCIA:** La reversión puede causar pérdida de datos en los permisos de origen asignados.

---

## Archivos Modificados

**Modelos:**
- `informes/models.py` - Modelo Origen y cambio en Informe.origen
- `usuarios/models.py` - Campos y métodos de permisos de origen

**Formularios:**
- `informes/forms.py` - Filtrado de orígenes por usuario

**Admin:**
- `informes/admin.py` - Administración del modelo Origen
- `usuarios/admin.py` - Configuración de orígenes en perfil de usuario

**Migraciones:**
- `informes/migrations/0014_*.py` a `0018_*.py` - Migraciones de informes
- `usuarios/migrations/0002_*.py` - Migración de usuarios

---

## Checklist Post-Migración

Después de migrar, verifica:

- [ ] ✅ Todas las migraciones se aplicaron sin errores
- [ ] ✅ Los 6 orígenes existen en `/admin/informes/origen/`
- [ ] ✅ Todos los usuarios tienen al menos un origen asignado
- [ ] ✅ Los informes existentes mantienen sus orígenes correctamente
- [ ] ✅ Puedes crear nuevos informes sin errores
- [ ] ✅ Los formularios solo muestran orígenes permitidos por usuario

---

## Notas Importantes

⚠️ **ANTES DE MIGRAR EN PRODUCCIÓN:**
1. ✅ Haz un backup completo de la base de datos
2. ✅ Prueba la migración en un entorno de desarrollo primero
3. ✅ Verifica que todos los usuarios tengan orígenes asignados después de migrar
4. ✅ Prueba crear y editar informes con diferentes usuarios

✅ **Ventajas del nuevo sistema:**
- Mayor flexibilidad
- Control granular por usuario
- Fácil agregar/eliminar orígenes sin código
- Auditable desde el admin de Django
- Mejor seguridad y control de acceso

---

## Soporte

Si encuentras problemas durante la migración:

1. Revisa esta guía completamente
2. Verifica los logs de Django para errores específicos
3. Comprueba que eliminaste las migraciones incorrectas
4. Asegúrate de tener el código más reciente del repositorio
