# ⚠️ Resolver Conflicto de Migraciones - ORIGEN

## 🚨 Error Detectado

```
CommandError: Conflicting migrations detected
```

Este error ocurre porque tienes migraciones conflictivas en tu sistema:
- Las migraciones **incorrectas** auto-generadas por Django
- Las migraciones **correctas** que yo creé para la conversión

---

## ✅ Solución Rápida (3 pasos)

### **Paso 1: Limpiar Migraciones Conflictivas**

Elige según tu sistema operativo:

#### 🪟 En Windows (PowerShell o CMD):

```bash
# Opción A: Usar el script batch
limpiar_migraciones_origen.bat

# Opción B: Ejecutar el script Python
python limpiar_migraciones_origen.py
```

#### 🐧 En Linux/Mac:

```bash
# Opción A: Usar el script shell
chmod +x limpiar_migraciones_origen.sh
./limpiar_migraciones_origen.sh

# Opción B: Ejecutar el script Python
python limpiar_migraciones_origen.py
```

---

### **Paso 2: Ejecutar las Migraciones Correctas**

```bash
python manage.py migrate
```

Deberías ver:
```
Applying informes.0014_crear_modelo_origen... OK
Applying informes.0015_poblar_origenes... OK
Applying informes.0016_agregar_campo_origen_nuevo... OK
Applying informes.0017_migrar_datos_origen... OK
Applying informes.0018_finalizar_migracion_origen... OK
Applying usuarios.0002_agregar_permisos_origenes... OK
```

---

### **Paso 3: Asignar Permisos de Origen a Usuarios**

```bash
# Dar acceso a todos los orígenes a todos los usuarios
python manage.py asignar_origenes --todos
```

Cuando te pida confirmación, escribe `si` y presiona Enter.

---

## ✅ Verificación

Para verificar que todo funcionó:

```bash
# 1. Ver estado de migraciones
python manage.py showmigrations informes usuarios

# 2. Verificar orígenes creados
python manage.py asignar_origenes --listar

# 3. Iniciar servidor
python manage.py runserver
```

---

## 🔍 ¿Qué Hacen los Scripts de Limpieza?

Los scripts automáticamente:

1. ✅ Eliminan las migraciones incorrectas:
   - `informes/migrations/0014_origen_alter_informe_origen.py`
   - `usuarios/migrations/0002_userprofile_origenes_and_more.py`

2. ✅ Limpian archivos cache (`__pycache__/*.pyc`)

3. ✅ Verifican que las migraciones correctas existan

4. ✅ Te muestran los próximos pasos

---

## 🛠️ Solución Manual (Si los Scripts No Funcionan)

### En Windows:

```bash
# Eliminar migraciones incorrectas
del informes\migrations\0014_origen_alter_informe_origen.py
del usuarios\migrations\0002_userprofile_origenes_and_more.py

# Limpiar cache
del informes\migrations\__pycache__\0014_*.pyc
del usuarios\migrations\__pycache__\0002_*.pyc

# Luego ejecutar migrate
python manage.py migrate
```

### En Linux/Mac:

```bash
# Eliminar migraciones incorrectas
rm informes/migrations/0014_origen_alter_informe_origen.py
rm usuarios/migrations/0002_userprofile_origenes_and_more.py

# Limpiar cache
rm informes/migrations/__pycache__/0014_*.pyc
rm usuarios/migrations/__pycache__/0002_*.pyc

# Luego ejecutar migrate
python manage.py migrate
```

---

## ❓ Preguntas Frecuentes

### **P: ¿Por qué ocurrió este conflicto?**

R: Ejecutaste `python manage.py makemigrations` antes de hacer `git pull`. Django generó migraciones automáticas que intentan convertir directamente el campo, causando el error de SQL Server.

### **P: ¿Perderé datos?**

R: No. Las migraciones correctas migran todos los datos existentes de forma segura.

### **P: ¿Qué pasa si ya ejecuté las migraciones incorrectas?**

R: Si las migraciones incorrectas ya se aplicaron a la base de datos, necesitarás revertirlas primero:

```bash
# Revertir a la migración anterior
python manage.py migrate informes 0013
python manage.py migrate usuarios 0001

# Luego ejecutar el script de limpieza
python limpiar_migraciones_origen.py

# Y finalmente migrar de nuevo
python manage.py migrate
```

### **P: Los scripts dicen "Faltan migraciones correctas"**

R: Necesitas hacer `git pull` para obtener las migraciones correctas del repositorio:

```bash
git pull origin claude/fix-repo-directory-011enfeVFS7UHE6jCBAnc3db
```

---

## 📞 Soporte

Si después de seguir todos estos pasos aún tienes problemas:

1. ✅ Verifica que eliminaste las migraciones incorrectas
2. ✅ Verifica que hiciste `git pull` para obtener las correctas
3. ✅ Revisa los logs de error completos
4. ✅ Comprueba que tu base de datos SQL Server esté funcionando

---

## 📋 Archivos de Ayuda Incluidos

- `limpiar_migraciones_origen.bat` - Script para Windows
- `limpiar_migraciones_origen.sh` - Script para Linux/Mac
- `limpiar_migraciones_origen.py` - Script Python multiplataforma
- `MIGRACION_ORIGEN.md` - Guía completa de migración
- `RESOLVER_CONFLICTO_MIGRACIONES.md` - Este archivo
