import os
import mimetypes
from pathlib import Path
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-@oic64r!trv^3_eydz6@4p0svih5_v-y)@!w%cq)22_=t^7mzh'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
ALLOWED_HOSTS = ['127.0.0.1',
                'localhost',
                '192.168.250.176',
                '190.183.254.254',
                'sql2022.dominio.local',
                'mx01.empresarecreo.com.ar',]

DATA_UPLOAD_MAX_MEMORY_SIZE = 524288000 
MAX_VIDEO_UPLOAD_SIZE_MB = 60 


# Application definition
INSTALLED_APPS = [
    # App de Registration Redux
    "django.contrib.sites",
    "registration",    

    # Apps por default de Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Apps de Terceros
    'admin_interface',
    'colorfield',
    "captcha",
    'debug_toolbar',
    'widget_tweaks',

    # Apps de la Aplicacion
    'inicio',
    'siniestros',
    'buses',
    'empleados',
    'categoria',
    'sucursales',
    'informes',
    'sit',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'StreamBus.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.static',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'usuarios.context_processors.user_groups', 
            ],
        },
    },
]

WSGI_APPLICATION = 'StreamBus.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'mssql',
        'NAME': 'streambus',
        'USER': 'sa',
        'PASSWORD': 'HPsql2012',
        'HOST': '190.183.254.254',
        'PORT': '62593',
        'OPTIONS': {'driver': 'ODBC Driver 17 for SQL Server',},
    },
    'SIT': {
        'ENGINE': 'mssql',
        'NAME': 'SIT',
        'USER': 'wwwStreamBusSitR',
        'PASSWORD': 'y57b8376*bn7HM-e5',
        'HOST': '190.183.254.254',
        'PORT': '62593',
        'OPTIONS': { 'driver': 'ODBC Driver 17 for SQL Server',},  
    },    
}



# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    #{'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Argentina/Buenos_Aires'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# JSESSION para autenticación con sistema GPS externo
JSESSION_GPS = None  # Este valor se actualizará dinámicamente al hacer login


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR,"static")
STATICFILES_DIRS = (os.path.join(BASE_DIR,"static_dev"),)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# PARA REGISTRATION REDUX
LOGIN_REDIRECT_URL = "inicio"
LOGIN_URL = 'login'
REGISTRATION_OPEN = True  # Permite el registro de nuevos usuarios
REGISTRATION_URL = '/usuarios/register/'  # URL para el formulario de registro
LOGIN_REDIRECT_URL = '/'  # URL a la que se redirige después del registro exitoso
ACCOUNT_ACTIVATION_DAYS = 7 # One-week activation window; you may, of course, use a different value.
REGISTRATION_AUTO_LOGIN = True # Automatically log the user in.
SITE_ID = 1


#EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
#EMAIL_HOST = 'smtp.gmail.com'
#EMAIL_PORT = 587
#EMAIL_USE_TLS = True  
#EMAIL_HOST_USER = 'streambusasf@gmail.com' 
#EMAIL_HOST_PASSWORD = 'ubbe khtu inuc qoci'  
#DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# 🔥 Coloca esto AL INICIO de settings.py (antes de otras configuraciones)
import ssl
import smtplib

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = '192.168.250.250'
EMAIL_PORT = 25
EMAIL_USE_SSL = False
EMAIL_USE_TLS = False
EMAIL_HOST_USER = 'cristian.gudino'  # Prueba sin @dominio primero
EMAIL_HOST_PASSWORD = 'cristian6163'
DEFAULT_FROM_EMAIL = 'sit.autobuses@autobusessantafe.com.ar'  # El FROM puede llevar dominio





LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,  # importante para no perder logs de Django
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'debug.log'),
        },
    },
    'loggers': {
        'django': {  # Logs del núcleo de Django
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        '': {  # Logs personalizados como los tuyos
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
        },
    },
}


# =============================================================================
# CONFIGURACIÓN GPS/CITOS MIGRATION
# =============================================================================

# Feature flag principal para activar citos
USE_CITOS_LIBRARY = os.environ.get('USE_CITOS_LIBRARY', 'False').lower() == 'true'

# Configuración GPS base (migrar desde hardcoded)
GPS_BASE_URL = os.environ.get('GPS_BASE_URL', 'http://190.183.254.253:8088')
GPS_TIMEOUT = int(os.environ.get('GPS_TIMEOUT', '30'))
GPS_VERIFY_SSL = os.environ.get('GPS_VERIFY_SSL', 'True').lower() == 'true'

# Credenciales GPS (migrar desde hardcoded - USAR LAS ACTUALES)
GPS_ACCOUNT = os.environ.get('GPS_ACCOUNT', "admin")  # ← Poner tu usuario actual
GPS_PASSWORD = os.environ.get('GPS_PASSWORD', "Buses2024")  # ← Poner tu password actual

# Funciones específicas a migrar (control granular)
CITOS_ENABLED_FUNCTIONS = {
    'obtener_ultima_ubicacion': USE_CITOS_LIBRARY,
    'obtener_vehiculos': USE_CITOS_LIBRARY,
    'query_security_photos': USE_CITOS_LIBRARY,
    'gps_login': USE_CITOS_LIBRARY,
}



if DEBUG:
    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware",]    
    INTERNAL_IPS = ["127.0.0.1",]
    import mimetypes
    mimetypes.add_type("application/javascript", ".js", True)
    DEBUG_TOOLBAR_CONFIG = {"INTERCEPT_REDIRECTS": False,}

# Agregar al final de tu settings.py existente

# =============================================================================
# CONFIGURACIONES BÁSICAS DE OPTIMIZACIÓN DE DESCARGA
# =============================================================================

# Configuración básica de descargas (versión simplificada)
DOWNLOAD_OPTIMIZATION = {
    # Número máximo de workers para descargas concurrentes
    'MAX_DOWNLOAD_WORKERS': 25,  # Empezamos conservador
    
    # Número máximo de descargas simultáneas
    'MAX_CONCURRENT_DOWNLOADS': 10,  # Empezamos conservador
    
    # Timeout para conexiones HTTP (segundos)
    'HTTP_TIMEOUT': 40,
    
    # Tamaño de batch para consultas de API
    'API_BATCH_SIZE': 200,  # Empezamos con páginas más pequeñas
    
    # Intervalo de polling (milisegundos)
    'INITIAL_POLL_INTERVAL': 8000,  # 3 segundos inicial
}

# Agregar el middleware (ya no debería dar error)
MIDDLEWARE += [
    'sit.middleware.DownloadOptimizationMiddleware',
]

# Configuración de cache básica
if 'default' not in locals().get('CACHES', {}):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
            'TIMEOUT': 300,  # 5 minutos
        }
    }

# Configuración de archivos grandes (si no está ya configurado)
if not hasattr(locals(), 'FILE_UPLOAD_MAX_MEMORY_SIZE'):
    FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50MB

# Logging básico para downloads (si no existe ya)
if 'sit.download_manager' not in LOGGING.get('loggers', {}):
    LOGGING['loggers']['sit.download_manager'] = {
        'handlers': ['console', 'file'],
        'level': 'INFO',
        'propagate': False,
    }

print(f"""
╔══════════════════════════════════════════════════════════════════╗
║                  ⚙️  CONFIGURACIÓN BÁSICA CARGADA                  ║
╠══════════════════════════════════════════════════════════════════╣
║  🚀 Workers máximos: {DOWNLOAD_OPTIMIZATION['MAX_DOWNLOAD_WORKERS']}                                 ║
║  ⚡ Descargas concurrentes: {DOWNLOAD_OPTIMIZATION['MAX_CONCURRENT_DOWNLOADS']}                        ║
║  ⏱️ Timeout HTTP: {DOWNLOAD_OPTIMIZATION['HTTP_TIMEOUT']}s                                ║
║  📦 Batch size API: {DOWNLOAD_OPTIMIZATION['API_BATCH_SIZE']}                               ║
║  🔄 Polling interval: {DOWNLOAD_OPTIMIZATION['INITIAL_POLL_INTERVAL']}ms                       ║
║                                                                  ║
║  ✅ Middleware básico activado                                   ║
║  ✅ Cache configurado                                            ║
║  ✅ Logging activado                                             ║
╚══════════════════════════════════════════════════════════════════╝
""")





# ===== CONFIGURACIÓN CELERY BEAT =====
CELERY_BEAT_SCHEDULE = {
    # Descarga automática cada 2 horas
    'auto-download-security-photos': {
        'task': 'sit.tasks.auto_download_security_photos',
        'schedule': crontab(minute=0, hour='*/2'),  # Cada 2 horas en punto
        'kwargs': {
            'empresa_id': None,  # Todas las empresas
            'custom_hours': 2    # 2 horas hacia atrás
        },
        'options': {
            'queue': 'photos_download',
            'priority': 5,
            'expires': 3600,  # Expira en 1 hora si no se ejecuta
        }
    },
    
    # OPCIONAL: Descarga específica para empresa prioritaria
    'auto-download-empresa-vip': {
        'task': 'sit.tasks.auto_download_security_photos', 
        'schedule': crontab(minute=15, hour='8,12,16,20'),  # 8:15, 12:15, 16:15, 20:15
        'kwargs': {
            'empresa_id': 1,     # Empresa específica
            'custom_hours': 4    # 4 horas hacia atrás para mayor cobertura
        },
        'options': {
            'queue': 'priority_downloads',
            'priority': 9
        }
    },
    
    # Limpieza de logs antiguos (semanal)
    'cleanup-old-download-logs': {
        'task': 'sit.tasks.cleanup_old_logs',
        'schedule': crontab(minute=0, hour=2, day_of_week=1),  # Lunes 2:00 AM
        'options': {'queue': 'maintenance'}
    }
}

# ===== ALTERNATIVAS DE HORARIOS (elige una) =====

# Opción 1: Usar crontab() - Estilo Unix
CELERY_BEAT_SCHEDULE_OPTION_1 = {
    'auto-download': {
        'task': 'sit.tasks.auto_download_security_photos',
        'schedule': crontab(minute=0, hour='*/2'),  # Cada 2 horas
    }
}

# Opción 2: Usar schedule directo - Más legible
from celery import schedules

CELERY_BEAT_SCHEDULE_OPTION_2 = {
    'auto-download': {
        'task': 'sit.tasks.auto_download_security_photos', 
        'schedule': schedules.schedule(run_every=7200),  # 7200 segundos = 2 horas
    }
}

# Opción 3: Horarios específicos - Más control
CELERY_BEAT_SCHEDULE_OPTION_3 = {
    'auto-download': {
        'task': 'sit.tasks.auto_download_security_photos',
        'schedule': crontab(
            minute=0, 
            hour='1,3,5,7,9,11,13,15,17,19,21,23'  # Horas específicas
        ),
    }
}

# ===== CONFIGURACIÓN DE COLAS =====
CELERY_TASK_ROUTES = {
    'sit.tasks.auto_download_security_photos': {
        'queue': 'photos_download',
        'routing_key': 'photos.download'
    },
    'sit.tasks.execute_automated_download': {
        'queue': 'photos_download',
        'routing_key': 'photos.process'
    },
    'sit.tasks.send_*_notification': {
        'queue': 'notifications',
        'routing_key': 'notifications.email'
    },
    'sit.tasks.cleanup_old_logs': {
        'queue': 'maintenance',
        'routing_key': 'maintenance.cleanup'
    }
}

# ===== CONFIGURACIÓN ESPECÍFICA PARA DESCARGAS =====
AUTO_DOWNLOAD_CONFIG = {
    'ENABLED': True,
    'DEFAULT_HOURS_BACK': 2,
    'MAX_CONCURRENT_DOWNLOADS': 10,
    'MAX_DOWNLOAD_WORKERS': 15,
    'TIMEOUT_MINUTES': 30,
    'MAX_RETRIES': 3,
    'RETRY_DELAY_SECONDS': 300,
    'NOTIFICATION_THRESHOLD': 100,
    'CLEANUP_LOGS_AFTER_DAYS': 30,
    
    # Empresas específicas (opcional)
    'PRIORITY_EMPRESAS': [1, 2],  # IDs de empresas prioritarias
    'EXCLUDE_EMPRESAS': [],       # IDs a excluir de descarga automática
}

# ===== NO usar django-crontab =====
# INSTALLED_APPS NO debe incluir 'django_crontab'
# CRONJOBS NO debe existir

# ===== SOLO Celery =====
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Argentina/Buenos_Aires'
CELERY_ENABLE_UTC = True

# Configuración de workers
CELERY_WORKER_CONCURRENCY = 4
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
CELERY_TASK_SOFT_TIME_LIMIT = 1800  # 30 minutos
CELERY_TASK_TIME_LIMIT = 2400       # 40 minutos

# Tareas programadas
CELERY_BEAT_SCHEDULE = {
    'auto-download-security-photos': {
        'task': 'sit.tasks.auto_download_security_photos',
        'schedule': crontab(minute=0, hour='*/2'),  # Cada 2 horas
        'options': {'queue': 'photos_download'},
    },
}

# Rutas de tareas
CELERY_TASK_ROUTES = {
    'sit.tasks.*': {'queue': 'photos_download'},
}