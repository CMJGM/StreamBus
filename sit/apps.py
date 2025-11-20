from django.apps import AppConfig
from django.conf import settings


class SitConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sit"

    def ready(self):        
        from .utils import gps_login
        settings.JSESSION_GPS=gps_login('admin','Buses2024')