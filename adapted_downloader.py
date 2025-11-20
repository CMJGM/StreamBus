"""
StreamBus Downloader Engine - Standalone Version
Adaptado del código Django views.py para uso independiente
"""

import os
import time
import threading
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any, Callable

from adapted_utils import (
    get_config, query_security_photos, obtener_vehiculos_por_empresa,
    crear_nombre_carpeta_vehiculo, crear_nombre_archivo_foto,
    verificar_archivo_existe, download_and_save_image
)

logger = logging.getLogger(__name__)

class DownloadStatistics:
    """Clase para manejar estadísticas de descarga"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reinicia todas las estadísticas"""
        self.total_procesadas = 0
        self.incluidas = 0
        self.excluidas = 0
        self.ya_existen = 0
        self.descargadas = 0
        self.errores = 0
        self.paginas_procesadas = 0
        self.vehiculos_unicos = set()
        self.dispositivos_unicos = set()
        self.start_time = time.time()
        self.end_time = None
    
    def add_page_stats(self, page_stats):
        """Agrega estadísticas de una página al total"""
        self.total_procesadas += page_stats.get('total_procesadas', 0)
        self.incluidas += page_stats.get('incluidas', 0)
        self.excluidas += page_stats.get('excluidas', 0)
        self.ya_existen += page_stats.get('ya_existen', 0)
        self.descargadas += page_stats.get('descargadas', 0)
        self.errores += page_stats.get('errores', 0)
        self.paginas_procesadas += 1
        
        if 'vehiculos' in page_stats:
            self.vehiculos_unicos.update(page_stats['vehiculos'])
        if 'dispositivos' in page_stats:
            self.dispositivos_unicos.update(page_stats['dispositivos'])
    
    def finalize(self):
        """Finaliza el conteo"""
        self.end_time = time.time()
    
    def get_duration(self):
        """Obtener duración total"""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    def get_summary(self):
        """Obtener resumen de estadísticas"""
        duration = self.get_duration()
        return {
            'total_procesadas': self.total_procesadas,
            'incluidas': self.incluidas,
            'excluidas': self.excluidas,
            'ya_existen': self.ya_existen,
            'descargadas': self.descargadas,
            'errores': self.errores,
            'paginas_procesadas': self.paginas_procesadas,
            'vehiculos_count': len(self.vehiculos_unicos),
            'dispositivos_count': len(self.dispositivos_unicos),
            'duration': duration,
            'total_disponibles': self.ya_existen + self.descargadas,
            'velocidad_promedio': (self.descargadas + self.ya_existen) / duration if duration > 0 else 0
        }
    
    def get_final_report(self):
        """Genera reporte final para logs"""
        duration = self.get_duration()
        duration_str = str(timedelta(seconds=int(duration)))
        
        total_intentos = self.incluidas
        porcentaje_exito = (self.descargadas / total_intentos * 100) if total_intentos > 0 else 0
        porcentaje_ya_existian = (self.ya_existen / total_intentos * 100) if total_intentos > 0 else 0
        porcentaje_errores = (self.errores / total_intentos * 100) if total_intentos > 0 else 0
        velocidad = self.descargadas / duration if duration > 0 else 0
        
        return f"""
╔══════════════════════════════════════════════════════════════════════╗
║                   📊 ESTADÍSTICAS FINALES DE DESCARGA                ║
╠══════════════════════════════════════════════════════════════════════╣
║  📈 RESUMEN GENERAL:                                                 ║
║  ├── Total de fotos procesadas: {self.total_procesadas:,}                        ║
║  ├── ✅ Incluidas en filtrado: {self.incluidas:,}                            ║
║  ├── ❌ Excluidas por filtro: {self.excluidas:,}                             ║
║  └── 📄 Páginas procesadas: {self.paginas_procesadas}                              ║
║                                                                      ║
║  🎯 RESULTADOS DE DESCARGA:                                          ║
║  ├── 📥 Descargadas nuevas: {self.descargadas:,} ({porcentaje_exito:.1f}%)              ║
║  ├── ⏭️ Ya existían: {self.ya_existen:,} ({porcentaje_ya_existian:.1f}%)                   ║
║  ├── 💥 Errores: {self.errores:,} ({porcentaje_errores:.1f}%)                             ║
║  └── ✅ Total disponibles: {self.ya_existen + self.descargadas:,}                   ║
║                                                                      ║
║  🚗 COBERTURA:                                                       ║
║  ├── 🚌 Vehículos únicos: {len(self.vehiculos_unicos)}                            ║
║  └── 📱 Dispositivos únicos: {len(self.dispositivos_unicos)}                      ║
║                                                                      ║
║  ⏱️ RENDIMIENTO:                                                      ║
║  ├── 🕐 Tiempo total: {duration_str}                                 ║
║  ├── 🚀 Velocidad: {velocidad:.1f} fotos/segundo                           ║
║  └── 📊 Promedio por página: {self.incluidas/self.paginas_procesadas:.1f} fotos  ║
╚══════════════════════════════════════════════════════════════════════╝
"""

class DownloadJob:
    """Clase para manejar un trabajo de descarga"""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.status = 'pending'  # pending, running, completed, error, cancelled
        self.progress = 0
        self.message = 'Preparando...'
        self.total_photos = 0
        self.downloaded_photos = 0
        self.start_time = None
        self.end_time = None
        self.error_message = None
        self.stats = None
        self.all_photos = []
        
        # Callbacks para actualizar GUI
        self.progress_callback = None
        self.completion_callback = None
        self.error_callback = None
    
    def set_callbacks(self, progress_callback=None, completion_callback=None, error_callback=None):
        """Establecer callbacks para actualizar la GUI"""
        self.progress_callback = progress_callback
        self.completion_callback = completion_callback
        self.error_callback = error_callback
    
    def update_progress(self, progress=None, message=None, downloaded=None):
        """Actualizar progreso del trabajo"""
        if progress is not None:
            self.progress = min(100, max(0, progress))
        if message is not None:
            self.message = message
        if downloaded is not None:
            self.downloaded_photos = downloaded
        
        # Llamar callback si está definido
        if self.progress_callback:
            try:
                self.progress_callback(self)
            except Exception as e:
                logger.error(f"❌ Error en progress_callback: {e}")
    
    def complete(self, stats=None, photos=None):
        """Marcar trabajo como completado"""
        self.status = 'completed'
        self.progress = 100
        self.end_time = time.time()
        if stats:
            self.stats = stats
        if photos:
            self.all_photos = photos
        
        # Llamar callback si está definido
        if self.completion_callback:
            try:
                self.completion_callback(self)
            except Exception as e:
                logger.error(f"❌ Error en completion_callback: {e}")
    
    def error(self, error_message):
        """Marcar trabajo como error"""
        self.status = 'error'
        self.error_message = error_message
        self.end_time = time.time()
        
        # Llamar callback si está definido
        if self.error_callback:
            try:
                self.error_callback(self, error_message)
            except Exception as e:
                logger.error(f"❌ Error en error_callback: {e}")
    
    def get_duration(self):
        """Obtener duración del trabajo"""
        if self.start_time:
            end = self.end_time or time.time()
            return end - self.start_time
        return 0

class DownloadManager:
    """Gestor principal de descargas"""
    
    def __init__(self):
        self.active_jobs = {}
        self.job_counter = 0
    
    def create_job(self) -> DownloadJob:
        """Crear un nuevo trabajo de descarga"""
        self.job_counter += 1
        job_id = f"download_{self.job_counter}_{int(time.time())}"
        job = DownloadJob(job_id)
        self.active_jobs[job_id] = job
        return job
    
    def get_job(self, job_id: str) -> Optional[DownloadJob]:
        """Obtener trabajo por ID"""
        return self.active_jobs.get(job_id)
    
    def start_download(self, begin_time: str, end_time: str, empresa_filter: Dict = None) -> DownloadJob:
        """Iniciar nueva descarga"""
        job = self.create_job()
        
        # Iniciar descarga en thread separado
        thread = threading.Thread(
            target=self._background_download_process,
            args=(job, begin_time, end_time, empresa_filter),
            daemon=True
        )
        thread.start()
        
        logger.info(f"🚀 Descarga iniciada: {job.job_id}")
        return job
    
    def _background_download_process(self, job: DownloadJob, begin_time: str, end_time: str, empresa_filter: Dict = None):
        """Proceso de descarga en background"""
        try:
            job.status = 'running'
            job.start_time = time.time()
            job.update_progress(0, "Inicializando descarga...")
            
            # Inicializar estadísticas
            global_stats = DownloadStatistics()
            
            # Crear directorio base
            base_dir = get_config('download.base_directory', 'downloads/fotos')
            photos_dir = os.path.join(base_dir, 'security_photos')
            os.makedirs(photos_dir, exist_ok=True)
            
            job.update_progress(5, "Obteniendo información de fotos...")
            
            # Obtener primera página para conocer el total
            first_page_result = query_security_photos(begin_time, end_time, 1, 10)
            
            if not first_page_result or first_page_result.get('result') != 0:
                job.error('Error al obtener las fotos de seguridad')
                return
            
            pagination = first_page_result.get('pagination', {})
            total_records = pagination.get('totalRecords', 0)
            total_pages = pagination.get('totalPages', 0)
            
            if total_records == 0:
                job.complete(global_stats.get_summary(), [])
                return
            
            job.total_photos = total_records
            job.update_progress(10, f'Procesando {total_records} fotos en {total_pages} páginas...')
            
            all_photos = []
            
            # Procesar primera página
            self._process_photos_page_with_filter(
                first_page_result, photos_dir, all_photos, global_stats, empresa_filter, job
            )
            
            job.update_progress(15, f"Página 1/{total_pages} completada")
            
            # Procesar páginas restantes
            for page in range(2, total_pages + 1):
                page_result = query_security_photos(begin_time, end_time, page, 10)
                
                if not page_result or page_result.get('result') != 0:
                    logger.warning(f"⚠️ Error en página {page}, continuando...")
                    continue
                
                self._process_photos_page_with_filter(
                    page_result, photos_dir, all_photos, global_stats, empresa_filter, job
                )
                
                # Actualizar progreso
                progress = 15 + int((page / total_pages) * 80)  # 15-95%
                elapsed = time.time() - job.start_time
                estimated_total = (elapsed / page) * total_pages
                remaining = max(0, estimated_total - elapsed)
                
                job.update_progress(
                    progress,
                    f"Página {page}/{total_pages} - {len(all_photos)} fotos - "
                    f"Restante: {timedelta(seconds=int(remaining))}",
                    len(all_photos)
                )
            
            # Finalizar estadísticas
            global_stats.finalize()
            
            # Ordenar fotos
            all_photos.sort(key=lambda x: (int(x.get('vehiIdno', 0)), x.get('fileTimeStr', '')))
            
            # Log del reporte final
            logger.info(global_stats.get_final_report())
            
            # Completar trabajo
            elapsed = time.time() - job.start_time
            final_message = (
                f"✅ COMPLETADO: {len(all_photos)} fotos disponibles "
                f"({global_stats.descargadas} nuevas) - {str(timedelta(seconds=int(elapsed)))}"
            )
            
            job.update_progress(100, final_message, len(all_photos))
            job.complete(global_stats.get_summary(), all_photos)
            
        except Exception as e:
            logger.error(f"❌ Error en descarga: {e}", exc_info=True)
            job.error(f"Error en descarga: {str(e)}")
    
    def _process_photos_page_with_filter(self, page_result, photos_dir, all_photos, global_stats, empresa_filter, job):
        """Procesar página de fotos con filtro de empresa"""
        prephotos = page_result.get('infos', [])
        photos_to_download = []
        
        page_stats = {
            'total_procesadas': 0,
            'incluidas': 0,
            'excluidas': 0,
            'ya_existen': 0,
            'descargadas': 0,
            'errores': 0,
            'vehiculos': set(),
            'dispositivos': set()
        }
        
        # Aplicar filtro de empresa
        for photo in prephotos:
            page_stats['total_procesadas'] += 1
            
            try:
                devIdno_raw = photo.get('devIdno', '0')
                devIdno = int(str(devIdno_raw).replace('C', '').replace('c', ''))
                vehiIdno = str(photo.get('vehiIdno', ''))
                
                # Verificar filtro de empresa
                if empresa_filter:
                    fichas_validas = empresa_filter.get('vehiIdnos', [])
                    devices_validos = [str(d) for d in empresa_filter.get('devIdnos', [])]
                    
                    ficha_valida = vehiIdno in fichas_validas
                    device_valido = str(devIdno) in devices_validos
                    
                    if not (ficha_valida or device_valido):
                        page_stats['excluidas'] += 1
                        continue
                
                # La foto pasa el filtro
                photos_to_download.append(photo)
                page_stats['incluidas'] += 1
                page_stats['vehiculos'].add(vehiIdno)
                page_stats['dispositivos'].add(str(devIdno))
                
            except ValueError:
                page_stats['errores'] += 1
                logger.error(f"❌ Error interpretando devIdno: {photo.get('devIdno')}")
                continue
        
        # Descargar fotos en paralelo
        max_workers = get_config('download.max_workers', 15)
        
        def download_single_photo(photo_info):
            return self._download_photo_optimized(photo_info, photos_dir, page_stats)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(download_single_photo, photo) for photo in photos_to_download]
            
            for future in futures:
                try:
                    result = future.result(timeout=30)
                    if result:
                        all_photos.append(result)
                except Exception as e:
                    page_stats['errores'] += 1
                    logger.error(f"❌ Error en descarga individual: {e}")
        
        # Agregar estadísticas de página
        global_stats.add_page_stats(page_stats)
        
        # Log de página
        empresa_nombre = "Todas"
        if empresa_filter:
            empresa_nombre = empresa_filter['empresa_info']['nombre']
        
        logger.info(f"""
📊 ESTADÍSTICAS PÁGINA - {empresa_nombre}:
├── Total procesadas: {page_stats['total_procesadas']}
├── ✅ Incluidas: {page_stats['incluidas']}
├── 🚫 Excluidas: {page_stats['excluidas']}
├── ⏭️ Ya existían: {page_stats['ya_existen']}
├── 📥 Descargadas: {page_stats['descargadas']}
└── 💥 Errores: {page_stats['errores']}
""")
    
    def _download_photo_optimized(self, photo_info, photos_dir, page_stats):
        """Descargar foto individual optimizada"""
        try:
            vehiIdno = photo_info.get('vehiIdno')
            devIdno = photo_info.get('devIdno')
            fileTimeStr = photo_info.get('fileTimeStr')
            
            # Crear directorio del vehículo
            vehicle_folder = crear_nombre_carpeta_vehiculo(vehiIdno, devIdno)
            vehicle_dir = os.path.join(photos_dir, vehicle_folder)
            os.makedirs(vehicle_dir, exist_ok=True)
            
            # Generar nombre de archivo
            file_name = crear_nombre_archivo_foto(vehiIdno, devIdno, fileTimeStr)
            file_path = os.path.join(vehicle_dir, file_name)
            
            # Verificar si ya existe
            if verificar_archivo_existe(file_path):
                page_stats['ya_existen'] += 1
                photo_info['local_path'] = f"security_photos/{vehicle_folder}/{file_name}"
                return photo_info
            
            # Obtener URL de descarga
            download_url = photo_info.get('downloadUrl')
            if not download_url:
                file_path_api = photo_info.get('FPATH')
                if file_path_api:
                    base_url = get_config('gps.base_url', 'http://190.183.254.253:8088')
                    jsession = get_config('gps.current_session')
                    download_url = f"{base_url}/StandardApiAction_downloadFile.action?jsession={jsession}&filePath={file_path_api}"
                else:
                    page_stats['errores'] += 1
                    return None
            
            # Descargar
            if download_and_save_image(download_url, file_path):
                page_stats['descargadas'] += 1
                photo_info['local_path'] = f"security_photos/{vehicle_folder}/{file_name}"
                return photo_info
            else:
                page_stats['errores'] += 1
                return None
                
        except Exception as e:
            page_stats['errores'] += 1
            logger.error(f"💥 Error descargando {vehiIdno}-{devIdno}: {e}")
            return None

# Instancia global del gestor de descargas
download_manager = DownloadManager()

def start_download_job(begin_time: str, end_time: str, empresa_id: str = None) -> DownloadJob:
    """Función principal para iniciar una descarga"""
    
    # Obtener filtro de empresa si se especifica
    empresa_filter = None
    if empresa_id:
        # 🔧 FIX: Convertir a string y limpiar
        empresa_id_str = str(empresa_id).strip() if empresa_id else None
        if empresa_id_str:
            logger.info(f"🏢 Aplicando filtro por empresa ID: {empresa_id_str}")
            empresa_filter = obtener_vehiculos_por_empresa(empresa_id_str)
            
            if not empresa_filter:
                raise ValueError(f"No se pudo obtener información de la empresa {empresa_id_str}")
            
            if empresa_filter['empresa_info']['total_vehiculos'] == 0:
                raise ValueError(f"La empresa seleccionada no tiene vehículos activos")
    else:
        logger.info("🌐 Descarga sin filtro de empresa")
    
    # Iniciar descarga
    job = download_manager.start_download(begin_time, end_time, empresa_filter)
    
    return job

def get_download_job(job_id: str) -> Optional[DownloadJob]:
    """Obtener trabajo de descarga por ID"""
    return download_manager.get_job(job_id)

def get_active_jobs() -> Dict[str, DownloadJob]:
    """Obtener todos los trabajos activos"""
    return download_manager.active_jobs.copy()