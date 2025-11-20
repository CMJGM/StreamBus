from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """
    Perfil extendido del usuario con asignación de sucursales.
    Permite controlar qué sucursales puede ver/editar cada usuario.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name="Usuario"
    )

    sucursales = models.ManyToManyField(
        'sucursales.Sucursales',
        blank=True,
        related_name='usuarios',
        verbose_name="Sucursales asignadas",
        help_text="Sucursales que el usuario puede ver y gestionar"
    )

    origenes = models.ManyToManyField(
        'informes.Origen',
        blank=True,
        related_name='usuarios',
        verbose_name="Orígenes permitidos",
        help_text="Orígenes que el usuario puede usar al crear/editar informes"
    )

    puede_ver_todas = models.BooleanField(
        default=False,
        verbose_name="¿Puede ver todas las sucursales?",
        help_text="Si está marcado, el usuario podrá ver todas las sucursales sin restricciones"
    )

    puede_usar_todos_origenes = models.BooleanField(
        default=False,
        verbose_name="¿Puede usar todos los orígenes?",
        help_text="Si está marcado, el usuario podrá usar todos los orígenes sin restricciones"
    )

    es_gerente = models.BooleanField(
        default=False,
        verbose_name="¿Es gerente?",
        help_text="Los gerentes tienen permisos especiales en sus sucursales asignadas"
    )

    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuarios"
        ordering = ['user__username']

    def __str__(self):
        sucursales_str = ', '.join([s.abreviatura for s in self.sucursales.all()[:3]])
        if self.puede_ver_todas:
            return f"{self.user.username} - TODAS LAS SUCURSALES"
        elif sucursales_str:
            return f"{self.user.username} - {sucursales_str}"
        return f"{self.user.username} - Sin sucursales asignadas"

    def get_sucursales_permitidas(self):
        """
        Retorna QuerySet de sucursales que el usuario puede ver.
        Si puede_ver_todas=True, retorna todas las sucursales.
        """
        from sucursales.models import Sucursales

        if self.puede_ver_todas:
            return Sucursales.objects.all()
        return self.sucursales.all()

    def get_origenes_permitidos(self):
        """
        Retorna QuerySet de orígenes que el usuario puede usar.
        Si puede_usar_todos_origenes=True, retorna todos los orígenes activos.
        """
        from informes.models import Origen

        if self.puede_usar_todos_origenes:
            return Origen.objects.filter(activo=True)
        return self.origenes.filter(activo=True)

    def tiene_acceso_sucursal(self, sucursal):
        """
        Verifica si el usuario tiene acceso a una sucursal específica.

        Args:
            sucursal: Instancia de Sucursales o ID de sucursal

        Returns:
            bool: True si tiene acceso, False en caso contrario
        """
        if self.puede_ver_todas:
            return True

        if isinstance(sucursal, int):
            return self.sucursales.filter(id=sucursal).exists()

        return sucursal in self.sucursales.all()

    def tiene_acceso_origen(self, origen):
        """
        Verifica si el usuario tiene acceso a un origen específico.

        Args:
            origen: Instancia de Origen o ID de origen

        Returns:
            bool: True si tiene acceso, False en caso contrario
        """
        if self.puede_usar_todos_origenes:
            return True

        if isinstance(origen, int):
            return self.origenes.filter(id=origen, activo=True).exists()

        return origen in self.origenes.filter(activo=True)


# Signal para crear automáticamente UserProfile cuando se crea un User
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Crea automáticamente un UserProfile cuando se crea un nuevo usuario.
    """
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Guarda el perfil del usuario cuando se guarda el usuario.
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()
