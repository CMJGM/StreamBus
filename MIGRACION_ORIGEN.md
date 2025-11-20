# Guía de Migración: Sistema de Permisos de Origen

## Resumen de Cambios

Se implementó un **sistema de permisos por usuario para el campo Origen** en los informes, reemplazando el sistema hardcodeado anterior.

### Cambios Principales:

1. **Nuevo Modelo `Origen`**: Gestiona los diferentes orígenes de informes de forma dinámica
2. **Permisos por Usuario**: Cada usuario puede tener asignados orígenes específicos
3. **Filtrado Automático**: Los formularios solo muestran orígenes permitidos para cada usuario

---

## Pasos para Migrar la Base de Datos

### 1. Crear Migraciones Iniciales

El cambio de `CharField` a `ForeignKey` requiere múltiples pasos de migración:

```bash
# Paso 1: Crear migración para el nuevo modelo Origen
python manage.py makemigrations informes

# Paso 2: Crear migración para UserProfile (campo origenes)
python manage.py makemigrations usuarios
```

### 2. Crear Migración de Datos Personalizada

Necesitas crear una migración de datos que:
1. Cree los registros en el modelo `Origen` con los valores antiguos
2. Migre las referencias del campo antiguo al nuevo

```bash
# Crear migración de datos vacía
python manage.py makemigrations informes --empty --name migrar_datos_origen
```

Edita el archivo de migración creado y agrega este código:

```python
from django.db import migrations

def migrar_origenes(apps, schema_editor):
    """
    Migra los datos del campo origen antiguo (CharField)
    al nuevo modelo Origen (ForeignKey)
    """
    Origen = apps.get_model('informes', 'Origen')

    # Crear los orígenes basados en los valores hardcodeados antiguos
    origenes_datos = [
        {'nombre': 'Sistemas', 'orden': 1, 'activo': True},
        {'nombre': 'Guardia', 'orden': 2, 'activo': True},
        {'nombre': 'RRHH', 'orden': 3, 'activo': True},
        {'nombre': 'Taller', 'orden': 4, 'activo': True},
        {'nombre': 'Siniestros', 'orden': 5, 'activo': True},
        {'nombre': 'Inspectores', 'orden': 6, 'activo': True},
    ]

    for datos in origenes_datos:
        Origen.objects.get_or_create(
            nombre=datos['nombre'],
            defaults={
                'orden': datos['orden'],
                'activo': datos['activo']
            }
        )

def revertir_migracion(apps, schema_editor):
    """
    Función para revertir la migración si es necesario
    """
    Origen = apps.get_model('informes', 'Origen')
    # Eliminar todos los orígenes creados
    Origen.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('informes', 'XXXX_previous_migration'),  # Reemplazar con el nombre de la migración anterior
    ]

    operations = [
        migrations.RunPython(migrar_origenes, revertir_migracion),
    ]
```

### 3. Ejecutar Migraciones

```bash
# Aplicar todas las migraciones
python manage.py migrate
```

---

## Configuración Post-Migración

### 1. Asignar Orígenes a Usuarios

Accede al **Django Admin** → **Usuarios** → selecciona un usuario:

1. En la sección **"Permisos de Orígenes"**:
   - Selecciona los orígenes permitidos para el usuario
   - O marca **"¿Puede usar todos los orígenes?"** para acceso total

### 2. Administrar Orígenes

Accede al **Django Admin** → **Orígenes**:

- Crear nuevos orígenes
- Activar/desactivar orígenes existentes
- Cambiar orden de visualización
- Editar descripciones

---

## Funcionalidad Nueva

### En los Formularios:

**Antes:**
- Todos los usuarios veían los mismos 6 orígenes hardcodeados

**Ahora:**
- Cada usuario solo ve los orígenes que tiene permitidos
- Se puede configurar desde el admin de Django
- Fácil agregar nuevos orígenes sin cambiar código

### Métodos Disponibles en UserProfile:

```python
# Obtener orígenes permitidos para un usuario
origenes = user.profile.get_origenes_permitidos()

# Verificar si tiene acceso a un origen específico
tiene_acceso = user.profile.tiene_acceso_origen(origen_id)
```

---

## Solución de Problemas

### Error: "Informe.origen must be a Origen instance"

**Causa:** Los informes existentes todavía tienen valores de texto en el campo origen

**Solución:** Asegúrate de ejecutar la migración de datos que convierte los valores antiguos a ForeignKeys

### Los usuarios no ven ningún origen

**Causa:** No tienen orígenes asignados en su perfil

**Solución:**
1. Ve al admin de Django → Usuarios
2. Edita el usuario
3. En "Permisos de Orígenes", asigna orígenes o marca "¿Puede usar todos los orígenes?"

### Error al crear nuevo informe

**Causa:** El formulario requiere que el usuario tenga al menos un origen permitido

**Solución:** Asigna al menos un origen activo al usuario en el admin

---

## Reversión (si es necesario)

Si necesitas revertir los cambios:

```bash
# Revertir migraciones
python manage.py migrate informes XXXX  # número de migración anterior
python manage.py migrate usuarios YYYY  # número de migración anterior

# Luego restaurar el código anterior desde git
git revert <commit_hash>
```

---

## Archivos Modificados

- `informes/models.py` - Modelo Origen y cambio en Informe.origen
- `informes/forms.py` - Filtrado de orígenes por usuario
- `informes/admin.py` - Administración del modelo Origen
- `usuarios/models.py` - Campos y métodos de permisos de origen
- `usuarios/admin.py` - Configuración de orígenes en perfil de usuario

---

## Notas Importantes

⚠️ **ANTES DE MIGRAR EN PRODUCCIÓN:**
1. Haz un backup completo de la base de datos
2. Prueba la migración en un entorno de desarrollo primero
3. Verifica que todos los usuarios tengan orígenes asignados después de migrar

✅ **Ventajas del nuevo sistema:**
- Mayor flexibilidad
- Control granular por usuario
- Fácil agregar/eliminar orígenes sin código
- Auditable desde el admin de Django
