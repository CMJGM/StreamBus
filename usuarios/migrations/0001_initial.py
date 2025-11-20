# Generated migration for usuarios app

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('sucursales', '__first__'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('puede_ver_todas', models.BooleanField(default=False, help_text='Si está marcado, el usuario podrá ver todas las sucursales sin restricciones', verbose_name='¿Puede ver todas las sucursales?')),
                ('es_gerente', models.BooleanField(default=False, help_text='Los gerentes tienen permisos especiales en sus sucursales asignadas', verbose_name='¿Es gerente?')),
                ('sucursales', models.ManyToManyField(blank=True, help_text='Sucursales que el usuario puede ver y gestionar', related_name='usuarios', to='sucursales.sucursales', verbose_name='Sucursales asignadas')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL, verbose_name='Usuario')),
            ],
            options={
                'verbose_name': 'Perfil de Usuario',
                'verbose_name_plural': 'Perfiles de Usuarios',
                'ordering': ['user__username'],
            },
        ),
    ]
