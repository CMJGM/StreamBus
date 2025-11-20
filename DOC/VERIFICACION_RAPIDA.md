# ✅ Checklist de Verificación Rápida - P0.1

## Verificación Post-Implementación

### 1. Archivos Críticos Existen
```bash
# Verificar que existen los archivos necesarios
ls -la .env.example  # ✓ Debe existir
ls -la .env          # ✓ Debe existir (NO subir a git)
ls -la DOC/          # ✓ Carpeta de documentación
ls -la TEST/         # ✓ Carpeta de tests
```

### 2. .env Protegido
```bash
# Verificar que .env está en .gitignore
git check-ignore .env
# Debe retornar: .env

# Verificar que .env NO está trackeado
git status | grep ".env"
# NO debe aparecer (solo .env.example)
```

### 3. No Hay Secrets en Código
```bash
# Buscar passwords hardcoded
grep -r "HPsql2012\|cristian6163\|Buses2024" \
     --include="*.py" \
     --exclude-dir=DOC \
     --exclude-dir=venv
# Debe retornar: (vacío)

# Buscar SECRET_KEY hardcoded
grep -r "django-insecure" --include="*.py" --exclude-dir=DOC
# Debe retornar: (vacío)
```

### 4. Settings.py Correcto
```bash
# Verificar que usa decouple
grep "from decouple import" StreamBus/settings.py
# Debe retornar: from decouple import config, Csv

# Verificar SECRET_KEY
grep "SECRET_KEY = config" StreamBus/settings.py
# Debe retornar: SECRET_KEY = config('DJANGO_SECRET_KEY')
```

### 5. Dependencias Instaladas
```bash
# Verificar python-decouple
pip freeze | grep decouple
# Debe retornar: python-decouple==3.8

# Verificar en requirements.txt
grep decouple requirements.txt
# Debe retornar: python-decouple==3.8
```

### 6. Aplicación Funciona
```bash
# Verificar configuración Django
python manage.py check
# Debe retornar: System check identified no issues (0 silenced).

# Verificar conexión a BD (si está configurada)
python manage.py migrate --check
# No debe dar error de conexión

# Probar servidor
python manage.py runserver
# Debe iniciar sin errores
```

### 7. Tests Organizados
```bash
# Verificar estructura TEST
ls TEST/*/tests.py
# Debe mostrar 9 archivos

# Ejecutar tests (si existen)
python manage.py test TEST --keepdb
# Debe ejecutar sin errores de importación
```

### 8. Documentación Completa
```bash
# Verificar docs
ls DOC/*.md
# Debe mostrar:
# - CONFIGURACION_ENV.md
# - RESUMEN_CAMBIOS_P0.1.md
# - VERIFICACION_RAPIDA.md (este archivo)
# - README.md
# - MIGRACION_ORIGEN.md
# - RESOLVER_CONFLICTO_MIGRACIONES.md
```

---

## Comandos de Verificación Todo-en-Uno

```bash
#!/bin/bash
# Script de verificación completa

echo "=== VERIFICACIÓN P0.1 ==="

echo -n "✓ .env existe: "
[ -f .env ] && echo "SÍ" || echo "NO ❌"

echo -n "✓ .env protegido: "
git check-ignore .env > /dev/null && echo "SÍ" || echo "NO ❌"

echo -n "✓ python-decouple instalado: "
pip freeze | grep -q decouple && echo "SÍ" || echo "NO ❌"

echo -n "✓ Settings usa config(): "
grep -q "from decouple import" StreamBus/settings.py && echo "SÍ" || echo "NO ❌"

echo -n "✓ No hay secrets hardcoded: "
! grep -rq "HPsql2012\|cristian6163\|Buses2024\|django-insecure" \
    --include="*.py" --exclude-dir=DOC --exclude-dir=venv . \
    && echo "SÍ" || echo "NO ❌"

echo -n "✓ Django check pasa: "
python manage.py check --quiet && echo "SÍ" || echo "NO ❌"

echo -n "✓ Carpeta DOC existe: "
[ -d DOC ] && echo "SÍ" || echo "NO ❌"

echo -n "✓ Carpeta TEST existe: "
[ -d TEST ] && echo "SÍ" || echo "NO ❌"

echo ""
echo "=== VERIFICACIÓN COMPLETADA ==="
```

Guardar como `verificar.sh` y ejecutar:
```bash
chmod +x verificar.sh
./verificar.sh
```

---

## Troubleshooting Rápido

### Error: "DJANGO_SECRET_KEY not found"
```bash
# Solución:
cp .env.example .env
nano .env  # Editar con valores reales
```

### Error: "ModuleNotFoundError: No module named 'decouple'"
```bash
# Solución:
pip install python-decouple
```

### Error: "Database connection failed"
```bash
# Verificar .env tiene credenciales correctas:
grep DB_ .env

# Probar conexión directa a BD
# (usar tu cliente SQL preferido)
```

### Servidor no inicia
```bash
# Verificar logs:
tail -f debug.log

# Verificar puertos:
netstat -tulpn | grep 8000

# Verificar permisos:
ls -la .env
# Debe ser legible
```

---

## Próximos Pasos

Una vez verificado todo:

1. ✅ Crear PR si todo funciona
2. ⏭️ Continuar con P0.2 (DEBUG=False en producción)
3. ⏭️ Implementar P0.3 (Autenticación endpoints)
4. ⏭️ Implementar P0.4 (Validación MIME)

Ver: `DOC/RESUMEN_CAMBIOS_P0.1.md` para roadmap completo.
