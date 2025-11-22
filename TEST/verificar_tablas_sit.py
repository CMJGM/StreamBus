import os
import sys
import django

# Configurar Django
sys.path.insert(0, r'E:\http\StreamBus')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'streambus.settings')
django.setup()

from django.db import connections

try:
    print("🔍 Verificando conexiones...\n")
    
    # Test base local
    conn_local = connections['default']
    with conn_local.cursor() as cursor:
        cursor.execute("SELECT DB_NAME()")
        db_name = cursor.fetchone()[0]
        print(f"✅ Base LOCAL conectada: {db_name}")
    
    # Test base SIT
    conn_sit = connections['SIT']
    with conn_sit.cursor() as cursor:
        cursor.execute("SELECT DB_NAME()")
        db_name = cursor.fetchone()[0]
        print(f"✅ Base SIT conectada: {db_name}\n")
        
        print("📋 Buscando tablas relevantes en SIT...\n")
        
        # Buscar tablas con nombres similares
        cursor.execute("""
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """)
        
        all_tables = cursor.fetchall()
        
        # Filtrar tablas que puedan ser relevantes
        keywords = ['sucursal', 'categor', 'bus', 'empleado', 'personal', 
                   'vehiculo', 'unidad', 'ficha', 'legajo']
        
        relevant_tables = []
        for table in all_tables:
            table_name = table[0].lower()
            for keyword in keywords:
                if keyword in table_name:
                    relevant_tables.append(table[0])
                    break
        
        if relevant_tables:
            print("📌 Tablas potencialmente relevantes:")
            for table in relevant_tables:
                print(f"   - {table}")
        
        # Mostrar todas las tablas si son pocas
        if len(all_tables) <= 50:
            print(f"\n📋 TODAS las tablas en SIT ({len(all_tables)} total):")
            for table in all_tables:
                print(f"   - {table[0]}")
        else:
            print(f"\n📋 Primeras 30 tablas de {len(all_tables)} en SIT:")
            for table in all_tables[:30]:
                print(f"   - {table[0]}")
                
        # Buscar columnas que contengan palabras clave
        print("\n🔍 Buscando columnas con nombres relevantes...")
        cursor.execute("""
            SELECT DISTINCT TABLE_NAME, COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE (COLUMN_NAME LIKE '%sucursal%'
                OR COLUMN_NAME LIKE '%categor%'
                OR COLUMN_NAME LIKE '%empleado%'
                OR COLUMN_NAME LIKE '%legajo%'
                OR COLUMN_NAME LIKE '%ficha%'
                OR COLUMN_NAME LIKE '%bus%'
                OR COLUMN_NAME LIKE '%vehiculo%')
            ORDER BY TABLE_NAME, COLUMN_NAME
        """)
        
        columns = cursor.fetchall()
        if columns:
            print("\n📌 Tablas con columnas relevantes:")
            current_table = None
            for table, column in columns:
                if table != current_table:
                    print(f"\n   Tabla: {table}")
                    current_table = table
                print(f"      - {column}")
                
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()