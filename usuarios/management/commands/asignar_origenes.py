"""
Management command para asignar permisos de origen a usuarios.

Uso:
    python manage.py asignar_origenes --todos
    python manage.py asignar_origenes --usuario username --origenes Guardia,RRHH
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from usuarios.models import UserProfile
from informes.models import Origen


class Command(BaseCommand):
    help = 'Asigna permisos de origen a usuarios del sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--todos',
            action='store_true',
            help='Dar acceso a todos los orígenes a todos los usuarios'
        )

        parser.add_argument(
            '--usuario',
            type=str,
            help='Username del usuario a configurar'
        )

        parser.add_argument(
            '--origenes',
            type=str,
            help='Orígenes separados por comas (ej: Guardia,RRHH,Sistemas)'
        )

        parser.add_argument(
            '--listar',
            action='store_true',
            help='Listar todos los orígenes disponibles'
        )

    def handle(self, *args, **options):
        # Opción: Listar orígenes
        if options['listar']:
            self.listar_origenes()
            return

        # Opción: Dar todos los orígenes a todos los usuarios
        if options['todos']:
            self.asignar_todos_a_todos()
            return

        # Opción: Asignar orígenes específicos a un usuario
        if options['usuario'] and options['origenes']:
            self.asignar_origenes_usuario(
                options['usuario'],
                options['origenes']
            )
            return

        # Si no se especificó ninguna opción válida
        self.stdout.write(
            self.style.ERROR('❌ Debe especificar una opción válida.')
        )
        self.stdout.write('\nUso:')
        self.stdout.write('  python manage.py asignar_origenes --todos')
        self.stdout.write('  python manage.py asignar_origenes --usuario juan --origenes Guardia,RRHH')
        self.stdout.write('  python manage.py asignar_origenes --listar')

    def listar_origenes(self):
        """Lista todos los orígenes disponibles"""
        self.stdout.write(self.style.SUCCESS('\n📋 Orígenes disponibles:'))
        self.stdout.write('─' * 60)

        origenes = Origen.objects.all().order_by('orden')

        if not origenes.exists():
            self.stdout.write(
                self.style.WARNING('⚠️  No hay orígenes en la base de datos')
            )
            self.stdout.write('   Ejecuta: python manage.py migrate')
            return

        for origen in origenes:
            estado = '✅ Activo' if origen.activo else '❌ Inactivo'
            self.stdout.write(
                f'  {origen.orden}. {origen.nombre:20} {estado}'
            )
            if origen.descripcion:
                self.stdout.write(f'     {origen.descripcion}')

        self.stdout.write('─' * 60)

    def asignar_todos_a_todos(self):
        """Asigna permiso de usar todos los orígenes a todos los usuarios"""
        self.stdout.write(
            self.style.WARNING('\n⚠️  ¿Dar acceso a TODOS los orígenes a TODOS los usuarios?')
        )
        self.stdout.write('   Esto marcará puede_usar_todos_origenes=True para cada usuario\n')

        # Contar usuarios
        count = UserProfile.objects.count()
        self.stdout.write(f'   Usuarios afectados: {count}\n')

        confirm = input('   Confirmar (escriba "si" para continuar): ')

        if confirm.lower() != 'si':
            self.stdout.write(self.style.ERROR('❌ Operación cancelada'))
            return

        # Actualizar todos los perfiles
        actualizados = 0
        for profile in UserProfile.objects.all():
            profile.puede_usar_todos_origenes = True
            profile.save()
            actualizados += 1
            self.stdout.write(
                self.style.SUCCESS(f'   ✅ {profile.user.username}')
            )

        self.stdout.write('─' * 60)
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ {actualizados} usuarios actualizados correctamente')
        )

    def asignar_origenes_usuario(self, username, origenes_str):
        """Asigna orígenes específicos a un usuario"""

        # Verificar que el usuario existe
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'❌ Usuario "{username}" no encontrado')

        # Parsear los orígenes
        nombres_origenes = [o.strip() for o in origenes_str.split(',')]

        self.stdout.write(
            self.style.WARNING(f'\n📝 Asignando orígenes a: {username}')
        )
        self.stdout.write('─' * 60)

        # Obtener los objetos Origen
        origenes = []
        for nombre in nombres_origenes:
            try:
                origen = Origen.objects.get(nombre=nombre, activo=True)
                origenes.append(origen)
                self.stdout.write(f'   ✅ {nombre}')
            except Origen.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'   ⚠️  {nombre} - No encontrado o inactivo')
                )

        if not origenes:
            raise CommandError('❌ No se encontró ningún origen válido')

        # Asignar los orígenes al usuario
        profile = user.profile
        profile.origenes.set(origenes)
        profile.save()

        self.stdout.write('─' * 60)
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ {len(origenes)} origen(es) asignado(s) a {username}'
            )
        )

        # Mostrar orígenes asignados
        self.stdout.write('\n📋 Orígenes del usuario:')
        for origen in profile.origenes.all():
            self.stdout.write(f'   • {origen.nombre}')
