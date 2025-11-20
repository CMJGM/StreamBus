from django.core.management.base import BaseCommand
from django.db import connections

class Command(BaseCommand):
    help = 'Verificar conexión y tablas en SIT'

    def handle(self, *args, **options):
        try:
            conn_sit = connections['SIT']
            with conn_sit.cursor() as cursor:
                cursor.execute("SELECT DB_NAME()")
                db_name = cursor.fetchone()[0]
                self.stdout.write(f"✅ Base SIT conectada: {db_name}\n")
                
                # Buscar todas las tablas
                cursor.execute("""
                    SELECT TABLE_NAME
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_TYPE = 'BASE TABLE'
                    ORDER BY TABLE_NAME
                """)
                
                all_tables = cursor.fetchall()
                
                self.stdout.write(f"📋 Total de tablas en SIT: {len(all_tables)}\n")
                
                # Buscar tablas relevantes
                keywords = ['sucursal', 'categor', 'bus', 'empleado', 'personal', 
                           'vehiculo', 'unidad', 'ficha', 'legajo']
                
                relevant = []
                for table in all_tables:
                    table_name = table[0].lower()
                    for keyword in keywords:
                        if keyword in table_name:
                            relevant.append(table[0])
                            break
                
                if relevant:
                    self.stdout.write("\n📌 Tablas potencialmente relevantes:")
                    for table in relevant:
                        self.stdout.write(f"   - {table}")
                
                # Mostrar todas si son pocas
                if len(all_tables) <= 40:
                    self.stdout.write(f"\n📋 TODAS las tablas:")
                    for table in all_tables:
                        self.stdout.write(f"   - {table[0]}")
                        
        except Exception as e:
            self.stdout.write(f"❌ Error: {e}")