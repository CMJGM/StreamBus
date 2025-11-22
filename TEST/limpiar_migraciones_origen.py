#!/usr/bin/env python
"""
Script para limpiar migraciones conflictivas de Origen
y preparar el sistema para las migraciones correctas.

Uso:
    python limpiar_migraciones_origen.py
"""

import os
import sys
import glob

def eliminar_archivo(ruta):
    """Elimina un archivo si existe"""
    if os.path.exists(ruta):
        try:
            os.remove(ruta)
            print(f"   ✅ Eliminado: {ruta}")
            return True
        except Exception as e:
            print(f"   ❌ Error al eliminar {ruta}: {e}")
            return False
    else:
        print(f"   ⚠️  No existe: {ruta}")
        return False

def limpiar_pycache(directorio):
    """Elimina archivos .pyc en __pycache__"""
    pycache_dir = os.path.join(directorio, '__pycache__')
    if os.path.exists(pycache_dir):
        archivos_eliminados = 0
        # Buscar archivos con patron 0014_*.pyc y 0002_*.pyc
        for patron in ['0014_*.pyc', '0002_*.pyc']:
            for archivo in glob.glob(os.path.join(pycache_dir, patron)):
                try:
                    os.remove(archivo)
                    archivos_eliminados += 1
                    print(f"   ✅ Eliminado cache: {os.path.basename(archivo)}")
                except Exception as e:
                    print(f"   ❌ Error: {e}")

        if archivos_eliminados == 0:
            print(f"   ℹ️  No hay archivos de cache para eliminar en {pycache_dir}")
        return archivos_eliminados > 0
    else:
        print(f"   ℹ️  No existe directorio __pycache__ en {directorio}")
        return False

def main():
    print("\n" + "="*70)
    print("  🧹 LIMPIEZA DE MIGRACIONES CONFLICTIVAS - ORIGEN")
    print("="*70)

    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Migraciones incorrectas a eliminar
    migraciones_incorrectas = [
        os.path.join(base_dir, 'informes', 'migrations', '0014_origen_alter_informe_origen.py'),
        os.path.join(base_dir, 'usuarios', 'migrations', '0002_userprofile_origenes_and_more.py'),
    ]

    # Directorios de migrations
    directorios_migrations = [
        os.path.join(base_dir, 'informes', 'migrations'),
        os.path.join(base_dir, 'usuarios', 'migrations'),
    ]

    print("\n📋 PASO 1: Eliminar migraciones auto-generadas incorrectas")
    print("-" * 70)

    eliminados = 0
    for migracion in migraciones_incorrectas:
        if eliminar_archivo(migracion):
            eliminados += 1

    print(f"\n   Total eliminado: {eliminados} archivo(s)")

    print("\n📋 PASO 2: Limpiar archivos __pycache__")
    print("-" * 70)

    for directorio in directorios_migrations:
        print(f"\n   Limpiando: {directorio}")
        limpiar_pycache(directorio)

    print("\n📋 PASO 3: Verificar migraciones correctas")
    print("-" * 70)

    # Verificar que las migraciones correctas existan
    migraciones_correctas = [
        ('informes/migrations/0014_crear_modelo_origen.py', 'Crea modelo Origen'),
        ('informes/migrations/0015_poblar_origenes.py', 'Pobla 6 orígenes'),
        ('informes/migrations/0016_agregar_campo_origen_nuevo.py', 'Agrega campo temporal'),
        ('informes/migrations/0017_migrar_datos_origen.py', 'Migra datos'),
        ('informes/migrations/0018_finalizar_migracion_origen.py', 'Finaliza migración'),
        ('usuarios/migrations/0002_agregar_permisos_origenes.py', 'Agrega permisos origen'),
    ]

    todas_existen = True
    for ruta, descripcion in migraciones_correctas:
        ruta_completa = os.path.join(base_dir, ruta)
        if os.path.exists(ruta_completa):
            print(f"   ✅ {os.path.basename(ruta):50} {descripcion}")
        else:
            print(f"   ❌ {os.path.basename(ruta):50} NO ENCONTRADO")
            todas_existen = False

    print("\n" + "="*70)

    if todas_existen and eliminados > 0:
        print("\n✅ LIMPIEZA COMPLETADA EXITOSAMENTE")
        print("\n📝 PRÓXIMOS PASOS:")
        print("   1. Ejecutar: python manage.py migrate")
        print("   2. Ejecutar: python manage.py asignar_origenes --todos")
        print("   3. Iniciar servidor: python manage.py runserver")
    elif todas_existen and eliminados == 0:
        print("\n✅ NO HAY MIGRACIONES CONFLICTIVAS")
        print("   Las migraciones incorrectas ya fueron eliminadas.")
        print("\n📝 PRÓXIMO PASO:")
        print("   Ejecutar: python manage.py migrate")
    elif not todas_existen:
        print("\n⚠️  ADVERTENCIA: Faltan migraciones correctas")
        print("\n📝 SOLUCIÓN:")
        print("   1. Ejecutar: git pull")
        print("   2. Ejecutar este script nuevamente")

    print("\n" + "="*70 + "\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Operación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
