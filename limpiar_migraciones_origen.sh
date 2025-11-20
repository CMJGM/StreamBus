#!/bin/bash
# Script para limpiar migraciones conflictivas en Linux/Mac

echo "========================================================================"
echo "  🧹 LIMPIEZA DE MIGRACIONES CONFLICTIVAS - ORIGEN"
echo "========================================================================"
echo ""

echo "📋 Paso 1: Eliminando migraciones auto-generadas incorrectas..."
echo ""

# Eliminar migraciones incorrectas
if [ -f "informes/migrations/0014_origen_alter_informe_origen.py" ]; then
    rm "informes/migrations/0014_origen_alter_informe_origen.py"
    echo "   ✅ Eliminado: 0014_origen_alter_informe_origen.py"
else
    echo "   ℹ️  No existe: 0014_origen_alter_informe_origen.py"
fi

if [ -f "usuarios/migrations/0002_userprofile_origenes_and_more.py" ]; then
    rm "usuarios/migrations/0002_userprofile_origenes_and_more.py"
    echo "   ✅ Eliminado: 0002_userprofile_origenes_and_more.py"
else
    echo "   ℹ️  No existe: 0002_userprofile_origenes_and_more.py"
fi

echo ""
echo "📋 Paso 2: Limpiando archivos cache..."
echo ""

# Limpiar cache de informes
if ls informes/migrations/__pycache__/0014_*.pyc 1> /dev/null 2>&1; then
    rm informes/migrations/__pycache__/0014_*.pyc
    echo "   ✅ Cache de informes limpiado"
fi

# Limpiar cache de usuarios
if ls usuarios/migrations/__pycache__/0002_*.pyc 1> /dev/null 2>&1; then
    rm usuarios/migrations/__pycache__/0002_*.pyc
    echo "   ✅ Cache de usuarios limpiado"
fi

echo ""
echo "📋 Paso 3: Verificando migraciones correctas..."
echo ""

ALL_OK=1

# Verificar que las migraciones correctas existan
if [ -f "informes/migrations/0014_crear_modelo_origen.py" ]; then
    echo "   ✅ 0014_crear_modelo_origen.py"
else
    echo "   ❌ No existe: 0014_crear_modelo_origen.py"
    ALL_OK=0
fi

if [ -f "informes/migrations/0015_poblar_origenes.py" ]; then
    echo "   ✅ 0015_poblar_origenes.py"
else
    echo "   ❌ No existe: 0015_poblar_origenes.py"
    ALL_OK=0
fi

if [ -f "informes/migrations/0016_agregar_campo_origen_nuevo.py" ]; then
    echo "   ✅ 0016_agregar_campo_origen_nuevo.py"
else
    echo "   ❌ No existe: 0016_agregar_campo_origen_nuevo.py"
    ALL_OK=0
fi

if [ -f "informes/migrations/0017_migrar_datos_origen.py" ]; then
    echo "   ✅ 0017_migrar_datos_origen.py"
else
    echo "   ❌ No existe: 0017_migrar_datos_origen.py"
    ALL_OK=0
fi

if [ -f "informes/migrations/0018_finalizar_migracion_origen.py" ]; then
    echo "   ✅ 0018_finalizar_migracion_origen.py"
else
    echo "   ❌ No existe: 0018_finalizar_migracion_origen.py"
    ALL_OK=0
fi

if [ -f "usuarios/migrations/0002_agregar_permisos_origenes.py" ]; then
    echo "   ✅ 0002_agregar_permisos_origenes.py"
else
    echo "   ❌ No existe: 0002_agregar_permisos_origenes.py"
    ALL_OK=0
fi

echo ""
echo "========================================================================"

if [ $ALL_OK -eq 1 ]; then
    echo ""
    echo "✅ LIMPIEZA COMPLETADA EXITOSAMENTE"
    echo ""
    echo "📝 PRÓXIMOS PASOS:"
    echo "   1. python manage.py migrate"
    echo "   2. python manage.py asignar_origenes --todos"
    echo "   3. python manage.py runserver"
    echo ""
else
    echo ""
    echo "⚠️  ADVERTENCIA: Faltan migraciones correctas"
    echo ""
    echo "📝 SOLUCIÓN:"
    echo "   1. Ejecutar: git pull"
    echo "   2. Ejecutar este script nuevamente"
    echo ""
fi

echo "========================================================================"
echo ""
