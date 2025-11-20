from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    """
    Inline para editar el perfil del usuario dentro del admin de User.
    """
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Perfil y Sucursales'

    fieldsets = (
        ('Permisos de Sucursales', {
            'fields': ('sucursales', 'puede_ver_todas', 'es_gerente'),
            'description': 'Configure las sucursales a las que este usuario tiene acceso.'
        }),
        ('Permisos de Orígenes', {
            'fields': ('origenes', 'puede_usar_todos_origenes'),
            'description': 'Configure los orígenes de informes que este usuario puede usar.'
        }),
    )

    filter_horizontal = ('sucursales', 'origenes')  # Widget mejorado para ManyToMany


class CustomUserAdmin(BaseUserAdmin):
    """
    Admin personalizado para User que incluye información de sucursales.
    """
    inlines = [UserProfileInline]

    # Columnas mostradas en la lista
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'get_sucursales_badge',
        'get_grupos_badge',
        'is_active',
        'is_staff',
    )

    list_filter = (
        'is_active',
        'is_staff',
        'is_superuser',
        'groups',
        'profile__puede_ver_todas',
        'profile__es_gerente',
    )

    search_fields = ('username', 'first_name', 'last_name', 'email')

    def get_sucursales_badge(self, obj):
        """
        Muestra las sucursales del usuario con badge colorido.
        """
        try:
            if not hasattr(obj, 'profile'):
                return format_html(
                    '<span style="background-color: #ff4444; color: white; padding: 3px 8px; '
                    'border-radius: 3px; font-size: 11px;">Sin Perfil</span>'
                )

            profile = obj.profile

            if profile.puede_ver_todas:
                return format_html(
                    '<span style="background-color: #4CAF50; color: white; padding: 3px 8px; '
                    'border-radius: 3px; font-size: 11px; font-weight: bold;">✓ TODAS</span>'
                )

            sucursales = profile.sucursales.all()
            count = sucursales.count()

            if count == 0:
                return format_html(
                    '<span style="background-color: #ff9800; color: white; padding: 3px 8px; '
                    'border-radius: 3px; font-size: 11px;">⚠ Sin Asignar</span>'
                )

            sucursales_str = ', '.join([s.abreviatura for s in sucursales[:3]])
            if count > 3:
                sucursales_str += f' +{count - 3}'

            return format_html(
                '<span style="background-color: #2196F3; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">{} ({})</span>',
                sucursales_str,
                count
            )

        except Exception as e:
            return format_html(
                '<span style="background-color: #ff4444; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">Error</span>'
            )

    get_sucursales_badge.short_description = 'Sucursales'

    def get_grupos_badge(self, obj):
        """
        Muestra los grupos del usuario con badges.
        """
        grupos = obj.groups.all()

        if not grupos:
            return format_html(
                '<span style="background-color: #9e9e9e; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">Sin Grupos</span>'
            )

        badges = []
        color_map = {
            'Completo': '#4CAF50',
            'RRHH': '#2196F3',
            'Vigilancia': '#FF9800',
            'GPS': '#9C27B0',
            'Siniestro': '#F44336',
            'Taller': '#00BCD4',
        }

        for grupo in grupos:
            color = color_map.get(grupo.name, '#607D8B')
            badges.append(
                f'<span style="background-color: {color}; color: white; padding: 3px 8px; '
                f'border-radius: 3px; font-size: 11px; margin-right: 3px;">{grupo.name}</span>'
            )

        return format_html(' '.join(badges))

    get_grupos_badge.short_description = 'Grupos'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin independiente para UserProfile (opcional, principalmente para debugging).
    """
    list_display = (
        'user',
        'get_sucursales_list',
        'puede_ver_todas',
        'puede_usar_todos_origenes',
        'es_gerente',
    )

    list_filter = ('puede_ver_todas', 'puede_usar_todos_origenes', 'es_gerente')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    filter_horizontal = ('sucursales', 'origenes')

    fieldsets = (
        ('Usuario', {
            'fields': ('user',)
        }),
        ('Permisos de Sucursales', {
            'fields': ('sucursales', 'puede_ver_todas', 'es_gerente'),
        }),
        ('Permisos de Orígenes', {
            'fields': ('origenes', 'puede_usar_todos_origenes'),
        }),
    )

    def get_sucursales_list(self, obj):
        """
        Muestra la lista de sucursales del perfil.
        """
        if obj.puede_ver_todas:
            return "TODAS LAS SUCURSALES"

        sucursales = obj.sucursales.all()
        count = sucursales.count()

        if count == 0:
            return "Sin sucursales asignadas"

        return ', '.join([s.abreviatura for s in sucursales])

    get_sucursales_list.short_description = 'Sucursales Asignadas'


# Re-registrar User con el admin personalizado
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
