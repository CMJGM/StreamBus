from django.apps import AppConfig
from django.conf import settings


class SitConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sit"

    def ready(self):
        from .utils import gps_login
        # Usar credenciales desde settings (que vienen de .env)
        gps_account = getattr(settings, 'GPS_ACCOUNT', 'admin')
        gps_password = getattr(settings, 'GPS_PASSWORD', '')
        settings.JSESSION_GPS = gps_login(gps_account, gps_password)