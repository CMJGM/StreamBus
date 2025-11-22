"""
Clases para manejo de estadísticas de descarga de fotos de seguridad
"""
import time
import logging
from datetime import timedelta

logger = logging.getLogger('sit.views.stats')


class DownloadStatistics:
    """
    Clase para manejar estadísticas consolidadas de descarga de fotos
    """

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
        """
        Agrega estadísticas de una página al total consolidado

        Args:
            page_stats: Diccionario con estadísticas de la página
        """
        self.total_procesadas += page_stats.get('total_procesadas', 0)
        self.incluidas += page_stats.get('incluidas', 0)
        self.excluidas += page_stats.get('excluidas', 0)
        self.ya_existen += page_stats.get('ya_existen', 0)
        self.descargadas += page_stats.get('descargadas', 0)
        self.errores += page_stats.get('errores', 0)
        self.paginas_procesadas += 1

        # Agregar vehículos y dispositivos únicos si están disponibles
        if 'vehiculos' in page_stats:
            self.vehiculos_unicos.update(page_stats['vehiculos'])
        if 'dispositivos' in page_stats:
            self.dispositivos_unicos.update(page_stats['dispositivos'])

    def finalize(self):
        """Finaliza el conteo y calcula métricas finales"""
        self.end_time = time.time()

    def get_duration(self):
        """Retorna duración total del proceso"""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    def get_final_report(self):
        """
        Genera reporte final consolidado

        Returns:
            str: Reporte formateado para mostrar en logs
        """
        duration = self.get_duration()
        duration_str = str(timedelta(seconds=int(duration)))

        # Calcular porcentajes
        total_intentos = self.incluidas
        porcentaje_exito = (self.descargadas / total_intentos * 100) if total_intentos > 0 else 0
        porcentaje_ya_existian = (self.ya_existen / total_intentos * 100) if total_intentos > 0 else 0
        porcentaje_errores = (self.errores / total_intentos * 100) if total_intentos > 0 else 0

        # Velocidad de descarga
        velocidad = self.descargadas / duration if duration > 0 else 0

        report = f"""
╔═══════════════════════════════════════════════════════════════════════╗
║                    📊 ESTADÍSTICAS FINALES DE DESCARGA                ║
╠═══════════════════════════════════════════════════════════════════════╣
║                                                                       ║
║  📈 RESUMEN GENERAL:                                                  ║
║  ├── Total de fotos procesadas: {self.total_procesadas:,}                             ║
║  ├── ✅ Incluidas en filtrado: {self.incluidas:,}                               ║
║  ├── ❌ Excluidas por filtro: {self.excluidas:,}                                ║
║  └── 📄 Páginas procesadas: {self.paginas_procesadas}                                    ║
║                                                                       ║
║  🎯 RESULTADOS DE DESCARGA:                                           ║
║  ├── 📥 Descargadas nuevas: {self.descargadas:,} ({porcentaje_exito:.1f}%)                    ║
║  ├── ⏭️ Ya existían: {self.ya_existen:,} ({porcentaje_ya_existian:.1f}%)                         ║
║  ├── 💥 Errores: {self.errores:,} ({porcentaje_errores:.1f}%)                                   ║
║  └── ✅ Total disponibles: {self.ya_existen + self.descargadas:,}                         ║
║                                                                       ║
║  🚗 COBERTURA:                                                        ║
║  ├── 🚌 Vehículos únicos: {len(self.vehiculos_unicos)}                                  ║
║  └── 📱 Dispositivos únicos: {len(self.dispositivos_unicos)}                            ║
║                                                                       ║
║  ⏱️ RENDIMIENTO:                                                       ║
║  ├── 🕐 Tiempo total: {duration_str}                                  ║
║  ├── 🚀 Velocidad: {velocidad:.1f} fotos/segundo                            ║
║  └── 📊 Promedio por página: {self.incluidas/self.paginas_procesadas:.1f} fotos        ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
"""
        return report


class BasicOptimizedStats:
    """Clase básica para manejar estadísticas de descarga"""

    def __init__(self):
        self.stats = {
            'incluidas': 0,
            'excluidas': 0,
            'ya_existen': 0,
            'descargadas': 0,
            'errores': 0
        }
        self.start_time = time.time()
        self.end_time = None

    def update(self, key, value):
        """Actualizar estadística"""
        if key in self.stats:
            self.stats[key] += value

    def finalize(self):
        """Finalizar conteo"""
        self.end_time = time.time()

    def get_duration(self):
        """Obtener duración"""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    def get_summary(self):
        """Obtener resumen de estadísticas"""
        return {
            **self.stats,
            'duration': self.get_duration(),
            'total_disponibles': self.stats['descargadas'] + self.stats['ya_existen']
        }
