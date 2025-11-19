from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Prueba la integración con citos'
    
        # En sit/management/commands/test_citos.py
    def handle(self, *args, **options):
        self.stdout.write("🧪 Probando integración citos...")
        
        # Test con legacy forzado primero
        from django.conf import settings
        original_setting = getattr(settings, 'USE_CITOS_LIBRARY', False)
        
        try:
            # Forzar legacy
            settings.USE_CITOS_LIBRARY = False
            from sit.utils import obtener_ultima_ubicacion
            
            result = obtener_ultima_ubicacion('101')
            if result and result[0] is not None:
                self.stdout.write(self.style.SUCCESS(f'✅ Legacy OK: lat={result[0]}, lng={result[1]}'))
            
            # Ahora probar citos (solo si el usuario lo activó)
            if original_setting:
                settings.USE_CITOS_LIBRARY = True
                result = obtener_ultima_ubicacion('101')
                if result and result[0] is not None:
                    self.stdout.write(self.style.SUCCESS(f'✅ Citos OK: lat={result[0]}, lng={result[1]}'))
        
        finally:
            settings.USE_CITOS_LIBRARY = original_setting
        
        self.stdout.write("🏁 Testing completado")