#!/usr/bin/env python
"""
Script de Diagnóstico - Problema de Login
Verifica configuración de autenticación y sesiones
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'StreamBus.settings')
django.setup()

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.contrib.auth import authenticate
import logging

def print_header(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def print_success(message):
    print(f"✓ {message}")

def print_error(message):
    print(f"✗ {message}")

def print_warning(message):
    print(f"⚠ {message}")

def test_middleware_configuration():
    """Test 1: Verificar configuración de middleware"""
    print_header("TEST 1: Configuración de Middleware")

    print("Middleware activos:")
    for i, mw in enumerate(settings.MIDDLEWARE, 1):
        print(f"{i:2}. {mw}")

    # Verificar middleware críticos para login
    critical_middleware = [
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
    ]

    print("\nMiddleware críticos para login:")
    for mw in critical_middleware:
        if mw in settings.MIDDLEWARE:
            print_success(f"{mw}")
        else:
            print_error(f"{mw} FALTANTE")

    # Verificar orden
    try:
        session_pos = settings.MIDDLEWARE.index('django.contrib.sessions.middleware.SessionMiddleware')
        auth_pos = settings.MIDDLEWARE.index('django.contrib.auth.middleware.AuthenticationMiddleware')
        logging_pos = settings.MIDDLEWARE.index('StreamBus.middleware.LoggingMiddleware')

        print(f"\nPosiciones:")
        print(f"  SessionMiddleware: {session_pos + 1}")
        print(f"  AuthenticationMiddleware: {auth_pos + 1}")
        print(f"  LoggingMiddleware: {logging_pos + 1}")

        if session_pos < auth_pos < logging_pos:
            print_success("Orden correcto: Session → Auth → Logging")
        else:
            print_warning("Orden puede causar problemas")
    except ValueError as e:
        print_error(f"Error verificando orden: {e}")

def test_authentication_backends():
    """Test 2: Verificar backends de autenticación"""
    print_header("TEST 2: Backends de Autenticación")

    backends = settings.AUTHENTICATION_BACKENDS if hasattr(settings, 'AUTHENTICATION_BACKENDS') else []

    if backends:
        print("Backends configurados:")
        for backend in backends:
            print(f"  - {backend}")
    else:
        print_success("Usando backend por defecto: django.contrib.auth.backends.ModelBackend")

def test_session_configuration():
    """Test 3: Verificar configuración de sesiones"""
    print_header("TEST 3: Configuración de Sesiones")

    print(f"SESSION_ENGINE: {settings.SESSION_ENGINE}")
    print(f"SESSION_COOKIE_AGE: {settings.SESSION_COOKIE_AGE} segundos ({settings.SESSION_COOKIE_AGE // 3600} horas)")
    print(f"SESSION_COOKIE_NAME: {settings.SESSION_COOKIE_NAME}")
    print(f"SESSION_COOKIE_HTTPONLY: {settings.SESSION_COOKIE_HTTPONLY}")
    print(f"SESSION_COOKIE_SECURE: {settings.SESSION_COOKIE_SECURE}")
    print(f"SESSION_SAVE_EVERY_REQUEST: {getattr(settings, 'SESSION_SAVE_EVERY_REQUEST', False)}")

    # Contar sesiones
    try:
        session_count = Session.objects.count()
        print(f"\nSesiones en BD: {session_count}")

        if session_count > 0:
            print("\nÚltimas 5 sesiones:")
            for session in Session.objects.all()[:5]:
                print(f"  - Expira: {session.expire_date}")
    except Exception as e:
        print_error(f"Error accediendo a sesiones: {e}")

def test_users():
    """Test 4: Verificar usuarios existentes"""
    print_header("TEST 4: Usuarios en Base de Datos")

    try:
        users = User.objects.all()
        print(f"Total usuarios: {users.count()}")

        if users.count() == 0:
            print_error("NO HAY USUARIOS - Crea uno con: python manage.py createsuperuser")
            return False

        print("\nUsuarios activos:")
        for user in users:
            status = "✓ Activo" if user.is_active else "✗ Inactivo"
            staff = "👤 Staff" if user.is_staff else ""
            super_status = "🔑 Superuser" if user.is_superuser else ""
            print(f"  {status} {user.username:<20} {staff} {super_status}")

        return True
    except Exception as e:
        print_error(f"Error accediendo a usuarios: {e}")
        return False

def test_authentication():
    """Test 5: Probar autenticación directa"""
    print_header("TEST 5: Prueba de Autenticación")

    # Obtener primer superuser
    try:
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            user = User.objects.filter(is_staff=True).first()
        if not user:
            user = User.objects.first()

        if not user:
            print_error("No hay usuarios para probar")
            return

        print(f"Probando con usuario: {user.username}")
        print("\nPara probar autenticación, necesitas la contraseña.")
        print("Este test solo verifica que el mecanismo funciona.\n")

        # Intentar autenticar con contraseña incorrecta (debería fallar)
        auth_result = authenticate(username=user.username, password='password_incorrecta_123')
        if auth_result is None:
            print_success("authenticate() funciona correctamente (rechazó password incorrecta)")
        else:
            print_warning("authenticate() aceptó password incorrecta - PROBLEMA")

        # Información del usuario
        print(f"\nDetalles del usuario {user.username}:")
        print(f"  - ID: {user.id}")
        print(f"  - Email: {user.email}")
        print(f"  - is_active: {user.is_active}")
        print(f"  - is_staff: {user.is_staff}")
        print(f"  - is_superuser: {user.is_superuser}")
        print(f"  - last_login: {user.last_login}")
        print(f"  - date_joined: {user.date_joined}")

        if not user.is_active:
            print_error("\n⚠️  USUARIO INACTIVO - No puede hacer login")
            print("   Solución: Activar con user.is_active = True; user.save()")

    except Exception as e:
        print_error(f"Error en test de autenticación: {e}")
        import traceback
        traceback.print_exc()

def test_installed_apps():
    """Test 6: Verificar apps necesarias"""
    print_header("TEST 6: Apps Instaladas")

    required_apps = [
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.admin',
    ]

    for app in required_apps:
        if app in settings.INSTALLED_APPS:
            print_success(f"{app}")
        else:
            print_error(f"{app} FALTANTE")

def check_debug_log_for_errors():
    """Test 7: Revisar debug.log por errores de login"""
    print_header("TEST 7: Errores en debug.log")

    if not os.path.exists('debug.log'):
        print_warning("debug.log no existe")
        return

    keywords = ['login', 'auth', 'session', 'error', 'exception', 'traceback']

    try:
        with open('debug.log', 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        print(f"Buscando errores relacionados con login en {len(lines)} líneas...")

        relevant_lines = []
        for line in lines[-200:]:  # Últimas 200 líneas
            line_lower = line.lower()
            if any(kw in line_lower for kw in keywords):
                if 'error' in line_lower or 'exception' in line_lower:
                    relevant_lines.append(line.strip())

        if relevant_lines:
            print(f"\n⚠️  Encontradas {len(relevant_lines)} líneas con posibles errores:")
            for line in relevant_lines[-10:]:  # Mostrar últimas 10
                print(f"  {line}")
        else:
            print_success("No se encontraron errores obvios relacionados con login")
    except Exception as e:
        print_error(f"Error leyendo debug.log: {e}")

def provide_recommendations():
    """Recomendaciones basadas en el diagnóstico"""
    print_header("RECOMENDACIONES")

    print("""
Para diagnosticar el problema de login:

1. Verifica que el usuario existe y está activo:
   python manage.py shell
   >>> from django.contrib.auth.models import User
   >>> user = User.objects.get(username='admin')  # tu username
   >>> print(f"Activo: {user.is_active}, Staff: {user.is_staff}")
   >>> exit()

2. Resetea la contraseña del usuario:
   python manage.py changepassword admin  # tu username

3. Prueba login en modo incógnito:
   - Abre navegador en modo incógnito (Ctrl+Shift+N)
   - Ve a http://localhost:8000/admin/
   - Intenta login con credenciales recién cambiadas

4. Verifica cookies en el navegador:
   - F12 → Application → Cookies
   - Elimina todas las cookies de localhost
   - Intenta login nuevamente

5. Revisa la consola del navegador:
   - F12 → Console
   - ¿Hay errores JavaScript?

6. Revisa los logs del servidor:
   - En la terminal donde corre runserver
   - ¿Aparecen errores cuando intentas login?

7. Si sigue fallando, temporalmente DESACTIVA LoggingMiddleware:
   En StreamBus/settings.py, comenta la línea:
   # 'StreamBus.middleware.LoggingMiddleware',

   Reinicia servidor y prueba login.
   Si funciona, hay un problema con el middleware.
   """)

def main():
    print("\n" + "="*70)
    print("  🔍 DIAGNÓSTICO DE PROBLEMA DE LOGIN")
    print("="*70)

    test_middleware_configuration()
    test_authentication_backends()
    test_session_configuration()
    has_users = test_users()

    if has_users:
        test_authentication()

    test_installed_apps()
    check_debug_log_for_errors()
    provide_recommendations()

    print("\n" + "="*70)
    print("  ✅ DIAGNÓSTICO COMPLETADO")
    print("="*70 + "\n")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error durante diagnóstico: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
