#!/usr/bin/env python
"""
Script para migrar fechas naive a timezone-aware en informes existentes
Ejecutar: python migrate_naive_datetimes.py
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'StreamBus.settings')
django.setup()

from django.utils.timezone import make_aware, is_naive
from informes.models import Informe

def migrate_naive_datetimes():
    """Convierte todas las fechas naive a timezone-aware"""

    print("Buscando informes con fechas naive...")

    informes_actualizados = 0
    informes_total = Informe.objects.count()

    for informe in Informe.objects.all():
        if informe.fecha_hora and is_naive(informe.fecha_hora):
            # Convertir a timezone-aware
            informe.fecha_hora = make_aware(informe.fecha_hora)
            informe.save(update_fields=['fecha_hora'])
            informes_actualizados += 1

            if informes_actualizados % 100 == 0:
                print(f"  Procesados {informes_actualizados} informes...")

    print(f"\n✓ Migración completada:")
    print(f"  - Total de informes: {informes_total}")
    print(f"  - Informes actualizados: {informes_actualizados}")
    print(f"  - Informes sin cambios: {informes_total - informes_actualizados}")

if __name__ == '__main__':
    try:
        migrate_naive_datetimes()
    except Exception as e:
        print(f"\n✗ Error durante migración: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
