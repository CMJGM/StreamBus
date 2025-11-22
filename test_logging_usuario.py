#!/usr/bin/env python
"""
Script de Diagnóstico - Logging con Usuario
Verifica que el middleware de logging capture correctamente el usuario
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'StreamBus.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User, AnonymousUser
from StreamBus.middleware import LoggingMiddleware
from StreamBus.logging_filters import get_current_request, set_current_request, clear_current_request
import logging

def print_header(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def test_thread_local_storage():
    """Test 1: Verificar thread-local storage funciona"""
    print_header("TEST 1: Thread-Local Storage")

    # Crear request falso
    factory = RequestFactory()
    request = factory.get('/')

    # Test sin usuario
    print("1. Sin request en thread-local:")
    result = get_current_request()
    print(f"   get_current_request() = {result}")

    # Guardar request
    print("\n2. Guardando request en thread-local:")
    set_current_request(request)
    result = get_current_request()
    print(f"   set_current_request(request)")
    print(f"   get_current_request() = {result}")
    print(f"   ✓ Request guardado correctamente" if result else "   ✗ ERROR")

    # Limpiar
    print("\n3. Limpiando thread-local:")
    clear_current_request()
    result = get_current_request()
    print(f"   clear_current_request()")
    print(f"   get_current_request() = {result}")
    print(f"   ✓ Thread-local limpiado correctamente" if result is None else "   ✗ ERROR")

def test_user_filter():
    """Test 2: Verificar UserFilter funciona"""
    print_header("TEST 2: UserFilter")

    from StreamBus.logging_filters import UserFilter

    # Crear logger de prueba
    logger = logging.getLogger('test.logging')
    logger.setLevel(logging.DEBUG)

    # Agregar handler con UserFilter
    handler = logging.StreamHandler()
    handler.addFilter(UserFilter())

    # Crear formatter para ver el campo user
    formatter = logging.Formatter('%(asctime)s | %(user)s | %(levelname)s | %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    print("1. Log sin request (debería ser 'system'):")
    clear_current_request()
    logger.info("Test sin request")

    print("\n2. Log con usuario autenticado:")
    factory = RequestFactory()
    request = factory.get('/')

    # Crear usuario de prueba
    try:
        user = User.objects.get(username='admin')
    except User.DoesNotExist:
        # Usar primer usuario disponible
        user = User.objects.first()

    if user:
        request.user = user
        set_current_request(request)
        print(f"   Usuario: {user.username}")
        logger.info(f"Test con usuario autenticado: {user.username}")
    else:
        print("   ⚠ No hay usuarios en la base de datos")

    print("\n3. Log con usuario anónimo:")
    request.user = AnonymousUser()
    set_current_request(request)
    logger.info("Test con usuario anónimo")

    # Limpiar
    clear_current_request()
    logger.removeHandler(handler)

def test_middleware():
    """Test 3: Verificar middleware funciona"""
    print_header("TEST 3: LoggingMiddleware")

    from django.http import HttpResponse

    # Crear middleware
    def simple_view(request):
        # Dentro de la view, el request debe estar disponible
        current_request = get_current_request()
        print(f"   Dentro de la view:")
        print(f"   - get_current_request() = {current_request}")
        print(f"   - request.user = {getattr(current_request, 'user', 'NO USER')}")
        return HttpResponse("OK")

    middleware = LoggingMiddleware(simple_view)

    # Test con usuario autenticado
    print("1. Request con usuario autenticado:")
    factory = RequestFactory()
    request = factory.get('/')

    try:
        user = User.objects.first()
        if user:
            request.user = user
            print(f"   Usuario: {user.username}")
            response = middleware(request)
            print(f"   ✓ Middleware ejecutado correctamente")
        else:
            print("   ⚠ No hay usuarios en la base de datos")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Verificar que se limpió
    print("\n2. Después del middleware:")
    result = get_current_request()
    print(f"   get_current_request() = {result}")
    print(f"   ✓ Thread-local limpiado correctamente" if result is None else "   ✗ ERROR: no se limpió")

def test_real_log_output():
    """Test 4: Verificar salida real de logs"""
    print_header("TEST 4: Salida Real de Logs")

    print("Generando logs de prueba...")
    print("Verifica el archivo debug.log para ver el formato real\n")

    # Log sin usuario (debería ser 'system')
    logger = logging.getLogger('sit.views.test')
    logger.info("Test 1: Log sin request (esperado: system)")

    # Log con usuario
    factory = RequestFactory()
    request = factory.get('/')

    user = User.objects.first()
    if user:
        request.user = user
        set_current_request(request)
        logger.info(f"Test 2: Log con usuario autenticado (esperado: {user.username})")
        clear_current_request()

    # Log con anónimo
    request.user = AnonymousUser()
    set_current_request(request)
    logger.info("Test 3: Log con usuario anónimo (esperado: AnonymousUser)")
    clear_current_request()

    print("✓ Logs generados. Ejecuta este comando para verlos:")
    print("  tail -5 debug.log")

def check_debug_log():
    """Test 5: Revisar debug.log actual"""
    print_header("TEST 5: Revisar debug.log")

    if os.path.exists('debug.log'):
        with open('debug.log', 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        print(f"Archivo debug.log: {len(lines)} líneas\n")

        # Analizar últimas 20 líneas
        print("Últimas 20 líneas:")
        print("-" * 70)
        for line in lines[-20:]:
            print(line.rstrip())
        print("-" * 70)

        # Contar usuarios
        users = {}
        for line in lines:
            if '|' in line:
                parts = line.split('|')
                if len(parts) >= 2:
                    user = parts[1].strip()
                    users[user] = users.get(user, 0) + 1

        print("\nEstadísticas de usuarios en logs:")
        for user, count in sorted(users.items(), key=lambda x: x[1], reverse=True):
            print(f"  {user:<20} : {count} logs")

        if users.get('system', 0) == len(lines):
            print("\n⚠️  PROBLEMA DETECTADO:")
            print("   Todos los logs muestran 'system'")
            print("   El middleware NO está capturando usuarios en requests HTTP")
    else:
        print("⚠️  debug.log no existe")

def main():
    print("\n" + "="*70)
    print("  🔍 DIAGNÓSTICO DE LOGGING CON USUARIO")
    print("="*70)

    try:
        test_thread_local_storage()
        test_user_filter()
        test_middleware()
        test_real_log_output()
        check_debug_log()

        print_header("CONCLUSIÓN")
        print("""
Para verificar si el logging funciona correctamente:

1. Ejecuta el servidor: python manage.py runserver
2. Haz login en la aplicación (ej: admin/tu_password)
3. Navega a alguna página (ej: /sit/ubicaciones-vehiculos/)
4. Verifica los logs:

   tail -20 debug.log

5. Deberías ver líneas como:

   2025-11-22 15:30:45 | admin | INFO | sit.views.gps | ...

   NO:
   2025-11-22 15:30:45 | system | INFO | sit.views.gps | ...

Si TODOS los logs muestran 'system', el problema puede ser:
- El middleware no está siendo llamado
- Hay un problema con el threading
- Los logs que ves son de inicio del servidor (antes de requests HTTP)
        """)

    except Exception as e:
        print(f"\n❌ Error durante diagnóstico: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
