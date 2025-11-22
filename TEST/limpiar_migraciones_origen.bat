@echo off
REM Script para limpiar migraciones conflictivas en Windows

echo ========================================================================
echo   LIMPIEZA DE MIGRACIONES CONFLICTIVAS - ORIGEN
echo ========================================================================
echo.

echo Paso 1: Eliminando migraciones auto-generadas incorrectas...
echo.

if exist "informes\migrations\0014_origen_alter_informe_origen.py" (
    del "informes\migrations\0014_origen_alter_informe_origen.py"
    echo    [OK] Eliminado: 0014_origen_alter_informe_origen.py
) else (
    echo    [INFO] No existe: 0014_origen_alter_informe_origen.py
)

if exist "usuarios\migrations\0002_userprofile_origenes_and_more.py" (
    del "usuarios\migrations\0002_userprofile_origenes_and_more.py"
    echo    [OK] Eliminado: 0002_userprofile_origenes_and_more.py
) else (
    echo    [INFO] No existe: 0002_userprofile_origenes_and_more.py
)

echo.
echo Paso 2: Limpiando archivos cache...
echo.

if exist "informes\migrations\__pycache__\0014_*.pyc" (
    del "informes\migrations\__pycache__\0014_*.pyc" 2>nul
    echo    [OK] Cache de informes limpiado
)

if exist "usuarios\migrations\__pycache__\0002_*.pyc" (
    del "usuarios\migrations\__pycache__\0002_*.pyc" 2>nul
    echo    [OK] Cache de usuarios limpiado
)

echo.
echo Paso 3: Verificando migraciones correctas...
echo.

set ALL_OK=1

if exist "informes\migrations\0014_crear_modelo_origen.py" (
    echo    [OK] 0014_crear_modelo_origen.py
) else (
    echo    [ERROR] No existe: 0014_crear_modelo_origen.py
    set ALL_OK=0
)

if exist "informes\migrations\0015_poblar_origenes.py" (
    echo    [OK] 0015_poblar_origenes.py
) else (
    echo    [ERROR] No existe: 0015_poblar_origenes.py
    set ALL_OK=0
)

if exist "informes\migrations\0016_agregar_campo_origen_nuevo.py" (
    echo    [OK] 0016_agregar_campo_origen_nuevo.py
) else (
    echo    [ERROR] No existe: 0016_agregar_campo_origen_nuevo.py
    set ALL_OK=0
)

if exist "informes\migrations\0017_migrar_datos_origen.py" (
    echo    [OK] 0017_migrar_datos_origen.py
) else (
    echo    [ERROR] No existe: 0017_migrar_datos_origen.py
    set ALL_OK=0
)

if exist "informes\migrations\0018_finalizar_migracion_origen.py" (
    echo    [OK] 0018_finalizar_migracion_origen.py
) else (
    echo    [ERROR] No existe: 0018_finalizar_migracion_origen.py
    set ALL_OK=0
)

if exist "usuarios\migrations\0002_agregar_permisos_origenes.py" (
    echo    [OK] 0002_agregar_permisos_origenes.py
) else (
    echo    [ERROR] No existe: 0002_agregar_permisos_origenes.py
    set ALL_OK=0
)

echo.
echo ========================================================================

if %ALL_OK%==1 (
    echo.
    echo [EXITO] LIMPIEZA COMPLETADA
    echo.
    echo PROXIMOS PASOS:
    echo    1. python manage.py migrate
    echo    2. python manage.py asignar_origenes --todos
    echo    3. python manage.py runserver
    echo.
) else (
    echo.
    echo [ADVERTENCIA] Faltan migraciones correctas
    echo.
    echo SOLUCION:
    echo    1. Ejecutar: git pull
    echo    2. Ejecutar este script nuevamente
    echo.
)

echo ========================================================================
echo.
pause
