import os
import re
from datetime import datetime

def fecha_mas_actual_jpg(carpeta_base):
    """
    Busca la fecha más actual en nombres de archivos JPG con formato yyyy-mm-dd_hh-mm-ss*.jpg
    en todas las subcarpetas de la carpeta especificada.
    
    Args:
        carpeta_base (str): Ruta de la carpeta base donde buscar
    
    Returns:
        datetime: Fecha más actual encontrada, o None si no hay archivos
    """
    patron = re.compile(r'(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2}).*\.jpg$', re.IGNORECASE)
    fecha_maxima = None
    
    for ruta, dirs, archivos in os.walk(carpeta_base):
        for archivo in archivos:
            match = patron.match(archivo)
            if match:
                try:
                    fecha = datetime(
                        int(match.group(1)),  # año
                        int(match.group(2)),  # mes
                        int(match.group(3)),  # día
                        int(match.group(4)),  # hora
                        int(match.group(5)),  # minuto
                        int(match.group(6))   # segundo
                    )
                    if fecha_maxima is None or fecha > fecha_maxima:
                        fecha_maxima = fecha
                except ValueError:
                    continue  # Ignorar fechas inválidas
    
    return fecha_maxima

# Ejemplo de uso:

carpeta = "e:/http/streambus/media/security_photos/"
fecha_reciente = fecha_mas_actual_jpg(carpeta)

if fecha_reciente:
    print(f"Fecha más actual encontrada: {fecha_reciente}")
    print(f"Formato legible: {fecha_reciente.strftime('%Y-%m-%d %H:%M:%S')}")
else:
    print("No se encontraron archivos con el formato especificado")