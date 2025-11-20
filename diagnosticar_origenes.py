"""
Script de diagnóstico para verificar orígenes de usuario

Uso:
    python diagnosticar_origenes.py
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'StreamBus.settings')
django.setup()

from django.contrib.auth.models import User
from usuarios.models import UserProfile
from informes.models import Origen

print("="*70)
print("  🔍 DIAGNÓSTICO DE ORÍGENES Y PERMISOS DE USUARIO")
print("="*70)
print()

# 1. Verificar si existen orígenes en la BD
print("📋 PASO 1: Verificar orígenes en la base de datos")
print("-" * 70)

origenes = Origen.objects.all()
if origenes.exists():
    print(f"✅ Se encontraron {origenes.count()} orígenes:")
    for origen in origenes.order_by('orden'):
        estado = "✅ Activo" if origen.activo else "❌ Inactivo"
        print(f"   {origen.orden}. {origen.nombre:20} {estado}")
else:
    print("❌ NO HAY ORÍGENES EN LA BASE DE DATOS")
    print("   Solución: Ejecutar las migraciones")
    print("   Comando: python manage.py migrate")
    sys.exit(1)

print()

# 2. Listar usuarios y sus permisos de origen
print("👥 PASO 2: Verificar permisos de origen por usuario")
print("-" * 70)

usuarios = User.objects.all()
sin_origenes = []

for user in usuarios:
    if hasattr(user, 'profile'):
        profile = user.profile

        # Verificar si puede usar todos los orígenes
        if profile.puede_usar_todos_origenes:
            print(f"✅ {user.username:20} → TODOS LOS ORÍGENES (puede_usar_todos_origenes=True)")
        else:
            # Verificar orígenes asignados
            origenes_usuario = profile.origenes.all()
            if origenes_usuario.exists():
                nombres = ", ".join([o.nombre for o in origenes_usuario])
                print(f"✅ {user.username:20} → {nombres}")
            else:
                print(f"⚠️  {user.username:20} → SIN ORÍGENES ASIGNADOS")
                sin_origenes.append(user.username)
    else:
        print(f"❌ {user.username:20} → SIN PERFIL")

print()

# 3. Resumen y recomendaciones
print("📊 PASO 3: Resumen y recomendaciones")
print("-" * 70)

if sin_origenes:
    print(f"⚠️  {len(sin_origenes)} usuario(s) sin orígenes asignados:")
    for username in sin_origenes:
        print(f"   - {username}")

    print()
    print("💡 SOLUCIÓN:")
    print("   Opción A - Dar acceso a todos los orígenes a todos los usuarios:")
    print("   python manage.py asignar_origenes --todos")
    print()
    print("   Opción B - Asignar orígenes específicos a un usuario:")
    print("   python manage.py asignar_origenes --usuario NOMBRE_USUARIO --origenes Guardia,RRHH")
else:
    print("✅ Todos los usuarios tienen orígenes asignados")

print()

# 4. Test de método get_origenes_permitidos()
print("🧪 PASO 4: Probar método get_origenes_permitidos()")
print("-" * 70)

if usuarios.exists():
    usuario_test = usuarios.first()
    print(f"Probando con usuario: {usuario_test.username}")

    if hasattr(usuario_test, 'profile'):
        origenes_permitidos = usuario_test.profile.get_origenes_permitidos()
        print(f"Orígenes permitidos: {origenes_permitidos.count()}")

        if origenes_permitidos.exists():
            for origen in origenes_permitidos:
                print(f"   ✅ {origen.nombre}")
        else:
            print("   ⚠️  get_origenes_permitidos() retorna QuerySet vacío")
            print("   El usuario no podrá ver ningún origen en los filtros")
    else:
        print("   ❌ Usuario no tiene perfil")

print()
print("="*70)
print("  FIN DEL DIAGNÓSTICO")
print("="*70)
