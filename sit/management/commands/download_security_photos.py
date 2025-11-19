from django.core.management.base import BaseCommand
from django.conf import settings
from datetime import datetime, timedelta
import logging
import os
import sys
import requests

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Descarga automática de fotos de seguridad cada 2 horas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=2,
            help='Horas hacia atrás para descargar (default: 2)'
        )
        parser.add_argument(
            '--empresa',
            type=int,
            help='ID específico de empresa (opcional)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar qué se haría, sin descargar'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Iniciando descarga automática de fotos de seguridad')
        )
        
        # Configurar parámetros
        # hours_back = options['hours']
        # empresa_id = options.get('empresa')
        hours_back = 2
        empresa_id = 1
        dry_run = options['dry_run']
        
        # Calcular rango de tiempo
        now = datetime.now()
        end_time = now.replace(minute=0, second=0, microsecond=0)
        start_time = end_time - timedelta(hours=hours_back)
        
        begin_time_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
        end_time_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
        
        self.stdout.write(f"📅 Rango: {begin_time_str} → {end_time_str}")
        
        if empresa_id:
            self.stdout.write(f"🏢 Empresa específica: {empresa_id}")
        else:
            self.stdout.write("🌐 Todas las empresas")
            
        if dry_run:
            self.stdout.write(self.style.WARNING("⚠️ MODO DRY-RUN - Solo simulación"))
        
        try:
            # Ejecutar descarga usando funciones básicas
            result = self.execute_download_basic(
                begin_time_str, 
                end_time_str, 
                empresa_id, 
                dry_run
            )
            
            # Mostrar resultados
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Descarga completada: {result['photos_downloaded']} fotos "
                    f"en {result['duration']:.1f} segundos"
                )
            )
            
            # Log para archivo
            self.log_result(result, begin_time_str, end_time_str, empresa_id)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error en descarga: {str(e)}")
            )
            self.log_error(str(e), begin_time_str, end_time_str)
            sys.exit(1)

    def execute_download_basic(self, begin_time, end_time, empresa_id=None, dry_run=False):
        """
        Versión básica usando requests directamente
        """
        start_timestamp = datetime.now()
        
        # Usar API directamente con requests (más simple)
        photos_data = self.query_photos_api(begin_time, end_time)
        
        total_photos = len(photos_data)
        self.stdout.write(f"📊 Total encontradas: {total_photos} fotos")
        
        if dry_run:
            return {
                'photos_downloaded': 0,
                'photos_total': total_photos,
                'duration': 0,
                'dry_run': True
            }
        
        # Descargar fotos
        photos_dir = os.path.join(settings.MEDIA_ROOT, 'security_photos')
        os.makedirs(photos_dir, exist_ok=True)
        
        downloaded_count = 0
        
        for i, photo in enumerate(photos_data, 1):
            try:
                # Crear estructura de carpetas simple
                vehiIdno = photo.get('vehiIdno', 'unknown')
                devIdno = photo.get('devIdno', 'unknown')
                fileTimeStr = photo.get('fileTimeStr', 'unknown')
                
                # Carpeta por vehículo
                vehicle_folder = f"vehiculo_{vehiIdno}"
                vehicle_dir = os.path.join(photos_dir, vehicle_folder)
                os.makedirs(vehicle_dir, exist_ok=True)
                
                # Nombre de archivo simple
                timestamp = fileTimeStr.replace(' ', '_').replace(':', '-')
                file_name = f"{timestamp}_dev_{devIdno}.jpg"
                file_path = os.path.join(vehicle_dir, file_name)
                
                # Verificar si ya existe
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    continue
                
                # Descargar archivo
                download_url = photo.get('downloadUrl')
                if not download_url:
                    file_path_api = photo.get('FPATH')
                    if file_path_api:
                        download_url = f"http://190.183.254.253:8088/StandardApiAction_downloadFile.action?jsession={settings.JSESSION_GPS}&filePath={file_path_api}"
                
                if download_url and self.download_image(download_url, file_path):
                    downloaded_count += 1
                    
                # Progreso cada 10 fotos
                if i % 10 == 0:
                    self.stdout.write(f"📥 Progreso: {i}/{total_photos}")
                    
            except Exception as e:
                self.stdout.write(f"⚠️ Error foto {i}: {e}")
                continue
        
        duration = (datetime.now() - start_timestamp).total_seconds()
        
        return {
            'photos_downloaded': downloaded_count,
            'photos_total': total_photos,
            'duration': duration,
            'dry_run': False
        }

    def query_photos_api(self, begin_time, end_time):
        """
        Consulta fotos usando requests directamente
        """
        url = "http://190.183.254.253:8088/StandardApiAction_queryPhoto.action"
        
        params = {
            "jsession": settings.JSESSION_GPS,
            "filetype": 2,
            "alarmType": 1,
            "begintime": begin_time,
            "endtime": end_time,
            "currentPage": 1,
            "pageRecords": 500,
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get("result") == 0:
                return data.get("infos", [])
            else:
                self.stdout.write(f"⚠️ API error: {data}")
                return []
                
        except Exception as e:
            self.stdout.write(f"❌ Error API: {e}")
            return []

    def download_image(self, url, file_path):
        """
        Descarga una imagen usando requests
        """
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            # Verificar que se escribió correctamente
            return os.path.getsize(file_path) > 0
            
        except Exception as e:
            self.stdout.write(f"❌ Error descargando {url}: {e}")
            return False

    def log_result(self, result, begin_time, end_time, empresa_id):
        """Log exitoso a archivo"""
        log_dir = os.path.join(settings.BASE_DIR, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, 'auto_download.log')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().isoformat()} SUCCESS "
                   f"Range:{begin_time}-{end_time} "
                   f"Empresa:{empresa_id} "
                   f"Downloaded:{result['photos_downloaded']} "
                   f"Total:{result['photos_total']} "
                   f"Duration:{result['duration']:.1f}s\n")

    def log_error(self, error, begin_time, end_time):
        """Log error a archivo"""
        log_dir = os.path.join(settings.BASE_DIR, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, 'auto_download.log')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().isoformat()} ERROR "
                   f"Range:{begin_time}-{end_time} "
                   f"Error:{error}\n")