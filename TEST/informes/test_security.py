"""
Tests de seguridad para endpoints de informes.

Verifica que todos los endpoints requieran autenticación y autorización correcta.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from informes.models import Informe, FotoInforme, VideoInforme
from empleados.models import Empleado
from buses.models import Buses
from sucursales.models import Sucursales
from usuarios.models import Perfil


class AuthenticationTestCase(TestCase):
    """Tests para verificar que los endpoints requieran autenticación"""

    def setUp(self):
        self.client = Client()
        # Crear usuario de prueba
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )

    def test_cargar_fotos_requires_login(self):
        """Verificar que cargar_fotos requiere autenticación"""
        response = self.client.get(reverse('informes:cargar_fotos', args=[1]))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        self.assertIn('/login/', response.url or response.get('Location', ''))

    def test_cargar_video_requires_login(self):
        """Verificar que cargar_video requiere autenticación"""
        response = self.client.get(reverse('informes:cargar_video', args=[1]))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        self.assertIn('/login/', response.url or response.get('Location', ''))

    def test_ver_foto_requires_login(self):
        """Verificar que ver_foto requiere autenticación"""
        response = self.client.get(reverse('informes:ver_foto', args=[1]))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        self.assertIn('/login/', response.url or response.get('Location', ''))

    def test_lista_informes_requires_login(self):
        """Verificar que lista_informes requiere autenticación"""
        response = self.client.get(reverse('informes:lista_informes'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_buscar_informes_requires_login(self):
        """Verificar que buscar_informes requiere autenticación"""
        response = self.client.get(reverse('informes:buscar_informes'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_informes_sin_legajo_requires_login(self):
        """Verificar que informes_sin_legajo requiere autenticación"""
        response = self.client.get(reverse('informes:informes_sin_legajo'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_informes_no_enviados_requires_login(self):
        """Verificar que informes_no_enviados requiere autenticación"""
        response = self.client.get(reverse('informes:informes_no_enviados'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_informes_asociar_sitinforme_requires_login(self):
        """Verificar que informes_asociar_sitinforme requiere autenticación"""
        response = self.client.get(reverse('informes:sit_informe'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_informes_asociar_sitsiniestro_requires_login(self):
        """Verificar que informes_asociar_sitsiniestro requiere autenticación"""
        response = self.client.get(reverse('informes:sit_siniestro'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_informes_desestimar_requires_login(self):
        """Verificar que informes_desestimar requiere autenticación"""
        response = self.client.get(reverse('informes:desestimar'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_estadisticas_informes_requires_login(self):
        """Verificar que estadisticas_informes requiere autenticación"""
        response = self.client.get(reverse('informes:dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_informes_disciplinarios_requires_login(self):
        """Verificar que informes_disciplinarios requiere autenticación"""
        response = self.client.get(reverse('informes:disciplinarios'))
        self.assertEqual(response.status_code, 302)  # Redirect to login


class CBVAuthenticationTestCase(TestCase):
    """Tests para verificar que las CBVs requieran autenticación"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )

    def test_lista_informes_borrar_requires_login(self):
        """Verificar que ListaInformesBorrarView requiere autenticación"""
        response = self.client.get(reverse('informes:lista_borrar'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_enviar_informe_email_requires_login(self):
        """Verificar que EnviarInformeEmailView requiere autenticación"""
        response = self.client.get(reverse('informes:enviar_email', args=[1]))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_informes_por_empleado_requires_login(self):
        """Verificar que InformesPorEmpleadoView requiere autenticación"""
        response = self.client.get(reverse('informes:informes_por_empleado'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_informe_borrar_requires_login(self):
        """Verificar que InformeBorrarView requiere autenticación"""
        response = self.client.get(reverse('informes:borrar_informe', args=[1]))
        self.assertEqual(response.status_code, 302)  # Redirect to login


class SucursalAccessTestCase(TestCase):
    """Tests para verificar control de acceso por sucursal"""

    def setUp(self):
        self.client = Client()

        # Crear sucursales
        self.sucursal_a = Sucursales.objects.create(
            codigo=1,
            descripcion='Sucursal A'
        )
        self.sucursal_b = Sucursales.objects.create(
            codigo=2,
            descripcion='Sucursal B'
        )

        # Crear usuarios
        self.user_a = User.objects.create_user(
            username='user_a',
            password='testpass123'
        )
        self.user_b = User.objects.create_user(
            username='user_b',
            password='testpass123'
        )

        # TODO: Crear perfiles y asignar sucursales
        # Este test requiere que exista el modelo Perfil y sus métodos
        # self.profile_a = Perfil.objects.create(user=self.user_a)
        # self.profile_a.sucursales.add(self.sucursal_a)

    def test_user_cannot_access_other_sucursal_photos(self):
        """
        Verificar que un usuario no pueda acceder a fotos de otra sucursal

        NOTA: Este test está pendiente de implementación completa.
        Requiere:
        - Modelo Perfil configurado
        - Informes de prueba
        - Fotos de prueba
        """
        self.skipTest("Requiere configuración completa de Perfil y datos de prueba")

    def test_user_with_puede_ver_todas_can_access_all(self):
        """
        Verificar que usuarios con puede_ver_todas puedan acceder a todo

        NOTA: Este test está pendiente de implementación completa.
        """
        self.skipTest("Requiere configuración completa de Perfil")


class AuditLoggingTestCase(TestCase):
    """Tests para verificar que las acciones sensibles se registren en logs"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_file_upload_is_logged(self):
        """
        Verificar que las subidas de archivos se registren en logs

        NOTA: Este test requiere captura de logs.
        Implementación pendiente.
        """
        self.skipTest("Requiere configuración de captura de logs")


# Ejecutar tests:
# python manage.py test TEST.informes.test_security -v 2
