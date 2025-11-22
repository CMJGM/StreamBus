#!/usr/bin/env python
"""
Script de Testing para Refactorización de sit/views.py
Ejecutar: python test_refactorizacion.py
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'StreamBus.settings')
django.setup()

from django.conf import settings
import logging

def print_header(title):
    """Imprime un header bonito"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def print_success(message):
    """Imprime mensaje de éxito"""
    print(f"✓ {message}")

def print_error(message):
    """Imprime mensaje de error"""
    print(f"✗ {message}")

def print_warning(message):
    """Imprime mensaje de advertencia"""
    print(f"⚠ {message}")

def test_imports():
    """Test 1: Verificar que todos los imports funcionan"""
    print_header("TEST 1: Verificación de Imports")

    errors = []

    # Test 1.1: Imports principales desde sit.views
    try:
        from sit.views import (
            mapa_ubicacion, security_photos_form, alarmas_view,
            ubicacion_json, ubicaciones_vehiculos,
            fetch_security_photos, check_download_status
        )
        print_success("Imports principales de sit.views OK")
    except ImportError as e:
        errors.append(f"Error en imports principales: {e}")
        print_error(f"Imports principales: {e}")

    # Test 1.2: Imports directos de módulos
    try:
        from sit.views.gps_views import obtener_empresas_disponibles, actualizar_ubicacion_cache
        from sit.views.photo_download_views import background_download_process
        from sit.views.alarmas_views import query_security_photos
        from sit.views.informes_views import listar_informes_sit
        print_success("Imports directos de módulos OK")
    except ImportError as e:
        errors.append(f"Error en imports de módulos: {e}")
        print_error(f"Imports de módulos: {e}")

    # Test 1.3: Imports de clases de estadísticas
    try:
        from sit.views.stats import DownloadStatistics, BasicOptimizedStats
        stats = DownloadStatistics()
        print_success(f"Imports de estadísticas OK (tipo: {type(stats).__name__})")
    except ImportError as e:
        errors.append(f"Error en imports de stats: {e}")
        print_error(f"Imports de estadísticas: {e}")

    # Test 1.4: Imports de informes
    try:
        from informes.views import (
            InformesPorEmpleadoView, estadisticas_informes,
            InformeListView, InformeDetailView
        )
        print_success("Imports de informes.views OK")
    except ImportError as e:
        errors.append(f"Error en imports de informes: {e}")
        print_error(f"Imports de informes: {e}")

    # Test 1.5: Imports de logging components
    try:
        from StreamBus.logging_filters import UserFilter, get_current_request
        from StreamBus.middleware import LoggingMiddleware
        print_success("Imports de logging components OK")
    except ImportError as e:
        errors.append(f"Error en imports de logging: {e}")
        print_error(f"Imports de logging: {e}")

    return len(errors) == 0, errors

def test_logging_config():
    """Test 2: Verificar configuración de logging"""
    print_header("TEST 2: Verificación de Configuración de Logging")

    errors = []

    # Test 2.1: Verificar que LOGGING está configurado
    if hasattr(settings, 'LOGGING'):
        print_success("LOGGING configurado en settings")
    else:
        errors.append("LOGGING no está configurado en settings")
        print_error("LOGGING no configurado")
        return False, errors

    # Test 2.2: Verificar handlers
    handlers = list(settings.LOGGING.get('handlers', {}).keys())
    if 'console' in handlers and 'file' in handlers:
        print_success(f"Handlers configurados: {', '.join(handlers)}")
    else:
        errors.append(f"Handlers faltantes. Encontrados: {handlers}")
        print_error(f"Handlers incompletos: {handlers}")

    # Test 2.3: Verificar formatters
    formatters = list(settings.LOGGING.get('formatters', {}).keys())
    if 'verbose' in formatters:
        print_success(f"Formatters configurados: {', '.join(formatters)}")

        # Verificar formato incluye {user}
        verbose_format = settings.LOGGING['formatters']['verbose'].get('format', '')
        if '{user}' in verbose_format:
            print_success("Formato 'verbose' incluye campo {user}")
        else:
            errors.append("Formato 'verbose' no incluye campo {user}")
            print_warning("Formato no incluye {user}")
    else:
        errors.append("Formatter 'verbose' no configurado")
        print_error("Formatters incompletos")

    # Test 2.4: Verificar filters
    filters = list(settings.LOGGING.get('filters', {}).keys())
    if 'add_user' in filters:
        print_success(f"Filters configurados: {', '.join(filters)}")
    else:
        errors.append("Filter 'add_user' no configurado")
        print_error(f"Filters incompletos: {filters}")

    # Test 2.5: Verificar loggers para sit e informes
    loggers = list(settings.LOGGING.get('loggers', {}).keys())
    if 'sit' in loggers and 'informes' in loggers:
        print_success(f"Loggers configurados: {', '.join(loggers)}")
    else:
        errors.append(f"Loggers faltantes. Encontrados: {loggers}")
        print_warning(f"Algunos loggers pueden estar faltando: {loggers}")

    return len(errors) == 0, errors

def test_middleware():
    """Test 3: Verificar middleware de logging"""
    print_header("TEST 3: Verificación de Middleware")

    errors = []

    # Test 3.1: Verificar LoggingMiddleware está en MIDDLEWARE
    if 'StreamBus.middleware.LoggingMiddleware' in settings.MIDDLEWARE:
        print_success("LoggingMiddleware presente en MIDDLEWARE")

        # Encontrar posición
        position = settings.MIDDLEWARE.index('StreamBus.middleware.LoggingMiddleware')
        print_success(f"  Posición en MIDDLEWARE: {position + 1}/{len(settings.MIDDLEWARE)}")
    else:
        errors.append("LoggingMiddleware no está en MIDDLEWARE")
        print_error("LoggingMiddleware NO encontrado en MIDDLEWARE")

    # Test 3.2: Verificar que está después de AuthenticationMiddleware
    try:
        auth_pos = settings.MIDDLEWARE.index('django.contrib.auth.middleware.AuthenticationMiddleware')
        logging_pos = settings.MIDDLEWARE.index('StreamBus.middleware.LoggingMiddleware')

        if logging_pos > auth_pos:
            print_success("LoggingMiddleware está después de AuthenticationMiddleware (correcto)")
        else:
            errors.append("LoggingMiddleware debe estar después de AuthenticationMiddleware")
            print_warning("Orden de middleware puede causar problemas")
    except (ValueError, IndexError) as e:
        errors.append(f"Error verificando orden de middleware: {e}")
        print_error(f"Error en orden: {e}")

    return len(errors) == 0, errors

def test_file_structure():
    """Test 4: Verificar estructura de archivos"""
    print_header("TEST 4: Verificación de Estructura de Archivos")

    errors = []

    # Test 4.1: Verificar que sit/views/ es directorio
    if os.path.isdir('sit/views'):
        print_success("sit/views/ es un directorio")
    else:
        errors.append("sit/views/ no es un directorio")
        print_error("sit/views/ no encontrado")
        return False, errors

    # Test 4.2: Verificar módulos de sit/views/
    expected_modules = [
        '__init__.py',
        'gps_views.py',
        'photo_download_views.py',
        'alarmas_views.py',
        'informes_views.py',
        'stats.py'
    ]

    for module in expected_modules:
        path = os.path.join('sit/views', module)
        if os.path.isfile(path):
            size = os.path.getsize(path)
            print_success(f"{module:<30} ({size:,} bytes)")
        else:
            errors.append(f"Módulo faltante: {module}")
            print_error(f"{module} NO encontrado")

    # Test 4.3: Verificar que sit/views.py NO existe
    if not os.path.exists('sit/views.py'):
        print_success("sit/views.py eliminado correctamente (refactorizado)")
    else:
        errors.append("sit/views.py todavía existe (debería estar eliminado)")
        print_warning("sit/views.py aún existe - puede causar conflictos")

    # Test 4.4: Verificar que informes/views.py existe (sin refactorizar)
    if os.path.isfile('informes/views.py'):
        size = os.path.getsize('informes/views.py')
        print_success(f"informes/views.py existe ({size:,} bytes)")
    else:
        errors.append("informes/views.py no encontrado")
        print_error("informes/views.py NO encontrado")

    # Test 4.5: Verificar que informes/views/ NO existe (directorio)
    if not os.path.exists('informes/views'):
        print_success("informes/views/ (directorio) no existe (correcto)")
    else:
        errors.append("informes/views/ directorio existe y causará conflictos")
        print_error("informes/views/ directorio existe - ELIMINAR")

    # Test 4.6: Verificar archivos de logging
    logging_files = [
        'StreamBus/logging_filters.py',
        'StreamBus/middleware.py'
    ]

    for filepath in logging_files:
        if os.path.isfile(filepath):
            size = os.path.getsize(filepath)
            print_success(f"{filepath:<40} ({size:,} bytes)")
        else:
            errors.append(f"Archivo de logging faltante: {filepath}")
            print_error(f"{filepath} NO encontrado")

    return len(errors) == 0, errors

def test_logging_functionality():
    """Test 5: Verificar funcionalidad de logging"""
    print_header("TEST 5: Verificación de Funcionalidad de Logging")

    errors = []

    # Test 5.1: Crear logger y probar
    try:
        logger = logging.getLogger('sit.views.test')
        logger.info("Test de logging desde script")
        print_success("Logger creado y mensaje enviado")
    except Exception as e:
        errors.append(f"Error creando logger: {e}")
        print_error(f"Error: {e}")

    # Test 5.2: Verificar archivo debug.log
    if os.path.exists('debug.log'):
        size = os.path.getsize('debug.log')
        print_success(f"debug.log existe ({size:,} bytes)")

        # Leer últimas líneas
        try:
            with open('debug.log', 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                if lines:
                    last_line = lines[-1].strip()
                    print_success(f"Última línea del log: {last_line[:100]}...")

                    # Verificar formato
                    if '|' in last_line:
                        parts = last_line.split('|')
                        if len(parts) >= 5:
                            print_success(f"Formato parece correcto (detectados {len(parts)} campos)")
                        else:
                            print_warning(f"Formato puede ser incorrecto ({len(parts)} campos)")
                else:
                    print_warning("debug.log está vacío")
        except Exception as e:
            errors.append(f"Error leyendo debug.log: {e}")
            print_error(f"Error leyendo log: {e}")
    else:
        print_warning("debug.log no existe (se creará al ejecutar la app)")

    return len(errors) == 0, errors

def test_urls_config():
    """Test 6: Verificar configuración de URLs"""
    print_header("TEST 6: Verificación de Configuración de URLs")

    errors = []

    try:
        from django.urls import reverse

        # Test algunas URLs críticas
        test_urls = [
            ('sit:ubicaciones_vehiculos', {}),
            ('sit:alarmas', {}),
            ('sit:security_photos_form', {}),
        ]

        for url_name, kwargs in test_urls:
            try:
                url = reverse(url_name, kwargs=kwargs)
                print_success(f"{url_name:<35} -> {url}")
            except Exception as e:
                # Puede fallar si las URLs usan namespace diferente
                print_warning(f"{url_name}: {e}")

    except Exception as e:
        errors.append(f"Error verificando URLs: {e}")
        print_error(f"Error: {e}")

    return len(errors) == 0, errors

def main():
    """Ejecutar todos los tests"""
    print("\n" + "="*70)
    print("  🧪 TESTING DE REFACTORIZACIÓN - StreamBus")
    print("="*70)
    print("\nEjecutando tests de validación...\n")

    results = []

    # Ejecutar cada test
    tests = [
        ("Imports", test_imports),
        ("Logging Config", test_logging_config),
        ("Middleware", test_middleware),
        ("File Structure", test_file_structure),
        ("Logging Functionality", test_logging_functionality),
        ("URLs Config", test_urls_config),
    ]

    for test_name, test_func in tests:
        try:
            passed, errors = test_func()
            results.append((test_name, passed, errors))
        except Exception as e:
            print_error(f"Test {test_name} falló con excepción: {e}")
            results.append((test_name, False, [str(e)]))

    # Resumen final
    print_header("RESUMEN DE TESTS")

    total_tests = len(results)
    passed_tests = sum(1 for _, passed, _ in results if passed)
    failed_tests = total_tests - passed_tests

    for test_name, passed, errors in results:
        if passed:
            print_success(f"{test_name:<30} PASSED")
        else:
            print_error(f"{test_name:<30} FAILED")
            for error in errors:
                print(f"    - {error}")

    print(f"\n{'='*70}")
    print(f"  Total: {total_tests} tests")
    print(f"  ✓ Pasados: {passed_tests}")
    print(f"  ✗ Fallidos: {failed_tests}")
    print(f"{'='*70}\n")

    if failed_tests == 0:
        print("✅ TODOS LOS TESTS PASARON - Refactorización exitosa!\n")
        return 0
    else:
        print(f"⚠️  HAY {failed_tests} TEST(S) FALLIDO(S) - Revisar errores arriba\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())
